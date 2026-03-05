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
from models import Row, RequestSpec, Bid, Seller, User
from dependencies import get_current_session

GUEST_EMAIL = "guest@buy-anything.com"


async def _resolve_user_id(authorization: Optional[str], session: AsyncSession) -> Optional[int]:
    """Resolve the user_id from auth session, falling back to guest user."""
    auth_session = await get_current_session(authorization, session)
    if auth_session:
        return auth_session.user_id
    # Fall back to guest user
    result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
    guest = result.first()
    if not guest:
        guest = User(email=GUEST_EMAIL, is_admin=False)
        session.add(guest)
        await session.commit()
        await session.refresh(guest)
    return guest.id
from sourcing import (
    SourcingRepository,
    SearchResult,
    ProviderStatusSnapshot,
    available_provider_ids,
)
from routes.rows_search_helpers import (
    _build_base_query,
    _sanitize_query,
    _extract_filters,
    _serialize_json_payload,
    _parse_intent_payload,
)
from sourcing.normalizers import normalize_generic_results
from sourcing.scorer import score_results
from sourcing.service import SourcingService
from sourcing.choice_filter import should_exclude_by_choices
from sourcing.messaging import determine_search_user_message

router = APIRouter(tags=["rows"])
logger = logging.getLogger(__name__)


# Lazy init sourcing repository to ensure env vars are loaded
_sourcing_repo = None

def get_sourcing_repo():
    global _sourcing_repo
    if _sourcing_repo is None:
        _sourcing_repo = SourcingRepository()
    return _sourcing_repo


