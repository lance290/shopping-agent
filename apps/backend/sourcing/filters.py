"""Unified result/bid filtering — single source of truth for all search paths.

Replaces 4 separate inline filter implementations that had inconsistent behavior.
Called by: rows.py, rows_search.py (streaming + non-streaming), service.py
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def should_include_result(
    price: Optional[float],
    source: str,
    desire_tier: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_service_provider: bool = False,
) -> bool:
    """Single source of truth for price filtering.

    Rules:
    - price=None (quote-based / vendor directory): ALWAYS include
    - No explicit min/max set: ALWAYS include
    - Otherwise: apply min/max price as hard filters
    """
    # Quote-based results always pass (no price to filter on).
    # This naturally includes vendor_directory results (price=None).
    if price is None:
        return True

    # No filters set — pass everything
    if min_price is None and max_price is None:
        return True

    # Apply hard price filters
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False

    return True


def should_exclude_by_exclusions(
    title: str,
    merchant: str,
    merchant_domain: str,
    exclude_keywords: List[str],
    exclude_merchants: List[str],
) -> bool:
    """Post-search exclusion filter using LLM-extracted exclusion lists.

    Amazon/Rainforest API does NOT support negative keywords, so we must
    filter results after they come back. The LLM populates exclude_keywords
    and exclude_merchants from user statements like "no digital", "NOT Amazon".

    Returns True if the result should be EXCLUDED.
    """
    if not exclude_keywords and not exclude_merchants:
        return False

    title_lower = title.lower() if title else ""
    merchant_lower = merchant.lower() if merchant else ""
    domain_lower = merchant_domain.lower() if merchant_domain else ""

    # Check merchant exclusions (e.g. user said "NOT Amazon")
    for excluded in exclude_merchants:
        ex = excluded.lower()
        if ex in merchant_lower or ex in domain_lower:
            logger.debug(f"[EXCLUSION] Dropping '{title}' — merchant '{merchant}' matches excluded '{excluded}'")
            return True

    # Check keyword exclusions (e.g. user said "no digital")
    for excluded in exclude_keywords:
        ex = excluded.lower()
        if ex in title_lower:
            logger.debug(f"[EXCLUSION] Dropping '{title}' — title matches excluded keyword '{excluded}'")
            return True

    return False
