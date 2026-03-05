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
        rainforest_key = os.getenv("RAINFOREST_API_KEY")
        rainforest_key_len = len(rainforest_key) if rainforest_key is not None else None
        rainforest_present = rainforest_key is not None and rainforest_key_len > 0
        print(
            f"[SourcingRepository] RAINFOREST_API_KEY present: {rainforest_present} "
            f"(is_none={rainforest_key is None}, len={rainforest_key_len})"
        )
        if rainforest_present:
            self.providers["amazon"] = RainforestAPIProvider(rainforest_key)

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

        # SerpAPI — Google Shopping (general-purpose fallback)
        serpapi_key = os.getenv("SERPAPI_API_KEY")
        if serpapi_key:
            self.providers["serpapi"] = SerpAPIProvider(serpapi_key)
            print(f"[SourcingRepository] SerpAPI provider initialized")

        # SearchAPI.io — Google Shopping
        searchapi_key = os.getenv("SEARCHAPI_API_KEY")
        if searchapi_key:
            self.providers["searchapi"] = SearchAPIProvider(searchapi_key)
            print(f"[SourcingRepository] SearchAPI provider initialized")

        # ScaleSerp — Google Shopping (same company as Rainforest)
        scaleserp_key = os.getenv("SCALESERP_API_KEY")
        if scaleserp_key:
            self.providers["scaleserp"] = ScaleSerpProvider(scaleserp_key)
            print(f"[SourcingRepository] ScaleSerp provider initialized")

        # Google Custom Search — 100 free queries/day
        google_cse_key = os.getenv("GOOGLE_CSE_API_KEY")
        google_cse_cx = os.getenv("GOOGLE_CSE_CX")
        if google_cse_key and google_cse_cx:
            self.providers["google_cse"] = GoogleCustomSearchProvider(google_cse_key, google_cse_cx)
            print(f"[SourcingRepository] Google CSE provider initialized")

        # Vendor Directory — pgvector semantic search (always runs)
        from sourcing.vendor_provider import VendorDirectoryProvider
        db_url = os.getenv("DATABASE_URL", "")
        if db_url:
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            self.providers["vendor_directory"] = VendorDirectoryProvider(db_url)

        use_mock_setting = (os.getenv("USE_MOCK_SEARCH", "auto") or "").strip().lower()
        if use_mock_setting in ("1", "true", "yes", "always"):
            self.providers["mock"] = MockShoppingProvider()
        elif use_mock_setting == "auto":
            if len(self.providers) == 0:
                self.providers["mock"] = MockShoppingProvider()

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

    async def search_all_with_status(self, query: str, **kwargs) -> SearchResultWithStatus:
        """Search all providers and return results with provider status."""
        print(f"[SourcingRepository] search_all called with query: {query}")
        print(f"[SourcingRepository] Available providers: {list(self.providers.keys())}")

        from sourcing.normalizers import normalize_results_for_provider

        providers_filter = kwargs.pop("providers", None)
        kwargs.pop("desire_tier", None)  # consumed but not used for filtering
        vendor_query = kwargs.pop("vendor_query", None)
        selected_providers: Dict[str, SourcingProvider] = self.providers
        if providers_filter:
            allow = self._normalize_provider_filter(
                [str(p).strip() for p in providers_filter if str(p).strip()]
            )
            selected_providers = {k: v for k, v in self.providers.items() if k in allow}
            print(f"[SourcingRepository] Provider filter requested: {sorted(list(allow))}")
            print(f"[SourcingRepository] Providers selected: {list(selected_providers.keys())}")
        
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
        
        seen_urls = set()
        unique_results = []
        for r in filtered_results:
            url_key = r.url.lower().rstrip('/')
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                unique_results.append(r)

        for i, r in enumerate(unique_results):
            try:
                if not getattr(r, "merchant_domain", ""):
                    r.merchant_domain = extract_merchant_domain(r.url)
                if not getattr(r, "click_url", ""):
                    r.click_url = "/api/out?" + urlencode(
                        {
                            "url": r.url,
                            "idx": i,
                            "source": getattr(r, "source", "unknown"),
                        }
                    )
            except Exception:
                pass
        
        for result in unique_results:
            result.match_score = compute_match_score(result, query)
            
        unique_results.sort(key=lambda r: r.match_score, reverse=True)
        
        elapsed = time.time() - start_time
        print(f"[SourcingRepository] Search completed in {elapsed:.2f}s")
        print(f"[SourcingRepository] Total results: {len(all_results)}")
        print(f"[SourcingRepository] Unique results with http(s) url: {len(unique_results)}")
        
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
        """Stream search results as each provider completes."""
        print(f"[SourcingRepository] search_streaming called with query: {query}")

        from sourcing.normalizers import normalize_results_for_provider

        providers_filter = kwargs.pop("providers", None)
        kwargs.pop("desire_tier", None)  # consumed but not used for filtering
        vendor_query = kwargs.pop("vendor_query", None)
        selected_providers: Dict[str, SourcingProvider] = self.providers
        if providers_filter:
            allow = {str(p).strip() for p in providers_filter if str(p).strip()}
            selected_providers = {k: v for k, v in self.providers.items() if k in allow}

        PROVIDER_TIMEOUT_SECONDS = float(os.getenv("SOURCING_PROVIDER_TIMEOUT_SECONDS", "30.0"))

        async def search_with_timeout(
            name: str, provider: SourcingProvider
        ) -> tuple[str, List[SearchResult], ProviderStatusSnapshot]:
            print(f"[SourcingRepository] [STREAM] Starting provider: {name}")
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
            print(f"[SourcingRepository] [STREAM] Provider {name} returned {len(results)} results")
            log_provider_result(name, status.status, len(results), status.latency_ms or 0)
            return (name, results, status)

        tasks = {
            asyncio.create_task(search_with_timeout(name, provider)): name
            for name, provider in selected_providers.items()
        }
        
        total_providers = len(tasks)
        completed_count = 0
        seen_urls = set()

        for coro in asyncio.as_completed(tasks.keys()):
            try:
                name, results, status = await coro
                completed_count += 1
                providers_remaining = total_providers - completed_count
                
                unique_results = []
                for r in results:
                    url = normalize_url(getattr(r, 'url', ''))
                    if url[:4] != 'http' and not url.startswith('mailto:'):
                        continue
                    url_key = url.lower().rstrip('/')
                    if url_key not in seen_urls:
                        seen_urls.add(url_key)
                        if not getattr(r, "merchant_domain", ""):
                            r.merchant_domain = extract_merchant_domain(r.url)
                        r.match_score = compute_match_score(r, query)
                        unique_results.append(r)
                
                unique_results.sort(key=lambda r: r.match_score, reverse=True)
                
                yield (name, unique_results, status, providers_remaining)
                
            except Exception as e:
                completed_count += 1
                providers_remaining = total_providers - completed_count
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


