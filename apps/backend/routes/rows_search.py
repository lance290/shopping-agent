import asyncio

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
from models import Row, RequestSpec, Bid, Seller, User, VendorCoverageGap
from models.bookmarks import VendorBookmark, ItemBookmark
from models.outreach import OutreachMessage
from dependencies import get_current_session
from routes.bookmarks import _normalize_bookmark_url

GUEST_EMAIL = "guest@buy-anything.com"


async def _resolve_user_id_and_guest(authorization: Optional[str], session: AsyncSession) -> tuple[int, bool]:
    from dependencies import resolve_user_id_and_guest_flag
    return await resolve_user_id_and_guest_flag(authorization, session)
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
from sourcing.adapters import build_provider_query_map
from sourcing.normalizers import normalize_generic_results
from sourcing.scorer import score_results
from sourcing.service import SourcingService
from sourcing.discovery.classifier import classify_search_path
from sourcing.coverage import evaluate_internal_vendor_coverage
from sourcing.choice_filter import should_exclude_by_choices
from sourcing.messaging import determine_search_user_message
from services.llm import assess_vendor_coverage

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


async def _load_search_state_for_bids(
    session: AsyncSession,
    user_id: int,
    bids: List[Bid],
) -> tuple[set[int], set[str], set[int]]:
    vendor_ids = {bid.vendor_id for bid in bids if bid.vendor_id}
    item_urls = {
        normalized
        for bid in bids
        if (normalized := _normalize_bookmark_url(bid.canonical_url or bid.item_url))
    }
    bid_ids = {bid.id for bid in bids if bid.id is not None}

    bookmarked_vendor_ids: set[int] = set()
    if vendor_ids:
        result = await session.exec(
            select(VendorBookmark.vendor_id)
            .where(VendorBookmark.user_id == user_id, VendorBookmark.vendor_id.in_(vendor_ids))
        )
        bookmarked_vendor_ids = set(result.all())

    bookmarked_item_urls: set[str] = set()
    if item_urls:
        result = await session.exec(
            select(ItemBookmark.canonical_url)
            .where(ItemBookmark.user_id == user_id, ItemBookmark.canonical_url.in_(item_urls))
        )
        bookmarked_item_urls = set(result.all())

    emailed_bid_ids: set[int] = set()
    if bid_ids:
        result = await session.exec(
            select(OutreachMessage.bid_id)
            .where(
                OutreachMessage.bid_id.isnot(None),
                OutreachMessage.bid_id.in_(bid_ids),
                OutreachMessage.status.in_(("sent", "delivered", "replied")),
            )
        )
        emailed_bid_ids = {bid_id for bid_id in result.all() if bid_id is not None}

    return bookmarked_vendor_ids, bookmarked_item_urls, emailed_bid_ids


def _build_vendor_coverage_context(
    results: List[SearchResult],
    provider_statuses: List[ProviderStatusSnapshot],
) -> dict[str, Any]:
    source_counts: dict[str, int] = {}
    top_results: list[dict[str, Any]] = []
    vendor_results: list[dict[str, Any]] = []

    for res in results:
        source = (getattr(res, "source", "") or "unknown").lower()
        source_counts[source] = source_counts.get(source, 0) + 1

        if len(top_results) < 12:
            top_results.append(
                {
                    "title": getattr(res, "title", ""),
                    "merchant": getattr(res, "merchant", ""),
                    "source": getattr(res, "source", ""),
                    "price": getattr(res, "price", None),
                    "match_score": getattr(res, "match_score", None),
                }
            )

        if source == "vendor_directory" and len(vendor_results) < 8:
            vendor_results.append(
                {
                    "title": getattr(res, "title", ""),
                    "merchant": getattr(res, "merchant", ""),
                    "description": getattr(res, "description", None),
                    "match_score": getattr(res, "match_score", None),
                }
            )

    return {
        "source_counts": source_counts,
        "top_results": top_results,
        "vendor_results": vendor_results,
        "provider_statuses": [status.model_dump() for status in provider_statuses],
    }


def _missing_requester_identity_fields(requester: Optional[User], is_guest: bool) -> list[str]:
    if is_guest or not requester:
        return ["name", "company"]
    missing: list[str] = []
    if not (requester.name or "").strip():
        missing.append("name")
    if not (requester.company or "").strip():
        missing.append("company")
    return missing


