"""eBay Browse API result normalizer."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sourcing.models import NormalizedResult


def normalize_ebay_result(item: Dict[str, Any]) -> Optional[NormalizedResult]:
    """Normalize a single eBay Browse API item summary into a NormalizedResult."""
    title = item.get("title", "")
    if not title:
        return None

    # Price extraction
    price_obj = item.get("price", {})
    price_value = None
    currency = "USD"
    if isinstance(price_obj, dict):
        try:
            price_value = float(price_obj.get("value", 0))
        except (ValueError, TypeError):
            price_value = None
        currency = price_obj.get("currency", "USD")

    # Image
    image = item.get("image", {})
    image_url = image.get("imageUrl") if isinstance(image, dict) else None

    # URL
    item_url = item.get("itemWebUrl", item.get("itemHref", ""))

    # Seller info
    seller_info = item.get("seller", {})
    seller_name = seller_info.get("username", "eBay Seller") if isinstance(seller_info, dict) else "eBay Seller"

    # Condition
    condition = item.get("condition", "")

    # Shipping
    shipping_options = item.get("shippingOptions", [])
    shipping_info = None
    if shipping_options and isinstance(shipping_options, list):
        first = shipping_options[0] if shipping_options else {}
        if isinstance(first, dict):
            cost = first.get("shippingCost", {})
            if isinstance(cost, dict) and cost.get("value") == "0.00":
                shipping_info = "Free shipping"
            else:
                shipping_info = first.get("type", "Standard")

    # Item ID for canonical URL
    item_id = item.get("itemId", "")
    canonical_url = f"https://www.ebay.com/itm/{item_id}" if item_id else item_url

    return NormalizedResult(
        title=title,
        url=item_url,
        source="ebay_browse",
        price=price_value,
        currency=currency,
        canonical_url=canonical_url,
        merchant_name=seller_name,
        merchant_domain="ebay.com",
        image_url=image_url,
        shipping_info=shipping_info,
        raw_data=item,
        provenance={
            "provider": "ebay_browse",
            "condition": condition,
            "item_id": item_id,
            "product_info": {
                "source_provider": "ebay_browse",
                "condition": condition,
            },
        },
    )


def normalize_ebay_results(raw_items: List[Dict[str, Any]]) -> List[NormalizedResult]:
    """Normalize a list of eBay Browse API results."""
    results = []
    for item in raw_items:
        normalized = normalize_ebay_result(item)
        if normalized:
            results.append(normalized)
    return results
