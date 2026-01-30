"""Sourcing package scaffolding for Search Architecture v2."""

from .models import (
    AggregatedSearchResponse,
    NormalizedResult,
    ProviderQuery,
    ProviderQueryMap,
    ProviderStatusSnapshot,
    SearchIntent,
)
from .repository import (
    SearchResult,
    SearchResultWithStatus,
    SourcingProvider,
    SourcingRepository,
    extract_merchant_domain,
    normalize_url,
)

__all__ = [
    "AggregatedSearchResponse",
    "NormalizedResult",
    "ProviderQuery",
    "ProviderQueryMap",
    "ProviderStatusSnapshot",
    "SearchIntent",
    "SearchResult",
    "SearchResultWithStatus",
    "SourcingProvider",
    "SourcingRepository",
    "extract_merchant_domain",
    "normalize_url",
]
