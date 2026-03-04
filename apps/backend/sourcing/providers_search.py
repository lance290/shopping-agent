"""
Search and event provider classes for the sourcing pipeline.

Extracted from sourcing/repository.py to keep files under 450 lines.
"""
import httpx
import os
import re
import time
import base64
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, urlencode

from sourcing.repository import SearchResult, SourcingProvider, normalize_url, compute_match_score
from sourcing.models import NormalizedResult, ProviderStatusSnapshot

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

class ScaleSerpProvider(SourcingProvider):
    """Scale SERP API - Google Shopping results (same company as Rainforest)"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.scaleserp.com/search"

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        print(f"[ScaleSerpProvider] Searching Google Shopping: {query!r}")
        
        min_price = kwargs.get("min_price")
        max_price = kwargs.get("max_price")
        
        params = {
            "api_key": self.api_key,
            "q": query,
            "search_type": "shopping",
            "location": "United States",
        }
        
        if min_price is not None:
            params["shopping_price_min"] = int(min_price)
        if max_price is not None:
            params["shopping_price_max"] = int(max_price)
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                shopping_results = data.get("shopping_results", [])
                print(f"[ScaleSerpProvider] Got {len(shopping_results)} results")
                
                # Debug: log first result structure
                if shopping_results:
                    print(f"[ScaleSerpProvider] Sample result keys: {list(shopping_results[0].keys())}")
                    print(f"[ScaleSerpProvider] Sample result: {shopping_results[0]}")
                
                results = []
                for item in shopping_results:
                    price = 0.0
                    # Try multiple price fields
                    price_raw = item.get("price") or item.get("extracted_price") or item.get("price_raw")
                    if price_raw:
                        if isinstance(price_raw, (int, float)):
                            price = float(price_raw)
                        else:
                            # Parse "$1,299.00" format
                            match = re.search(r"(\d[\d,]*\.?\d*)", str(price_raw))
                            if match:
                                try:
                                    price = float(match.group(1).replace(",", ""))
                                except (ValueError, AttributeError):
                                    pass
                    
                    # Try multiple URL fields
                    url = item.get("link") or item.get("url") or item.get("product_link") or ""
                    url = normalize_url(url) if url else ""
                    
                    # Try multiple image fields
                    image_url = item.get("thumbnail") or item.get("image") or item.get("image_url")
                    
                    results.append(SearchResult(
                        title=item.get("title", "Unknown"),
                        price=price,
                        currency="USD",
                        merchant=item.get("source") or item.get("merchant") or "Google Shopping",
                        url=url,
                        merchant_domain=extract_merchant_domain(url) if url else "",
                        image_url=image_url,
                        rating=item.get("rating"),
                        reviews_count=item.get("reviews") or item.get("reviews_count"),
                        source="google_shopping"
                    ))
                return results
        except httpx.HTTPStatusError as e:
            print(f"[ScaleSerpProvider] HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            print(f"[ScaleSerpProvider] Error: {e}")
            raise

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
        search_query = f"{query} buy price"
        print(f"[GoogleCSE] Searching: {search_query}")
        
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": search_query,
            "num": 10,
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                print(f"[GoogleCSE] Got {len(data.get('items', []))} results")
                
                results = []
                for item in data.get("items", []):
                    url = normalize_url(item.get("link", ""))
                    image_url = None
                    pagemap = item.get("pagemap", {})
                    if pagemap.get("cse_image"):
                        image_url = pagemap["cse_image"][0].get("src")
                    elif pagemap.get("cse_thumbnail"):
                        image_url = pagemap["cse_thumbnail"][0].get("src")
                    
                    results.append(SearchResult(
                        title=item.get("title", "Unknown"),
                        price=0.0,
                        merchant=extract_merchant_domain(url) or "Web",
                        url=url,
                        merchant_domain=extract_merchant_domain(url),
                        image_url=image_url,
                        source="google_cse"
                    ))
                return results
        except httpx.HTTPStatusError as e:
            print(f"[GoogleCSE] HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return []
        except Exception as e:
            print(f"[GoogleCSE] Error: {e}")
            return []

class TicketmasterProvider(SourcingProvider):
    """Ticketmaster Discovery API — event tickets (concerts, sports, theater, etc.)"""

    # Keywords that suggest the user is looking for events/tickets
    _EVENT_KEYWORDS = {
        "ticket", "tickets", "concert", "concerts", "show", "shows",
        "game", "games", "match", "event", "events", "tour",
        "festival", "stadium", "arena", "theater", "theatre",
        "live", "performance", "nba", "nfl", "mlb", "nhl",
        "mls", "ncaa", "ufc", "wwe", "broadway",
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://app.ticketmaster.com/discovery/v2/events.json"

    def _is_event_query(self, query: str) -> bool:
        """Check if the query is likely about events/tickets."""
        words = set(query.lower().split())
        return bool(words & self._EVENT_KEYWORDS)

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        # Skip non-event queries to avoid wasting API calls
        if not self._is_event_query(query):
            return []

        print(f"[TicketmasterProvider] Searching: {query!r}")

        params = {
            "apikey": self.api_key,
            "keyword": query,
            "size": 20,
            "countryCode": kwargs.get("country_code", "US"),
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            status = getattr(e.response, "status_code", None)
            safe_msg = redact_secrets(str(e))
            print(f"[TicketmasterProvider] HTTP error status={status}: {safe_msg}")
            return []
        except Exception as e:
            safe_msg = redact_secrets(str(e))
            print(f"[TicketmasterProvider] Error: {safe_msg}")
            return []

        results = []
        embedded = data.get("_embedded", {})
        events = embedded.get("events", [])
        print(f"[TicketmasterProvider] Found {len(events)} events")

        for event in events:
            try:
                title = event.get("name", "Unknown Event")

                # Price range
                price_ranges = event.get("priceRanges", [])
                min_price = 0.0
                currency = "USD"
                if price_ranges and isinstance(price_ranges, list) and len(price_ranges) > 0:
                    pr = price_ranges[0]
                    min_price = float(pr.get("min", 0.0))
                    currency = pr.get("currency", "USD")

                # URL
                url = event.get("url", "")
                if not url:
                    continue

                # Venue
                venues = event.get("_embedded", {}).get("venues", [])
                venue_name = venues[0].get("name", "Venue TBA") if venues else "Venue TBA"

                # Date
                dates = event.get("dates", {})
                start = dates.get("start", {})
                local_date = start.get("localDate", "")
                local_time = start.get("localTime", "")
                date_str = f"{local_date} {local_time}".strip() if local_date else "Date TBA"

                # Image — highest resolution
                images = event.get("images", [])
                image_url = None
                if images:
                    images_sorted = sorted(
                        images,
                        key=lambda x: x.get("width", 0) * x.get("height", 0),
                        reverse=True,
                    )
                    image_url = images_sorted[0].get("url")

                full_title = f"{title} - {venue_name}"
                if date_str != "Date TBA":
                    full_title += f" ({date_str})"

                results.append(SearchResult(
                    title=full_title,
                    price=min_price,
                    currency=currency,
                    merchant="Ticketmaster",
                    url=url,
                    merchant_domain="ticketmaster.com",
                    image_url=image_url,
                    rating=None,
                    reviews_count=None,
                    shipping_info=f"Event: {date_str}" if date_str != "Date TBA" else None,
                    source="ticketmaster",
                ))
            except Exception as e:
                safe_msg = redact_secrets(str(e))
                print(f"[TicketmasterProvider] Error parsing event: {safe_msg}")
                continue

        return results
