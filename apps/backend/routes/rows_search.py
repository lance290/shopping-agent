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
from dependencies import get_current_session
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
from sourcing.material_filter import extract_material_constraints, should_exclude_result
from sourcing.choice_filter import should_exclude_by_choices, extract_choice_constraints
from sourcing.messaging import determine_search_user_message
from utils.json_utils import safe_json_loads

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


def _extract_filters(row: Row, spec: Optional[RequestSpec]) -> tuple[Optional[float], Optional[float], bool, set, dict]:
    """
    Extract price, material, and choice filters from row.choice_answers and spec.constraints.
    Returns (min_price, max_price, exclude_synthetics, custom_exclude_keywords, choice_constraints).
    """
    min_price = None
    max_price = None
    exclude_synthetics = False
    custom_exclude_keywords: set = set()
    choice_constraints: dict = {}

    # Check for material constraints in spec
    if spec and spec.constraints:
        constraints_obj = safe_json_loads(spec.constraints, {})
        if constraints_obj:
            exclude_synthetics, custom_exclude_keywords = extract_material_constraints(constraints_obj)

    def _parse_price_value(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            match = re.search(r"(\d[\d,]*\.?\d*)", str(value))
            if not match:
                return None
            return float(match.group(1).replace(",", ""))
        except Exception:
            return None

    # Check for price and material constraints in choice_answers
    if row.choice_answers:
        answers_obj = safe_json_loads(row.choice_answers, {})
        if answers_obj:
            # Extract price constraints
            min_price = _parse_price_value(answers_obj.get("min_price"))
            max_price = _parse_price_value(answers_obj.get("max_price"))

            # Backward-compatible fallback: some rows store a single "price" answer
            # like "50000" or ">50000" instead of min_price/max_price.
            if min_price is None and max_price is None:
                parsed_price = _parse_price_value(answers_obj.get("price"))
                if parsed_price is not None:
                    min_price = parsed_price

            # Swap if inverted (min > max)
            if min_price is not None and max_price is not None and min_price > max_price:
                min_price, max_price = max_price, min_price

            # Extract material constraints
            exclude_synth_from_answers, custom_keywords_from_answers = extract_material_constraints(answers_obj)
            exclude_synthetics = exclude_synthetics or exclude_synth_from_answers
            custom_exclude_keywords.update(custom_keywords_from_answers)

            # Extract choice constraints (color, size, etc.)
            choice_constraints = extract_choice_constraints(row.choice_answers)

    return min_price, max_price, exclude_synthetics, custom_exclude_keywords, choice_constraints

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
                # Optional fields that might be missing in Bid but exist in SearchResult
                shipping_info=None, # Bid has shipping_cost (float), SearchResult has shipping_info (str)
                rating=None, 
                reviews_count=None,
            )
        )


    # Extract filters using helper function
    min_price_filter, max_price_filter, exclude_synthetics, custom_exclude_keywords, choice_constraints = _extract_filters(row, spec)
    logger.info(f"[SEARCH] Filters for row {row_id}: price=[{min_price_filter}, {max_price_filter}], exclude_synthetics={exclude_synthetics}, custom_keywords={custom_exclude_keywords}, choice_constraints={choice_constraints}")

    # Apply price, material, and choice filtering
    from sourcing.filters import should_include_result
    if min_price_filter is not None or max_price_filter is not None or exclude_synthetics or custom_exclude_keywords or choice_constraints:
        filtered_results = []
        dropped_price = 0
        dropped_materials = 0
        dropped_choices = 0

        for r in results:
            title = getattr(r, "title", "")
            source = (getattr(r, "source", "") or "").lower()

            # Vector-searched results (vendor_directory) are already semantically
            # matched — their titles are company names, not product descriptions.
            # Skip keyword title-matching filters for them.
            is_vector_searched = source == "vendor_directory"

            # Check material constraints (skip for vector-searched sources)
            if not is_vector_searched and (exclude_synthetics or custom_exclude_keywords):
                if should_exclude_result(title, exclude_synthetics, custom_exclude_keywords):
                    dropped_materials += 1
                    continue

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
            f"material_filter: exclude_synthetics={exclude_synthetics}, dropped={dropped_materials}; "
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
    min_price_filter, max_price_filter, exclude_synthetics, custom_exclude_keywords, choice_constraints = _extract_filters(row, spec)

    sourcing_repo = get_sourcing_repo()
    sourcing_service = SourcingService(session, sourcing_repo)

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
            min_price=min_price_filter,
            max_price=max_price_filter,
            desire_tier=row.desire_tier,
        ):
            all_statuses.append(status)

            # Convert and filter results
            from sourcing.filters import should_include_result as _should_include
            filtered_batch = []
            for r in results:
                title = getattr(r, "title", "")
                source = (getattr(r, "source", "") or "").lower()
                is_vector_searched = source == "vendor_directory"

                # Check material constraints (skip for vector-searched sources)
                if not is_vector_searched and (exclude_synthetics or custom_exclude_keywords):
                    if should_exclude_result(title, exclude_synthetics, custom_exclude_keywords):
                        continue

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
                    normalized_batch = normalize_results_for_provider(provider_name, filtered_batch)
                    if normalized_batch:
                        await sourcing_service._persist_results(row_id, normalized_batch)
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
