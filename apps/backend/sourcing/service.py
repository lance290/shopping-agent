"""Sourcing service for orchestrating search and result persistence."""

import json
import logging
import re
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Bid, Row, Seller
from sourcing.models import NormalizedResult, ProviderStatusSnapshot, SearchIntent
from sourcing.repository import SourcingRepository
from sourcing.metrics import get_metrics_collector, log_search_start
from sourcing.scorer import score_results
from sourcing.filters import should_exclude_by_exclusions

logger = logging.getLogger(__name__)


class SourcingService:
    def __init__(self, session: AsyncSession, sourcing_repo: SourcingRepository):
        self.session = session
        self.repo = sourcing_repo

    @staticmethod
    def _parse_price_value(val) -> Optional[float]:
        """Parse a price value that might be a number, string like '>50', or None."""
        if val is None or val == "":
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # Be permissive: extract the first numeric token from free-form text
            # like ">$50", "$50, please", "minimum 50", etc.
            cleaned = re.sub(r"^[\s><=~$€£:]+", "", val.strip())
            if not cleaned:
                return None
            match = re.search(r"(-?\d[\d,]*(?:\.\d+)?)", cleaned)
            if not match:
                return None
            try:
                return float(match.group(1).replace(",", ""))
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _normalize_constraint_key(key: object) -> str:
        """Normalize choice/intent keys to a stable snake_case-like token."""
        return re.sub(r"[^a-z0-9]+", "_", str(key or "").strip().lower()).strip("_")

    def _parse_range_hint_value(self, val) -> tuple[Optional[float], Optional[float]]:
        """Parse range-style strings such as '>50', '<100', or '50-100'."""
        if val is None or val == "":
            return None, None

        if isinstance(val, (int, float)):
            # Bare numbers under generic budget/value fields are treated as max.
            return None, float(val)

        if not isinstance(val, str):
            return None, None

        raw = val.strip()
        if not raw:
            return None, None

        if raw[0] in (">", "≥"):
            return self._parse_price_value(raw), None
        if raw[0] in ("<", "≤"):
            return None, self._parse_price_value(raw)

        range_match = re.match(
            r"^\s*[^0-9]*([\d,]+(?:\.\d+)?)\s*[-–—]\s*[^0-9]*([\d,]+(?:\.\d+)?)\s*$",
            raw,
        )
        if range_match:
            lo = self._parse_price_value(range_match.group(1))
            hi = self._parse_price_value(range_match.group(2))
            return lo, hi

        lower = raw.lower()
        parsed = self._parse_price_value(raw)
        if parsed is None:
            return None, None

        if re.search(r"\b(over|above|at\s*least|min(?:imum)?)\b", lower):
            return parsed, None
        if re.search(r"\b(under|below|at\s*most|max(?:imum)?)\b", lower):
            return None, parsed

        return None, parsed

    def _extract_prices_from_mapping(self, payload: dict) -> tuple[Optional[float], Optional[float]]:
        """Extract min/max price from a dict with flexible key naming."""
        if not isinstance(payload, dict):
            return None, None

        normalized: dict[str, object] = {}
        for raw_key, raw_val in payload.items():
            key = self._normalize_constraint_key(raw_key)
            if key and key not in normalized:
                normalized[key] = raw_val

        min_price: Optional[float] = None
        max_price: Optional[float] = None

        min_keys = (
            "min_price",
            "price_min",
            "minimum_price",
            "min_budget",
            "budget_min",
            "minimum_budget",
            "min_value",
            "value_min",
            "minimum_value",
            "min_amount",
            "amount_min",
            "minimum_amount",
            "at_least",
        )
        max_keys = (
            "max_price",
            "price_max",
            "maximum_price",
            "max_budget",
            "budget_max",
            "maximum_budget",
            "max_value",
            "value_max",
            "maximum_value",
            "max_amount",
            "amount_max",
            "maximum_amount",
            "at_most",
        )

        for key in min_keys:
            parsed = self._parse_price_value(normalized.get(key))
            if parsed is not None:
                min_price = parsed
                break

        for key in max_keys:
            parsed = self._parse_price_value(normalized.get(key))
            if parsed is not None:
                max_price = parsed
                break

        priceish_tokens = {"price", "budget", "value", "amount", "cost"}
        min_hints = ("min", "minimum", "at_least", "from", "over", "above", "greater")
        max_hints = ("max", "maximum", "at_most", "to", "under", "below", "less")

        if min_price is None or max_price is None:
            for key, raw_val in normalized.items():
                parsed = self._parse_price_value(raw_val)
                if parsed is None:
                    continue

                has_priceish = any(tok in key for tok in priceish_tokens)
                if not has_priceish:
                    continue

                if min_price is None and any(h in key for h in min_hints):
                    min_price = parsed
                if max_price is None and any(h in key for h in max_hints):
                    max_price = parsed
                if min_price is not None and max_price is not None:
                    break

        # Generic fields can still carry encoded range hints (e.g. ">50", "50-100").
        if min_price is None or max_price is None:
            for key in ("price", "budget", "value", "amount", "cost", "gift_card_value"):
                if key not in normalized:
                    continue
                hint_min, hint_max = self._parse_range_hint_value(normalized.get(key))
                if min_price is None and hint_min is not None:
                    min_price = hint_min
                if max_price is None and hint_max is not None:
                    max_price = hint_max
                if min_price is not None and max_price is not None:
                    break

        return min_price, max_price

    @staticmethod
    def _extract_exclusions(row) -> tuple[List[str], List[str]]:
        """Extract LLM-populated exclude_keywords and exclude_merchants from row.search_intent."""
        if not row or not row.search_intent:
            return [], []
        try:
            si = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
            if isinstance(si, dict):
                return (
                    si.get("exclude_keywords") or [],
                    si.get("exclude_merchants") or [],
                )
        except Exception:
            pass
        return [], []

    @staticmethod
    def extract_vendor_query(row) -> Optional[str]:
        """Extract the LLM's clean product_name from search_intent for vendor vector search.

        The LLM distills 'jet to nashville' → product_name: 'Private jet charter'.
        Web providers get the full query (locations help find routes).
        Vendor provider gets the clean intent (no location noise in embeddings).
        """
        if not row or not row.search_intent:
            return None
        try:
            si = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
            if isinstance(si, dict):
                return si.get("product_name") or si.get("raw_input") or None
        except Exception:
            pass
        return None

    def _extract_price_constraints(self, row: Row) -> tuple[Optional[float], Optional[float]]:
        min_price: Optional[float] = None
        max_price: Optional[float] = None

        # 1. Check search_intent first (structured, most reliable)
        if row.search_intent:
            try:
                payload = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
                if isinstance(payload, dict):
                    min_price, max_price = self._extract_prices_from_mapping(payload)
            except Exception:
                pass

        # 2. Fallback to choice_answers (LLM/UI use varying key names)
        if row.choice_answers and (min_price is None or max_price is None):
            try:
                answers = json.loads(row.choice_answers) if isinstance(row.choice_answers, str) else row.choice_answers
                if isinstance(answers, dict):
                    fallback_min, fallback_max = self._extract_prices_from_mapping(answers)
                    if min_price is None:
                        min_price = fallback_min
                    if max_price is None:
                        max_price = fallback_max
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

        # 1. Execute Search with metrics tracking
        metrics = get_metrics_collector()
        log_search_start(row_id, query, providers or [])
        
        # Extract desire_tier and product_name for search context
        desire_tier = row.desire_tier if row else None

        # Extract clean product intent for vendor vector search.
        vendor_query = self.extract_vendor_query(row) if row else None

        with metrics.track_search(row_id=row_id, query=query):
            search_response = await self.repo.search_all_with_status(
                query,
                providers=providers,
                min_price=min_price,
                max_price=max_price,
                desire_tier=desire_tier,
                vendor_query=vendor_query,
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
        
        # Record result counts (no filtering — scorer handles ranking)
        metrics.record_price_filter(applied=False, dropped=0)
        metrics.record_results(
            total=len(search_response.results),
            unique=len(search_response.normalized_results),
            filtered=len(normalized_results)
        )

        logger.info(
            f"[SourcingService] Row {row_id}: Got {len(normalized_results)} normalized results from {len(provider_statuses)} providers"
        )

        # 2. Score & Rank Results (no filtering — only re-ranking)
        search_intent = self._parse_search_intent(row) if row else None
        normalized_results = score_results(
            normalized_results,
            intent=search_intent,
            min_price=min_price,
            max_price=max_price,
            desire_tier=desire_tier,
        )

        # 2b. Apply LLM-extracted exclusions (Amazon doesn't support negative keywords)
        exclude_kw, exclude_merchants = self._extract_exclusions(row)
        if exclude_kw or exclude_merchants:
            before = len(normalized_results)
            normalized_results = [
                r for r in normalized_results
                if not should_exclude_by_exclusions(
                    r.title, r.merchant_name, r.merchant_domain,
                    exclude_kw, exclude_merchants,
                )
            ]
            dropped = before - len(normalized_results)
            if dropped:
                logger.info(f"[SourcingService] Row {row_id}: Excluded {dropped} results by user exclusions (keywords={exclude_kw}, merchants={exclude_merchants})")

        # 3. Persist Results
        bids = await self._persist_results(row_id, normalized_results, row)
        
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

    @staticmethod
    def _safe_total_cost(price: Optional[float], shipping: Optional[float]) -> Optional[float]:
        """Compute total_cost without crashing on None values."""
        if price is None:
            return None
        return (price or 0.0) + (shipping or 0.0)

    async def _persist_results(self, row_id: int, results: List[NormalizedResult], row: Optional["Row"] = None) -> List[Bid]:
        """Persist normalized results as Bids, creating Sellers as needed. Returns list of Bids."""
        if not results:
            return []

        # Pre-resolve all sellers in a single pass to avoid mid-loop commits
        seller_cache: dict[str, Seller] = {}
        unique_merchants = {(r.merchant_name, r.merchant_domain) for r in results}
        for name, domain in unique_merchants:
            seller_cache[name] = await self._get_or_create_seller(name, domain)

        # Fetch existing bids to handle upserts (deduplication) — exclude superseded
        existing_bids_stmt = select(Bid).where(Bid.row_id == row_id, Bid.is_superseded == False)
        existing_bids_res = await self.session.exec(existing_bids_stmt)
        existing_bids = existing_bids_res.all()
        
        bids_by_canonical = {b.canonical_url: b for b in existing_bids if b.canonical_url}
        bids_by_url = {b.item_url: b for b in existing_bids if b.item_url}

        new_bids_count = 0
        updated_bids_count = 0

        for res in results:
            seller = seller_cache[res.merchant_name]
            
            existing_bid = None
            if res.canonical_url and res.canonical_url in bids_by_canonical:
                existing_bid = bids_by_canonical[res.canonical_url]
            elif res.url in bids_by_url:
                existing_bid = bids_by_url[res.url]

            provenance_json = self._build_enriched_provenance(res, row)

            score_data = res.provenance.get("score", {}) if res.provenance else {}
            combined_score = score_data.get("combined")
            price_score_val = score_data.get("price")
            relevance_score_val = score_data.get("relevance")
            quality_score_val = score_data.get("quality")
            diversity_bonus_val = score_data.get("diversity")

            source_tier = "marketplace"
            if res.source in ("seller_quote", "vendor_directory"):
                source_tier = "outreach"
            elif res.source == "registered_merchant":
                source_tier = "registered"

            if existing_bid:
                existing_bid.price = res.price if res.price is not None else existing_bid.price
                existing_bid.total_cost = self._safe_total_cost(existing_bid.price, existing_bid.shipping_cost)
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
                updated_bids_count += 1
            else:
                new_bid = Bid(
                    row_id=row_id,
                    vendor_id=seller.id,
                    price=res.price,
                    total_cost=self._safe_total_cost(res.price, 0.0),
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
                if new_bid.canonical_url:
                    bids_by_canonical[new_bid.canonical_url] = new_bid
                if new_bid.item_url:
                    bids_by_url[new_bid.item_url] = new_bid
                
                new_bids_count += 1

        await self.session.commit()
        
        # Authoritative reload: query ALL bids for this row from DB.
        # Never rely on in-memory object IDs which may be expired after async commit.
        stmt = (
            select(Bid)
            .where(Bid.row_id == row_id, Bid.is_superseded == False)
            .options(selectinload(Bid.seller))
            .order_by(Bid.combined_score.desc().nullslast(), Bid.id)
        )
        result = await self.session.exec(stmt)
        all_bids = list(result.all())
            
        logger.info(f"[SourcingService] Row {row_id}: Created {new_bids_count}, Updated {updated_bids_count}, Total {len(all_bids)} bids")
        return all_bids

    async def _get_or_create_seller(self, name: str, domain: str) -> Seller:
        stmt = select(Seller).where(Seller.name == name)
        result = await self.session.exec(stmt)
        seller = result.first()
        
        if not seller:
            seller = Seller(name=name, domain=domain)
            self.session.add(seller)
            await self.session.flush()  # Get ID without committing — avoids partial commits mid-loop
            
        return seller
