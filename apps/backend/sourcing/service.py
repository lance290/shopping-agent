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

    @staticmethod
    def _parse_price_value(val) -> Optional[float]:
        """Parse a price value that might be a number, string like '>50', or None."""
        if val is None or val == "":
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # Strip currency symbols, comparison operators, whitespace
            cleaned = val.strip().lstrip("><=~$€£").strip()
            if not cleaned:
                return None
            try:
                return float(cleaned.replace(",", ""))
            except (ValueError, TypeError):
                return None
        return None

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
                    if payload.get("min_price") is not None:
                        min_price = float(payload["min_price"])
                    if payload.get("max_price") is not None:
                        max_price = float(payload["max_price"])
            except Exception:
                pass

        # 2. Fallback to choice_answers (LLM uses varying key names)
        if (min_price is None and max_price is None) and row.choice_answers:
            try:
                answers = json.loads(row.choice_answers) if isinstance(row.choice_answers, str) else row.choice_answers
                if isinstance(answers, dict):
                    # Try all known key variants for min price
                    for key in ("min_price", "price_min", "minimum_price"):
                        v = self._parse_price_value(answers.get(key))
                        if v is not None:
                            min_price = v
                            break

                    # Try all known key variants for max price
                    for key in ("max_price", "price_max", "maximum_price"):
                        v = self._parse_price_value(answers.get(key))
                        if v is not None:
                            max_price = v
                            break

                    # Handle generic "price" key (e.g. ">50", "<100", "50-100")
                    if min_price is None and max_price is None:
                        price_val = answers.get("price")
                        if isinstance(price_val, str) and price_val.strip():
                            p = price_val.strip()
                            if p.startswith(">"):
                                min_price = self._parse_price_value(p)
                            elif p.startswith("<"):
                                max_price = self._parse_price_value(p)
                            elif "-" in p:
                                parts = p.split("-", 1)
                                min_price = self._parse_price_value(parts[0])
                                max_price = self._parse_price_value(parts[1])
                        elif isinstance(price_val, (int, float)):
                            max_price = float(price_val)
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
        
        # If no normalized results (e.g. legacy providers only), fallback to normalizing raw results
        if not normalized_results and search_response.results:
            # Fallback logic if needed, or rely on repo to handle normalization
            pass

        # Unified price/source filtering
        from sourcing.filters import should_include_result
        desire_tier = row.desire_tier if row else None
        if min_price is not None or max_price is not None:
            filtered: List[NormalizedResult] = []
            dropped = 0
            for res in normalized_results:
                if should_include_result(
                    price=res.price,
                    source=res.source,
                    desire_tier=desire_tier,
                    min_price=min_price,
                    max_price=max_price,
                ):
                    filtered.append(res)
                else:
                    dropped += 1
            logger.info(f"[SourcingService] Price filter: {len(normalized_results)} -> {len(filtered)} (dropped={dropped})")
            metrics.record_price_filter(applied=True, dropped=dropped)
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
        desire_tier = row.desire_tier if row else None
        normalized_results = score_results(
            normalized_results,
            intent=search_intent,
            min_price=min_price,
            max_price=max_price,
            desire_tier=desire_tier,
        )

        # 2b. Quantum re-ranking (for results with embeddings)
        try:
            from sourcing.quantum.reranker import QuantumReranker
            if not hasattr(self, '_quantum_reranker'):
                self._quantum_reranker = QuantumReranker()
            reranker = self._quantum_reranker
            if reranker.is_available() and row:
                # Build result dicts with embeddings for quantum scoring, keyed by index
                results_for_quantum = []
                for idx, res in enumerate(normalized_results):
                    rd = {
                        "_idx": idx,
                        "title": res.title,
                        "embedding": res.raw_data.get("embedding") if res.raw_data else None,
                    }
                    results_for_quantum.append(rd)

                # Get query embedding from search intent
                query_emb = None
                if row.search_intent:
                    try:
                        intent_data = json.loads(row.search_intent) if isinstance(row.search_intent, str) else row.search_intent
                        query_emb = intent_data.get("query_embedding")
                    except Exception:
                        pass

                if query_emb and any(r.get("embedding") for r in results_for_quantum):
                    reranked = await reranker.rerank_results(
                        query_embedding=query_emb,
                        search_results=results_for_quantum,
                        top_k=len(normalized_results),
                    )
                    # Apply quantum scores back using the _idx key to match correctly
                    score_map = {}
                    for r in reranked:
                        if r.get("quantum_reranked") and "_idx" in r:
                            score_map[r["_idx"]] = r
                    for idx, res in enumerate(normalized_results):
                        if idx in score_map:
                            qr = score_map[idx]
                            res.provenance["quantum_score"] = qr.get("quantum_score", 0.0)
                            res.provenance["blended_score"] = qr.get("blended_score", 0.0)
                            res.provenance["novelty_score"] = qr.get("novelty_score", 0.0)
                            res.provenance["coherence_score"] = qr.get("coherence_score", 0.0)
                    logger.info(f"[SourcingService] Quantum reranking applied to {len(score_map)} results")
        except ImportError:
            pass  # Quantum module not available — classical scoring only
        except Exception as e:
            logger.warning(f"[SourcingService] Quantum reranking failed (graceful degradation): {e}")

        # 2c. Constraint satisfaction scoring
        if row and row.structured_constraints:
            try:
                from sourcing.quantum.constraint_scorer import constraint_satisfaction_score
                constraints = json.loads(row.structured_constraints) if isinstance(row.structured_constraints, str) else row.structured_constraints
                if isinstance(constraints, dict) and constraints:
                    for res in normalized_results:
                        result_data = {"title": res.title, "raw_data": res.raw_data}
                        c_score = constraint_satisfaction_score(result_data, constraints)
                        res.provenance["constraint_score"] = round(c_score, 4)
                    logger.info(f"[SourcingService] Constraint scoring applied to {len(normalized_results)} results")
            except Exception as e:
                logger.warning(f"[SourcingService] Constraint scoring failed: {e}")

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

        # Fetch existing bids to handle upserts (deduplication)
        existing_bids_stmt = select(Bid).where(Bid.row_id == row_id)
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
            .where(Bid.row_id == row_id)
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
