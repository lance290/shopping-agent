"""
Result scoring and ranking for the Search Architecture v2 aggregation layer.

Scores each NormalizedResult on multiple dimensions, then sorts by combined score.
Dimensions:
  - price_score: How well the price fits the user's budget (0-1)
  - relevance_score: Keyword/brand match quality (0-1)
  - quality_score: Rating, reviews, shipping info (0-1)
  - diversity_bonus: Small bonus for results from underrepresented providers (0-0.1)
"""

import logging
from typing import Dict, List, Optional

from sourcing.location import location_weight_profile
from sourcing.models import NormalizedResult, SearchIntent
from sourcing.scorer_dimensions import (  # noqa: F401 — re-exported
    _constraint_score,
    _contains_any_term,
    _diversity_bonus,
    _fts_score,
    _geo_score,
    _important_terms,
    _price_score,
    _quality_score,
    _relevance_score,
    _score_value,
    _source_fit_score,
    _specific_terms,
    _tier_relevance_score,
    _vendor_searchable_text,
)

logger = logging.getLogger(__name__)


def score_results(
    results: List[NormalizedResult],
    intent: Optional[SearchIntent] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    desire_tier: Optional[str] = None,  # DEPRECATED — kept for backwards compat, use is_service/service_category
    is_service: Optional[bool] = None,
    service_category: Optional[str] = None,
    endorsement_boosts: Optional[Dict[int, float]] = None,
) -> List[NormalizedResult]:
    """
    Score and rank a list of NormalizedResults.

    Returns a new list sorted by descending combined score.
    Each result's provenance dict is enriched with a 'score' key.
    """
    if not results:
        return results

    # Bridge: derive is_service from desire_tier if caller hasn't migrated yet
    if is_service is None and desire_tier:
        is_service = desire_tier in ("service", "bespoke", "high_value", "advisory")

    scored: List[tuple[float, NormalizedResult]] = []

    # Count results per source for diversity bonus
    source_counts: Dict[str, int] = {}
    for r in results:
        source_counts[r.source] = source_counts.get(r.source, 0) + 1
    total = len(results)

    for r in results:
        ps = _price_score(r, min_price, max_price)
        rs = _relevance_score(r, intent)
        qs = _quality_score(r)
        db = _diversity_bonus(r.source, source_counts, total)
        sf = _source_fit_score(r.source, is_service, service_category)
        fts_score = _fts_score(r)
        constraint_score = _constraint_score(r)
        geo_score = _geo_score(r, intent, rs, fts_score, constraint_score)
        weights = location_weight_profile(
            intent.location_context.relevance if intent and intent.location_context else "none"
        )
        semantic_signal = rs if r.source != "vendor_directory" else (r.raw_data.get("search_metadata", {}) or {}).get("semantic_score", rs)
        semantic_weight = weights["semantic"]
        fts_weight = weights["fts"]
        geo_weight = weights["geo"]
        constraint_weight = weights["constraint"]

        base = (
            semantic_signal * semantic_weight
            + fts_score * fts_weight
            + geo_score * geo_weight
            + constraint_score * constraint_weight
        )
        support_bonus = ((ps * 0.4) + (qs * 0.4) + (db * 0.2)) * 0.05
        vendor_id = r.raw_data.get("vendor_id") if isinstance(r.raw_data, dict) else None
        endorsement_boost = 0.0
        if isinstance(vendor_id, int) and endorsement_boosts:
            endorsement_boost = float(endorsement_boosts.get(vendor_id, 0.0) or 0.0)
        combined = min(1.0, (min(1.0, base + support_bonus) * (0.3 + 0.7 * sf)) + endorsement_boost)

        # DEFENSE-IN-DEPTH: multiplicative geo penalty.
        # When location is important and a vendor_directory result has NO geo
        # match (geo_score==0), crush its score so local Apify/web results
        # always outrank generic national brands.
        geo_penalty = 1.0
        location_mode = (
            intent.location_context.relevance
            if intent and intent.location_context
            else "none"
        )
        if (
            r.source == "vendor_directory"
            and geo_score == 0.0
            and location_mode in {"service_area", "vendor_proximity"}
        ):
            geo_penalty = 0.15 if location_mode == "service_area" else 0.10
            combined = combined * geo_penalty

        # Enrich provenance with score breakdown
        r.provenance["score"] = {
            "combined": round(combined, 4),
            "relevance": round(rs, 4),
            "semantic": round(float(semantic_signal), 4),
            "fts": round(fts_score, 4),
            "geo": round(geo_score, 4),
            "geo_penalty": round(geo_penalty, 4),
            "constraint": round(constraint_score, 4),
            "source_fit": round(sf, 4),
            "price": round(ps, 4),
            "quality": round(qs, 4),
            "diversity": round(db, 4),
            "endorsement_boost": round(endorsement_boost, 4),
        }

        scored.append((combined, r))

    # Sort descending by combined score, stable sort preserves original order for ties
    scored.sort(key=lambda x: x[0], reverse=True)

    logger.info(
        f"[Scorer] Ranked {len(scored)} results. "
        f"Top score: {scored[0][0]:.3f}, Bottom: {scored[-1][0]:.3f}"
    )

    return [r for _, r in scored]


def filter_vendor_results(
    results: List[NormalizedResult],
    *,
    intent: Optional[SearchIntent] = None,
    is_service: Optional[bool] = None,
    service_category: Optional[str] = None,
) -> List[NormalizedResult]:
    return [
        result
        for result in results
        if _should_keep_vendor_result(
            result,
            intent=intent,
            is_service=is_service,
            service_category=service_category,
        )
    ]


def _should_keep_vendor_result(
    result: NormalizedResult,
    *,
    intent: Optional[SearchIntent],
    is_service: Optional[bool],
    service_category: Optional[str],
) -> bool:
    if result.source != "vendor_directory":
        return True

    combined = _score_value(result, "combined")
    semantic = _score_value(result, "semantic")
    fts = _score_value(result, "fts")

    if combined < 0.15:
        return False

    if is_service or service_category:
        return combined >= 0.18

    if not intent:
        return combined >= 0.18

    searchable = _vendor_searchable_text(result)
    brand_terms = _important_terms(intent.brand)
    model_terms = _important_terms(intent.model)
    product_terms = _important_terms(intent.product_name)
    keyword_terms = _important_terms(" ".join(intent.keywords))
    category_terms = _important_terms(intent.product_category.replace("_", " ") if intent.product_category else None)

    brand_match = _contains_any_term(searchable, brand_terms)
    model_match = _contains_any_term(searchable, model_terms)
    specific_product_terms = _specific_terms(product_terms + keyword_terms)
    product_match = _contains_any_term(searchable, specific_product_terms)
    category_match = _contains_any_term(searchable, category_terms)

    if brand_terms:
        if brand_match:
            return combined >= 0.16
        return semantic >= 0.92 and (fts >= 0.12 or model_match or product_match)

    if model_terms:
        if model_match:
            return combined >= 0.16
        return semantic >= 0.92 and (fts >= 0.12 or product_match)

    if product_terms or keyword_terms:
        if product_match:
            return combined >= 0.16
        return combined >= 0.28 and semantic >= 0.90 and fts >= 0.12

    return combined >= 0.18
