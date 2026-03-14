"""Individual scoring dimension functions for the aggregation layer.

Extracted from scorer.py. Each function scores a NormalizedResult on one
dimension (price, relevance, quality, geo, FTS, constraints, diversity,
source fit).
"""

import logging
import math
import re
import unicodedata
from typing import Dict, List, Optional

from sourcing.location import neutral_geo_score
from sourcing.models import NormalizedResult, SearchIntent

logger = logging.getLogger(__name__)


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
