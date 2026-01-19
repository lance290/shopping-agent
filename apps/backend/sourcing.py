from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import httpx
import os
import re
from urllib.parse import urlparse
import asyncio
import time
import base64


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


def redact_secrets(text: str) -> str:
    if not text:
        return text
    redactions = [
        (r"(api_key=)[^&\s]+", r"\\1[REDACTED]"),
        (r"(key=)[^&\s]+", r"\\1[REDACTED]"),
        (r"(token=)[^&\s]+", r"\\1[REDACTED]"),
        (r"(Authorization: Bearer)\s+[^\s]+", r"\\1 [REDACTED]"),
    ]
    out = text
    for pattern, repl in redactions:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return out

class SearchResult(BaseModel):
    title: str
    price: float
    currency: str = "USD"
    merchant: str
    url: str
    merchant_domain: str = ""
    match_score: float = 0.0
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    shipping_info: Optional[str] = None
    source: str

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

class SearchAPIProvider(SourcingProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.searchapi.io/api/v1/search"

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": self.api_key,
            "gl": kwargs.get("gl", "us"),
            "hl": kwargs.get("hl", "en"),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            shopping_results = data.get("shopping_results", [])
            
            for item in shopping_results:
                # Basic normalization
                price_str = str(item.get("price", "0")).replace("$", "").replace(",", "")
                try:
                    price = float(price_str)
                except ValueError:
                    price = 0.0
                
                url = normalize_url(item.get("product_link") or item.get("offers_link") or item.get("link", ""))

                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=price,
                    merchant=item.get("seller") or item.get("source", "Unknown"),
                    url=url,
                    merchant_domain=extract_merchant_domain(url),
                    image_url=item.get("thumbnail"),
                    rating=item.get("rating"),
                    reviews_count=item.get("reviews"),
                    shipping_info=item.get("delivery"),
                    source="searchapi_google_shopping"
                ))
            return results


