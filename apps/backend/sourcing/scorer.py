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

from sourcing.models import NormalizedResult, SearchIntent

logger = logging.getLogger(__name__)


def score_results(
    results: List[NormalizedResult],
    intent: Optional[SearchIntent] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    desire_tier: Optional[str] = None,
) -> List[NormalizedResult]:
    """
    Score and rank a list of NormalizedResults.

    Returns a new list sorted by descending combined score.
    Each result's provenance dict is enriched with a 'score' key.
    """
    if not results:
        return results

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
        sf = _source_fit_score(r)
        am = _affiliate_multiplier(r.source)

        # Source fit is a soft multiplier — vendor vector similarity drives ranking
        base = (rs * 0.45) + (ps * 0.20) + (qs * 0.20) + (db * 0.15)
        combined = base * (0.3 + 0.7 * sf) * am

        # Enrich provenance with score breakdown
        r.provenance["score"] = {
            "combined": round(combined, 4),
            "relevance": round(rs, 4),
            "source_fit": round(sf, 4),
            "price": round(ps, 4),
            "quality": round(qs, 4),
            "diversity": round(db, 4),
            "affiliate_multiplier": round(am, 4),
        }

        scored.append((combined, r))

    # Sort descending by combined score, stable sort preserves original order for ties
    scored.sort(key=lambda x: x[0], reverse=True)

    logger.info(
        f"[Scorer] Ranked {len(scored)} results. "
        f"Top score: {scored[0][0]:.3f}, Bottom: {scored[-1][0]:.3f}"
    )

    return [r for _, r in scored]


def _source_fit_score(
    result: NormalizedResult,
) -> float:
    """
    Score how well the source fits the result, using LLM-derived signals only.

    For vendor_directory results, the vector similarity score already encodes
    semantic relevance (set by the embedding model). We just pass it through.

    For marketplace results, we return a neutral score — the relevance_score
    function handles keyword/brand matching for those.

    No hardcoded tier→provider matrices. No keyword heuristics.
    """
    # Vendor results: use vector similarity as the source-fit signal.
    # High similarity = the embedding model thinks this vendor is relevant.
    if result.source == "vendor_directory":
        vec_sim = result.provenance.get("vector_similarity")
        if vec_sim is not None:
            try:
                return max(0.3, min(1.0, float(vec_sim) * 1.5))
            except (ValueError, TypeError):
                pass
        return 0.5

    # All other sources: neutral — let relevance_score do the work
    return 0.5


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

    For vendor_directory results, the vector similarity score IS the
    relevance signal. The embedding model already understands that
    "Jettly" means private aviation and "Gepetto" means toy store —
    no keyword matching on vendor names needed.
    """
    # Vendor directory: use vector similarity directly as relevance
    # This is the LLM's understanding of semantic relevance.
    vec_sim = result.provenance.get("vector_similarity")
    if vec_sim is not None and result.source == "vendor_directory":
        # vec_sim is 0.45-0.62 for threshold 0.55 (1 - distance)
        # Scale to 0-1 range: 0.45 → 0.0, 0.62 → 1.0
        # (tighter matches get dramatically higher scores)
        scaled = max(0.0, min(1.0, (vec_sim - 0.40) / 0.25))
        return scaled

    if not intent:
        return 0.5

    score = 0.0
    title_lower = result.title.lower() if result.title else ""
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
        title_matched = sum(1 for kw in intent.keywords if kw.lower() in title_lower)
        full_matched = sum(1 for kw in intent.keywords if kw.lower() in searchable)
        kw_count = len(intent.keywords)
        title_ratio = title_matched / kw_count if kw_count else 0
        full_ratio = full_matched / kw_count if kw_count else 0
        score += title_ratio * 0.35 + (full_ratio - title_ratio) * 0.10

    # Product name match
    if intent.product_name:
        name_words = [w for w in intent.product_name.lower().split() if len(w) > 2]
        if name_words:
            name_matched = sum(1 for w in name_words if w in title_lower)
            score += (name_matched / len(name_words)) * 0.15

    # Category match
    if intent.product_category:
        cat_words = intent.product_category.lower().replace("_", " ").split()
        cat_matched = sum(1 for w in cat_words if w in searchable)
        cat_ratio = cat_matched / max(len(cat_words), 1)
        score += cat_ratio * 0.10

    # Base relevance
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


def _affiliate_multiplier(source: str) -> float:
    """
    Boost sources we have affiliate programs for; penalize those we don't.

    - rainforest (Amazon): boosted — we have Amazon Associates configured.
    - vendor_directory: neutral — our own vendors, always show.
    - Google Shopping (serpapi, searchapi, google_cse, google_shopping): penalized
      until we have affiliate coverage for those merchants.
    - ebay_browse: neutral for now — eBay Partner Network not yet configured.
    """
    BOOSTED = {"rainforest", "amazon"}
    PENALIZED = {"serpapi", "searchapi", "google_cse", "google_shopping"}

    if source in BOOSTED:
        return 1.25
    if source in PENALIZED:
        return 0.60
    return 1.0
