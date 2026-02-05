"""Rows search routes - sourcing/search for procurement rows."""
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Any, AsyncGenerator
from datetime import datetime
import re
import json
import logging

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
from sourcing.material_filter import extract_material_constraints, should_exclude_result
from sourcing.messaging import determine_search_user_message

router = APIRouter(tags=["rows"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions to avoid DRY violations
# ---------------------------------------------------------------------------

def _build_base_query(row: Row, spec: Optional[RequestSpec], explicit_query: Optional[str]) -> tuple[str, bool]:
    """
    Build the base search query from row data, spec constraints, and choice answers.
    Returns (base_query, user_provided_query).
    """
    base_query = explicit_query or row.provider_query or row.title or (spec.item_name if spec else "")
    user_provided = bool(explicit_query)

    if not explicit_query:
        if spec and spec.constraints:
            try:
                constraints_obj = json.loads(spec.constraints)
                constraint_parts = [f"{k}: {v}" for k, v in constraints_obj.items()]
                if constraint_parts:
                    base_query = base_query + " " + " ".join(constraint_parts)
            except Exception:
                pass

        if row.choice_answers:
            try:
                answers_obj = json.loads(row.choice_answers)
                answer_parts = [
                    f"{k} {v}"
                    for k, v in answers_obj.items()
                    if k not in ("min_price", "max_price") and v and str(v).lower() != "not answered"
                ]
                if answer_parts:
                    base_query = base_query + " " + " ".join(answer_parts)
            except Exception:
                pass

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


def _extract_filters(row: Row, spec: Optional[RequestSpec]) -> tuple[Optional[float], Optional[float], bool, set]:
    """
    Extract price and material filters from row.choice_answers and spec.constraints.
    Returns (min_price, max_price, exclude_synthetics, custom_exclude_keywords).
    """
    min_price = None
    max_price = None
    exclude_synthetics = False
    custom_exclude_keywords: set = set()

    # Check for material constraints in spec
    if spec and spec.constraints:
        try:
            constraints_obj = json.loads(spec.constraints)
            exclude_synthetics, custom_exclude_keywords = extract_material_constraints(constraints_obj)
        except Exception:
            pass

    # Check for price and material constraints in choice_answers
    if row.choice_answers:
        try:
            answers_obj = json.loads(row.choice_answers)

            # Extract price constraints
            if answers_obj.get("min_price"):
                min_price = float(answers_obj["min_price"])
            if answers_obj.get("max_price"):
                max_price = float(answers_obj["max_price"])
            # Swap if inverted (min > max)
            if min_price is not None and max_price is not None and min_price > max_price:
                min_price, max_price = max_price, min_price

            # Extract material constraints
            exclude_synth_from_answers, custom_keywords_from_answers = extract_material_constraints(answers_obj)
            exclude_synthetics = exclude_synthetics or exclude_synth_from_answers
            custom_exclude_keywords.update(custom_keywords_from_answers)
        except Exception:
            pass

    return min_price, max_price, exclude_synthetics, custom_exclude_keywords

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
    from routes.auth import get_current_session
    from routes.rate_limit import check_rate_limit

    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    rate_key = f"search:{auth_session.user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
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

    # Convert Bids back to SearchResults for response compatibility and UI filtering
    results: List[SearchResult] = []
    for bid in bids:
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
                # Optional fields that might be missing in Bid but exist in SearchResult
                shipping_info=None, # Bid has shipping_cost (float), SearchResult has shipping_info (str)
                rating=None, 
                reviews_count=None,
            )
        )

    # Extract filters using helper function
    min_price_filter, max_price_filter, exclude_synthetics, custom_exclude_keywords = _extract_filters(row, spec)
    logger.info(f"[SEARCH] Filters for row {row_id}: price=[{min_price_filter}, {max_price_filter}], exclude_synthetics={exclude_synthetics}, custom_keywords={custom_exclude_keywords}")

    # Apply price and material filtering
    if min_price_filter is not None or max_price_filter is not None or exclude_synthetics or custom_exclude_keywords:
        filtered_results = []
        # Sources that don't provide price data - allow through without price filtering
        non_shopping_sources = {"google_cse"}
        # Service providers that do not have fixed prices - allow through without price filtering
        service_sources = {"wattdata"}
        dropped_price = 0
        dropped_materials = 0

        for r in results:
            source = getattr(r, "source", None)
            source_key = str(source or "").lower()

            # Check material constraints first (applies to all sources)
            if exclude_synthetics or custom_exclude_keywords:
                title = getattr(r, "title", "")
                if should_exclude_result(title, exclude_synthetics, custom_exclude_keywords):
                    dropped_materials += 1
                    logger.debug(f"[SEARCH] Excluded due to materials: {title}")
                    continue

            # Apply price filtering (skip for non-shopping sources and service providers)
            if source_key in non_shopping_sources or source_key in service_sources:
                filtered_results.append(r)
                continue

            price = getattr(r, "price", None)
            if price is None or price == 0:
                dropped_price += 1
                continue
            # Filter: keep items where price >= min AND price <= max
            if min_price_filter is not None and price < min_price_filter:
                dropped_price += 1
                continue
            if max_price_filter is not None and price > max_price_filter:
                dropped_price += 1
                continue
            filtered_results.append(r)

        logger.info(
            f"[SEARCH] Filtered {len(results)} -> {len(filtered_results)} results "
            f"(price_filter: min={min_price_filter}, max={max_price_filter}, dropped={dropped_price}; "
            f"material_filter: exclude_synthetics={exclude_synthetics}, dropped={dropped_materials})"
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
    from routes.auth import get_current_session
    from routes.rate_limit import check_rate_limit

    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    rate_key = f"search:{auth_session.user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
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
    min_price_filter, max_price_filter, exclude_synthetics, custom_exclude_keywords = _extract_filters(row, spec)

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
        non_shopping_sources = {"google_cse"}

        async for provider_name, results, status, providers_remaining in sourcing_repo.search_streaming(
            sanitized_query,
            providers=body.providers,
            min_price=min_price_filter,
            max_price=max_price_filter,
        ):
            all_statuses.append(status)

            # Convert and filter results
            filtered_batch = []
            for r in results:
                # Check material constraints first (applies to all sources)
                if exclude_synthetics or custom_exclude_keywords:
                    title = getattr(r, "title", "")
                    if should_exclude_result(title, exclude_synthetics, custom_exclude_keywords):
                        continue

                source = getattr(r, "source", None)
                # Allow non-shopping sources through (skip price filtering)
                if source in non_shopping_sources:
                    filtered_batch.append(r)
                    continue

                # Apply price filtering
                price = getattr(r, "price", None)
                if price is None or price == 0:
                    continue
                if min_price_filter is not None and price < min_price_filter:
                    continue
                if max_price_filter is not None and price > max_price_filter:
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
