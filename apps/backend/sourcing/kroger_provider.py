"""Kroger Product Search provider for grocery sourcing.

Uses Kroger's public API (developer.kroger.com) to search products
with real-time pricing, stock availability, and images.

Required env vars:
  KROGER_CLIENT_ID     — OAuth2 client ID
  KROGER_CLIENT_SECRET — OAuth2 client secret

Optional:
  KROGER_LOCATION_ID   — default store location ID (for local pricing)
  KROGER_ZIP_CODE      — ZIP code for nearby store lookup
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from sourcing.repository import SearchResult, SourcingProvider, extract_merchant_domain, normalize_url

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"
_PRODUCTS_URL = "https://api.kroger.com/v1/products"
_LOCATIONS_URL = "https://api.kroger.com/v1/locations"


class KrogerProvider(SourcingProvider):
    """Kroger Product API — grocery search with real-time pricing."""

    # Keywords that signal a grocery / household query (broad; most Pop queries qualify)
    _GROCERY_KEYWORDS = {
        "milk", "eggs", "bread", "butter", "cheese", "chicken", "beef", "pork",
        "rice", "pasta", "cereal", "yogurt", "juice", "water", "soda", "coffee",
        "tea", "sugar", "flour", "oil", "sauce", "ketchup", "mustard", "mayo",
        "salt", "pepper", "spice", "snack", "chips", "crackers", "cookies",
        "fruit", "apple", "banana", "orange", "grape", "berry", "strawberry",
        "vegetable", "tomato", "potato", "onion", "lettuce", "carrot", "broccoli",
        "frozen", "pizza", "ice cream", "soup", "canned", "beans", "corn",
        "paper towel", "toilet paper", "detergent", "soap", "shampoo", "toothpaste",
        "diaper", "wipes", "trash bag", "foil", "wrap", "bag", "napkin",
        "grocery", "food", "drink", "beverage", "organic", "gluten free",
    }

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        location_id: Optional[str] = None,
        zip_code: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self._default_location_id = location_id
        self._default_zip_code = zip_code
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        # Cache: zip_code -> locationId (avoids repeated location lookups)
        self._zip_to_location: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # OAuth2 client-credentials flow
    # ------------------------------------------------------------------

    async def _get_access_token(self) -> Optional[str]:
        now = time.time()
        if self._token and now < (self._token_expires_at - 60):
            return self._token

        basic = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("utf-8")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    _TOKEN_URL,
                    data={"grant_type": "client_credentials", "scope": "product.compact"},
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": f"Basic {basic}",
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
        except Exception as e:
            logger.error(f"[KrogerProvider] OAuth token request failed: {e}")
            return None

        token = payload.get("access_token")
        expires_in = payload.get("expires_in", 1800)
        if not token:
            logger.error("[KrogerProvider] No access_token in OAuth response")
            return None

        self._token = token
        try:
            self._token_expires_at = time.time() + float(expires_in)
        except Exception:
            self._token_expires_at = time.time() + 1800

        logger.info("[KrogerProvider] OAuth token acquired")
        return token

    # ------------------------------------------------------------------
    # Location lookup (cached per zip code)
    # ------------------------------------------------------------------

    async def _resolve_location_id(self, token: str, zip_code: Optional[str] = None) -> Optional[str]:
        """Resolve a Kroger locationId from ZIP code, with per-zip caching."""
        if self._default_location_id and not zip_code:
            return self._default_location_id

        effective_zip = zip_code or self._default_zip_code
        if not effective_zip:
            return None

        # Return cached location for this zip
        if effective_zip in self._zip_to_location:
            return self._zip_to_location[effective_zip]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    _LOCATIONS_URL,
                    params={"filter.zipCode.near": effective_zip, "filter.limit": 1},
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                locations = data.get("data", [])
                if locations:
                    loc_id = locations[0].get("locationId")
                    self._zip_to_location[effective_zip] = loc_id
                    logger.info(f"[KrogerProvider] Resolved zip {effective_zip} -> location {loc_id}")
                    return loc_id
        except Exception as e:
            logger.warning(f"[KrogerProvider] Location lookup failed for {effective_zip}: {e}")

        return None

    # ------------------------------------------------------------------
    # Product search
    # ------------------------------------------------------------------

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        token = await self._get_access_token()
        if not token:
            return []

        # Per-user zip_code override (passed from sourcing pipeline)
        user_zip = kwargs.pop("zip_code", None)
        location_id = await self._resolve_location_id(token, zip_code=user_zip)

        params: Dict[str, Any] = {
            "filter.term": query,
            "filter.limit": 20,
        }
        if location_id:
            params["filter.locationId"] = location_id

        logger.info(f"[KrogerProvider] Searching: {query!r} location={location_id}")

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(
                    _PRODUCTS_URL,
                    params=params,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"[KrogerProvider] HTTP {e.response.status_code}: {e.response.text[:200]}")
            return []
        except Exception as e:
            logger.error(f"[KrogerProvider] Search failed: {e}")
            return []

        products = data.get("data", [])
        logger.info(f"[KrogerProvider] Got {len(products)} products")

        results: List[SearchResult] = []
        for item in products:
            try:
                product_id = item.get("productId", "")
                description = item.get("description", "Unknown")
                brand = item.get("brand", "")
                title = f"{brand} {description}".strip() if brand else description

                # Price: items[].price.regular and items[].price.promo
                items_list = item.get("items", [])
                price = 0.0
                promo_price = None
                size_text = ""
                if items_list:
                    first_item = items_list[0]
                    price_obj = first_item.get("price", {})
                    price = price_obj.get("regular", 0.0) or 0.0
                    promo_price = price_obj.get("promo", None)
                    size_text = first_item.get("size", "")

                # Use promo price if available
                display_price = promo_price if promo_price and promo_price > 0 else price
                if display_price <= 0:
                    continue

                # Images: prefer large → medium → small → thumbnail
                images = item.get("images", [])
                image_url = None
                for img_group in images:
                    sizes = img_group.get("sizes", [])
                    # Sort by size descending
                    for preferred in ("large", "medium", "small", "thumbnail"):
                        for s in sizes:
                            if s.get("size") == preferred and s.get("url"):
                                image_url = s["url"]
                                break
                        if image_url:
                            break
                    if image_url:
                        break

                # Build Kroger product URL
                url = f"https://www.kroger.com/p/{product_id}"

                # Shipping info: show size and promo status
                shipping_parts = []
                if size_text:
                    shipping_parts.append(size_text)
                if promo_price and promo_price > 0 and promo_price < price:
                    savings = price - promo_price
                    shipping_parts.append(f"Save ${savings:.2f}")
                shipping_info = " · ".join(shipping_parts) if shipping_parts else None

                results.append(SearchResult(
                    title=title,
                    price=display_price,
                    currency="USD",
                    merchant="Kroger",
                    url=url,
                    merchant_domain="kroger.com",
                    image_url=image_url,
                    rating=None,
                    reviews_count=None,
                    shipping_info=shipping_info,
                    source="kroger",
                ))
            except Exception as e:
                logger.warning(f"[KrogerProvider] Error parsing product: {e}")
                continue

        logger.info(f"[KrogerProvider] Returning {len(results)} results")
        return results
