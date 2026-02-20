"""Rows search routes - sourcing/search for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Any, AsyncGenerator
from datetime import datetime
import re
import json
import logging

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Row, RequestSpec, Bid, Seller
from sourcing import (
    SourcingRepository,
    SearchResult,
    SearchIntent,
    ProviderStatusSnapshot,
    build_provider_query_map,
    available_provider_ids,
)
from sourcing.normalizers import normalize_results_for_provider
from sourcing.service import SourcingService
from sourcing.scorer import score_results
from sourcing.filters import should_exclude_by_exclusions
from sourcing.messaging import determine_search_user_message

router = APIRouter(tags=["rows"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions to avoid DRY violations
# ---------------------------------------------------------------------------

def _build_base_query(row: Row, spec: Optional[RequestSpec], explicit_query: Optional[str]) -> tuple[str, bool]:
    """
    Build the base search query from row data.
    Returns (base_query, user_provided_query).

    The LLM sets row.provider_query with the correct search intent.
    We use it as-is — no appending of choice_answers or spec constraints,
    which pollute the query (e.g. 'diamond earrings' → 'diamond earrings recipient niece').
    """
    base_query = explicit_query or row.provider_query or row.title or (spec.item_name if spec else "")
    user_provided = bool(explicit_query)

    return base_query, user_provided


def _sanitize_query(base_query: str, user_provided: bool) -> str:
    """
    Sanitize search query: remove price patterns, truncate if auto-constructed.
    """
    clean_query = re.sub(r"\$\d+", "", base_query)
    clean_query = re.sub(
        r"\b(over|under|below|above)\s*\$?\d+\b", "", clean_query, flags=re.IGNORECASE
    )
    sanitized = " ".join(clean_query.replace("(", " ").replace(")", " ").split())

    # Only truncate if query was NOT explicitly provided by user
    if not user_provided:
        sanitized = " ".join(sanitized.split()[:12]).strip()

    return sanitized if sanitized else base_query.strip()


# Lazy init sourcing repository to ensure env vars are loaded
_sourcing_repo = None

def get_sourcing_repo():
    global _sourcing_repo
    if _sourcing_repo is None:
        _sourcing_repo = SourcingRepository()
    return _sourcing_repo


from dependencies import resolve_user_id as _resolve_user_id


class RowSearchRequest(BaseModel):
    query: Optional[str] = None
    providers: Optional[List[str]] = None
    search_intent: Optional[Any] = None
    provider_query_map: Optional[Any] = None


def _serialize_json_payload(payload: Optional[Any]) -> Optional[str]:
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload
    try:
        return json.dumps(payload)
    except TypeError:
        return json.dumps(payload, default=str)


def _parse_intent_payload(payload: Optional[Any]) -> Optional[SearchIntent]:
    if payload is None:
        return None
    if isinstance(payload, SearchIntent):
        return payload
    data = payload
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None
    try:
        return SearchIntent.model_validate(data)
    except Exception:
        return None


def _normalized_to_search_result(res) -> SearchResult:
    score_data = res.provenance.get("score", {}) if res.provenance else {}
    combined = score_data.get("combined")
    match_score = float(combined) if isinstance(combined, (int, float)) else 0.0
    return SearchResult(
        title=res.title,
        price=res.price,
        currency=res.currency,
        merchant=res.merchant_name,
        url=res.url,
        merchant_domain=res.merchant_domain,
        image_url=res.image_url,
        rating=res.rating,
        reviews_count=res.reviews_count,
        shipping_info=res.shipping_info,
        source=res.source,
        match_score=match_score,
    )


class SearchResponse(BaseModel):
    results: List[SearchResult]
    provider_statuses: List[ProviderStatusSnapshot]
    user_message: Optional[str] = None


@router.post("/rows/{row_id}/search", response_model=SearchResponse)
async def search_row_listings(
    row_id: int,
    body: RowSearchRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.rate_limit import check_rate_limit

    user_id = await _resolve_user_id(authorization, session)

    rate_key = f"search:{user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    spec_result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
    spec = spec_result.first()

    # Build and sanitize query using helper functions
    base_query, user_provided_query = _build_base_query(row, spec, body.query)
    logger.info(f"[SEARCH DEBUG] body.query={body.query!r}, row.title={row.title!r}, base_query={base_query!r}")
    
    sanitized_query = _sanitize_query(base_query, user_provided_query)
    logger.info(f"[SEARCH DEBUG] base_query={base_query!r}, sanitized_query={sanitized_query!r}")

    if body.search_intent is not None or body.provider_query_map is not None:
        parsed_intent = _parse_intent_payload(body.search_intent)
        row.search_intent = _serialize_json_payload(
            parsed_intent.model_dump() if parsed_intent else body.search_intent
        )
        if body.provider_query_map is not None:
            row.provider_query_map = _serialize_json_payload(body.provider_query_map)
        elif parsed_intent:
            provider_ids = body.providers or available_provider_ids()
            query_map = build_provider_query_map(parsed_intent, provider_ids)
            row.provider_query_map = _serialize_json_payload(query_map.model_dump())
        row.updated_at = datetime.utcnow()
        session.add(row)
        await session.commit()

    # Initialize SourcingService
    sourcing_service = SourcingService(session, get_sourcing_repo())

    # Execute search and persist results as Bids
    bids, provider_statuses, user_message = await sourcing_service.search_and_persist(
        row_id=row_id,
        query=sanitized_query,
        providers=body.providers,
    )

    # Merge in any liked/selected bids that weren't returned by the new search.
    # This ensures user-chosen bids survive re-searches even if providers don't return them.
    search_bid_ids = {b.id for b in bids}
    preserved_stmt = (
        select(Bid)
        .where(
            Bid.row_id == row_id,
            Bid.id.notin_(search_bid_ids) if search_bid_ids else True,
            (Bid.is_liked == True) | (Bid.is_selected == True),
        )
        .options(selectinload(Bid.seller))
    )
    preserved_res = await session.exec(preserved_stmt)
    preserved_bids = preserved_res.all()
    all_bids = list(bids) + list(preserved_bids)

    # Convert Bids back to SearchResults for response compatibility and UI filtering
    results: List[SearchResult] = []
    for bid in all_bids:
        # Construct click_url with row_id tracking
        click_url = bid.item_url or ""
        if click_url:
            try:
                if "row_id=" not in click_url:
                    joiner = "&" if "?" in click_url else "?"
                    click_url = f"{click_url}{joiner}row_id={row_id}"
            except Exception:
                pass

        results.append(
            SearchResult(
                title=bid.item_title,
                price=bid.price,
                currency=bid.currency,
                merchant=bid.seller.name if bid.seller else "Unknown",
                url=bid.item_url or "",
                merchant_domain=bid.seller.domain if bid.seller else "",
                click_url=click_url,
                image_url=bid.image_url,
                source=bid.source,
                bid_id=bid.id,
                is_selected=bid.is_selected,
                is_liked=bid.is_liked,
                liked_at=bid.liked_at.isoformat() if bid.liked_at else None,
                match_score=bid.combined_score if bid.combined_score is not None else 0.0,
                # Optional fields that might be missing in Bid but exist in SearchResult
                shipping_info=None, # Bid has shipping_cost (float), SearchResult has shipping_info (str)
                rating=None, 
                reviews_count=None,
            )
        )


    row.status = "bids_arriving"
    row.updated_at = datetime.utcnow()
    session.add(row)

    await session.commit()

    return SearchResponse(results=results, provider_statuses=provider_statuses, user_message=user_message)


@router.post("/rows/{row_id}/search/stream")
async def search_row_listings_stream(
    row_id: int,
    body: RowSearchRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Stream search results as each provider completes.
    Returns SSE events with partial results and a 'more_incoming' flag.
    """
    from routes.rate_limit import check_rate_limit

    user_id = await _resolve_user_id(authorization, session)

    rate_key = f"search:{user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Expire all cached objects so we read fresh data committed by the chat route
    session.expire_all()

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    spec_result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
    spec = spec_result.first()

    # Build and sanitize query using helper functions
    base_query, user_provided_query = _build_base_query(row, spec, body.query)
    sanitized_query = _sanitize_query(base_query, user_provided_query)

    sourcing_repo = get_sourcing_repo()
    sourcing_service = SourcingService(session, sourcing_repo)

    # Extract price constraints from search_intent / choice_answers
    min_price, max_price = sourcing_service._extract_price_constraints(row)
    search_intent = sourcing_service._parse_search_intent(row)
    logger.info(f"[SEARCH STREAM] row={row_id} min_price={min_price} max_price={max_price} search_intent_snippet={str(row.search_intent)[:200]}")

    # Extract clean product intent for vendor vector search
    vendor_query = sourcing_service.extract_vendor_query(row)

    # Extract LLM-populated exclusions for post-search filtering
    exclude_kw, exclude_merchants = sourcing_service._extract_exclusions(row)

    row.status = "bids_arriving"
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()

    async def generate_sse() -> AsyncGenerator[str, None]:
        """Generate SSE events as each provider completes."""
        all_results: List[SearchResult] = []
        all_statuses: List[ProviderStatusSnapshot] = []

        async for provider_name, results, status, providers_remaining in sourcing_repo.search_streaming(
            sanitized_query,
            providers=body.providers,
            desire_tier=row.desire_tier,
            min_price=min_price,
            max_price=max_price,
            vendor_query=vendor_query,
        ):
            all_statuses.append(status)

            # Persist results as Bids
            if results:
                try:
                    normalized_batch = normalize_results_for_provider(provider_name, results)
                    if normalized_batch:
                        scored_batch = score_results(
                            normalized_batch,
                            intent=search_intent,
                            min_price=min_price,
                            max_price=max_price,
                            desire_tier=row.desire_tier,
                        )
                        # Apply LLM-extracted exclusions (Amazon can't do negative keywords)
                        if exclude_kw or exclude_merchants:
                            before = len(scored_batch)
                            scored_batch = [
                                r for r in scored_batch
                                if not should_exclude_by_exclusions(
                                    r.title, r.merchant_name, r.merchant_domain,
                                    exclude_kw, exclude_merchants,
                                )
                            ]
                            dropped = before - len(scored_batch)
                            if dropped:
                                logger.info(f"[SEARCH STREAM] Excluded {dropped}/{before} results from {provider_name} by user exclusions")
                        await sourcing_service._persist_results(row_id, scored_batch, row)
                        # Emit ranked results for this provider batch so UI "Featured"
                        # order reflects scorer output during streaming.
                        results = [_normalized_to_search_result(r) for r in scored_batch]
                except Exception as err:
                    logger.error(f"[SEARCH STREAM] Failed to persist results for provider {provider_name}: {err}")

            all_results.extend(results)
            
            # Build SSE event
            event_data = {
                "provider": provider_name,
                "results": [r.model_dump() for r in results],
                "status": status.model_dump(),
                "providers_remaining": providers_remaining,
                "more_incoming": providers_remaining > 0,
                "total_results_so_far": len(all_results),
            }
            
            yield f"data: {json.dumps(event_data)}\n\n"
        
        # Determine user_message based on results and statuses
        user_message = determine_search_user_message(all_results, all_statuses)

        # Final event with complete status
        final_event = {
            "event": "complete",
            "total_results": len(all_results),
            "provider_statuses": [s.model_dump() for s in all_statuses],
            "more_incoming": False,
            "user_message": user_message,
        }
        yield f"data: {json.dumps(final_event)}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