class EbayBrowseProvider(SourcingProvider):
    """eBay Browse API (official)"""

    def __init__(self, client_id: str, client_secret: str, marketplace_id: str = "EBAY-US"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.marketplace_id = marketplace_id
        self.auth_url = "https://api.ebay.com/identity/v1/oauth2/token"
        self.base_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def _get_access_token(self) -> Optional[str]:
        now = time.time()
        if self._token and now < (self._token_expires_at - 60):
            return self._token

        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode("utf-8")

        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
        }

        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.post(self.auth_url, data=data, headers=headers)
                resp.raise_for_status()
                payload = resp.json()
        except Exception:
            return None

        token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not token:
            return None

        try:
            expires_in_s = float(expires_in) if expires_in is not None else 7200.0
        except Exception:
            expires_in_s = 7200.0

        self._token = token
        self._token_expires_at = time.time() + expires_in_s
        return token

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        token = await self._get_access_token()
        if not token:
            return []

        params: Dict[str, Any] = {
            "q": query,
            "limit": 20,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
        }

        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.get(self.base_url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        results: List[SearchResult] = []
        for item in data.get("itemSummaries", []) or []:
            title = item.get("title") or "Unknown"

            price_obj = item.get("price") or {}
            try:
                price = float(price_obj.get("value") or 0.0)
            except Exception:
                price = 0.0
            currency = price_obj.get("currency") or "USD"

            url = normalize_url(item.get("itemWebUrl") or "")

            seller = item.get("seller") or {}
            merchant = seller.get("username") or "eBay"

            image_obj = item.get("image") or {}
            image_url = image_obj.get("imageUrl")

            shipping_info = None
            shipping_options = item.get("shippingOptions") or []
            if shipping_options:
                first = shipping_options[0] or {}
                ship_cost = first.get("shippingCost") or {}
                ship_type = first.get("shippingCostType")
                if ship_type and str(ship_type).lower() == "free":
                    shipping_info = "Free shipping"
                elif ship_cost.get("value") is not None:
                    try:
                        ship_val = float(ship_cost.get("value"))
                        ship_cur = ship_cost.get("currency") or currency
                        shipping_info = f"Shipping {ship_cur} {ship_val:.2f}"
                    except Exception:
                        shipping_info = None

            results.append(
                SearchResult(
                    title=title,
                    price=price,
                    currency=currency,
                    merchant=merchant,
                    url=url,
                    merchant_domain=extract_merchant_domain(url),
                    image_url=image_url,
                    rating=None,
                    reviews_count=None,
                    shipping_info=shipping_info,
                    source="ebay_browse",
                )
            )

        return results

class SerpAPIProvider(SourcingProvider):
    """SerpAPI - alternative Google Shopping search provider"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": self.api_key,
            "gl": kwargs.get("gl", "us"),
            "hl": kwargs.get("hl", "en"),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            shopping_results = data.get("shopping_results", [])
            
            for item in shopping_results:
                price_str = str(item.get("price", "0")).replace("$", "").replace(",", "")
                try:
                    price = float(price_str)
                except ValueError:
                    price = 0.0

                url = normalize_url(item.get("product_link") or item.get("offers_link") or item.get("link", ""))
                
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=price,
                    merchant=item.get("source", "Unknown"),
                    url=url,
                    merchant_domain=extract_merchant_domain(url),
                    image_url=item.get("thumbnail"),
                    rating=item.get("rating"),
                    reviews_count=item.get("reviews"),
                    shipping_info=item.get("delivery"),
                    source="serpapi_google_shopping"
                ))
            return results


class ValueSerpProvider(SourcingProvider):
    """ValueSerp - cheap alternative at $50/5000 searches"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.valueserp.com/search"

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        params = {
            "search_type": "shopping",
            "q": query,
            "api_key": self.api_key,
            "gl": kwargs.get("gl", "us"),
            "hl": kwargs.get("hl", "en"),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            shopping_results = data.get("shopping_results", [])
            
            for item in shopping_results:
                price_str = str(item.get("price", "0")).replace("$", "").replace(",", "")
                try:
                    price = float(price_str)
                except ValueError:
                    price = 0.0

                url = normalize_url(item.get("product_link") or item.get("offers_link") or item.get("link", ""))
                
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=price,
                    merchant=item.get("source", "Unknown"),
                    url=url,
                    merchant_domain=extract_merchant_domain(url),
                    image_url=item.get("thumbnail"),
                    rating=item.get("rating"),
                    reviews_count=item.get("reviews"),
                    shipping_info=item.get("delivery"),
                    source="valueserp_shopping"
                ))
            return results


