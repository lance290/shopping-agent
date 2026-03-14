"""Rows search routes - sourcing/search for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator
from datetime import datetime
import json
import logging

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Row, RequestSpec, Bid, User
from routes.rows_search_helpers import (
    RowSearchRequest,
    SearchResponse,
    get_sourcing_repo,
    resolve_user_id_and_guest,
    log_request_event,
    _build_base_query,
    _sanitize_query,
    _extract_filters,
    _parse_intent_payload,
)
from sourcing.service import SourcingService

router = APIRouter(tags=["rows"])
logger = logging.getLogger(__name__)


from routes.rows_search_sync import search_row_listings as _search_row_listings_impl

@router.post("/rows/{row_id}/search", response_model=SearchResponse)
async def search_row_listings(
    row_id: int,
    body: RowSearchRequest,
    authorization: Optional[str] = Header(None),
    x_anonymous_session_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    return await _search_row_listings_impl(
        row_id, body, authorization, x_anonymous_session_id, session,
    )


@router.post("/rows/{row_id}/search/stream")
async def search_row_listings_stream(
    row_id: int,
    body: RowSearchRequest,
    authorization: Optional[str] = Header(None),
    x_anonymous_session_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Stream search results as each provider completes.
    Returns SSE events with partial results and a 'more_incoming' flag.
    """
    from routes.rate_limit import check_rate_limit

    user_id, is_guest = await resolve_user_id_and_guest(authorization, session)
    requester = None if is_guest else await session.get(User, user_id)

    rate_key = f"search:{user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    from dependencies import resolve_accessible_row
    row = await resolve_accessible_row(session, row_id, user_id, is_guest, x_anonymous_session_id)

    await log_request_event(
        session,
        row_id=row_id,
        user_id=user_id,
        event_type="search_stream_requested",
        metadata={
            "providers": body.providers or [],
            "is_guest": is_guest,
            "routing_mode": row.routing_mode,
        },
    )
    await session.commit()

    spec_result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
    spec = spec_result.first()

    # Build and sanitize query using helper functions
    base_query, user_provided_query = _build_base_query(row, spec, body.query)
    sanitized_query = _sanitize_query(base_query, user_provided_query)

    # Extract filters using helper function
    min_price_filter, max_price_filter, choice_constraints = _extract_filters(row, spec)

    sourcing_repo = get_sourcing_repo()
    sourcing_service = SourcingService(session, sourcing_repo)

    # Extract clean vendor query from row intent (e.g. "yacht charter" not "yacht charter San Diego to Acapulco March")
    vendor_query = SourcingService.extract_vendor_query(row) or row.title

    row.status = "bids_arriving"
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()

    # Feature flag: use LLM tool-calling agent instead of old pipeline
    from sourcing.agent import USE_TOOL_CALLING_AGENT
    if USE_TOOL_CALLING_AGENT:
        async def generate_agent_sse() -> AsyncGenerator[str, None]:
            """Agent-based SSE: LLM decides which tools to call."""
            from sourcing.agent import agent_search
            from sourcing.normalizers import normalize_generic_results
            from sourcing.scorer import score_results

            # Parse search intent for scoring
            agent_parsed_intent = _parse_intent_payload(row.search_intent)

            row_ctx = {
                "title": row.title,
                "is_service": row.is_service,
                "service_category": row.service_category,
                "desire_tier": row.desire_tier,
            }
            if row.choice_answers:
                try:
                    row_ctx["constraints"] = json.loads(row.choice_answers) if isinstance(row.choice_answers, str) else row.choice_answers
                except Exception:
                    pass

            # Track only NEW bid IDs from this agent run (not all bids for the row)
            new_bid_ids_this_run: set[int] = set()

            async for event in agent_search(
                user_message=sanitized_query,
                row_context=row_ctx,
            ):
                if event.type == "tool_results":
                    # Persist tool results as Bids (reuse existing persistence)
                    from sourcing.models import NormalizedResult
                    normalized_items = []
                    for item_data in event.data.get("results", []):
                        try:
                            normalized_items.append(NormalizedResult.model_validate(item_data))
                        except Exception:
                            pass

                    if normalized_items:
                        # Score results before persisting so combined_score is populated
                        normalized_items = score_results(
                            normalized_items,
                            intent=agent_parsed_intent,
                            desire_tier=row.desire_tier,
                            is_service=row.is_service,
                            service_category=row.service_category,
                        )
                        # Record existing bid IDs so we can identify truly new ones
                        existing_stmt = select(Bid.id).where(Bid.row_id == row_id, Bid.is_superseded == False)
                        existing_res = await session.exec(existing_stmt)
                        pre_existing_ids = {bid_id for bid_id in existing_res.all()}

                        persisted = await sourcing_service._persist_results(
                            row_id, normalized_items, row=row,
                        )
                        all_returned_ids = {bid.id for bid in persisted if bid.id is not None}
                        # Only track IDs that are new or updated in THIS run
                        new_bid_ids_this_run.update(all_returned_ids - pre_existing_ids)

                    # Convert to SearchResult format for frontend compatibility
                    search_results = []
                    for item_data in event.data.get("results", []):
                        search_results.append({
                            "title": item_data.get("title", ""),
                            "price": item_data.get("price"),
                            "currency": item_data.get("currency", "USD"),
                            "merchant": item_data.get("merchant_name", "Unknown"),
                            "url": item_data.get("url", ""),
                            "image_url": item_data.get("image_url"),
                            "source": item_data.get("source", event.data.get("tool", "agent")),
                        })

                    yield f"data: {json.dumps({'provider': event.data.get('tool', 'agent'), 'results': search_results, 'providers_remaining': 1, 'more_incoming': True, 'phase': 'agent_results', 'total_results_so_far': len(search_results)})}\n\n"

                elif event.type == "agent_message":
                    yield f"data: {json.dumps({'event': 'agent_message', 'text': event.data.get('text', ''), 'more_incoming': True})}\n\n"

                elif event.type == "complete":
                    # Supersede stale bids — only keep bids from this run
                    try:
                        if new_bid_ids_this_run:
                            await sourcing_service.supersede_stale_bids(row_id, new_bid_ids_this_run)
                    except Exception as e:
                        logger.warning(f"[Agent SSE] Failed to supersede stale bids: {e}")

                    row.status = "bids_arriving" if new_bid_ids_this_run else "sourcing"
                    row.updated_at = datetime.utcnow()
                    session.add(row)
                    await session.commit()

                    yield f"data: {json.dumps({'event': 'complete', 'total_results': event.data.get('total_results', 0), 'more_incoming': False, 'tool_calls_used': event.data.get('tool_calls_used', 0)})}\n\n"

        return StreamingResponse(
            generate_agent_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    from routes.rows_search_classic_sse import generate_classic_sse

    return StreamingResponse(
        generate_classic_sse(
            session=session,
            row=row,
            row_id=row_id,
            user_id=user_id,
            is_guest=is_guest,
            requester=requester,
            sanitized_query=sanitized_query,
            vendor_query=vendor_query,
            providers=body.providers,
            min_price_filter=min_price_filter,
            max_price_filter=max_price_filter,
            choice_constraints=choice_constraints,
            sourcing_service=sourcing_service,
            sourcing_repo=sourcing_repo,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
