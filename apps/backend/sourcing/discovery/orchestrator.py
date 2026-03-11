"""DB-first vendor discovery orchestration."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator, Iterable, List, Optional, Sequence

from models import DiscoveredVendorCandidate, VendorEnrichmentQueueItem
from models.rows import Row
from sourcing.coverage import CoverageEvaluation, evaluate_internal_vendor_coverage
from sourcing.discovery.adapters.base import DiscoveryBatch
from sourcing.discovery.adapters.organic import OrganicDiscoveryAdapter
from sourcing.discovery.classifier import select_discovery_mode
from sourcing.discovery.classification import classify_candidates, enrich_candidates_for_classification
from sourcing.discovery.debug import build_discovery_audit_record
from sourcing.discovery.dedupe import dedupe_discovery_candidates
from sourcing.discovery.gating import gate_discovery_candidates
from sourcing.discovery.llm_rerank import rerank_gated_candidates
from sourcing.discovery.normalization import normalize_discovery_candidates
from sourcing.discovery.query_planner import build_discovery_queries
from sourcing.models import NormalizedResult, ProviderStatusSnapshot, SearchIntent
from sourcing.repository import SearchResult

logger = logging.getLogger(__name__)


class DiscoveryOrchestrator:
    def __init__(self, session, sourcing_service):
        self.session = session
        self.sourcing_service = sourcing_service
        self.adapters = [OrganicDiscoveryAdapter()]

    async def run_sync(
        self,
        *,
        row: Row,
        search_intent: SearchIntent,
        internal_results: Sequence[SearchResult],
    ) -> tuple[CoverageEvaluation, List[NormalizedResult], List[ProviderStatusSnapshot], Optional[str], str]:
        session_id = str(uuid.uuid4())
        evaluation = evaluate_internal_vendor_coverage(
            list(internal_results),
            high_risk=(row.desire_tier or "").strip().lower() in {"high_value", "advisory"},
        )
        logger.info(
            "[VendorDiscovery] coverage evaluated row=%s session=%s status=%s",
            row.id,
            session_id,
            evaluation.status,
        )
        if evaluation.status == "sufficient":
            return evaluation, [], [], None, session_id

        discovery_mode = select_discovery_mode(search_intent, row)
        queries = build_discovery_queries(search_intent, discovery_mode)
        normalized_results: List[NormalizedResult] = []
        statuses: List[ProviderStatusSnapshot] = []
        for batch in await self._run_batches(queries, discovery_mode):
            statuses.append(
                ProviderStatusSnapshot(
                    provider_id=f"vendor_discovery_{batch.adapter_id}",
                    status=batch.status if batch.status in {"ok", "error", "timeout", "exhausted", "rate_limited"} else "error",
                    result_count=len(batch.results),
                    latency_ms=batch.latency_ms,
                    message=batch.error_message,
                )
            )
            if batch.results:
                processed = await self._process_batch(
                    row=row,
                    discovery_session_id=session_id,
                    discovery_mode=discovery_mode,
                    query=batch.query,
                    search_intent=search_intent,
                    batch=batch,
                )
                normalized_results.extend(processed)

        # Run LLM-selected Apify Actors (if available)
        apify_batches = await self._run_apify_actors(
            query=queries[0] if queries else "",
            search_intent=search_intent,
            discovery_mode=discovery_mode,
            row=row,
        )
        for batch in apify_batches:
            statuses.append(
                ProviderStatusSnapshot(
                    provider_id=f"vendor_discovery_{batch.adapter_id}",
                    status=batch.status if batch.status in {"ok", "error", "timeout", "exhausted", "rate_limited"} else "error",
                    result_count=len(batch.results),
                    latency_ms=batch.latency_ms,
                    message=batch.error_message,
                )
            )
            if batch.results:
                processed = await self._process_batch(
                    row=row,
                    discovery_session_id=session_id,
                    discovery_mode=discovery_mode,
                    query=batch.query,
                    search_intent=search_intent,
                    batch=batch,
                )
                normalized_results.extend(processed)

        user_message = None
        if evaluation.status in {"borderline", "insufficient"}:
            user_message = "I'm expanding the search beyond our current vendor database."

        await self._persist_candidates(row, session_id, discovery_mode, queries, normalized_results)
        return evaluation, normalized_results, statuses, user_message, session_id

    async def stream(
        self,
        *,
        row: Row,
        search_intent: SearchIntent,
        internal_results: Sequence[SearchResult],
    ) -> AsyncGenerator[tuple[CoverageEvaluation, List[NormalizedResult], ProviderStatusSnapshot, str, str], None]:
        session_id = str(uuid.uuid4())
        evaluation = evaluate_internal_vendor_coverage(
            list(internal_results),
            high_risk=(row.desire_tier or "").strip().lower() in {"high_value", "advisory"},
        )
        if evaluation.status == "sufficient":
            return

        discovery_mode = select_discovery_mode(search_intent, row)
        queries = build_discovery_queries(search_intent, discovery_mode)
        async for batch in self._stream_batches(queries, discovery_mode):
            status = ProviderStatusSnapshot(
                provider_id=f"vendor_discovery_{batch.adapter_id}",
                status=batch.status if batch.status in {"ok", "error", "timeout", "exhausted", "rate_limited"} else "error",
                result_count=len(batch.results),
                latency_ms=batch.latency_ms,
                message=batch.error_message,
            )
            normalized_results = await self._process_batch(
                row=row,
                discovery_session_id=session_id,
                discovery_mode=discovery_mode,
                query=batch.query,
                search_intent=search_intent,
                batch=batch,
            )
            if normalized_results:
                await self._persist_candidates(row, session_id, discovery_mode, [batch.query], normalized_results)
            yield evaluation, normalized_results, status, session_id, discovery_mode

        # Stream Apify results after organic batches
        apify_batches = await self._run_apify_actors(
            query=queries[0] if queries else "",
            search_intent=search_intent,
            discovery_mode=discovery_mode,
            row=row,
        )
        for batch in apify_batches:
            status = ProviderStatusSnapshot(
                provider_id=f"vendor_discovery_{batch.adapter_id}",
                status=batch.status if batch.status in {"ok", "error", "timeout", "exhausted", "rate_limited"} else "error",
                result_count=len(batch.results),
                latency_ms=batch.latency_ms,
                message=batch.error_message,
            )
            normalized_results = await self._process_batch(
                row=row,
                discovery_session_id=session_id,
                discovery_mode=discovery_mode,
                query=batch.query,
                search_intent=search_intent,
                batch=batch,
            )
            if normalized_results:
                await self._persist_candidates(row, session_id, discovery_mode, [batch.query], normalized_results)
            yield evaluation, normalized_results, status, session_id, discovery_mode

    async def _run_batches(self, queries: Iterable[str], discovery_mode: str) -> List[DiscoveryBatch]:
        batches: List[DiscoveryBatch] = []
        for query in queries:
            for adapter in self.adapters:
                if discovery_mode not in adapter.supported_modes:
                    continue
                batches.append(
                    await adapter.search(
                        query,
                        discovery_mode=discovery_mode,
                        timeout_seconds=4.0,
                        max_results=5,
                    )
                )
        return batches

    async def _run_apify_actors(
        self,
        *,
        query: str,
        search_intent: SearchIntent,
        discovery_mode: str,
        row: Row,
    ) -> List[DiscoveryBatch]:
        """Ask LLM which Apify Actors to run, then execute them."""
        import os
        if not os.getenv("APIFY_API_TOKEN") or not query:
            return []

        try:
            from sourcing.discovery.adapters.apify import ApifyDiscoveryAdapter
            from sourcing.discovery.apify_selector import select_apify_actors

            # Build location hint from intent
            location_hint = ""
            if search_intent and search_intent.location_context:
                targets = search_intent.location_context.targets.non_empty_items()
                location_hint = " ".join(v for v in targets.values() if v)

            selection = await select_apify_actors(
                query=query,
                intent=search_intent,
                discovery_mode=discovery_mode,
                location_hint=location_hint,
            )

            if not selection.actors:
                return []

            adapter = ApifyDiscoveryAdapter()
            batches: List[DiscoveryBatch] = []
            for actor in selection.actors:
                logger.info(
                    "[VendorDiscovery] Running Apify actor=%s reason='%s'",
                    actor.actor_id, actor.reason,
                )
                batch = await adapter.run_actor(
                    actor_id=actor.actor_id,
                    run_input=actor.run_input,
                    query=query,
                    timeout_seconds=60.0,
                    max_results=10,
                )
                batches.append(batch)
            return batches

        except Exception as e:
            logger.warning("[VendorDiscovery] Apify actor execution failed: %s", e)
            return []

    async def _stream_batches(self, queries: Iterable[str], discovery_mode: str) -> AsyncGenerator[DiscoveryBatch, None]:
        for query in queries:
            for adapter in self.adapters:
                if discovery_mode not in adapter.supported_modes:
                    continue
                yield await adapter.search(
                    query,
                    discovery_mode=discovery_mode,
                    timeout_seconds=4.0,
                    max_results=5,
                )

    async def _process_batch(
        self,
        *,
        row: Row,
        discovery_session_id: str,
        discovery_mode: str,
        query: str,
        search_intent: SearchIntent,
        batch: DiscoveryBatch,
    ) -> List[NormalizedResult]:
        if not batch.results:
            return []
        deduped = dedupe_discovery_candidates(batch.results)
        await enrich_candidates_for_classification(deduped)
        classified = classify_candidates(
            deduped,
            discovery_mode=discovery_mode,
            intent=search_intent,
            row=row,
        )
        gated = gate_discovery_candidates(
            classified,
            discovery_mode=discovery_mode,
            intent=search_intent,
            row=row,
        )
        reranked, decisions = await rerank_gated_candidates(gated, intent=search_intent, row=row)
        for item in reranked:
            candidate_id = item.candidate.canonical_domain or item.candidate.url
            decision = decisions.get(candidate_id)
            if decision:
                item.candidate.trust_signals["llm_rerank_summary"] = decision.fit_summary
            logger.info(
                "[VendorDiscovery] %s",
                build_discovery_audit_record(
                    discovery_session_id=discovery_session_id,
                    discovery_mode=discovery_mode,
                    query=query,
                    candidate=item,
                    llm_summary=decision.fit_summary if decision else None,
                ),
            )
        admitted = [item for item in reranked if item.admissible]
        return normalize_discovery_candidates(admitted)

    async def _persist_candidates(
        self,
        row: Row,
        discovery_session_id: str,
        discovery_mode: str,
        queries: Sequence[str],
        results: Sequence[NormalizedResult],
    ) -> None:
        now = datetime.utcnow()
        for result in results:
            raw_data = result.raw_data if isinstance(result.raw_data, dict) else {}
            provenance = result.provenance if isinstance(result.provenance, dict) else {}
            confidence = float((provenance.get("score") or {}).get("combined", 0.7) or 0.7)
            candidate = DiscoveredVendorCandidate(
                row_id=row.id,
                user_id=row.user_id,
                discovery_session_id=discovery_session_id,
                adapter_id=str(provenance.get("source_provider") or "google_organic"),
                discovery_mode=discovery_mode,
                source_type=str(provenance.get("source_type") or raw_data.get("source_type") or "official_site"),
                source_query=queries[0] if queries else result.title,
                vendor_name=result.merchant_name,
                website_url=result.url,
                canonical_domain=result.merchant_domain or None,
                source_url=str(raw_data.get("source_url") or result.url),
                snippet=str(raw_data.get("snippet") or "") or None,
                image_url=result.image_url,
                email=raw_data.get("email"),
                phone=raw_data.get("phone"),
                location_hint=raw_data.get("location_hint"),
                official_site=bool(provenance.get("official_site") or raw_data.get("official_site")),
                first_party_contact=bool(provenance.get("first_party_contact") or raw_data.get("first_party_contact")),
                confidence=confidence,
                completeness_score=0.75 if (result.merchant_domain and (raw_data.get("email") or raw_data.get("phone") or result.url)) else 0.4,
                trust_score=0.8 if provenance.get("official_site") else 0.5,
                status="discovered",
                raw_payload=raw_data,
                extraction_payload=raw_data,
                provenance=provenance,
                created_at=now,
                updated_at=now,
            )
            self.session.add(candidate)
            await self.session.flush()
            if candidate.confidence >= 0.65 and candidate.completeness_score >= 0.65 and candidate.canonical_domain:
                self.session.add(
                    VendorEnrichmentQueueItem(
                        candidate_id=candidate.id,
                        row_id=row.id,
                        vendor_id=None,
                        discovery_session_id=discovery_session_id,
                        canonical_domain=candidate.canonical_domain,
                        discovery_mode=discovery_mode,
                        source_provider=candidate.adapter_id,
                        confidence=candidate.confidence,
                        completeness_score=candidate.completeness_score,
                        trust_score=candidate.trust_score,
                        status="queued",
                        payload={
                            "row_id": row.id,
                            "candidate_id": candidate.id,
                            "website_url": candidate.website_url,
                        },
                        created_at=now,
                        updated_at=now,
                    )
                )
        await self.session.commit()
