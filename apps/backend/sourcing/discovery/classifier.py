"""Runtime pathing for commodity search vs vendor discovery."""

from __future__ import annotations

from typing import Optional

from models.rows import Row
from sourcing.models import SearchIntent


def classify_search_path(intent: Optional[SearchIntent], row: Optional[Row]) -> str:
    desire_tier = (getattr(row, "desire_tier", None) or "").strip().lower()
    is_service = bool(getattr(row, "is_service", False))
    service_category = (getattr(row, "service_category", None) or "").strip().lower()

    if is_service or service_category:
        return "vendor_discovery_path"
    if desire_tier in {"service", "bespoke", "high_value", "advisory"}:
        return "vendor_discovery_path"
    if intent and intent.location_context.relevance in {"service_area", "vendor_proximity"}:
        return "vendor_discovery_path"
    return "commodity_marketplace_path"


def select_discovery_mode(intent: Optional[SearchIntent], row: Optional[Row]) -> str:
    service_category = (getattr(row, "service_category", None) or "").strip().lower()
    desire_tier = (getattr(row, "desire_tier", None) or "").strip().lower()
    relevance = intent.location_context.relevance if intent else "none"
    raw_input = (intent.raw_input if intent else "") or ""
    text = f"{service_category} {raw_input}".lower()

    if any(token in text for token in ("aircraft", "gulfstream", "jet", "yacht", "broker")):
        return "asset_market_discovery"
    if service_category in {"real_estate", "luxury_real_estate"} or any(token in text for token in ("real estate", "brokerage", "realtor", "listing")):
        return "luxury_brokerage_discovery"
    if desire_tier == "advisory":
        return "advisory_discovery"
    if any(token in text for token in ("whisky", "watch", "jewelry", "auction", "collector")):
        return "uhnw_goods_discovery"
    if relevance == "endpoint":
        return "destination_service_discovery"
    if relevance in {"service_area", "vendor_proximity"}:
        return "local_service_discovery"
    if desire_tier in {"high_value", "bespoke"}:
        return "uhnw_goods_discovery"
    return "local_service_discovery"