def _build_vendor_coverage_user_message(requester: Optional[User], is_guest: bool) -> str:
    missing = _missing_requester_identity_fields(requester, is_guest)
    base = "I’m not seeing strong vendor coverage for this request yet, so I’ve flagged it internally and we’ll expand the vendor set as quickly as we can."
    if not missing:
        return base
    if len(missing) == 2:
        return base + " When you have a moment, send me your name and company so I can attach them to the sourcing request."
    return base + f" When you have a moment, send me your {missing[0]} so I can attach it to the sourcing request."


async def _record_vendor_coverage_gap_if_needed(
    session: AsyncSession,
    row: Row,
    user_id: int,
    search_query: str,
    results: List[SearchResult],
    provider_statuses: List[ProviderStatusSnapshot],
) -> Optional[dict[str, Any]]:
    context = _build_vendor_coverage_context(results, provider_statuses)
    assessment = await assess_vendor_coverage(
        row_title=row.title or "",
        search_query=search_query,
        desire_tier=row.desire_tier,
        service_type=row.service_category,
        search_intent=row.search_intent,
        choice_answers=row.choice_answers,
        provider_statuses=context["provider_statuses"],
        results=context["top_results"],
    )
    if not assessment or not assessment.should_log_gap:
        return None

    normalized_geo = (assessment.geo_hint or "").strip().lower()
    existing_stmt = select(VendorCoverageGap).where(
        VendorCoverageGap.canonical_need == assessment.canonical_need,
        VendorCoverageGap.desire_tier == row.desire_tier,
        VendorCoverageGap.service_type == row.service_category,
    )
    existing_res = await session.exec(existing_stmt)
    existing = None
    for candidate in existing_res.all():
        candidate_geo = (candidate.geo_hint or "").strip().lower()
        if candidate_geo == normalized_geo:
            existing = candidate
            break

    now = datetime.utcnow()
    if existing:
        existing.row_id = row.id
        existing.user_id = user_id
        existing.row_title = row.title or existing.row_title
        existing.search_query = search_query
        existing.vendor_query = assessment.vendor_query or existing.vendor_query
        existing.geo_hint = assessment.geo_hint or existing.geo_hint
        existing.summary = assessment.summary
        existing.rationale = assessment.rationale
        existing.suggested_queries = assessment.suggested_vendor_search_queries
        existing.assessment = assessment.model_dump()
        existing.supporting_context = context
        existing.confidence = max(existing.confidence or 0.0, assessment.confidence)
        existing.times_seen = (existing.times_seen or 0) + 1
        existing.last_seen_at = now
        existing.status = "new"
        session.add(existing)
    else:
        session.add(
            VendorCoverageGap(
                row_id=row.id,
                user_id=user_id,
                row_title=row.title or "",
                canonical_need=assessment.canonical_need,
                search_query=search_query,
                vendor_query=assessment.vendor_query,
                geo_hint=assessment.geo_hint,
                desire_tier=row.desire_tier,
                service_type=row.service_category,
                summary=assessment.summary,
                rationale=assessment.rationale,
                suggested_queries=assessment.suggested_vendor_search_queries,
                assessment=assessment.model_dump(),
                supporting_context=context,
                confidence=assessment.confidence,
                first_seen_at=now,
                last_seen_at=now,
            )
        )

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.warning(f"[VendorCoverage] Failed to persist gap: {e}")
        return None
    return assessment.model_dump()


