"""Synchronous (non-streaming) search endpoint for procurement rows."""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Row, RequestSpec, Bid, User
from routes.bookmarks import _normalize_bookmark_url
from sourcing import SearchResult, ProviderStatusSnapshot, available_provider_ids
from routes.rows_search_helpers import (
    RowSearchRequest,
    SearchResponse,
    get_sourcing_repo,
    resolve_user_id_and_guest,
    log_request_event,
    load_search_state_for_bids,
    _build_base_query,
    _sanitize_query,
    _extract_filters,
    _serialize_json_payload,
    _parse_intent_payload,
)
from routes.rows_search_coverage import (
    record_vendor_coverage_gap_if_needed,
    _build_vendor_coverage_user_message,
)
from sourcing.adapters import build_provider_query_map
from sourcing.choice_filter import should_exclude_by_choices
from sourcing.service import SourcingService

logger = logging.getLogger(__name__)


async def search_row_listings(
    row_id: int,
    body: RowSearchRequest,
    authorization: Optional[str] = Header(None),
    x_anonymous_session_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    from routes.rate_limit import check_rate_limit

    user_id, is_guest = await resolve_user_id_and_guest(authorization, session)
    requester = None if is_guest else await session.get(User, user_id)

    rate_key = f"search:{user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    from dependencies import resolve_accessible_row
    row = await resolve_accessible_row(session, row_id, user_id, is_guest, x_anonymous_session_id)

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
            parsed_intent.model_dump(mode="json") if parsed_intent else body.search_intent
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
    await log_request_event(
        session,
        row_id=row_id,
        user_id=user_id,
        event_type="search_requested",
        event_value=sanitized_query,
        metadata={
            "providers": body.providers or [],
            "is_guest": is_guest,
            "has_search_intent": body.search_intent is not None,
            "has_provider_query_map": body.provider_query_map is not None,
            "routing_mode": row.routing_mode,
        },
    )
    await session.commit()

    # Execute search and persist results as Bids
    bids, provider_statuses, user_message = await sourcing_service.search_and_persist(
        row_id=row_id,
        query=sanitized_query,
        providers=body.providers,
    )

    search_bid_ids = {b.id for b in bids}
    preserved_stmt = (
        select(Bid)
        .where(
            Bid.row_id == row_id,
            Bid.id.notin_(search_bid_ids) if search_bid_ids else True,
        )
        .options(selectinload(Bid.seller))
    )
    preserved_res = await session.exec(preserved_stmt)
    candidate_bids = [bid for bid in preserved_res.all() if not bid.is_superseded]

    bookmarked_vendors, bookmarked_items, emailed_bid_ids = await load_search_state_for_bids(
        session,
        user_id,
        list(bids) + candidate_bids,
    )
    preserved_bids = []
    for bid in candidate_bids:
        bookmark_url = _normalize_bookmark_url(bid.canonical_url or bid.item_url)
        if (
            bid.is_selected
            or (bid.vendor_id and bid.vendor_id in bookmarked_vendors)
            or (bookmark_url and bookmark_url in bookmarked_items)
        ):
            preserved_bids.append(bid)

    keep_bid_ids = search_bid_ids | {bid.id for bid in preserved_bids if bid.id is not None}
    await sourcing_service.supersede_stale_bids(row_id, keep_bid_ids)

    all_bids = list(bids) + preserved_bids

    # Convert Bids back to SearchResults for response compatibility and UI filtering
    results: List[SearchResult] = []
    for bid in all_bids:
        provenance = bid.provenance if isinstance(bid.provenance, dict) else {}
        merchant_name = bid.seller.name if bid.seller else provenance.get("merchant_name") or bid.contact_name or "Unknown"
        merchant_domain = bid.seller.domain if bid.seller else provenance.get("merchant_domain") or ""
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
                merchant=merchant_name,
                url=bid.item_url or "",
                canonical_url=bid.canonical_url or _normalize_bookmark_url(bid.item_url),
                merchant_domain=merchant_domain,
                click_url=click_url,
                image_url=bid.image_url,
                source=bid.source,
                bid_id=bid.id,
                vendor_id=bid.vendor_id,
                is_selected=bid.is_selected,
                is_liked=(
                    bool(bid.vendor_id and bid.vendor_id in bookmarked_vendors)
                    or bool(_normalize_bookmark_url(bid.canonical_url or bid.item_url) in bookmarked_items)
                ),
                liked_at=bid.liked_at.isoformat() if bid.liked_at else None,
                is_vendor_bookmarked=bool(bid.vendor_id and bid.vendor_id in bookmarked_vendors),
                is_item_bookmarked=bool(_normalize_bookmark_url(bid.canonical_url or bid.item_url) in bookmarked_items),
                is_emailed=bool(bid.id and bid.id in emailed_bid_ids),
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

    try:
        coverage_assessment = await record_vendor_coverage_gap_if_needed(
            session=session,
            row=row,
            user_id=user_id,
            search_query=sanitized_query,
            results=results,
            provider_statuses=provider_statuses,
        )
        if coverage_assessment and not user_message:
            user_message = _build_vendor_coverage_user_message(requester, is_guest)
    except Exception as e:
        logger.warning(f"[VendorCoverage] Failed to record sync gap: {e}")

    await log_request_event(
        session,
        row_id=row_id,
        user_id=user_id,
        event_type="search_completed",
        metadata={
            "result_count": len(results),
            "provider_status_count": len(provider_statuses),
            "had_user_message": bool(user_message),
        },
    )
    await session.commit()

    return SearchResponse(results=results, provider_statuses=provider_statuses, user_message=user_message)
