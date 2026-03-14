"""Sourcing service for orchestrating search and result persistence."""

import json
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Bid, Row
from models.auth import User
from sourcing.discovery.classifier import classify_search_path, execution_mode_for_row
from sourcing.models import NormalizedResult, ProviderStatusSnapshot, SearchIntent  # noqa: F401 — re-exported
from sourcing.repository import SourcingRepository
from sourcing.metrics import get_metrics_collector, log_search_start
from sourcing.scorer import filter_vendor_results, score_results
from sourcing.vendor_provider import build_query_embedding
from sourcing.service_helpers import (
    extract_vendor_query,
    extract_price_constraints,
    build_endorsement_boosts,
    parse_search_intent,
    resolve_search_locations,
)
from sourcing.service_persist import (
    persist_results,
    safe_total_cost,
    filter_discovery_results_for_bid_persistence,
)
from sourcing.service_routes import (
    search_internal_vendors_only,
    search_vendor_discovery_path,
    search_hybrid_path,
)

logger = logging.getLogger(__name__)


class SourcingService:
    def __init__(self, session: AsyncSession, sourcing_repo: SourcingRepository):
        self.session = session
        self.repo = sourcing_repo

    @staticmethod
    def extract_vendor_query(row) -> Optional[str]:
        return extract_vendor_query(row)

    def _extract_price_constraints(self, row: Row) -> tuple[Optional[float], Optional[float]]:
        return extract_price_constraints(row)

    async def _build_endorsement_boosts(self, user_id: Optional[int]) -> dict[int, float]:
        return await build_endorsement_boosts(self.session, user_id)

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
            # Instead of hard-deleting, we supersede bids that exceed the budget ceiling (max_price).
            # Keep bids with no price and bids below min_price — scorer ranks them.
            # Protect liked/selected bids and service providers.
            from sqlalchemy import update as sql_update
            await self.session.exec(
                sql_update(Bid).where(
                    Bid.row_id == row_id,
                    Bid.price > max_price,
                    Bid.source != "vendor_directory",
                    Bid.is_liked == False,
                    Bid.is_selected == False,
                    Bid.is_superseded == False,
                ).values(is_superseded=True, superseded_at=datetime.utcnow())
            )
            await self.session.commit()

        # 1. Execute Search with metrics tracking
        metrics = get_metrics_collector()
        log_search_start(row_id, query, providers or [])
        
        # Extract desire_tier for logging/repo context
        desire_tier = row.desire_tier if row else None
        search_intent = self._parse_search_intent(row) if row else None
        if row and search_intent:
            search_intent = await self._resolve_search_locations(row, search_intent)
        vendor_query = self.extract_vendor_query(row) if row else None
        intent_payload = search_intent.model_dump() if search_intent else None
        query_embedding = None
        selected_provider_ids = None
        should_precompute_vendor_embedding = True

        if providers:
            raw_provider_ids = [str(p).strip() for p in providers if str(p).strip()]
            normalizer = getattr(self.repo, "_normalize_provider_filter", None)
            if callable(normalizer):
                try:
                    selected_provider_ids = normalizer(raw_provider_ids)
                except Exception:
                    selected_provider_ids = set(raw_provider_ids)
            else:
                selected_provider_ids = set(raw_provider_ids)
            should_precompute_vendor_embedding = "vendor_directory" in selected_provider_ids

        if should_precompute_vendor_embedding:
            try:
                query_embedding = await build_query_embedding(
                    vendor_query or query,
                    context_query=query,
                    intent_payload=intent_payload,
                )
            except Exception as e:
                logger.warning(f"[SourcingService] Query embedding failed (graceful degradation): {e}")

        search_path = classify_search_path(search_intent, row)
        resolved_mode = execution_mode_for_row(search_intent, row)

        # Persist routing_mode for trust-metric analysis (Trust Metrics PRD §7.1)
        if row:
            if row.routing_mode != resolved_mode:
                row.routing_mode = resolved_mode
                self.session.add(row)
                await self.session.commit()

        # --- Phase 2: Adapter-family enforcement ---
        # sourcing_only: only vendor discovery, no affiliate marketplace providers
        # affiliate_only: only affiliate/marketplace providers, no vendor discovery
        # affiliate_plus_sourcing: both adapter families run
        if resolved_mode == "sourcing_only" and row and search_intent:
            return await self._search_vendor_discovery_path(
                row=row,
                query=query,
                providers=providers,
                min_price=min_price,
                max_price=max_price,
                search_intent=search_intent,
                vendor_query=vendor_query,
                query_embedding=query_embedding,
            )

        if resolved_mode == "affiliate_plus_sourcing" and row and search_intent:
            return await self._search_hybrid_path(
                row=row,
                query=query,
                providers=providers,
                min_price=min_price,
                max_price=max_price,
                search_intent=search_intent,
                vendor_query=vendor_query,
                query_embedding=query_embedding,
            )

        # affiliate_only (or fallback): run commodity marketplace path
        # Exclude vendor_directory from affiliate-only searches
        if resolved_mode == "affiliate_only" and not providers:
            repo_providers = getattr(self.repo, "providers", None)
            if repo_providers:
                providers = [pid for pid in repo_providers if pid != "vendor_directory"]

        # Resolve user's zip_code for location-aware providers (Kroger, etc.)
        user_zip: Optional[str] = None
        if row and row.user_id:
            try:
                user_res = await self.session.exec(
                    select(User.zip_code).where(User.id == row.user_id)
                )
                user_zip = user_res.first()
            except Exception:
                pass

        with metrics.track_search(row_id=row_id, query=query):
            search_response = await self.repo.search_all_with_status(
                query,
                providers=providers,
                min_price=min_price,
                max_price=max_price,
                desire_tier=desire_tier,
                zip_code=user_zip,
                vendor_query=vendor_query,
                intent_payload=intent_payload,
                query_embedding=query_embedding,
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
        desire_tier = row.desire_tier if row else None
        normalized_results = score_results(
            normalized_results,
            intent=search_intent,
            min_price=min_price,
            max_price=max_price,
            desire_tier=desire_tier,
            is_service=row.is_service if row else None,
            service_category=row.service_category if row else None,
        )
        normalized_results = filter_vendor_results(
            normalized_results,
            intent=search_intent,
            is_service=row.is_service if row else None,
            service_category=row.service_category if row else None,
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

                if query_embedding and any(r.get("embedding") for r in results_for_quantum):
                    reranked = await reranker.rerank_results(
                        query_embedding=query_embedding,
                        search_results=results_for_quantum,
                        top_k=len(normalized_results),
                    )
                elif not query_embedding and any(r.get("embedding") for r in results_for_quantum):
                    try:
                        query_embedding = await build_query_embedding(
                            vendor_query or query,
                            context_query=query,
                            intent_payload=intent_payload,
                        )
                    except Exception as e:
                        logger.warning(f"[SourcingService] Lazy query embedding failed for quantum reranking: {e}")
                    if query_embedding:
                        reranked = await reranker.rerank_results(
                            query_embedding=query_embedding,
                            search_results=results_for_quantum,
                            top_k=len(normalized_results),
                        )
                    else:
                        reranked = None
                else:
                    reranked = None
                if reranked:
                    # Write scores back to NormalizedResult.provenance
                    idx_map = {r["title"]: r for r in reranked}
                    for res in normalized_results:
                        qr = idx_map.get(res.title)
                        if qr:
                            res.provenance["quantum_score"] = qr.get("quantum_score")
                            res.provenance["classical_score"] = qr.get("classical_score")
                            res.provenance["novelty_score"] = qr.get("novelty_score")
                            res.provenance["coherence_score"] = qr.get("coherence_score")
                            res.provenance["blended_score"] = qr.get("blended_score")
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

    async def search_internal_vendors_only(self, **kwargs):
        return await search_internal_vendors_only(self.repo, **kwargs)

    async def _search_vendor_discovery_path(self, **kwargs):
        endorsement_boosts = await self._build_endorsement_boosts(kwargs.get("row") and kwargs["row"].user_id)
        return await search_vendor_discovery_path(
            self.session, self.repo, self,
            endorsement_boosts=endorsement_boosts,
            **kwargs,
        )

    async def _search_hybrid_path(self, **kwargs):
        endorsement_boosts = await self._build_endorsement_boosts(kwargs.get("row") and kwargs["row"].user_id)
        return await search_hybrid_path(
            self.session, self.repo, self,
            endorsement_boosts=endorsement_boosts,
            **kwargs,
        )

    def _parse_search_intent(self, row: Row) -> Optional[SearchIntent]:
        return parse_search_intent(row)

    async def _resolve_search_locations(self, row: Row, intent: SearchIntent) -> SearchIntent:
        return await resolve_search_locations(self.session, row, intent)

    async def _persist_results(self, row_id, results, row=None):
        return await persist_results(self.session, row_id, results, row)

    @staticmethod
    def _safe_total_cost(price, shipping):
        return safe_total_cost(price, shipping)

    @staticmethod
    def _build_enriched_provenance(res, row):
        from sourcing.provenance import build_enriched_provenance
        return build_enriched_provenance(res, row)

    @staticmethod
    def _filter_discovery_results_for_bid_persistence(row, results):
        return filter_discovery_results_for_bid_persistence(row, results)

    async def supersede_stale_bids(self, row_id: int, keep_bid_ids: set[int]) -> int:
        """Supersede bids that were NOT part of the latest search results.

        Called AFTER persist so that only truly stale bids are retired.
        Liked/selected bids are always preserved.

        Returns the number of bids superseded.
        """
        from sqlalchemy import update as sql_update

        result = await self.session.exec(
            sql_update(Bid).where(
                Bid.row_id == row_id,
                Bid.id.notin_(keep_bid_ids) if keep_bid_ids else True,
                Bid.is_liked == False,
                Bid.is_selected == False,
                Bid.is_superseded == False,
            ).values(is_superseded=True, superseded_at=datetime.utcnow())
        )
        await self.session.commit()
        count = result.rowcount  # type: ignore[union-attr]
        if count:
            logger.info(f"[SourcingService] Row {row_id}: Superseded {count} stale bids (kept {len(keep_bid_ids)})")
        return count