class RowSearchRequest(BaseModel):
    query: Optional[str] = None
    providers: Optional[List[str]] = None
    search_intent: Optional[Any] = None
    provider_query_map: Optional[Any] = None


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

    # Supersede stale bids AFTER persist — only bids not returned by the new search.
    # This preserves good results from providers that returned different URLs on refinement.
    search_bid_ids = {b.id for b in bids}
    await sourcing_service.supersede_stale_bids(row_id, search_bid_ids)
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
                # Optional fields that might be missing in Bid but exist in SearchResult
                shipping_info=None, # Bid has shipping_cost (float), SearchResult has shipping_info (str)
                rating=None, 
                reviews_count=None,
            )
        )


    # Extract filters using helper function
    min_price_filter, max_price_filter, choice_constraints = _extract_filters(row, spec)
    logger.info(f"[SEARCH] Filters for row {row_id}: price=[{min_price_filter}, {max_price_filter}], choice_constraints={choice_constraints}")

    # Apply price and choice filtering
    from sourcing.filters import should_include_result
    if min_price_filter is not None or max_price_filter is not None or choice_constraints:
        filtered_results = []
        dropped_price = 0
        dropped_choices = 0

        for r in results:
            title = getattr(r, "title", "")
            source = (getattr(r, "source", "") or "").lower()
            is_vector_searched = source == "vendor_directory"

            # Check choice constraints (skip for vector-searched sources)
            if not is_vector_searched and choice_constraints:
                if should_exclude_by_choices(title, choice_constraints):
                    dropped_choices += 1
                    continue

            # Unified price/source filtering
            if not should_include_result(
                price=getattr(r, "price", None),
                source=source,
                desire_tier=row.desire_tier,
                min_price=min_price_filter,
                max_price=max_price_filter,
            ):
                dropped_price += 1
                continue
            filtered_results.append(r)

        logger.info(
            f"[SEARCH] Filtered {len(results)} -> {len(filtered_results)} results "
            f"(price_filter: min={min_price_filter}, max={max_price_filter}, dropped={dropped_price}; "
            f"choice_filter: constraints={choice_constraints}, dropped={dropped_choices})"
        )
        results = filtered_results

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

    async def generate_sse() -> AsyncGenerator[str, None]:
        """Generate SSE events as each provider completes."""
        all_results: List[SearchResult] = []
        all_statuses: List[ProviderStatusSnapshot] = []
        all_persisted_bid_ids: set[int] = set()

        # Compute query embedding ONCE — shared by vendor_provider (vector search) and quantum reranker
        query_embedding = None
        quantum_reranker = None
        try:
            from sourcing.vendor_provider import _embed_texts
            embed_text = vendor_query or sanitized_query
            vecs = await _embed_texts([embed_text])
            if vecs and len(vecs) > 0:
                query_embedding = vecs[0]
                logger.info(f"[SEARCH STREAM] Query embedding computed for '{embed_text[:50]}' (shared with vendor_provider + quantum reranker)")
        except Exception as e:
            logger.warning(f"[SEARCH STREAM] Query embedding failed: {e}")

        # Initialize quantum reranker (uses the shared query embedding)
        if query_embedding:
            try:
                from sourcing.quantum.reranker import QuantumReranker
                quantum_reranker = QuantumReranker()
                if not quantum_reranker.is_available():
                    quantum_reranker = None
            except Exception as e:
                logger.warning(f"[SEARCH STREAM] Quantum reranker init failed (graceful degradation): {e}")

        async for provider_name, results, status, providers_remaining in sourcing_repo.search_streaming(
            sanitized_query,
            providers=body.providers,
            min_price=min_price_filter,
            max_price=max_price_filter,
            desire_tier=row.desire_tier,
            vendor_query=vendor_query,
            query_embedding=query_embedding,  # shared — vendor_provider skips its own embed call
        ):
            all_statuses.append(status)

            # Convert and filter results
            from sourcing.filters import should_include_result as _should_include
            filtered_batch = []
            for r in results:
                title = getattr(r, "title", "")
                source = (getattr(r, "source", "") or "").lower()
                is_vector_searched = source == "vendor_directory"

                # Check choice constraints (skip for vector-searched sources)
                if not is_vector_searched and choice_constraints:
                    if should_exclude_by_choices(title, choice_constraints):
                        continue

                # Unified price/source filtering
                if not _should_include(
                    price=getattr(r, "price", None),
                    source=getattr(r, "source", "") or "",
                    desire_tier=row.desire_tier,
                    min_price=min_price_filter,
                    max_price=max_price_filter,
                ):
                    continue
                filtered_batch.append(r)
            
            if filtered_batch:
                try:
                    normalized_batch = normalize_generic_results(filtered_batch, provider_name)
                    if normalized_batch:
                        normalized_batch = score_results(
                            normalized_batch,
                            intent=sourcing_service._parse_search_intent(row),
                            min_price=min_price_filter,
                            max_price=max_price_filter,
                            desire_tier=row.desire_tier,
                        )

                        # Quantum reranking: score batch against user intent embedding
                        if quantum_reranker and query_embedding:
                            try:
                                results_for_quantum = []
                                for idx, res in enumerate(normalized_batch):
                                    rd = {
                                        "_idx": idx,
                                        "title": res.title,
                                        "embedding": res.raw_data.get("embedding") if res.raw_data else None,
                                    }
                                    results_for_quantum.append(rd)

                                if any(r.get("embedding") for r in results_for_quantum):
                                    reranked = await quantum_reranker.rerank_results(
                                        query_embedding=query_embedding,
                                        search_results=results_for_quantum,
                                        top_k=len(normalized_batch),
                                    )
                                    score_map = {}
                                    for r in reranked:
                                        if r.get("quantum_reranked") and "_idx" in r:
                                            score_map[r["_idx"]] = r
                                    for idx, res in enumerate(normalized_batch):
                                        if idx in score_map:
                                            qr = score_map[idx]
                                            res.provenance["quantum_score"] = qr.get("quantum_score", 0.0)
                                            res.provenance["blended_score"] = qr.get("blended_score", 0.0)
                                            res.provenance["novelty_score"] = qr.get("novelty_score", 0.0)
                                            res.provenance["coherence_score"] = qr.get("coherence_score", 0.0)
                                    logger.info(f"[SEARCH STREAM] Quantum reranked {len(score_map)}/{len(normalized_batch)} results from {provider_name}")
                            except Exception as qe:
                                logger.warning(f"[SEARCH STREAM] Quantum reranking failed for {provider_name}: {qe}")

                        persisted_bids = await sourcing_service._persist_results(row_id, normalized_batch)
                        all_persisted_bid_ids.update(b.id for b in persisted_bids if b.id)
                except Exception as err:
                    logger.error(f"[SEARCH STREAM] Failed to persist results for provider {provider_name}: {err}")

            all_results.extend(filtered_batch)
            
            # Build SSE event
            event_data = {
                "provider": provider_name,
                "results": [r.model_dump() for r in filtered_batch],
                "status": status.model_dump(),
                "providers_remaining": providers_remaining,
                "more_incoming": providers_remaining > 0,
                "total_results_so_far": len(all_results),
            }
            
            yield f"data: {json.dumps(event_data)}\n\n"
        
        # Supersede stale bids AFTER all providers complete.
        # Only bids not returned by any provider in this search get retired.
        try:
            await sourcing_service.supersede_stale_bids(row_id, all_persisted_bid_ids)
        except Exception as e:
            logger.error(f"[SEARCH STREAM] Failed to supersede stale bids: {e}")

        # Determine user_message based on results and statuses
        user_message = determine_search_user_message(all_results, all_statuses)

        # Update row status to reflect search completion
        try:
            from services.sdui_builder import build_ui_schema, build_zero_results_schema
            await session.refresh(row)
            if len(all_results) == 0:
                row.status = "sourcing"
                row.ui_schema = build_zero_results_schema(row)
                row.ui_schema_version = (row.ui_schema_version or 0) + 1
            else:
                row.status = "bids_arriving"
            row.updated_at = datetime.utcnow()
            session.add(row)
            await session.commit()
        except Exception as e:
            logger.error(f"[SEARCH STREAM] Failed to update row status after completion: {e}")

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
