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

        combined = (ps * 0.35) + (rs * 0.30) + (qs * 0.25) + (db * 0.10)

        # Enrich provenance with score breakdown
        r.provenance["score"] = {
            "combined": round(combined, 4),
            "price": round(ps, 4),
            "relevance": round(rs, 4),
            "quality": round(qs, 4),
            "diversity": round(db, 4),
        }

        scored.append((combined, r))

    # Sort descending by combined score, stable sort preserves original order for ties
    scored.sort(key=lambda x: x[0], reverse=True)

    logger.info(
        f"[Scorer] Ranked {len(scored)} results. "
        f"Top score: {scored[0][0]:.3f}, Bottom: {scored[-1][0]:.3f}"
    )

    return [r for _, r in scored]


def _price_score(
    result: NormalizedResult,
    min_price: Optional[float],
    max_price: Optional[float],
) -> float:
    """Score how well the result's price fits the requested budget."""
    price = result.price
    if price is None or price <= 0:
        return 0.3  # Unknown price — neutral-low score

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
    """Score how relevant the result is to the search intent."""
    if not intent:
        return 0.5

    score = 0.0
    title_lower = result.title.lower() if result.title else ""

    # Brand match
    if intent.brand:
        brand_lower = intent.brand.lower()
        if brand_lower in title_lower:
            score += 0.3
        elif any(word in title_lower for word in brand_lower.split()):
            score += 0.15

    # Keyword match
    if intent.keywords:
        matched = sum(1 for kw in intent.keywords if kw.lower() in title_lower)
        kw_ratio = matched / len(intent.keywords) if intent.keywords else 0
        score += kw_ratio * 0.4

    # Category match (looser — check if category words appear in title)
    if intent.product_category:
        cat_words = intent.product_category.lower().replace("_", " ").split()
        cat_matched = sum(1 for w in cat_words if w in title_lower)
        cat_ratio = cat_matched / max(len(cat_words), 1)
        score += cat_ratio * 0.2

    # Base relevance — all results have some relevance since they came from a targeted search
    score += 0.1

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
