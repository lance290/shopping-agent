"""Runtime pathing for commodity search vs vendor discovery.

The LLM is authoritative for execution_mode when present and confident.
Heuristics are fallback-only for missing, invalid, or low-confidence intent.
"""

from __future__ import annotations

import logging
from typing import Optional

from models.rows import Row
from sourcing.models import SearchIntent

logger = logging.getLogger(__name__)

_VALID_EXECUTION_MODES = {"affiliate_only", "sourcing_only", "affiliate_plus_sourcing"}

# Minimum intent confidence to trust the LLM's execution_mode
_LLM_TRUST_THRESHOLD = 0.5


def _llm_execution_mode(intent: Optional[SearchIntent]) -> Optional[str]:
    """Return the LLM's execution_mode if present, valid, and confident."""
    if not intent or not intent.execution_mode:
        return None
    mode = intent.execution_mode.strip().lower()
    if mode not in _VALID_EXECUTION_MODES:
        return None
    if intent.confidence < _LLM_TRUST_THRESHOLD:
        logger.info("[classifier] LLM execution_mode=%s but confidence=%.2f < threshold, falling back", mode, intent.confidence)
        return None
    return mode


def classify_search_path(intent: Optional[SearchIntent], row: Optional[Row]) -> str:
    """Determine whether this request takes the vendor discovery path or commodity marketplace path.

    Priority:
    1. LLM execution_mode (authoritative when valid and confident)
    2. Heuristic fallback from desire_tier, service flags, and location context
    """
    llm_mode = _llm_execution_mode(intent)
    if llm_mode:
        if llm_mode == "affiliate_only":
            logger.info("[classifier] LLM authoritative: affiliate_only -> commodity_marketplace_path")
            return "commodity_marketplace_path"
        logger.info("[classifier] LLM authoritative: %s -> vendor_discovery_path", llm_mode)
        return "vendor_discovery_path"

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


def execution_mode_for_row(intent: Optional[SearchIntent], row: Optional[Row]) -> str:
    """Return a concrete execution_mode string for persistence and downstream logic."""
    llm_mode = _llm_execution_mode(intent)
    if llm_mode:
        return llm_mode
    path = classify_search_path(intent, row)
    return "sourcing_only" if path == "vendor_discovery_path" else "affiliate_only"


def select_discovery_mode(intent: Optional[SearchIntent], row: Optional[Row]) -> str:
    """Select the discovery sub-mode for vendor discovery path.

    Uses LLM search_strategies when available; falls back to token heuristics.
    """
    if intent and intent.search_strategies:
        strategies = set(intent.search_strategies)
        if "specialist_first" in strategies:
            service_category = (getattr(row, "service_category", None) or "").strip().lower()
            if service_category in {"real_estate", "luxury_real_estate"}:
                return "luxury_brokerage_discovery"
            raw_input = (intent.raw_input if intent else "") or ""
            text = f"{service_category} {raw_input}".lower()
            if any(tok in text for tok in ("aircraft", "gulfstream", "jet", "yacht")):
                return "asset_market_discovery"
            if any(tok in text for tok in ("real estate", "realtor", "brokerage")):
                return "luxury_brokerage_discovery"
        if "local_network_first" in strategies:
            return "local_service_discovery"
        if "prestige_first" in strategies:
            desire_tier = (getattr(row, "desire_tier", None) or "").strip().lower()
            if desire_tier == "advisory":
                return "advisory_discovery"
            return "uhnw_goods_discovery"
        if "official_first" in strategies:
            return "advisory_discovery"

    service_category = (getattr(row, "service_category", None) or "").strip().lower()
    desire_tier = (getattr(row, "desire_tier", None) or "").strip().lower()
    relevance = intent.location_context.relevance if intent else "none"
    raw_input = (intent.raw_input if intent else "") or ""
    text = f"{service_category} {raw_input}".lower()

    if any(token in text for token in ("aircraft", "gulfstream", "jet", "yacht")):
        return "asset_market_discovery"
    if " broker" in text and any(tok in text for tok in ("aircraft", "jet", "yacht")):
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
