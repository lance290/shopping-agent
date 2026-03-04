from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import httpx
import os
import re
from urllib.parse import urlparse, urlencode
import asyncio
import time
import base64

from utils.security import redact_secrets_from_text
from sourcing.executors import run_provider_with_status
from sourcing.models import NormalizedResult, ProviderStatusSnapshot
from sourcing.metrics import log_provider_result


def extract_merchant_domain(url: str) -> str:
    """Extract the merchant domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return "unknown"


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("/"):
        return f"https://www.google.com{url}"
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("www."):
        return f"https://{url}"
    return url


# Redaction moved to utils.security.redact_secrets_from_text
# Keeping this alias for backward compatibility
redact_secrets = redact_secrets_from_text

class SearchResult(BaseModel):
    title: str
    price: Optional[float] = None
    currency: str = "USD"
    merchant: str
    url: str
    merchant_domain: str = ""
    click_url: str = ""
    match_score: float = 0.0
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    shipping_info: Optional[str] = None
    source: str
    bid_id: Optional[int] = None
    is_selected: bool = False
    is_liked: bool = False
    liked_at: Optional[str] = None


class SearchResultWithStatus(BaseModel):
    """Search results with provider status information."""
    results: List[SearchResult] = []
    normalized_results: List[NormalizedResult] = []
    provider_statuses: List[ProviderStatusSnapshot] = []
    all_providers_failed: bool = False
    user_message: Optional[str] = None

def compute_match_score(result: SearchResult, query: str) -> float:
    """
    Compute a basic relevance score for a search result.
    
    Factors:
        - Title contains query words
        - Has image
        - Has rating
        - Has reviews
        - Price is present
    
    Returns: 0.0 - 1.0
    """
    score = 0.0
    query_words = set(query.lower().split())
    title_words = set(result.title.lower().split())
    
    # Title relevance (0-0.4)
    if query_words:
        overlap = len(query_words & title_words)
        score += 0.4 * (overlap / len(query_words))
    
    # Has image (0.15)
    if result.image_url:
        score += 0.15
    
    # Has rating (0.15)
    if result.rating and result.rating > 0:
        score += 0.15
    
    # Has reviews (0.15)
    if result.reviews_count and result.reviews_count > 0:
        score += 0.15
    
    # Has price (0.15)
    if result.price and result.price > 0:
        score += 0.15
    
    return min(score, 1.0)


class SourcingProvider(ABC):
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        pass


# Provider classes extracted to separate files — re-exported for backward compat
from sourcing.providers_search import (  # noqa: F401
    SearchAPIProvider, SerpAPIProvider, ValueSerpProvider,
    ScaleSerpProvider, MockShoppingProvider, GoogleCustomSearchProvider,
    TicketmasterProvider,
)
from sourcing.providers_marketplace import (  # noqa: F401
    EbayBrowseProvider, RainforestAPIProvider,
)


class SourcingRepository:
    def __init__(self):
        self.providers: Dict[str, SourcingProvider] = {}
        
        # Initialize providers in priority order
        # SerpAPI - DISABLED (registration issues)
        # serpapi_key = os.getenv("SERPAPI_API_KEY")
        # if serpapi_key and serpapi_key != "demo":
        #     self.providers["serpapi"] = SerpAPIProvider(serpapi_key)
        
        # Rainforest API - Amazon search
        rainforest_key = os.getenv("RAINFOREST_API_KEY")
        rainforest_key_len = len(rainforest_key) if rainforest_key is not None else None
        rainforest_present = rainforest_key is not None and rainforest_key_len > 0
        print(
            f"[SourcingRepository] RAINFOREST_API_KEY present: {rainforest_present} "
            f"(is_none={rainforest_key is None}, len={rainforest_key_len})"
        )
        if rainforest_present:
            self.providers["amazon"] = RainforestAPIProvider(rainforest_key)

        # SerpAPI, ValueSerp, SearchAPI, ScaleSerp — DISABLED (Skimlinks conflict / registration issues)
        # serpapi_key = os.getenv("SERPAPI_API_KEY")
        # if serpapi_key and serpapi_key != "demo":
        #     self.providers["serpapi"] = SerpAPIProvider(serpapi_key)
        #
        # valueserp_key = os.getenv("VALUESERP_API_KEY")
        # if valueserp_key and valueserp_key != "demo":
        #     self.providers["valueserp"] = ValueSerpProvider(valueserp_key)
        #
        # searchapi_key = os.getenv("SEARCHAPI_API_KEY")
        # if searchapi_key and searchapi_key != "demo":
        #     self.providers["searchapi"] = SearchAPIProvider(searchapi_key)
        #
        # scaleserp_key = os.getenv("SCALESERP_API_KEY")
        # if scaleserp_key and scaleserp_key != "demo":
        #     self.providers["google_shopping"] = ScaleSerpProvider(scaleserp_key)
            
        # Kroger Product API - for grocery/household items
        kroger_client_id = os.getenv("KROGER_CLIENT_ID")
        kroger_client_secret = os.getenv("KROGER_CLIENT_SECRET")
        kroger_location_id = os.getenv("KROGER_LOCATION_ID")
        kroger_zip_code = os.getenv("KROGER_ZIP_CODE")
        if kroger_client_id and kroger_client_secret:
            from sourcing.kroger_provider import KrogerProvider
            self.providers["kroger"] = KrogerProvider(
                client_id=kroger_client_id,
                client_secret=kroger_client_secret,
                location_id=kroger_location_id,
                zip_code=kroger_zip_code,
            )
        
        # Other providers DISABLED - using only Rainforest for now
        # ValueSerp - cheap alternative
        # valueserp_key = os.getenv("VALUESERP_API_KEY")
        # if valueserp_key:
        #     self.providers["valueserp"] = ValueSerpProvider(valueserp_key)
        
        # Google Custom Search - DISABLED
        # google_key = os.getenv("GOOGLE_CSE_API_KEY")
        # google_cx = os.getenv("GOOGLE_CSE_CX")
        # if google_key and google_cx:
        #     self.providers["google_cse"] = GoogleCustomSearchProvider(google_key, google_cx)
        
        # SearchAPI (original)
        # searchapi_key = os.getenv("SEARCHAPI_API_KEY")
        # if searchapi_key:
        #     self.providers["searchapi"] = SearchAPIProvider(searchapi_key)

        # eBay Browse API (official)
        ebay_client_id = os.getenv("EBAY_CLIENT_ID")
        ebay_client_secret = os.getenv("EBAY_CLIENT_SECRET")
        ebay_marketplace_id = os.getenv("EBAY_MARKETPLACE_ID", "EBAY-US")
        if ebay_client_id and ebay_client_secret:
            self.providers["ebay"] = EbayBrowseProvider(ebay_client_id, ebay_client_secret, ebay_marketplace_id)
            print(f"[SourcingRepository] eBay Browse provider initialized")
        
        # Ticketmaster Discovery API — event tickets
        ticketmaster_key = os.getenv("TICKETMASTER_API_KEY")
        if ticketmaster_key:
            self.providers["ticketmaster"] = TicketmasterProvider(ticketmaster_key)
            print(f"[SourcingRepository] Ticketmaster provider initialized")

        # Vendor Directory — pgvector semantic search (always runs)
        from sourcing.vendor_provider import VendorDirectoryProvider
        db_url = os.getenv("DATABASE_URL", "")
        if db_url:
            # Ensure asyncpg driver
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            self.providers["vendor_directory"] = VendorDirectoryProvider(db_url)

        use_mock_setting = (os.getenv("USE_MOCK_SEARCH", "auto") or "").strip().lower()
        if use_mock_setting in ("1", "true", "yes", "always"):
            self.providers["mock"] = MockShoppingProvider()
        elif use_mock_setting == "auto":
            if len(self.providers) == 0:
                self.providers["mock"] = MockShoppingProvider()

    # Provider alias map: user-facing name → internal provider key
    _PROVIDER_ALIASES: Dict[str, str] = {
        "rainforest": "amazon",
        "google": "serpapi",
        "ebay_browse": "ebay",
    }

    def _normalize_provider_filter(self, provider_names: List[str]) -> set:
        """Resolve provider aliases to canonical internal names."""
        resolved = set()
        for name in provider_names:
            canonical = self._PROVIDER_ALIASES.get(name, name)
            resolved.add(canonical)
        return resolved

    async def search_all(self, query: str, **kwargs) -> List[SearchResult]:
        """Search all providers and return results only (backwards compatible)."""
        result = await self.search_all_with_status(query, **kwargs)
        return result.results

    def _filter_providers_by_tier(self, providers: Dict[str, "SourcingProvider"], desire_tier: Optional[str] = None) -> Dict[str, "SourcingProvider"]:
        """
        Gate providers based on desire tier.
        
        Only exclude MARKETPLACE-specific providers (Amazon via rainforest, eBay via ebay_browse)
        for service/bespoke/high-value tiers. General web search providers (serpapi, valueserp,
        searchapi, google_cse, google_shopping) are kept because they find luxury retailers,
        specialist sites, and broker pages.
        """
        if not desire_tier:
            return providers

        # Only marketplace-specific aggregators that return mass-market products
        MARKETPLACE_ONLY_PROVIDERS = {
            "amazon",         # Amazon-specific — doesn't sell jets or $50k earrings
            "ebay",           # eBay-specific — mostly consumer goods
            "mock",           # Test provider
        }

        if desire_tier in ("service", "bespoke", "high_value"):
            filtered = {k: v for k, v in providers.items() if k not in MARKETPLACE_ONLY_PROVIDERS}
            print(f"[SourcingRepository] Tier '{desire_tier}' — excluded marketplace-only providers, running: {list(filtered.keys())}")
            if not filtered:
                print(f"[SourcingRepository] WARNING: No providers left after tier filtering, falling back to all")
                return providers
            return filtered

        if desire_tier == "advisory":
            print(f"[SourcingRepository] Tier 'advisory' — no search providers (handled by chat)")
            return {}

        # commodity / considered: run everything
        print(f"[SourcingRepository] Tier '{desire_tier}' — running all providers: {list(providers.keys())}")
        return providers

    async def search_all_with_status(self, query: str, **kwargs) -> SearchResultWithStatus:
        """Search all providers and return results with provider status."""
        print(f"[SourcingRepository] search_all called with query: {query}")
        print(f"[SourcingRepository] Available providers: {list(self.providers.keys())}")

        from sourcing.normalizers import normalize_results_for_provider

        providers_filter = kwargs.pop("providers", None)
        desire_tier = kwargs.pop("desire_tier", None)
        vendor_query = kwargs.pop("vendor_query", None)
        selected_providers: Dict[str, SourcingProvider] = self.providers
        if providers_filter:
            allow = self._normalize_provider_filter(
                [str(p).strip() for p in providers_filter if str(p).strip()]
            )
            selected_providers = {k: v for k, v in self.providers.items() if k in allow}
            print(f"[SourcingRepository] Provider filter requested: {sorted(list(allow))}")
            print(f"[SourcingRepository] Providers selected: {list(selected_providers.keys())}")

        # Apply desire-tier filtering
        selected_providers = self._filter_providers_by_tier(selected_providers, desire_tier)
        
        start_time = time.time()
        try:
            PROVIDER_TIMEOUT_SECONDS = float(os.getenv("SOURCING_PROVIDER_TIMEOUT_SECONDS", "5.0"))
        except Exception:
            PROVIDER_TIMEOUT_SECONDS = 5.0

        provider_statuses: List[ProviderStatusSnapshot] = []
        normalized_results: List[NormalizedResult] = []

        async def search_with_timeout(
            name: str, provider: SourcingProvider
        ) -> tuple[str, List[SearchResult], ProviderStatusSnapshot]:
            print(f"[SourcingRepository] Starting search with provider: {name}")
            # Route vendor_query to vendor_directory, full query to others
            effective_query = query
            extra_kwargs = dict(kwargs)
            if name == "vendor_directory" and vendor_query:
                effective_query = vendor_query
                extra_kwargs["context_query"] = query
            results, status = await run_provider_with_status(
                name,
                provider,
                effective_query,
                timeout_seconds=PROVIDER_TIMEOUT_SECONDS,
                **extra_kwargs,
            )
            if status.status != "ok":
                error_str = redact_secrets(status.message or "")
                if "402" in error_str or "Payment Required" in error_str:
                    status.status = "exhausted"
                    status.message = "API quota exhausted"
                elif "429" in error_str or "Too Many Requests" in error_str:
                    status.status = "rate_limited"
                    status.message = "Rate limit exceeded"
                elif status.status == "error":
                    status.message = "Search failed"
            print(f"[SourcingRepository] Provider {name} returned {len(results)} results")
            return (name, results, status)

        # Run all providers in parallel
        tasks = [
            search_with_timeout(name, provider)
            for name, provider in selected_providers.items()
        ]
        
        task_results = await asyncio.gather(*tasks)
        
        results_lists = []
        for name, results, status in task_results:
            results_lists.append(results)
            provider_statuses.append(status)
            normalized_results.extend(normalize_results_for_provider(name, results))
        
        all_results = []
        for results in results_lists:
            all_results.extend(results)
            
        def _allow_url(u: str) -> bool:
            norm = normalize_url(u)
            if not norm:
                return False
            key = norm.lower()
            return key.startswith('http://') or key.startswith('https://') or key.startswith('mailto:')

        filtered_results = [r for r in all_results if _allow_url(getattr(r, 'url', ''))]
        
        # Deduplication
        seen_urls = set()
        unique_results = []
        for r in filtered_results:
            url_key = r.url.lower().rstrip('/')
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                unique_results.append(r)

        # Ensure merchant_domain and click_url are always present (PRD contract)
        for i, r in enumerate(unique_results):
            try:
                if not getattr(r, "merchant_domain", ""):
                    r.merchant_domain = extract_merchant_domain(r.url)
                if not getattr(r, "click_url", ""):
                    # Note: row_id is not known at this layer; row-scoped endpoints can override.
                    r.click_url = "/api/out?" + urlencode(
                        {
                            "url": r.url,
                            "idx": i,
                            "source": getattr(r, "source", "unknown"),
                        }
                    )
            except Exception:
                # Non-fatal: clickout fallback exists on frontend
                pass
        
        # Scoring
        for result in unique_results:
            result.match_score = compute_match_score(result, query)
            
        # Sort by match score
        unique_results.sort(key=lambda r: r.match_score, reverse=True)
        
        elapsed = time.time() - start_time
        print(f"[SourcingRepository] Search completed in {elapsed:.2f}s")
        print(f"[SourcingRepository] Total results: {len(all_results)}")
        print(f"[SourcingRepository] Unique results with http(s) url: {len(unique_results)}")
        
        # Determine if all providers failed and generate user message
        all_failed = all(s.status != "ok" for s in provider_statuses) if provider_statuses else True
        user_message = None
        
        if len(unique_results) == 0:
            exhausted_count = sum(1 for s in provider_statuses if s.status == "exhausted")
            rate_limited_count = sum(1 for s in provider_statuses if s.status == "rate_limited")
            
            if exhausted_count > 0 and exhausted_count == len(provider_statuses):
                user_message = "Search providers have exhausted their quota. Please try again later or contact support."
            elif rate_limited_count > 0:
                user_message = "Search is temporarily rate-limited. Please wait a moment and try again."
            elif all_failed:
                user_message = "Unable to search at this time. Please try again later."
        
        return SearchResultWithStatus(
            results=unique_results,
            normalized_results=normalized_results,
            provider_statuses=provider_statuses,
            all_providers_failed=all_failed,
            user_message=user_message
        )

    async def search_streaming(self, query: str, **kwargs):
        """
        Stream search results as each provider completes.
        Yields (provider_name, results, status, providers_remaining) tuples.
        """
        print(f"[SourcingRepository] search_streaming called with query: {query}")

        from sourcing.normalizers import normalize_results_for_provider

        providers_filter = kwargs.pop("providers", None)
        desire_tier = kwargs.pop("desire_tier", None)
        selected_providers: Dict[str, SourcingProvider] = self.providers
        if providers_filter:
            allow = {str(p).strip() for p in providers_filter if str(p).strip()}
            selected_providers = {k: v for k, v in self.providers.items() if k in allow}

        # Apply desire-tier filtering
        selected_providers = self._filter_providers_by_tier(selected_providers, desire_tier)

        # No timeout for streaming - results flow in as each provider completes
        # Slow providers just arrive later in the stream
        PROVIDER_TIMEOUT_SECONDS = float(os.getenv("SOURCING_PROVIDER_TIMEOUT_SECONDS", "30.0"))

        async def search_with_timeout(
            name: str, provider: SourcingProvider
        ) -> tuple[str, List[SearchResult], ProviderStatusSnapshot]:
            print(f"[SourcingRepository] [STREAM] Starting provider: {name}")
            results, status = await run_provider_with_status(
                name,
                provider,
                query,
                timeout_seconds=PROVIDER_TIMEOUT_SECONDS,
                **kwargs,
            )
            if status.status != "ok":
                error_str = redact_secrets(status.message or "")
                if "402" in error_str or "Payment Required" in error_str:
                    status.status = "exhausted"
                    status.message = "API quota exhausted"
                elif "429" in error_str or "Too Many Requests" in error_str:
                    status.status = "rate_limited"
                    status.message = "Rate limit exceeded"
                elif status.status == "error":
                    status.message = "Search failed"
            print(f"[SourcingRepository] [STREAM] Provider {name} returned {len(results)} results")
            log_provider_result(name, status.status, len(results), status.latency_ms or 0)
            return (name, results, status)

        # Create tasks with provider name tracking
        tasks = {
            asyncio.create_task(search_with_timeout(name, provider)): name
            for name, provider in selected_providers.items()
        }
        
        total_providers = len(tasks)
        completed_count = 0
        seen_urls = set()

        # Yield results as each provider completes
        for coro in asyncio.as_completed(tasks.keys()):
            try:
                name, results, status = await coro
                completed_count += 1
                providers_remaining = total_providers - completed_count
                
                # Filter and dedupe results
                unique_results = []
                for r in results:
                    url = normalize_url(getattr(r, 'url', ''))
                    if url[:4] != 'http' and not url.startswith('mailto:'):
                        continue
                    url_key = url.lower().rstrip('/')
                    if url_key not in seen_urls:
                        seen_urls.add(url_key)
                        # Add merchant_domain if missing
                        if not getattr(r, "merchant_domain", ""):
                            r.merchant_domain = extract_merchant_domain(r.url)
                        # Score the result
                        r.match_score = compute_match_score(r, query)
                        unique_results.append(r)
                
                # Sort this batch by score
                unique_results.sort(key=lambda r: r.match_score, reverse=True)
                
                yield (name, unique_results, status, providers_remaining)
                
            except Exception as e:
                completed_count += 1
                providers_remaining = total_providers - completed_count
                # Find which provider failed
                failed_name = "unknown"
                for task, task_name in tasks.items():
                    if task.done() and task.exception():
                        failed_name = task_name
                        break
                status = ProviderStatusSnapshot(
                    provider_id=failed_name,
                    status="error",
                    result_count=0,
                    message=str(e)[:100]
                )
                yield (failed_name, [], status, providers_remaining)
