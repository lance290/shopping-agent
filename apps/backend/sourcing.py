from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import httpx
import os
from urllib.parse import urlparse
import asyncio
import time


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
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
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
        print(f"[SourcingRepository] SERPAPI_API_KEY present: {bool(serpapi_key)}, value starts with: {serpapi_key[:8] if serpapi_key else 'N/A'}")
        if serpapi_key and serpapi_key != "demo":
            self.providers["serpapi"] = SerpAPIProvider(serpapi_key)
            print(f"[SourcingRepository] SerpAPI provider initialized")
        
        # Rainforest API - Amazon search
        rainforest_key = os.getenv("RAINFOREST_API_KEY")
        if rainforest_key:
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
        
        # Mock provider - FREE fallback for testing, always available
        use_mock = os.getenv("USE_MOCK_SEARCH", "true").lower() == "true"
        if use_mock:
            self.providers["mock"] = MockShoppingProvider()

    async def search_all(self, query: str, **kwargs) -> List[SearchResult]:
        print(f"[SourcingRepository] search_all called with query: {query}")
        print(f"[SourcingRepository] Available providers: {list(self.providers.keys())}")
        
        start_time = time.time()
        PROVIDER_TIMEOUT_SECONDS = 3.0

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
                print(f"Provider {name} failed: {e}")
                return []

        # Run all providers in parallel
        tasks = [
            search_with_timeout(name, provider)
            for name, provider in self.providers.items()
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
