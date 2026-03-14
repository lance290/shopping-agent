"""Execution-path routing for vendor discovery and hybrid search modes."""

import asyncio
import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Bid, Row
from models.auth import User
from sourcing.discovery.orchestrator import DiscoveryOrchestrator
from sourcing.filters import should_include_result
from sourcing.metrics import get_metrics_collector
from sourcing.models import NormalizedResult, ProviderStatusSnapshot, SearchIntent
from sourcing.reranker import should_rerank, rerank_candidates
from sourcing.repository import SourcingRepository
from sourcing.scorer import filter_vendor_results, score_results
from sourcing.service_persist import (
    filter_discovery_results_for_bid_persistence,
    persist_results,
)

logger = logging.getLogger(__name__)


async def search_internal_vendors_only(
    repo: SourcingRepository,
    *,
    query: str,
    vendor_query: Optional[str],
    intent_payload: Optional[dict],
    query_embedding: Optional[List[float]],
):
    return await repo.search_all_with_status(
        query,
        providers=["vendor_directory"],
        vendor_query=vendor_query,
        intent_payload=intent_payload,
        query_embedding=query_embedding,
    )


async def search_vendor_discovery_path(
    session: AsyncSession,
    repo: SourcingRepository,
    service_ref,
    *,
    row: Row,
    query: str,
    providers: Optional[List[str]],
    min_price: Optional[float],
    max_price: Optional[float],
    search_intent: SearchIntent,
    vendor_query: Optional[str],
    query_embedding: Optional[List[float]],
    endorsement_boosts: dict[int, float],
) -> Tuple[List[Bid], List[ProviderStatusSnapshot], Optional[str]]:
    intent_payload = search_intent.model_dump()
    internal_response = await search_internal_vendors_only(
        repo,
        query=query,
        vendor_query=vendor_query,
        intent_payload=intent_payload,
        query_embedding=query_embedding,
    )
    internal_results = internal_response.results
    internal_statuses = list(internal_response.provider_statuses)
    normalized_internal = internal_response.normalized_results
    if normalized_internal:
        normalized_internal = score_results(
            normalized_internal,
            intent=search_intent,
            min_price=min_price,
            max_price=max_price,
            desire_tier=row.desire_tier,
            is_service=row.is_service,
            service_category=row.service_category,
            endorsement_boosts=endorsement_boosts,
        )
        normalized_internal = filter_vendor_results(
            normalized_internal,
            intent=search_intent,
            is_service=row.is_service,
            service_category=row.service_category,
        )
        if normalized_internal and should_rerank(search_intent, row.desire_tier, row.routing_mode):
            normalized_internal = await rerank_candidates(query, normalized_internal, search_intent)
        keep_vendor_ids = {
            int(result.raw_data["vendor_id"])
            for result in normalized_internal
            if isinstance(result.raw_data, dict) and result.raw_data.get("vendor_id") is not None
        }
        internal_results = [
            result
            for result in internal_results
            if getattr(result, "vendor_id", None) in keep_vendor_ids
        ]

    bids: List[Bid] = []
    if normalized_internal:
        bids = await persist_results(session, row.id, normalized_internal, row=row)

    orchestrator = DiscoveryOrchestrator(session, service_ref)
    evaluation, discovery_results, discovery_statuses, user_message, session_id = await orchestrator.run_sync(
        row=row,
        search_intent=search_intent,
        internal_results=internal_results,
    )

    if discovery_results:
        for result in discovery_results:
            result.provenance["discovery_session_id"] = session_id
        persisted_discovery = await persist_results(
            session,
            row.id,
            filter_discovery_results_for_bid_persistence(row, discovery_results),
            row=row,
        )
        keep_ids = {bid.id for bid in bids if bid.id is not None}
        keep_ids.update({bid.id for bid in persisted_discovery if bid.id is not None})
        if keep_ids:
            all_bids_stmt = (
                select(Bid)
                .where(Bid.row_id == row.id, Bid.id.in_(keep_ids))
                .options(selectinload(Bid.seller))
                .order_by(Bid.combined_score.desc().nullslast(), Bid.id)
            )
            all_bids_res = await session.exec(all_bids_stmt)
            bids = list(all_bids_res.all())

    all_statuses = internal_statuses + list(discovery_statuses)
    if evaluation.status in {"borderline", "insufficient"} and not user_message:
        user_message = "I'm expanding the search beyond our current vendor database."

    return bids, all_statuses, user_message


