"""Vendor coverage gap detection and recording."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Row, User, VendorCoverageGap
from sourcing import SearchResult, ProviderStatusSnapshot
from services.llm import assess_vendor_coverage

logger = logging.getLogger(__name__)


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
    base = "I'm not seeing strong vendor coverage for this request yet, so I've flagged it internally and we'll expand the vendor set as quickly as we can."
    if not missing:
        return base
    if len(missing) == 2:
        return base + " When you have a moment, send me your name and company so I can attach them to the sourcing request."
    return base + f" When you have a moment, send me your {missing[0]} so I can attach it to the sourcing request."


async def record_vendor_coverage_gap_if_needed(
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
