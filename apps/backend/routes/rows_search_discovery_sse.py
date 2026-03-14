"""Vendor discovery path SSE — internal vendors + optional external discovery."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Any, AsyncGenerator

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Row, Bid, User
from routes.bookmarks import _normalize_bookmark_url
from sourcing import SearchResult, ProviderStatusSnapshot
from routes.rows_search_helpers import load_search_state_for_bids
from routes.rows_search_coverage import (
    record_vendor_coverage_gap_if_needed,
    _build_vendor_coverage_user_message,
)
from sourcing.scorer import filter_vendor_results, score_results
from sourcing.reranker import rerank_candidates, should_rerank
from sourcing.service import SourcingService
from sourcing.coverage import evaluate_internal_vendor_coverage

logger = logging.getLogger(__name__)


async def vendor_discovery_sse(
    *,
    session: AsyncSession,
    row: Row,
    row_id: int,
    user_id: int,
    is_guest: bool,
    requester: Optional[User],
    sanitized_query: str,
    vendor_query: str,
    min_price_filter: Optional[float],
    max_price_filter: Optional[float],
    sourcing_service: SourcingService,
    parsed_intent: Any,
    intent_payload: Optional[dict],
    query_embedding: Any,
    all_results: List[SearchResult],
    all_statuses: List[ProviderStatusSnapshot],
    all_persisted_bid_ids: set[int],
) -> AsyncGenerator[str, None]:
    """Vendor discovery path SSE — internal vendors + optional external discovery."""
    internal_response = await sourcing_service.search_internal_vendors_only(
        query=sanitized_query,
        vendor_query=vendor_query,
        intent_payload=intent_payload,
        query_embedding=query_embedding,
    )
    internal_results = list(internal_response.results)
    internal_statuses = list(internal_response.provider_statuses)
    normalized_internal = list(internal_response.normalized_results)
    if normalized_internal:
        endorsement_boosts = await sourcing_service._build_endorsement_boosts(row.user_id)
        normalized_internal = score_results(
            normalized_internal,
            intent=parsed_intent,
            min_price=min_price_filter,
            max_price=max_price_filter,
            desire_tier=row.desire_tier,
            is_service=row.is_service,
            service_category=row.service_category,
            endorsement_boosts=endorsement_boosts,
        )
        normalized_internal = filter_vendor_results(
            normalized_internal,
            intent=parsed_intent,
            is_service=row.is_service,
            service_category=row.service_category,
        )
        if normalized_internal and should_rerank(parsed_intent, row.desire_tier, row.routing_mode):
            normalized_internal = await rerank_candidates(sanitized_query, normalized_internal, parsed_intent)
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
        persisted_internal = await sourcing_service._persist_results(row_id, normalized_internal, row=row)
        all_persisted_bid_ids.update({bid.id for bid in persisted_internal if bid.id is not None})
    all_results.extend(internal_results)
    all_statuses.extend(internal_statuses)

    if internal_results:
        yield f"data: {json.dumps({'provider': 'vendor_directory', 'results': [r.model_dump() for r in internal_results], 'status': internal_statuses[0].model_dump() if internal_statuses else None, 'providers_remaining': 1, 'more_incoming': True, 'phase': 'internal_results', 'coverage_status': 'pending', 'total_results_so_far': len(all_results)})}\n\n"

    evaluation = evaluate_internal_vendor_coverage(
        internal_results,
        high_risk=(row.desire_tier or "").strip().lower() in {"high_value", "advisory"},
    )

    if evaluation.status != "sufficient":
        orchestrator = sourcing_service._parse_search_intent(row)
        if orchestrator:
            from sourcing.discovery.orchestrator import DiscoveryOrchestrator

            discovery = DiscoveryOrchestrator(session, sourcing_service)
            async for eval_result, normalized_results, status, discovery_session_id, discovery_mode in discovery.stream(
                row=row,
                search_intent=orchestrator,
                internal_results=internal_results,
            ):
                persisted_discovery = await sourcing_service._persist_results(
                    row_id,
                    sourcing_service._filter_discovery_results_for_bid_persistence(row, normalized_results),
                    row=row,
                )
                all_persisted_bid_ids.update({bid.id for bid in persisted_discovery if bid.id is not None})
                search_results = [
                    SearchResult(
                        title=item.title,
                        price=item.price,
                        currency=item.currency,
                        merchant=item.merchant_name,
                        url=item.url,
                        canonical_url=item.canonical_url,
                        merchant_domain=item.merchant_domain,
                        image_url=item.image_url,
                        source=item.source,
                        metadata={
                            "discovery_session_id": discovery_session_id,
                            "discovery_mode": discovery_mode,
                        },
                    )
                    for item in normalized_results
                ]
                all_results.extend(search_results)
                all_statuses.append(status)
                _expanding_msg = "I'm expanding the search beyond our current vendor database."
                discovery_event = {
                    "provider": status.provider_id,
                    "results": [r.model_dump() for r in search_results],
                    "status": status.model_dump(),
                    "providers_remaining": 0,
                    "more_incoming": True,
                    "phase": "discovery_results",
                    "coverage_status": eval_result.status,
                    "discovery_session_id": discovery_session_id,
                    "total_results_so_far": len(all_results),
                    "user_message": _expanding_msg,
                }
                yield f"data: {json.dumps(discovery_event)}\n\n"

    try:
        existing_stmt = (
            select(Bid)
            .where(
                Bid.row_id == row_id,
                Bid.id.notin_(all_persisted_bid_ids) if all_persisted_bid_ids else True,
            )
            .options(selectinload(Bid.seller))
        )
        existing_res = await session.exec(existing_stmt)
        existing_bids = [bid for bid in existing_res.all() if not bid.is_superseded]
        bookmarked_vendors, bookmarked_items, _ = await load_search_state_for_bids(
            session,
            user_id,
            existing_bids,
        )
        protected_existing_ids = {
            bid.id
            for bid in existing_bids
            if bid.id is not None and (
                bid.is_selected
                or (bid.vendor_id and bid.vendor_id in bookmarked_vendors)
                or (_normalize_bookmark_url(bid.canonical_url or bid.item_url) in bookmarked_items)
            )
        }
        await sourcing_service.supersede_stale_bids(
            row_id,
            all_persisted_bid_ids | protected_existing_ids,
        )

        from services.sdui_builder import build_zero_results_schema

        row.status = "bids_arriving" if all_results else "sourcing"
        if not all_results:
            row.ui_schema = build_zero_results_schema(row)
            row.ui_schema_version = (row.ui_schema_version or 0) + 1
        row.updated_at = datetime.utcnow()
        session.add(row)
        await session.commit()
        coverage_assessment = await record_vendor_coverage_gap_if_needed(
            session=session,
            row=row,
            user_id=user_id,
            search_query=sanitized_query,
            results=all_results,
            provider_statuses=all_statuses,
        )
        if coverage_assessment:
            requester_message = _build_vendor_coverage_user_message(requester, is_guest)
        else:
            requester_message = None
    except Exception as e:
        logger.error(f"[SEARCH STREAM] Failed vendor discovery stream finalization: {e}")
        requester_message = None

    final_event = {
        "event": "complete",
        "total_results": len(all_results),
        "provider_statuses": [s.model_dump() for s in all_statuses],
        "more_incoming": False,
        "user_message": requester_message or (None if evaluation.status == "sufficient" else "I'm expanding the search beyond our current vendor database."),
    }
    yield f"data: {json.dumps(final_event)}\n\n"
