from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import httpx
import os

class SearchResult(BaseModel):
    title: str
    price: float
    currency: str = "USD"
    merchant: str
    url: str
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    shipping_info: Optional[str] = None
    source: str

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
                
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=price,
                    merchant=item.get("seller") or item.get("source", "Unknown"),
                    url=item.get("product_link") or item.get("offers_link") or item.get("link", ""),
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
                
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=price,
                    merchant=item.get("source", "Unknown"),
                    url=item.get("link", ""),
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
                
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=price,
                    merchant=item.get("source", "Unknown"),
                    url=item.get("link", ""),
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
                
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=float(price) if price else 0.0,
                    merchant="Amazon",
                    url=item.get("link", ""),
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
            results.append(SearchResult(
                title=f"{query} - Style {chr(65 + i)} {'Premium' if i % 3 == 0 else 'Standard'} Edition",
                price=round(base_price, 2),
                currency="USD",
                merchant=random.choice(merchants),
                url=f"https://example.com/product/{query_hash + i}",
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
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=0.0,  # Google CSE doesn't return prices
                    merchant="Google Search",
                    url=item.get("link", ""),
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
        all_results = []
        for name, provider in self.providers.items():
            try:
                print(f"[SourcingRepository] Searching with provider: {name}")
                results = await provider.search(query, **kwargs)
                print(f"[SourcingRepository] Provider {name} returned {len(results)} results")
                all_results.extend(results)
            except Exception as e:
                print(f"Provider {name} failed: {e}")
        print(f"[SourcingRepository] Total results: {len(all_results)}")
        return all_results