@router.post("/rows/{row_id}/search", response_model=SearchResponse)
async def search_row_listings(
    row_id: int,
    body: RowSearchRequest,
    authorization: Optional[str] = Header(None),
    x_anonymous_session_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.rate_limit import check_rate_limit

    user_id, is_guest = await _resolve_user_id_and_guest(authorization, session)
    requester = None if is_guest else await session.get(User, user_id)

    rate_key = f"search:{user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    if is_guest and row.anonymous_session_id and row.anonymous_session_id != x_anonymous_session_id:
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

    bookmarked_vendors, bookmarked_items, emailed_bid_ids = await _load_search_state_for_bids(
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
        coverage_assessment = await _record_vendor_coverage_gap_if_needed(
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

    return SearchResponse(results=results, provider_statuses=provider_statuses, user_message=user_message)


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

    user_id, is_guest = await _resolve_user_id_and_guest(authorization, session)
    requester = None if is_guest else await session.get(User, user_id)

    rate_key = f"search:{user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    if is_guest and row.anonymous_session_id and row.anonymous_session_id != x_anonymous_session_id:
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
        db_lock = asyncio.Lock()

        parsed_intent = _parse_intent_payload(row.search_intent)
        search_path = classify_search_path(parsed_intent, row)
        intent_payload = parsed_intent.model_dump() if parsed_intent else None
        query_embedding = None
        quantum_reranker = None
        try:
            from sourcing.vendor_provider import build_query_embedding

            query_embedding = await build_query_embedding(
                vendor_query or sanitized_query,
                context_query=sanitized_query,
                intent_payload=intent_payload,
            )
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

        if parsed_intent and search_path == "vendor_discovery_path":
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
                normalized_internal = score_results(
                    normalized_internal,
                    intent=parsed_intent,
                    min_price=min_price_filter,
                    max_price=max_price_filter,
                    desire_tier=row.desire_tier,
                    is_service=row.is_service,
                    service_category=row.service_category,
                )
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
                        yield f"data: {json.dumps({'provider': status.provider_id, 'results': [r.model_dump() for r in search_results], 'status': status.model_dump(), 'providers_remaining': 0, 'more_incoming': True, 'phase': 'discovery_results', 'coverage_status': eval_result.status, 'discovery_session_id': discovery_session_id, 'total_results_so_far': len(all_results), 'user_message': 'I’m expanding the search beyond our current vendor database.'})}\n\n"

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
                bookmarked_vendors, bookmarked_items, _ = await _load_search_state_for_bids(
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
                coverage_assessment = await _record_vendor_coverage_gap_if_needed(
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
                "user_message": requester_message or (None if evaluation.status == "sufficient" else "I’m expanding the search beyond our current vendor database."),
            }
            yield f"data: {json.dumps(final_event)}\n\n"
            return

        generator = sourcing_repo.search_streaming(
            sanitized_query,
            providers=body.providers,
            min_price=min_price_filter,
            max_price=max_price_filter,
            desire_tier=row.desire_tier,
            vendor_query=vendor_query,
            intent_payload=intent_payload,
            query_embedding=query_embedding,  # shared — vendor_provider skips its own embed call
        )

        async def get_next_batch():
            try:
                # Use anext to manually pull from the async generator
                return await anext(generator)
            except StopAsyncIteration:
                return None

        async def process_batch(provider_name, results, status, providers_remaining):
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
            
            persisted_bid_ids = set()
            if filtered_batch:
                try:
                    normalized_batch = normalize_generic_results(filtered_batch, provider_name)
                    if normalized_batch:
                        normalized_batch = score_results(
                            normalized_batch,
                            intent=parsed_intent,
                            min_price=min_price_filter,
                            max_price=max_price_filter,
                            desire_tier=row.desire_tier,
                        )

                        # Quantum reranking: embed ALL results + score against user intent
                        if quantum_reranker and query_embedding:
                            try:
                                from sourcing.vendor_provider import _embed_texts as _batch_embed

                                # Build result dicts — reuse existing embeddings, collect texts to embed
                                results_for_quantum = []
                                texts_to_embed = []  # (idx_in_batch, text)
                                for idx, res in enumerate(normalized_batch):
                                    existing_emb = res.raw_data.get("embedding") if res.raw_data else None
                                    rd = {"_idx": idx, "title": res.title, "embedding": existing_emb}
                                    results_for_quantum.append(rd)
                                    if not existing_emb:
                                        # Rich text: title + merchant + description for better semantic matching
                                        desc = ""
                                        if res.raw_data:
                                            desc = str(res.raw_data.get("snippet", "") or res.raw_data.get("description", "") or "")
                                        parts = [res.title, res.merchant_name]
                                        if desc:
                                            parts.append(desc[:200])
                                        texts_to_embed.append((idx, " | ".join(parts)))

                                # Batch-embed titles that don't have embeddings (one API call)
                                if texts_to_embed:
                                    embed_texts = [t for _, t in texts_to_embed]
                                    new_embeddings = await _batch_embed(embed_texts)
                                    if new_embeddings and len(new_embeddings) == len(texts_to_embed):
                                        for (idx, _), emb in zip(texts_to_embed, new_embeddings):
                                            results_for_quantum[idx]["embedding"] = emb

                                # Run quantum reranker on ALL results with embeddings
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
                                    q_count = len(score_map)
                                    emb_new = len(texts_to_embed) if texts_to_embed else 0
                                    emb_reused = len(normalized_batch) - emb_new
                                    logger.info(f"[SEARCH STREAM] Quantum reranked {q_count}/{len(normalized_batch)} from {provider_name} (embedded {emb_new} new, reused {emb_reused})")
                            except Exception as qe:
                                logger.warning(f"[SEARCH STREAM] Quantum reranking failed for {provider_name}: {qe}")

                        # Filter out low-quality vendor_directory results after scoring.
                        # Vendors with near-zero relevance for product queries are noise.
                        VENDOR_MIN_SCORE = 0.15
                        if provider_name == "vendor_directory":
                            before_count = len(normalized_batch)
                            normalized_batch = [
                                r for r in normalized_batch
                                if (r.provenance.get("score", {}).get("combined", 1.0) >= VENDOR_MIN_SCORE)
                            ]
                            dropped = before_count - len(normalized_batch)
                            if dropped:
                                logger.info(f"[SEARCH STREAM] Filtered {dropped} low-score vendor results (< {VENDOR_MIN_SCORE})")

                        if normalized_batch:
                            async with db_lock:
                                persisted_bids = await sourcing_service._persist_results(row_id, normalized_batch)
                                persisted_bid_ids.update(b.id for b in persisted_bids if b.id)
                except Exception as err:
                    logger.error(f"[SEARCH STREAM] Failed to persist results for provider {provider_name}: {err}")
                    
            return provider_name, filtered_batch, status, persisted_bid_ids

        pending_fetches = set()
        pending_fetches.add(asyncio.create_task(get_next_batch()))
        pending_processes = set()
        
        # We need to compute total providers from the body to know when we're fully done
        # search_streaming yields providers_remaining, but we also want a fallback
        # in case all tasks fail. We'll rely on the tasks draining.
        providers_completed = 0
        last_providers_remaining = len(body.providers) if body.providers else 8 # rough estimate

        while pending_fetches or pending_processes:
            done, _ = await asyncio.wait(
                pending_fetches | pending_processes,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                if task in pending_fetches:
                    pending_fetches.remove(task)
                    try:
                        batch = await task
                        if batch is not None:
                            # Start fetching the next batch immediately
                            pending_fetches.add(asyncio.create_task(get_next_batch()))
                            
                            provider_name, results, status, providers_remaining = batch
                            last_providers_remaining = providers_remaining
                            all_statuses.append(status)
                            
                            # Start processing this batch in the background
                            pending_processes.add(asyncio.create_task(
                                process_batch(provider_name, results, status, providers_remaining)
                            ))
                    except Exception as e:
                        logger.error(f"[SEARCH STREAM] Generator error: {e}")
                        
                elif task in pending_processes:
                    pending_processes.remove(task)
                    try:
                        provider_name, filtered_batch, status, persisted_bid_ids = await task
                        providers_completed += 1
                        
                        all_persisted_bid_ids.update(persisted_bid_ids)
                        all_results.extend(filtered_batch)
                        
                        # We calculate remaining based on pending processes + last known remaining from fetch
                        # This ensures the frontend doesn't think we're done until all processing is complete
                        actual_remaining = last_providers_remaining + len(pending_processes)
                        
                        event_data = {
                            "provider": provider_name,
                            "results": [r.model_dump() for r in filtered_batch],
                            "status": status.model_dump(),
                            "providers_remaining": actual_remaining,
                            "more_incoming": actual_remaining > 0,
                            "total_results_so_far": len(all_results),
                        }
                        
                        yield f"data: {json.dumps(event_data)}\n\n"
                    except Exception as e:
                        logger.error(f"[SEARCH STREAM] Processing error: {e}")
        
        # Supersede stale bids AFTER all providers complete.
        # Only bids not returned by any provider in this search get retired.
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
            bookmarked_vendors, bookmarked_items, _ = await _load_search_state_for_bids(
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
            await sourcing_service.supersede_stale_bids(row_id, all_persisted_bid_ids | protected_existing_ids)
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
            coverage_assessment = await _record_vendor_coverage_gap_if_needed(
                session=session,
                row=row,
                user_id=user_id,
                search_query=sanitized_query,
                results=all_results,
                provider_statuses=all_statuses,
            )
            if coverage_assessment and not user_message:
                user_message = _build_vendor_coverage_user_message(requester, is_guest)
        except Exception as e:
            logger.error(f"[SEARCH STREAM] Failed to update row status after completion: {e}")
            try:
                coverage_assessment = await _record_vendor_coverage_gap_if_needed(
                    session=session,
                    row=row,
                    user_id=user_id,
                    search_query=sanitized_query,
                    results=all_results,
                    provider_statuses=all_statuses,
                )
                if coverage_assessment and not user_message:
                    user_message = _build_vendor_coverage_user_message(requester, is_guest)
            except Exception as e:
                logger.error(f"[SEARCH STREAM] Failed to record vendor coverage gap: {e}")

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
