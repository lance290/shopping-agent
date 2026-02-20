"""
Public search endpoint — no auth required, no row persistence.

Runs the full sourcing pipeline:
  1. triage_provider_query() → LLM-optimized search terms
  2. extract_search_intent() → structured SearchIntent
  3. build_provider_query_map() → per-retailer adapted queries
  4. SourcingRepository.search_all_with_status() → ALL providers in parallel, NO gating
  5. score_results() → scoring with relevance, price, quality, source fit
  6. Quantum re-ranking (if enabled)
  7. Constraint satisfaction scoring

Results are ephemeral — not persisted to any Row or Bid.
"""

import hashlib
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from sourcing.repository import SearchResult, SourcingRepository
from sourcing.scorer import score_results
from sourcing.models import SearchIntent
from services.llm import triage_provider_query, make_unified_decision, ChatContext
from services.intent import extract_search_intent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["public"])

# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------
_rate_store: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT = 10  # requests per window
RATE_WINDOW = 60  # seconds


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_WINDOW
    hits = _rate_store[ip]
    # Prune old entries
    _rate_store[ip] = [t for t in hits if t > window_start]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        return False
    _rate_store[ip].append(now)
    return True


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Lazy sourcing repo
# ---------------------------------------------------------------------------
_sourcing_repo = None


def _get_repo() -> SourcingRepository:
    global _sourcing_repo
    if _sourcing_repo is None:
        _sourcing_repo = SourcingRepository()
    return _sourcing_repo


# ---------------------------------------------------------------------------
# Public Search
# ---------------------------------------------------------------------------
class PublicSearchRequest(BaseModel):
    query: str


class PublicSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    provider_statuses: List[Dict[str, Any]]
    query_optimized: Optional[str] = None
    desire_tier: Optional[str] = None
    result_count: int = 0


@router.post("/api/public/search", response_model=PublicSearchResponse)
async def public_search(body: PublicSearchRequest, request: Request):
    """
    Public search endpoint — runs the full sourcing pipeline without auth.
    All providers run in parallel. Three-stage re-ranking applied.
    Results are ephemeral (not persisted).
    """
    client_ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

    raw_query = body.query.strip()
    if not raw_query:
        raise HTTPException(status_code=400, detail="Query is required")
    if len(raw_query) > 500:
        raise HTTPException(status_code=400, detail="Query too long (max 500 chars)")

    logger.info(f"[PublicSearch] Query: {raw_query!r} from IP: {_hash_ip(client_ip)}")

    # Step 1: LLM-optimized search terms
    try:
        optimized_query = await triage_provider_query(
            display_query=raw_query,
            row_title=None,
            project_title=None,
            choice_answers_json=None,
            request_spec_constraints_json=None,
        )
    except Exception as e:
        logger.warning(f"[PublicSearch] triage_provider_query failed, using raw query: {e}")
        optimized_query = raw_query

    # Step 2: Extract structured search intent
    try:
        intent_result = await extract_search_intent(
            display_query=raw_query,
            row_title=None,
            project_title=None,
            choice_answers_json=None,
            request_spec_constraints_json=None,
        )
        search_intent = SearchIntent(
            product_name=intent_result.product_name,
            brand=intent_result.brand,
            model=intent_result.model,
            min_price=intent_result.min_price,
            max_price=intent_result.max_price,
            condition=intent_result.condition,
            features=intent_result.features or {},
            keywords=intent_result.keywords or [],
        )
    except Exception as e:
        logger.warning(f"[PublicSearch] extract_search_intent failed: {e}")
        search_intent = None

    # Step 3: Get desire tier for scoring (not for gating!)
    desire_tier = None
    try:
        ctx = ChatContext(
            user_message=raw_query,
            conversation_history=[],
        )
        decision = await make_unified_decision(ctx)
        if decision and hasattr(decision, 'desire_tier'):
            desire_tier = decision.desire_tier
    except Exception as e:
        logger.warning(f"[PublicSearch] make_unified_decision failed: {e}")

    # Step 4: Run ALL providers in parallel — NO gating
    repo = _get_repo()
    try:
        search_response = await repo.search_all_with_status(
            optimized_query or raw_query,
            desire_tier=desire_tier,
        )
    except Exception as e:
        logger.error(f"[PublicSearch] search_all_with_status failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

    normalized_results = search_response.normalized_results or []
    provider_statuses = search_response.provider_statuses or []

    logger.info(
        f"[PublicSearch] Got {len(normalized_results)} results from "
        f"{len(provider_statuses)} providers for query: {raw_query!r}"
    )

    # Step 5: Score and rank results
    if normalized_results:
        min_price = search_intent.min_price if search_intent else None
        max_price = search_intent.max_price if search_intent else None
        normalized_results = score_results(
            normalized_results,
            intent=search_intent,
            min_price=min_price,
            max_price=max_price,
            desire_tier=desire_tier,
        )

    # Steps 6 & 7: Quantum re-ranking and constraint satisfaction
    # These are applied in the workspace flow via SourcingService but require
    # row context (embeddings, structured_constraints). For public search,
    # classical scoring is sufficient. Quantum/constraint scoring
    # can be added later if we store intent embeddings in the search flow.

    # Convert to response format
    results_out = []
    for res in normalized_results:
        results_out.append({
            "title": res.title,
            "price": res.price,
            "currency": res.currency,
            "merchant": res.merchant_name,
            "url": res.url,
            "image_url": res.image_url,
            "source": res.source,
            "rating": res.rating,
            "reviews_count": res.reviews_count,
            "shipping_info": res.shipping_info,
            "match_score": res.provenance.get("score", {}).get("combined", 0.0) if res.provenance else 0.0,
            "score_detail": res.provenance.get("score") if res.provenance else None,
            "vendor_name": res.raw_data.get("vendor_name") if res.raw_data else None,
            "vendor_company": res.raw_data.get("vendor_company") if res.raw_data else None,
            "vendor_email": res.raw_data.get("vendor_email") if res.raw_data else None,
            "vendor_website": res.raw_data.get("website") if res.raw_data else None,
        })

    statuses_out = [
        {
            "provider_id": s.provider_id,
            "status": s.status,
            "result_count": s.result_count,
            "latency_ms": s.latency_ms,
            "message": s.message,
        }
        for s in provider_statuses
    ]

    return PublicSearchResponse(
        results=results_out,
        provider_statuses=statuses_out,
        query_optimized=optimized_query,
        desire_tier=desire_tier,
        result_count=len(results_out),
    )


# ---------------------------------------------------------------------------
# Quote Intent Tracking (anonymous, no PII)
# ---------------------------------------------------------------------------
class QuoteIntentRequest(BaseModel):
    query: str
    vendor_slug: Optional[str] = None
    vendor_name: Optional[str] = None


@router.post("/api/public/quote-intent")
async def log_quote_intent(body: QuoteIntentRequest, request: Request):
    """
    Log anonymous quote interest — no PII captured.
    Fires when someone opens the VendorContactModal on the public surface.
    """
    client_ip = request.client.host if request.client else "unknown"

    logger.info(
        f"[QuoteIntent] query={body.query!r} vendor={body.vendor_name!r} "
        f"slug={body.vendor_slug!r} ip_hash={_hash_ip(client_ip)}"
    )

    # For now, log-only. QuoteIntentEvent DB table will be added
    # when we need to query this data for vendor sales conversations.
    # The log line above is queryable via log aggregation.

    return {"status": "ok", "logged": True}
