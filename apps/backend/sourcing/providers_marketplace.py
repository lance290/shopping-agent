"""
Marketplace provider classes (eBay Browse, Rainforest/Amazon).

Extracted from sourcing/repository.py to keep files under 450 lines.
"""
import httpx
import os
import re
import time
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from sourcing.repository import SearchResult, SourcingProvider, normalize_url, compute_match_score
from sourcing.models import NormalizedResult, ProviderStatusSnapshot
from utils.security import redact_secrets_from_text

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


