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

        # Price range filtering via tbs param (Google Shopping format)
        tbs_parts = []
        min_price = kwargs.get("min_price")
        max_price = kwargs.get("max_price")
        if min_price is not None or max_price is not None:
            tbs_parts.append("mr:1")
            tbs_parts.append("price:1")
            if min_price is not None:
                tbs_parts.append(f"ppr_min:{int(float(min_price) * 100)}")
            if max_price is not None:
                tbs_parts.append(f"ppr_max:{int(float(max_price) * 100)}")
            params["tbs"] = ",".join(tbs_parts)
        
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

        # Price range filtering via tbs param (Google Shopping format)
        tbs_parts = []
        min_price = kwargs.get("min_price")
        max_price = kwargs.get("max_price")
        if min_price is not None or max_price is not None:
            tbs_parts.append("mr:1")
            tbs_parts.append("price:1")
            if min_price is not None:
                tbs_parts.append(f"ppr_min:{int(float(min_price) * 100)}")
            if max_price is not None:
                tbs_parts.append(f"ppr_max:{int(float(max_price) * 100)}")
            params["tbs"] = ",".join(tbs_parts)
        
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

        # Price range filtering via tbs param (Google Shopping format)
        tbs_parts = []
        min_price = kwargs.get("min_price")
        max_price = kwargs.get("max_price")
        if min_price is not None or max_price is not None:
            tbs_parts.append("mr:1")
            tbs_parts.append("price:1")
            if min_price is not None:
                tbs_parts.append(f"ppr_min:{int(float(min_price) * 100)}")
            if max_price is not None:
                tbs_parts.append(f"ppr_max:{int(float(max_price) * 100)}")
            params["tbs"] = ",".join(tbs_parts)
        
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

    def _parse_price_to_float(self, price_info) -> float:
        if price_info is None:
            return 0.0

        value = None
        raw = None

        if isinstance(price_info, dict):
            value = price_info.get("value")
            raw = price_info.get("raw")
        else:
            value = price_info

        candidates = [value, raw]
        for c in candidates:
            if c is None:
                continue
            if isinstance(c, (int, float)):
                try:
                    return float(c)
                except Exception:
                    continue
            if isinstance(c, str):
                s = c.strip()
                if not s:
                    continue
                # Extract first numeric component (handles "$1,299.99", "1,299", "USD 1299", "$500 - $800")
                m = re.search(r"(\d[\d,]*\.?\d*)", s)
                if not m:
                    continue
                num = m.group(1).replace(",", "")
                try:
                    return float(num)
                except Exception:
                    continue

        return 0.0

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        print(f"[RainforestAPIProvider] Searching with query: {query!r}")

        min_price = kwargs.get("min_price")
        max_price = kwargs.get("max_price")

        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": "amazon.com",
            "search_term": query,
        }

        # Best-effort: pass through price constraints if supported by Rainforest.
        # Even if upstream ignores these, we also enforce constraints locally below.
        try:
            if min_price is not None:
                params["min_price"] = float(min_price)
            if max_price is not None:
                params["max_price"] = float(max_price)
        except Exception:
            pass

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
                    raise
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

            search_results = data.get("search_results") if isinstance(data, dict) else None
            if not search_results:
                fallback_query = " ".join(query.split()[:4]).strip()
                if fallback_query and fallback_query.lower() != query.lower():
                    print(
                        f"[RainforestAPIProvider] Empty results for query='{query}'. "
                        f"Retrying with simplified query='{fallback_query}'."
                    )
                    params = {
                        "api_key": self.api_key,
                        "type": "search",
                        "amazon_domain": "amazon.com",
                        "search_term": fallback_query,
                    }

                    try:
                        if min_price is not None:
                            params["min_price"] = float(min_price)
                        if max_price is not None:
                            params["max_price"] = float(max_price)
                    except Exception:
                        pass

                    try:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            response = await client.get(self.base_url, params=params)
                            response.raise_for_status()
                            data = response.json()
                    except httpx.HTTPStatusError as e:
                        status = None
                        try:
                            status = e.response.status_code
                        except Exception:
                            status = None
                        safe_msg = redact_secrets(str(e))
                        print(f"[RainforestAPIProvider] HTTP error status={status}: {safe_msg}")
                        raise
                    search_results = data.get("search_results") if isinstance(data, dict) else None

            results = []
            dropped_price = 0
            dropped_constraints = 0
            for item in (search_results or [])[:20]:
                price_info = item.get("price")
                if price_info is None:
                    prices_obj = item.get("prices")
                    if isinstance(prices_obj, dict):
                        for key in (
                            "current_price",
                            "buybox_price",
                            "price",
                            "current",
                            "main_price",
                            "list_price",
                        ):
                            if key in prices_obj:
                                price_info = prices_obj.get(key)
                                break
                price_f = self._parse_price_to_float(price_info)

                # Drop unknown/0 priced items; they cause $0.00 tiles and bypass min_price.
                if price_f <= 0:
                    dropped_price += 1
                    continue

                # Enforce constraints locally regardless of upstream support.
                if min_price is not None and price_f < float(min_price):
                    dropped_constraints += 1
                    continue
                if max_price is not None and price_f > float(max_price):
                    dropped_constraints += 1
                    continue
                
                url = normalize_url(item.get("link", ""))
                
                results.append(SearchResult(
                    title=item.get("title", "Unknown"),
                    price=price_f,
                    merchant="Amazon",
                    url=url,
                    merchant_domain=extract_merchant_domain(url),
                    image_url=item.get("image"),
                    rating=item.get("rating"),
                    reviews_count=item.get("ratings_total"),
                    shipping_info=item.get("delivery", {}).get("tagline"),
                    source="rainforest_amazon"
                ))

            if (not results) and search_results:
                try:
                    sample = (search_results or [])[0]
                    sample_price = sample.get("price") if isinstance(sample, dict) else None
                    print(
                        f"[RainforestAPIProvider] Filtered all results (raw={len(search_results)}, "
                        f"dropped_price={dropped_price}, dropped_constraints={dropped_constraints}). "
                        f"Sample price={sample_price}"
                    )
                except Exception:
                    pass
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


