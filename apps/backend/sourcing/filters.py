"""Unified result/bid filtering — single source of truth for all search paths.

Replaces 4 separate inline filter implementations that had inconsistent behavior.
Called by: rows.py, rows_search.py (streaming + non-streaming), service.py
"""

import logging
from typing import Optional

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
