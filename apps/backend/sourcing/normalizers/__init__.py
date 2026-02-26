"""Result normalizers for Search Architecture v2."""

from __future__ import annotations

from typing import Callable, Dict, List
from urllib.parse import urlsplit

from sourcing.models import NormalizedResult
from sourcing.repository import SearchResult
from sourcing.utils.currency import convert_currency
from sourcing.utils.url import canonicalize_url


def _extract_merchant_domain(url: str) -> str:
    try:
        parsed = urlsplit(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return "unknown"


def _build_provenance(result: SearchResult, provider_id: str) -> dict:
    """Build structured provenance data from search result fields."""
    matched_features = []

    if result.rating is not None and result.rating > 4.0:
        matched_features.append(f"Highly rated ({result.rating:.1f}★)")
    if result.shipping_info:
        matched_features.append(result.shipping_info)
    if result.reviews_count is not None and result.reviews_count > 100:
        matched_features.append(f"Popular ({result.reviews_count:,} reviews)")
    if getattr(result, "match_score", 0) > 0.7:
        matched_features.append("Strong match for your search")

    provenance = {
        "product_info": {
            "title": result.title,
            "brand": None,
            "specs": {},
        },
        "matched_features": matched_features,
        "chat_excerpts": [],
        "source_provider": provider_id,
    }

    # Preserve vector similarity score for the scorer (vendor_directory uses this)
    ms = getattr(result, "match_score", None)
    if ms is not None and ms > 0:
        provenance["vector_similarity"] = float(ms)

    return provenance


def _normalize_result(result: SearchResult, provider_id: str) -> NormalizedResult:
    canonical_url = canonicalize_url(result.url)
    merchant_domain = result.merchant_domain or _extract_merchant_domain(result.url)
    converted_price = convert_currency(result.price, result.currency, "USD")
    normalized_price = converted_price if converted_price is not None else result.price
    normalized_currency = "USD" if converted_price is not None else (result.currency or "USD")

    return NormalizedResult(
        title=result.title,
        url=result.url,
        source=provider_id,
        price=normalized_price,
        currency=normalized_currency,
        price_original=result.price,
        currency_original=result.currency,
        canonical_url=canonical_url,
        merchant_name=result.merchant,
        merchant_domain=merchant_domain,
        image_url=result.image_url,
        rating=result.rating,
        reviews_count=result.reviews_count,
        shipping_info=result.shipping_info,
        raw_data={"provider_id": provider_id},
        provenance=_build_provenance(result, provider_id),
    )


def normalize_generic_results(results: List[SearchResult], provider_id: str) -> List[NormalizedResult]:
    return [_normalize_result(result, provider_id) for result in results]


def normalize_results_for_provider(
    provider_id: str, results: List[SearchResult]
) -> List[NormalizedResult]:
    normalizer = NORMALIZER_REGISTRY.get(provider_id)
    if not normalizer:
        return normalize_generic_results(results, provider_id)
    return normalizer(results)


from sourcing.normalizers.google_cse import normalize_google_cse_results
from sourcing.normalizers.rainforest import normalize_rainforest_results
from sourcing.normalizers.ebay import normalize_ebay_results

NORMALIZER_REGISTRY: Dict[str, Callable[[List[SearchResult]], List[NormalizedResult]]] = {
    "rainforest": normalize_rainforest_results,
    "google_cse": normalize_google_cse_results,
}

__all__ = [
    "normalize_results_for_provider",
    "normalize_generic_results",
    "normalize_rainforest_results",
    "normalize_google_cse_results",
    "normalize_ebay_results",
]