class ScaleSerpAmazonProvider(SourcingProvider):
    """Amazon product search via ScaleSerp organic results scoped to amazon.com.

    Uses ``site:amazon.com`` queries to return direct Amazon product links.
    Appends an Amazon Associates affiliate tag when configured.
    """

    # Regex to pull a price from an Amazon snippet like "$12.99" or "$1,299.00"
    _PRICE_RE = re.compile(r"\$(\d[\d,]*\.?\d*)")

    def __init__(self, api_key: str, affiliate_tag: str | None = None):
        self.api_key = api_key
        self.base_url = "https://api.scaleserp.com/search"
        self.affiliate_tag = affiliate_tag or os.getenv("AMAZON_AFFILIATE_TAG", "")

    def _append_affiliate_tag(self, url: str) -> str:
        """Append ?tag=<affiliate> to an Amazon URL (or replace existing tag)."""
        if not self.affiliate_tag:
            return url
        sep = "&" if "?" in url else "?"
        # Strip existing tag param if present
        url = re.sub(r"[?&]tag=[^&]*", "", url)
        return f"{url}{sep}tag={self.affiliate_tag}"

    def _extract_price(self, *texts: str) -> float:
        """Best-effort price extraction from title, snippet, or any text fields."""
        for text in texts:
            if not text:
                continue
            m = self._PRICE_RE.search(text)
            if m:
                try:
                    val = float(m.group(1).replace(",", ""))
                    if val > 0:
                        return val
                except (ValueError, TypeError):
                    pass
        return 0.0

    def _is_product_url(self, url: str) -> bool:
        """Filter to actual Amazon product/store pages, skip Q&A / forums."""
        if not url:
            return False
        lower = url.lower()
        # Skip non-product pages
        for skip in ("/ask/", "/forum/", "/gp/help", "/ap/signin", "/review/"):
            if skip in lower:
                return False
        return "amazon.com" in lower

    def _get_amazon_placeholder_image(self) -> str:
        """Return a generic Amazon product placeholder image."""
        # Use Amazon's standard "no image available" placeholder
        return "https://m.media-amazon.com/images/G/01/ui/loadIndicators/loading-large_labeled._CB485921773_.gif"

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        print(f"[ScaleSerpAmazon] Searching Amazon for: {query!r}")

        min_price = kwargs.get("min_price")
        max_price = kwargs.get("max_price")

        # Build price hint for the query
        price_hint = ""
        if min_price is not None and max_price is not None:
            price_hint = f" ${int(min_price)}-${int(max_price)}"
        elif min_price is not None:
            price_hint = f" over ${int(min_price)}"
        elif max_price is not None:
            price_hint = f" under ${int(max_price)}"

        params = {
            "api_key": self.api_key,
            "q": f"{query}{price_hint} site:amazon.com",
            "num": 15,
            "gl": "us",
            "hl": "en",
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            status = getattr(e.response, "status_code", None)
            safe_msg = redact_secrets(str(e))
            print(f"[ScaleSerpAmazon] HTTP error status={status}: {safe_msg}")
            raise
        except Exception as e:
            safe_msg = redact_secrets(str(e))
            print(f"[ScaleSerpAmazon] Error: {safe_msg}")
            raise

        organic = data.get("organic_results", [])
        print(f"[ScaleSerpAmazon] Got {len(organic)} organic results")

        results: List[SearchResult] = []
        for item in organic:
            url = item.get("link", "")
            if not self._is_product_url(url):
                continue

            url = normalize_url(url)
            url = self._append_affiliate_tag(url)

            title = item.get("title", "Unknown")
            snippet = item.get("snippet", "")

            # Try rich snippet price first, then title/snippet
            price = 0.0
            rich = item.get("rich_snippet", {})
            if isinstance(rich, dict):
                top = rich.get("top", {})
                if isinstance(top, dict):
                    detected = top.get("detected_extensions", {})
                    if isinstance(detected, dict) and "price" in detected:
                        try:
                            price = float(str(detected["price"]).replace(",", ""))
                        except (ValueError, TypeError):
                            pass
            if price <= 0:
                price = self._extract_price(title, snippet)

            # Skip price filtering for Amazon organic results — prices are unreliable
            # The query hint (e.g. "over $50") guides Amazon's search algorithm instead

            # Extract image from rich snippet or use placeholder
            image_url = None
            rich = item.get("rich_snippet", {})
            if isinstance(rich, dict):
                top = rich.get("top", {})
                if isinstance(top, dict):
                    image_url = top.get("image")
            
            # Use placeholder if no image from API
            if not image_url:
                image_url = self._get_amazon_placeholder_image()

            results.append(SearchResult(
                title=title,
                price=price,
                currency="USD",
                merchant="Amazon",
                url=url,
                merchant_domain="amazon.com",
                image_url=image_url,
                rating=None,
                reviews_count=None,
                shipping_info=None,
                source="amazon",
            ))

        print(f"[ScaleSerpAmazon] Returning {len(results)} Amazon product results")
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
        min_price = kwargs.get("min_price")
        max_price = kwargs.get("max_price")
        price_hint = ""
        if min_price is not None and max_price is not None:
            price_hint = f" ${int(min_price)}-${int(max_price)}"
        elif min_price is not None:
            price_hint = f" over ${int(min_price)}"
        elif max_price is not None:
            price_hint = f" under ${int(max_price)}"
        search_query = f"{query} buy price{price_hint}"
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


class SourcingRepository:
    def __init__(self):
        self.providers: Dict[str, SourcingProvider] = {}
        
        # Initialize providers in priority order
        # SerpAPI - DISABLED (registration issues)
        # serpapi_key = os.getenv("SERPAPI_API_KEY")
        # if serpapi_key and serpapi_key != "demo":
        #     self.providers["serpapi"] = SerpAPIProvider(serpapi_key)
        
        # Rainforest API - Amazon search with real images, prices, and ratings
        rainforest_key = os.getenv("RAINFOREST_API_KEY")
        if rainforest_key:
            self.providers["amazon"] = RainforestAPIProvider(rainforest_key)

        # Google providers - ALL DISABLED (results show as google.com, not useful)
        # serpapi_key = os.getenv("SERPAPI_API_KEY")
        # if serpapi_key and serpapi_key != "demo":
        #     self.providers["serpapi"] = SerpAPIProvider(serpapi_key)

        # valueserp_key = os.getenv("VALUESERP_API_KEY")
        # if valueserp_key and valueserp_key != "demo":
        #     self.providers["valueserp"] = ValueSerpProvider(valueserp_key)

        # searchapi_key = os.getenv("SEARCHAPI_API_KEY")
        # if searchapi_key and searchapi_key != "demo":
        #     self.providers["searchapi"] = SearchAPIProvider(searchapi_key)

        # scaleserp_key = os.getenv("SCALESERP_API_KEY")
        # if scaleserp_key and scaleserp_key != "demo":
        #     self.providers["google_shopping"] = ScaleSerpProvider(scaleserp_key)

        # google_key = os.getenv("GOOGLE_CSE_API_KEY")
        # google_cx = os.getenv("GOOGLE_CSE_CX")
        # if google_key and google_cx:
        #     self.providers["google_cse"] = GoogleCustomSearchProvider(google_key, google_cx)

        # ScaleSerpAmazon - DISABLED (organic search has no images or prices)
        # scaleserp_key = os.getenv("SCALESERP_API_KEY")
        # if scaleserp_key and scaleserp_key != "demo":
        #     self.providers["amazon"] = ScaleSerpAmazonProvider(scaleserp_key)
        
        # SearchAPI (original)
        # searchapi_key = os.getenv("SEARCHAPI_API_KEY")
        # if searchapi_key:
        #     self.providers["searchapi"] = SearchAPIProvider(searchapi_key)

        # eBay Browse API (official)
        # ebay_client_id = os.getenv("EBAY_CLIENT_ID")
        # ebay_client_secret = os.getenv("EBAY_CLIENT_SECRET")
        # ebay_marketplace_id = os.getenv("EBAY_MARKETPLACE_ID", "EBAY-US")
        # if ebay_client_id and ebay_client_secret:
        #     self.providers["ebay"] = EbayBrowseProvider(...)
        
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

    async def search_all(self, query: str, **kwargs) -> List[SearchResult]:
        """Search all providers and return results only (backwards compatible)."""
        result = await self.search_all_with_status(query, **kwargs)
        return result.results

    def _filter_providers_by_tier(self, providers: Dict[str, "SourcingProvider"], desire_tier: Optional[str] = None) -> Dict[str, "SourcingProvider"]:
        """
        PASS-THROUGH: All providers run for all queries. No hard-gating.

        The three-stage re-ranker's tier_fit multiplier in scorer.py handles
        relevance scoring (Amazon scores 0.2 for service queries, vendors score
        0.85 for commodity). Hard-gating was removed because:
        - Vendors span all tiers (toy stores ARE commodity sellers)
        - Prevents serendipitous discoveries
        - Fails on edge cases (e.g., "catering equipment" IS on Amazon)
        """
        if desire_tier:
            print(f"[SourcingRepository] Tier '{desire_tier}' — running ALL providers (no gating): {list(providers.keys())}")
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
            allow = {str(p).strip() for p in providers_filter if str(p).strip()}
            selected_providers = {k: v for k, v in self.providers.items() if k in allow}
            print(f"[SourcingRepository] Provider filter requested: {sorted(list(allow))}")
            print(f"[SourcingRepository] Providers selected: {list(selected_providers.keys())}")

        # Apply desire-tier filtering
        selected_providers = self._filter_providers_by_tier(selected_providers, desire_tier)
        
        if vendor_query:
            print(f"[SourcingRepository] Vendor query (LLM intent): {vendor_query!r}")

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
            # Vendor directory: use LLM's clean intent as primary query,
            # pass full query as context_query for weighted blending (70/30)
            if name == "vendor_directory" and vendor_query:
                effective_query = vendor_query
                extra_kwargs = {**kwargs, "context_query": query}
            else:
                effective_query = query
                extra_kwargs = kwargs
            print(f"[SourcingRepository] Starting search with provider: {name} query={effective_query!r}")
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
        vendor_query = kwargs.pop("vendor_query", None)
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
            if name == "vendor_directory" and vendor_query:
                effective_query = vendor_query
                extra_kwargs = {**kwargs, "context_query": query}
            else:
                effective_query = query
                extra_kwargs = kwargs
            print(f"[SourcingRepository] [STREAM] Starting provider: {name} query={effective_query!r}")
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
