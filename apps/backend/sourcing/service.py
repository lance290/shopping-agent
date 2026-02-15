"""Sourcing service for orchestrating search and result persistence."""

import json
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import selectinload
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Bid, Row, Seller
from sourcing.models import NormalizedResult, ProviderStatusSnapshot, SearchIntent
from sourcing.repository import SourcingRepository
from sourcing.metrics import get_metrics_collector, log_search_start
from sourcing.scorer import score_results

logger = logging.getLogger(__name__)


class SourcingService:
    def __init__(self, session: AsyncSession, sourcing_repo: SourcingRepository):
        self.session = session
        self.repo = sourcing_repo

    def _extract_price_constraints(self, row: Row) -> tuple[Optional[float], Optional[float]]:
        min_price: Optional[float] = None
        max_price: Optional[float] = None

        if row.search_intent:
            try:
                payload = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
                if isinstance(payload, dict):
                    if payload.get("min_price") is not None:
                        min_price = float(payload["min_price"])
                    if payload.get("max_price") is not None:
                        max_price = float(payload["max_price"])
            except Exception:
                pass

        if (min_price is None and max_price is None) and row.choice_answers:
            try:
                answers = json.loads(row.choice_answers) if isinstance(row.choice_answers, str) else row.choice_answers
                if isinstance(answers, dict):
                    if answers.get("min_price") not in (None, ""):
                        min_price = float(answers["min_price"])
                    if answers.get("max_price") not in (None, ""):
                        max_price = float(answers["max_price"])
            except Exception:
                pass

        if min_price is not None and max_price is not None and min_price > max_price:
            min_price, max_price = max_price, min_price

        return min_price, max_price

    async def search_and_persist(
        self,
        row_id: int,
        query: str,
        providers: Optional[List[str]] = None,
    ) -> Tuple[List[Bid], List[ProviderStatusSnapshot], Optional[str]]:
        """
        Execute search across providers, normalize results, and persist them as Bids.
        
        Args:
            row_id: ID of the row to attach bids to
            query: Search query string
            providers: Optional list of provider IDs to use
            
        Returns:
            Tuple of (persisted_bids, provider_statuses)
        """
        # 0. Load row to extract constraints.
        row_stmt = select(Row).where(Row.id == row_id)
        row_res = await self.session.exec(row_stmt)
        row = row_res.first()
        min_price, max_price = self._extract_price_constraints(row) if row else (None, None)

        if row and max_price is not None:
            # Only hard-delete bids that exceed the budget ceiling (max_price).
            # Keep bids with no price and bids below min_price — scorer ranks them.
            # Protect liked/selected bids and service providers.
            await self.session.exec(
                delete(Bid).where(
                    Bid.row_id == row_id,
                    Bid.price > max_price,
                    Bid.source != "vendor_directory",
                    Bid.is_liked == False,
                    Bid.is_selected == False,
                )
            )
            await self.session.commit()

        # 1. Execute Search with metrics tracking
        metrics = get_metrics_collector()
        log_search_start(row_id, query, providers or [])
        
        with metrics.track_search(row_id=row_id, query=query):
            search_response = await self.repo.search_all_with_status(
                query,
                providers=providers,
                min_price=min_price,
                max_price=max_price,
            )

            normalized_results = search_response.normalized_results
            provider_statuses = search_response.provider_statuses
            user_message = search_response.user_message
            
            # Record provider metrics
            for status in provider_statuses:
                metrics.record_provider(
                    provider_id=status.provider_id,
                    status=status.status,
                    result_count=status.result_count,
                    latency_ms=status.latency_ms or 0,
                    error_message=status.message
                )
        
        # If no normalized results (e.g. legacy providers only), fallback to normalizing raw results
        if not normalized_results and search_response.results:
            # Fallback logic if needed, or rely on repo to handle normalization
            pass

        if max_price is not None:
            filtered: List[NormalizedResult] = []
            from sourcing.constants import NON_SHOPPING_SOURCES, SERVICE_SOURCES
            
            dropped_max = 0
            for res in normalized_results:
                # Allow non-shopping sources through (they don't have price data)
                if res.source in NON_SHOPPING_SOURCES or res.source in SERVICE_SOURCES:
                    filtered.append(res)
                    continue
                price = res.price
                # Keep results with no price — scorer will rank them lower
                if price is None or price <= 0:
                    filtered.append(res)
                    continue
                # Only hard-filter on max_price (budget ceiling).
                # min_price is aspirational — the scorer handles it via price_score.
                if price > max_price:
                    dropped_max += 1
                    continue
                filtered.append(res)
            logger.info(f"[SourcingService] Price filter: {len(normalized_results)} -> {len(filtered)} (dropped: max={dropped_max})")
            metrics.record_price_filter(applied=True, dropped=dropped_max)
            normalized_results = filtered
        else:
            metrics.record_price_filter(applied=False, dropped=0)

        # Record result counts
        metrics.record_results(
            total=len(search_response.results),
            unique=len(search_response.normalized_results),
            filtered=len(normalized_results)
        )

        logger.info(
            f"[SourcingService] Row {row_id}: Got {len(normalized_results)} normalized results from {len(provider_statuses)} providers"
        )

        # 2. Score & Rank Results
        search_intent = self._parse_search_intent(row) if row else None
        normalized_results = score_results(
            normalized_results,
            intent=search_intent,
            min_price=min_price,
            max_price=max_price,
        )

        # 3. Persist Results
        bids = await self._persist_results(row_id, normalized_results, row)
        
        # Record persistence metrics
        new_count = sum(1 for b in bids if not any(eb.id == b.id for eb in []))
        metrics.record_persistence(created=len(bids), updated=0)

        return bids, provider_statuses, user_message

    def _parse_search_intent(self, row: Row) -> Optional[SearchIntent]:
        """Parse SearchIntent from row's stored search_intent JSON."""
        if not row or not row.search_intent:
            return None
        try:
            payload = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
            if isinstance(payload, dict):
                return SearchIntent(**payload)
        except Exception as e:
            logger.debug(f"[SourcingService] Could not parse SearchIntent: {e}")
        return None

    def _build_enriched_provenance(self, res: NormalizedResult, row: Optional["Row"]) -> str:
        """Merge normalizer provenance with search intent context, choice factors, and chat excerpts."""
        provenance = dict(res.provenance) if res.provenance else {}

        # Ensure product_info exists
        product_info = provenance.get("product_info", {})
        if not isinstance(product_info, dict):
            product_info = {}
        if res.source and not product_info.get("source_provider"):
            product_info["source_provider"] = res.source
        provenance["product_info"] = product_info

        # Enrich matched_features from search intent
        matched_features = list(provenance.get("matched_features", []))
        if row and row.search_intent:
            try:
                intent = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
                if isinstance(intent, dict):
                    keywords = intent.get("keywords", [])
                    if keywords:
                        matched_features.append(f"Matches: {', '.join(keywords[:5])}")
                    brand = intent.get("brand")
                    if brand:
                        if not product_info.get("brand"):
                            product_info["brand"] = brand
                            provenance["product_info"] = product_info
                    features = intent.get("features", {})
                    if features:
                        for key, val in list(features.items())[:3]:
                            label = f"{key}: {val}" if not isinstance(val, list) else f"{key}: {', '.join(val)}"
                            matched_features.append(label)
            except (json.JSONDecodeError, TypeError):
                pass

        # Match against choice_answers for concrete "why this matches" signals
        if row and row.choice_answers:
            try:
                answers = json.loads(row.choice_answers) if isinstance(row.choice_answers, str) else row.choice_answers
                if isinstance(answers, dict):
                    price = res.price

                    # Budget check
                    budget = answers.get("max_price") or answers.get("max_budget") or answers.get("budget")
                    if budget and price and price > 0:
                        try:
                            budget_val = float(budget)
                            if price <= budget_val:
                                matched_features.append(f"Price ${price:.2f} is within your ${budget_val:.0f} budget")
                        except (ValueError, TypeError):
                            pass

                    # Brand check
                    pref_brand = answers.get("preferred_brand") or answers.get("brand")
                    product_brand = product_info.get("brand") or ""
                    if pref_brand and product_brand and str(pref_brand).lower() in str(product_brand).lower():
                        matched_features.append(f"Brand: {product_brand} (matches your preference)")

                    # Condition check
                    pref_condition = answers.get("condition")
                    product_condition = product_info.get("condition", "new")
                    if pref_condition and product_condition and str(pref_condition).lower() == str(product_condition).lower():
                        matched_features.append(f"Condition: {product_condition} (as requested)")

                    # Rating check
                    if hasattr(res, "rating") and res.rating and float(res.rating) >= 4.0:
                        matched_features.append(f"Highly rated: {res.rating}/5 stars")

                    # Free shipping check
                    if hasattr(res, "shipping_info") and res.shipping_info:
                        shipping_str = str(res.shipping_info).lower()
                        if "free" in shipping_str:
                            matched_features.append("Free shipping available")
            except (json.JSONDecodeError, TypeError):
                pass

        # Deduplicate matched features
        seen = set()
        unique_features = []
        for f in matched_features:
            if f not in seen:
                seen.add(f)
                unique_features.append(f)
        provenance["matched_features"] = unique_features

        # Extract chat excerpts from row
        if row and row.chat_history and not provenance.get("chat_excerpts"):
            try:
                chat = json.loads(row.chat_history) if isinstance(row.chat_history, str) else row.chat_history
                if isinstance(chat, list):
                    excerpts = []
                    for msg in chat:
                        if not isinstance(msg, dict):
                            continue
                        role = msg.get("role", "")
                        content = str(msg.get("content", ""))
                        if role in ("user", "assistant") and len(content) > 10:
                            excerpts.append({"role": role, "content": content[:200]})
                            if len(excerpts) >= 3:
                                break
                    if excerpts:
                        provenance["chat_excerpts"] = excerpts
            except (json.JSONDecodeError, TypeError):
                pass

        return json.dumps(provenance)

    async def _persist_results(self, row_id: int, results: List[NormalizedResult], row: Optional["Row"] = None) -> List[Bid]:
        """Persist normalized results as Bids, creating Sellers as needed. Returns list of Bids."""
        if not results:
            return []

        # Fetch existing bids to handle upserts (deduplication)
        # We assume canonical_url is the primary deduplication key if present, otherwise item_url
        existing_bids_stmt = select(Bid).where(Bid.row_id == row_id)
        existing_bids_res = await self.session.exec(existing_bids_stmt)
        existing_bids = existing_bids_res.all()
        
        # Map existing bids by canonical_url (preferred) and item_url (fallback)
        bids_by_canonical = {b.canonical_url: b for b in existing_bids if b.canonical_url}
        bids_by_url = {b.item_url: b for b in existing_bids if b.item_url}

        processed_bids: List[Bid] = []
        new_bids_count = 0
        updated_bids_count = 0

        for res in results:
            # 2.1 Get or Create Seller
            seller = await self._get_or_create_seller(res.merchant_name, res.merchant_domain)
            
            # 2.2 Check for existing bid
            existing_bid = None
            if res.canonical_url and res.canonical_url in bids_by_canonical:
                existing_bid = bids_by_canonical[res.canonical_url]
            elif res.url in bids_by_url:
                existing_bid = bids_by_url[res.url]

            provenance_json = self._build_enriched_provenance(res, row)

            # Extract score dimensions from provenance (PRD 11)
            score_data = res.provenance.get("score", {}) if res.provenance else {}
            combined_score = score_data.get("combined")
            price_score_val = score_data.get("price")
            relevance_score_val = score_data.get("relevance")
            quality_score_val = score_data.get("quality")
            diversity_bonus_val = score_data.get("diversity")

            # Determine source tier
            source_tier = "marketplace"  # default
            if res.source in ("seller_quote", "vendor_directory"):
                source_tier = "outreach"
            elif res.source == "registered_merchant":
                source_tier = "registered"

            if existing_bid:
                # Update
                existing_bid.price = res.price if res.price is not None else existing_bid.price
                existing_bid.total_cost = existing_bid.price + existing_bid.shipping_cost
                existing_bid.currency = res.currency
                existing_bid.item_title = res.title
                existing_bid.image_url = res.image_url
                existing_bid.source = res.source
                existing_bid.vendor_id = seller.id
                existing_bid.canonical_url = res.canonical_url
                existing_bid.provenance = provenance_json
                existing_bid.combined_score = combined_score
                existing_bid.price_score = price_score_val
                existing_bid.relevance_score = relevance_score_val
                existing_bid.quality_score = quality_score_val
                existing_bid.diversity_bonus = diversity_bonus_val
                existing_bid.source_tier = source_tier
                
                self.session.add(existing_bid)
                processed_bids.append(existing_bid)
                updated_bids_count += 1
            else:
                # Create
                new_bid = Bid(
                    row_id=row_id,
                    vendor_id=seller.id,
                    price=res.price or 0.0,
                    total_cost=res.price or 0.0,
                    currency=res.currency,
                    item_title=res.title,
                    item_url=res.url,
                    image_url=res.image_url,
                    source=res.source,
                    canonical_url=res.canonical_url,
                    is_selected=False,
                    provenance=provenance_json,
                    combined_score=combined_score,
                    price_score=price_score_val,
                    relevance_score=relevance_score_val,
                    quality_score=quality_score_val,
                    diversity_bonus=diversity_bonus_val,
                    source_tier=source_tier,
                )
                self.session.add(new_bid)
                # Add to maps to prevent duplicates within the same batch
                if new_bid.canonical_url:
                    bids_by_canonical[new_bid.canonical_url] = new_bid
                bids_by_url[new_bid.item_url] = new_bid
                
                processed_bids.append(new_bid)
                new_bids_count += 1

        await self.session.commit()
        
        # Reload bids with eager loading to avoid MissingGreenlet error on relationship access
        if not processed_bids:
            return []
            
        bid_ids = [b.id for b in processed_bids if b.id is not None]
        if not bid_ids:
            return []
            
        stmt = select(Bid).where(Bid.id.in_(bid_ids)).options(selectinload(Bid.seller))
        result = await self.session.exec(stmt)
        reloaded_bids = result.all()
            
        logger.info(f"[SourcingService] Row {row_id}: Created {new_bids_count}, Updated {updated_bids_count} bids")
        return list(reloaded_bids)

    async def _get_or_create_seller(self, name: str, domain: str) -> Seller:
        # Simple cache could be added here if needed for batch processing
        stmt = select(Seller).where(Seller.name == name)
        result = await self.session.exec(stmt)
        seller = result.first()
        
        if not seller:
            seller = Seller(name=name, domain=domain)
            self.session.add(seller)
            await self.session.commit()
            await self.session.refresh(seller)
            
        return seller