async def search_hybrid_path(
    session: AsyncSession,
    repo: SourcingRepository,
    service_ref,
    *,
    row: Row,
    query: str,
    providers: Optional[List[str]],
    min_price: Optional[float],
    max_price: Optional[float],
    search_intent: SearchIntent,
    vendor_query: Optional[str],
    query_embedding: Optional[List[float]],
    endorsement_boosts: dict[int, float],
) -> Tuple[List[Bid], List[ProviderStatusSnapshot], Optional[str]]:
    """Run both affiliate marketplace and vendor discovery paths for hybrid execution mode."""

    affiliate_providers = [pid for pid in repo.providers if pid != "vendor_directory"]

    user_zip: Optional[str] = None
    if row.user_id:
        try:
            user_res = await session.exec(
                select(User.zip_code).where(User.id == row.user_id)
            )
            user_zip = user_res.first()
        except Exception:
            pass

    intent_payload = search_intent.model_dump()

    async def _run_affiliate():
        metrics = get_metrics_collector()
        with metrics.track_search(row_id=row.id, query=query):
            return await repo.search_all_with_status(
                query,
                providers=affiliate_providers,
                min_price=min_price,
                max_price=max_price,
                desire_tier=row.desire_tier,
                zip_code=user_zip,
                vendor_query=vendor_query,
                intent_payload=intent_payload,
                query_embedding=query_embedding,
            )

    async def _run_vendor_discovery():
        return await search_vendor_discovery_path(
            session,
            repo,
            service_ref,
            row=row,
            query=query,
            providers=["vendor_directory"],
            min_price=min_price,
            max_price=max_price,
            search_intent=search_intent,
            vendor_query=vendor_query,
            query_embedding=query_embedding,
            endorsement_boosts=endorsement_boosts,
        )

    affiliate_result, vendor_result = await asyncio.gather(
        _run_affiliate(),
        _run_vendor_discovery(),
        return_exceptions=True,
    )

    all_bids: List[Bid] = []
    all_statuses: List[ProviderStatusSnapshot] = []
    user_message: Optional[str] = None

    if isinstance(vendor_result, tuple):
        v_bids, v_statuses, v_msg = vendor_result
        all_bids.extend(v_bids)
        all_statuses.extend(v_statuses)
        if v_msg:
            user_message = v_msg

    if isinstance(affiliate_result, Exception):
        logger.warning("[SourcingService] Hybrid: affiliate path failed: %s", affiliate_result)
    elif affiliate_result is not None:
        normalized = affiliate_result.normalized_results
        if min_price is not None or max_price is not None:
            normalized = [
                r for r in normalized
                if should_include_result(
                    price=r.price, source=r.source,
                    desire_tier=row.desire_tier,
                    min_price=min_price, max_price=max_price,
                )
            ]
        normalized = score_results(
            normalized, intent=search_intent,
            min_price=min_price, max_price=max_price,
            desire_tier=row.desire_tier,
            is_service=row.is_service,
            service_category=row.service_category,
        )
        normalized = filter_vendor_results(
            normalized,
            intent=search_intent,
            is_service=row.is_service,
            service_category=row.service_category,
        )
        persisted = await persist_results(session, row.id, normalized, row=row)
        all_bids.extend(persisted)
        all_statuses.extend(affiliate_result.provider_statuses)
        if affiliate_result.user_message and not user_message:
            user_message = affiliate_result.user_message

    all_bids.sort(key=lambda b: (b.combined_score or 0.0), reverse=True)
    return all_bids, all_statuses, user_message
