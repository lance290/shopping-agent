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
import re
import unicodedata
from typing import Dict, List, Optional

from sourcing.location import location_weight_profile, neutral_geo_score
from sourcing.models import NormalizedResult, SearchIntent

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


def _score_value(result: NormalizedResult, key: str) -> float:
    provenance = result.provenance if isinstance(result.provenance, dict) else {}
    score = provenance.get("score", {}) if isinstance(provenance.get("score"), dict) else {}
    if key in score:
        try:
            return float(score.get(key) or 0.0)
        except (TypeError, ValueError):
            return 0.0
    search_metadata = result.raw_data.get("search_metadata", {}) if isinstance(result.raw_data, dict) else {}
    metadata_key = "semantic_score" if key == "semantic" else "fts_score" if key == "fts" else key
    try:
        return float(search_metadata.get(metadata_key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _vendor_searchable_text(result: NormalizedResult) -> str:
    parts: List[str] = [result.title or "", result.merchant_name or "", result.merchant_domain or ""]
    if isinstance(result.raw_data, dict):
        parts.append(str(result.raw_data.get("description") or ""))
        parts.append(str(result.raw_data.get("snippet") or ""))
        search_metadata = result.raw_data.get("search_metadata", {}) or {}
        if isinstance(search_metadata, dict):
            parts.append(str(search_metadata.get("vendor_category") or ""))
    normalized = " ".join(parts)
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return normalized.casefold()


def _important_terms(value: Optional[str]) -> List[str]:
    if not value:
        return []
    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return [
        token
        for token in re.findall(r"[a-z0-9]+", normalized.casefold())
        if len(token) >= 3 and token not in {"the", "and", "for", "with"}
    ]


def _contains_any_term(searchable: str, terms: List[str]) -> bool:
    return any(term in searchable for term in terms)


def _specific_terms(terms: List[str]) -> List[str]:
    generic = {
        "bag", "bags", "handbag", "handbags", "purse", "purses",
        "luxury", "goods", "accessories", "product", "products",
        "item", "items", "service", "services", "vendor", "vendors",
    }
    return [term for term in terms if term not in generic]


def _source_fit_score(source: str, is_service: Optional[bool], service_category: Optional[str] = None) -> float:
    """
    Score how well the source fits the request context.
    Replaces desire_tier-based _tier_relevance_score with context-derived signals.
    """
    BIG_BOX_PROVIDERS = {
        "rainforest", "ebay_browse", "google_shopping",
        "searchapi", "google_cse", "serpapi", "ticketmaster"
    }
    VENDOR_PROVIDERS = {"vendor_directory"}

    # Service requests → prefer vendor directory
    if is_service or service_category:
        if source in VENDOR_PROVIDERS:
            return 1.0
        if source in BIG_BOX_PROVIDERS:
            return 0.2  # Heavy penalty — Amazon doesn't sell private jets
        return 0.5

    # Product requests (default) → prefer big box
    if source in BIG_BOX_PROVIDERS:
        return 1.0
    if source in VENDOR_PROVIDERS:
        return 0.3  # Penalize but don't hide
    return 0.5


# DEPRECATED — kept for backwards compat during migration
def _tier_relevance_score(source: str, desire_tier: Optional[str]) -> float:
    """Deprecated: use _source_fit_score instead."""
    if not desire_tier:
        return 0.5
    is_service = desire_tier in ("service", "bespoke", "high_value", "advisory")
    return _source_fit_score(source, is_service)


def _price_score(
    result: NormalizedResult,
    min_price: Optional[float],
    max_price: Optional[float],
) -> float:
    """Score how well the result's price fits the requested budget."""
    price = result.price
    if price is None:
        return 0.5  # Quote-based (no fixed price) — neutral score
    if price <= 0:
        return 0.3  # Free or unknown — neutral-low score

    if min_price is None and max_price is None:
        return 0.5  # No budget constraint — neutral score

    # Calculate how centered the price is within the range
    if min_price is not None and max_price is not None:
        mid = (min_price + max_price) / 2
        span = max_price - min_price
        if span <= 0:
            return 1.0 if abs(price - mid) < 1 else 0.2
        # Distance from midpoint as fraction of half-span
        distance = abs(price - mid) / (span / 2)
        if distance <= 1.0:
            return 1.0 - (distance * 0.3)  # 0.7-1.0 within range
        else:
            return max(0.0, 0.7 - (distance - 1.0) * 0.5)  # Decays outside range

    if max_price is not None:
        if price <= max_price:
            return 0.8 + 0.2 * (1 - price / max_price)  # 0.8-1.0, cheaper is better
        return max(0.0, 0.5 - (price - max_price) / max_price)

    if min_price is not None:
        if price >= min_price:
            return 0.8
        return max(0.0, 0.5 - (min_price - price) / min_price)

    return 0.5


def _relevance_score(
    result: NormalizedResult,
    intent: Optional[SearchIntent],
) -> float:
    """Score how relevant the result is to the search intent.

    This is the most important scoring dimension — it determines whether
    a result actually matches what the user asked for.
    """
    # Vendor results with vector_similarity use embedding distance directly
    if result.provenance and isinstance(result.provenance, dict):
        vec_sim = result.provenance.get("vector_similarity")
        if vec_sim is not None and vec_sim > 0:
            # Normalize: similarity of 0.40 → 0.0, similarity of 0.65 → 1.0
            return max(0.0, min(1.0, (float(vec_sim) - 0.40) / 0.25))

    if not intent:
        return 0.5

    score = 0.0
    title_lower = result.title.lower() if result.title else ""
    # Also check merchant name and raw_data description for broader matching
    merchant_lower = result.merchant_name.lower() if result.merchant_name else ""
    desc_lower = ""
    if result.raw_data:
        desc_lower = str(result.raw_data.get("snippet", "") or result.raw_data.get("description", "")).lower()
    searchable = f"{title_lower} {merchant_lower} {desc_lower}"

    # Brand match (strong signal)
    if intent.brand:
        brand_lower = intent.brand.lower()
        if brand_lower in title_lower:
            score += 0.25
        elif brand_lower in searchable:
            score += 0.15
        elif any(word in searchable for word in brand_lower.split()):
            score += 0.08

    # Keyword match (strongest signal — these are the core "what" words)
    if intent.keywords:
        # Check against title first (strongest), then full searchable text
        title_matched = sum(1 for kw in intent.keywords if kw.lower() in title_lower)
        full_matched = sum(1 for kw in intent.keywords if kw.lower() in searchable)
        kw_count = len(intent.keywords)
        # Title matches are worth more than description matches
        title_ratio = title_matched / kw_count if kw_count else 0
        full_ratio = full_matched / kw_count if kw_count else 0
        score += title_ratio * 0.35 + (full_ratio - title_ratio) * 0.10

    # Product name match (if set, check if the product name appears in title)
    if intent.product_name:
        name_words = [w for w in intent.product_name.lower().split() if len(w) > 2]
        if name_words:
            name_matched = sum(1 for w in name_words if w in title_lower)
            score += (name_matched / len(name_words)) * 0.15

    # Category match (looser — check if category words appear)
    if intent.product_category:
        cat_words = intent.product_category.lower().replace("_", " ").split()
        cat_matched = sum(1 for w in cat_words if w in searchable)
        cat_ratio = cat_matched / max(len(cat_words), 1)
        score += cat_ratio * 0.10

    # Base relevance — results came from a targeted search, so some baseline
    score += 0.05

    return min(score, 1.0)


def _quality_score(result: NormalizedResult) -> float:
    """Score based on result quality signals (rating, reviews, shipping)."""
    score = 0.3  # Base quality

    # Rating (0-5 scale)
    if result.rating is not None and result.rating > 0:
        score += (result.rating / 5.0) * 0.35

    # Reviews count (log scale, caps at ~1000)
    if result.reviews_count is not None and result.reviews_count > 0:
        import math
        review_signal = min(math.log10(result.reviews_count + 1) / 3.0, 1.0)
        score += review_signal * 0.2

    # Has image
    if result.image_url:
        score += 0.05

    # Has shipping info
    if result.shipping_info:
        score += 0.1

    return min(score, 1.0)


def _fts_score(result: NormalizedResult) -> float:
    if not isinstance(result.raw_data, dict):
        return 0.0
    search_metadata = result.raw_data.get("search_metadata", {}) or {}
    try:
        return max(0.0, min(1.0, float(search_metadata.get("fts_score", 0.0))))
    except (TypeError, ValueError):
        return 0.0


def _constraint_score(result: NormalizedResult) -> float:
    provenance = result.provenance if isinstance(result.provenance, dict) else {}
    raw = provenance.get("constraint_score")
    if raw is None:
        search_metadata = result.raw_data.get("search_metadata", {}) if isinstance(result.raw_data, dict) else {}
        raw = search_metadata.get("constraint_score", 0.0)
    try:
        return max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return 0.0


def _geo_score(
    result: NormalizedResult,
    intent: Optional[SearchIntent],
    semantic_score: float,
    fts_score: float,
    constraint_score: float,
) -> float:
    if not intent or not intent.location_context:
        return 0.0
    if result.source != "vendor_directory":
        return 0.0
    mode = intent.location_context.relevance
    if mode == "none":
        return 0.0
    search_metadata = result.raw_data.get("search_metadata", {}) if isinstance(result.raw_data, dict) else {}
    raw_geo = search_metadata.get("geo_score")
    try:
        geo = float(raw_geo)
    except (TypeError, ValueError):
        geo = 0.0
    if geo > 0:
        return max(0.0, min(1.0, geo))
    return neutral_geo_score(mode, semantic_score, fts_score, constraint_score)


def _diversity_bonus(
    source: str,
    source_counts: Dict[str, int],
    total: int,
) -> float:
    """
    Small bonus for results from underrepresented providers.
    Encourages variety in the result set.
    """
    if total <= 1:
        return 0.5

    count = source_counts.get(source, 1)
    share = count / total

    # Underrepresented sources get a bonus
    if share < 0.2:
        return 1.0
    elif share < 0.4:
        return 0.7
    elif share < 0.6:
        return 0.4
    else:
        return 0.2