class RainforestAPIProvider(SourcingProvider):
    """Rainforest API - Amazon product search with free tier"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.rainforestapi.com/request"

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": "amazon.com",
            "search_term": query,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            data = None
            request_id = None
            for attempt in range(4):
                try:
                    response = await client.get(self.base_url, params=params)
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    status = None
                    try:
                        status = e.response.status_code
                    except Exception:
                        status = None
                    safe_msg = redact_secrets(str(e))
                    print(f"[RainforestAPIProvider] HTTP error status={status}: {safe_msg}")
                    return []
                data = response.json()

                request_info = data.get("request_info") if isinstance(data, dict) else None
                if isinstance(request_info, dict):
                    request_id = request_info.get("request_id") or request_info.get("id")
                    success = request_info.get("success")
                    status = request_info.get("status")
                    message = request_info.get("message")
                    if attempt == 0:
                        print(
                            f"[RainforestAPIProvider] request_info: success={success} status={status} "
                            f"request_id={request_id} message={message}"
                        )

                if isinstance(data, dict) and data.get("error"):
                    print(f"[RainforestAPIProvider] error: {data.get('error')}")

                search_results = data.get("search_results") if isinstance(data, dict) else None
                if isinstance(search_results, list) and len(search_results) > 0:
                    break

                if request_id and attempt < 3:
                    params = {"api_key": self.api_key, "request_id": request_id}
                    await asyncio.sleep(1.0 + attempt)
                    continue

                break

            if not isinstance(data, dict):
                return []

            results = []
            for item in data.get("search_results", [])[:20]:
                price_info = item.get("price", {})
                price = price_info.get("value", 0) if isinstance(price_info, dict) else 0
                
                url = normalize_url(item.get("link", ""))
                
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=float(price) if price else 0.0,
                    merchant="Amazon",
                    url=url,
                    merchant_domain=extract_merchant_domain(url),
                    image_url=item.get("image"),
                    rating=item.get("rating"),
                    reviews_count=item.get("ratings_total"),
                    shipping_info=item.get("delivery", {}).get("tagline"),
                    source="rainforest_amazon"
                ))
            return results


class MockShoppingProvider(SourcingProvider):
    """Mock provider for testing - returns sample data based on query"""
    def __init__(self):
        pass

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        import random
        import hashlib
        
        # Generate deterministic but varied results based on query
        query_hash = int(hashlib.md5(query.encode()).hexdigest()[:8], 16)
        random.seed(query_hash)
        
        merchants = ["Amazon", "Walmart", "Target", "eBay", "Best Buy", "Costco", "Kohl's", "Macy's"]
        
        results = []
        for i in range(random.randint(8, 15)):
            base_price = random.uniform(15, 150)
            url = f"https://example.com/product/{query_hash + i}"
            results.append(SearchResult(
                title=f"{query} - Style {chr(65 + i)} {'Premium' if i % 3 == 0 else 'Standard'} Edition",
                price=round(base_price, 2),
                currency="USD",
                merchant=random.choice(merchants),
                url=url,
                merchant_domain=extract_merchant_domain(url),
                image_url=f"https://picsum.photos/seed/{query_hash + i}/300/300",
                rating=round(random.uniform(3.5, 5.0), 1),
                reviews_count=random.randint(10, 5000),
                shipping_info="Free shipping" if random.random() > 0.3 else "Ships in 2-3 days",
                source="mock_provider"
            ))
        return results


class GoogleCustomSearchProvider(SourcingProvider):
    """Google Custom Search - 100 free queries/day"""
    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "searchType": "image",  # For product images
            "num": 10,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("items", []):
                url = normalize_url(item.get("link", ""))
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=0.0,  # Google CSE doesn't return prices
                    merchant="Google Search",
                    url=url,
                    merchant_domain=extract_merchant_domain(url),
                    image_url=item.get("link"),
                    source="google_cse"
                ))
            return results


class SourcingRepository:
    def __init__(self):
        self.providers: Dict[str, SourcingProvider] = {}
        
        # Initialize providers in priority order
        # SerpAPI - 100 free searches/month
        serpapi_key = os.getenv("SERPAPI_API_KEY")
        print(f"[SourcingRepository] SERPAPI_API_KEY present: {bool(serpapi_key)}")
        if serpapi_key and serpapi_key != "demo":
            self.providers["serpapi"] = SerpAPIProvider(serpapi_key)
            print(f"[SourcingRepository] SerpAPI provider initialized")
        
        # Rainforest API - Amazon search
        rainforest_key = os.getenv("RAINFOREST_API_KEY")
        rainforest_key_len = len(rainforest_key) if rainforest_key is not None else None
        rainforest_present = rainforest_key is not None and rainforest_key_len > 0
        print(
            f"[SourcingRepository] RAINFOREST_API_KEY present: {rainforest_present} "
            f"(is_none={rainforest_key is None}, len={rainforest_key_len})"
        )
        if rainforest_present:
            self.providers["rainforest"] = RainforestAPIProvider(rainforest_key)
        
        # ValueSerp - cheap alternative
        valueserp_key = os.getenv("VALUESERP_API_KEY")
        if valueserp_key:
            self.providers["valueserp"] = ValueSerpProvider(valueserp_key)
        
        # Google Custom Search - 100 free/day
        google_key = os.getenv("GOOGLE_CSE_API_KEY")
        google_cx = os.getenv("GOOGLE_CSE_CX")
        if google_key and google_cx:
            self.providers["google_cse"] = GoogleCustomSearchProvider(google_key, google_cx)
        
        # SearchAPI (original)
        searchapi_key = os.getenv("SEARCHAPI_API_KEY")
        if searchapi_key:
            self.providers["searchapi"] = SearchAPIProvider(searchapi_key)

        # eBay Browse API (official)
        ebay_client_id = os.getenv("EBAY_CLIENT_ID")
        ebay_client_secret = os.getenv("EBAY_CLIENT_SECRET")
        ebay_marketplace_id = os.getenv("EBAY_MARKETPLACE_ID", "EBAY-US")
        if ebay_client_id and ebay_client_secret:
            self.providers["ebay"] = EbayBrowseProvider(
                client_id=ebay_client_id,
                client_secret=ebay_client_secret,
                marketplace_id=ebay_marketplace_id,
            )
        
        # Mock provider - FREE fallback for testing, always available
        use_mock = os.getenv("USE_MOCK_SEARCH", "true").lower() == "true"
        if use_mock:
            self.providers["mock"] = MockShoppingProvider()

    async def search_all(self, query: str, **kwargs) -> List[SearchResult]:
        print(f"[SourcingRepository] search_all called with query: {query}")
        print(f"[SourcingRepository] Available providers: {list(self.providers.keys())}")

        providers_filter = kwargs.pop("providers", None)
        selected_providers: Dict[str, SourcingProvider] = self.providers
        if providers_filter:
            allow = {str(p).strip() for p in providers_filter if str(p).strip()}
            selected_providers = {k: v for k, v in self.providers.items() if k in allow}
            print(f"[SourcingRepository] Provider filter requested: {sorted(list(allow))}")
            print(f"[SourcingRepository] Providers selected: {list(selected_providers.keys())}")
        
        start_time = time.time()
        try:
            PROVIDER_TIMEOUT_SECONDS = float(os.getenv("SOURCING_PROVIDER_TIMEOUT_SECONDS", "8.0"))
        except Exception:
            PROVIDER_TIMEOUT_SECONDS = 8.0

        async def search_with_timeout(name: str, provider: SourcingProvider) -> List[SearchResult]:
            try:
                print(f"[SourcingRepository] Starting search with provider: {name}")
                results = await asyncio.wait_for(
                    provider.search(query, **kwargs),
                    timeout=PROVIDER_TIMEOUT_SECONDS
                )
                print(f"[SourcingRepository] Provider {name} returned {len(results)} results")
                return results
            except asyncio.TimeoutError:
                print(f"[SourcingRepository] Provider {name} timed out after {PROVIDER_TIMEOUT_SECONDS}s")
                return []
            except Exception as e:
                print(f"[SourcingRepository] Provider {name} failed: {redact_secrets(str(e))}")
                return []

        # Run all providers in parallel
        tasks = [
            search_with_timeout(name, provider)
            for name, provider in selected_providers.items()
        ]
        
        results_lists = await asyncio.gather(*tasks)
        
        all_results = []
        for results in results_lists:
            all_results.extend(results)
            
        filtered_results = [r for r in all_results if normalize_url(getattr(r, 'url', ''))[:4] == 'http']
        
        # Deduplication
        seen_urls = set()
        unique_results = []
        for r in filtered_results:
            url_key = r.url.lower().rstrip('/')
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                unique_results.append(r)
        
        # Scoring
        for result in unique_results:
            result.match_score = compute_match_score(result, query)
            
        # Sort by match score
        unique_results.sort(key=lambda r: r.match_score, reverse=True)
        
        elapsed = time.time() - start_time
        print(f"[SourcingRepository] Search completed in {elapsed:.2f}s")
        print(f"[SourcingRepository] Total results: {len(all_results)}")
        print(f"[SourcingRepository] Unique results with http(s) url: {len(unique_results)}")
        
        return unique_results
