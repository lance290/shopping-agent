"""Sourcing package scaffolding for Search Architecture v2."""

from .models import (
    AggregatedSearchResponse,
    NormalizedResult,
    ProviderQuery,
    ProviderQueryMap,
    ProviderStatusSnapshot,
    SearchIntent,
)
from .adapters import build_provider_query_map, available_provider_ids
from .taxonomy import DEFAULT_TAXONOMY_VERSION, resolve_category_label, resolve_category_path
from .repository import (
    SearchResult,
    SearchResultWithStatus,
    SourcingProvider,
    SourcingRepository,
    TicketmasterProvider,
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
    "TicketmasterProvider",
    "extract_merchant_domain",
    "normalize_url",
    "available_provider_ids",
    "build_provider_query_map",
    "DEFAULT_TAXONOMY_VERSION",
    "resolve_category_label",
    "resolve_category_path",
]
