"""Tool executor — thin wrappers that route ToolCall objects to existing providers.

Each _tool_* function calls existing provider code and returns ToolResult.
No routing, no gating, no reranking — just pass-through to providers.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from sourcing.models import NormalizedResult
from sourcing.normalizers import normalize_results_for_provider
from sourcing.tools import ToolCall, ToolResult
from sourcing.tool_web_search import (  # noqa: F401 — re-exported + used by _execute_single
    _ddg_html_search,
    _is_non_commercial_url,
    _tool_search_web,
)
from sourcing.tool_apify import (  # noqa: F401 — re-exported + used by _execute_single
    _APIFY_BLOCKLIST,
    _tool_run_apify,
    _tool_search_apify_store,
)

logger = logging.getLogger(__name__)


async def execute_tools_parallel(
    tool_calls: list[ToolCall],
    timeout_per_tool: float = 90.0,
) -> list[ToolResult]:
    """Execute multiple tool calls in parallel with per-tool timeout."""

    async def _safe_execute(tc: ToolCall) -> ToolResult:
        try:
            return await asyncio.wait_for(
                _execute_single(tc),
                timeout=timeout_per_tool,
            )
        except asyncio.TimeoutError:
            logger.warning("[ToolExec] %s timed out after %.0fs", tc.name, timeout_per_tool)
            return ToolResult(error=f"Tool {tc.name} timed out")
        except Exception as e:
            logger.error("[ToolExec] %s failed: %s", tc.name, e, exc_info=True)
            return ToolResult(error=f"Tool {tc.name} failed: {e}")

    tasks = [_safe_execute(tc) for tc in tool_calls]
    return list(await asyncio.gather(*tasks))


async def _execute_single(tool_call: ToolCall) -> ToolResult:
    """Route a tool call to its implementation."""
    match tool_call.name:
        case "search_vendors":
            return await _tool_search_vendors(**tool_call.params)
        case "search_marketplace":
            return await _tool_search_marketplace(**tool_call.params)
        case "search_web":
            return await _tool_search_web(**tool_call.params)
        case "run_apify_actor":
            return await _tool_run_apify(**tool_call.params)
        case "search_apify_store":
            return await _tool_search_apify_store(**tool_call.params)
        case _:
            return ToolResult(error=f"Unknown tool: {tool_call.name}")


# ---------------------------------------------------------------------------
# Individual tool implementations (vendors + marketplace kept here,
# web search → tool_web_search.py, apify → tool_apify.py)
# ---------------------------------------------------------------------------

async def _tool_search_vendors(
    query: str,
    location: Optional[str] = None,
    category: Optional[str] = None,
    max_results: int = 10,
) -> ToolResult:
    """Search internal vendor database via VendorDirectoryProvider.

    The provider handles embedding, hybrid vector+FTS search, and geo filtering
    internally. We pass the right parameters to leverage existing logic.
    """
    from sourcing.vendor_provider import VendorDirectoryProvider

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        return ToolResult(error="DATABASE_URL not configured")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    provider = VendorDirectoryProvider(db_url)

    kwargs: Dict[str, Any] = {"limit": max_results}

    # Build structured intent_payload so the vendor provider's geo-filtering
    # can activate (it needs location_context + location_resolution with lat/lon).
    intent_payload: Dict[str, Any] = {}
    if category:
        intent_payload["product_category"] = category

    if location:
        kwargs["context_query"] = f"{query} {location}"
        # Geocode the location so the vendor provider can do proximity filtering
        try:
            from services.geocoding import GeocodingService
            geo_svc = GeocodingService()
            resolution = await geo_svc.resolve_location(location, "service_location")
            resolution_dict = resolution.model_dump()
            intent_payload["location_context"] = {
                "relevance": "service_area",
                "targets": {"service_location": location},
            }
            intent_payload["location_resolution"] = {
                "service_location": resolution_dict,
            }
            logger.info(
                "[ToolExec] search_vendors geocoded location=%r → status=%s lat=%s lon=%s",
                location, resolution.status, resolution.lat, resolution.lon,
            )
        except Exception as e:
            logger.warning("[ToolExec] search_vendors geocoding failed for %r: %s", location, e)
            # Fall back to text-based location matching (terms only, no lat/lon)
            intent_payload["location_context"] = {
                "relevance": "service_area",
                "targets": {"service_location": location},
            }

    if intent_payload:
        kwargs["intent_payload"] = intent_payload

    try:
        results = await provider.search(query, **kwargs)
    except Exception as e:
        logger.error("[ToolExec] search_vendors failed: %s", e, exc_info=True)
        return ToolResult(error=f"Vendor search failed: {e}")

    normalized = normalize_results_for_provider("vendor_directory", results)

    return ToolResult(
        items=normalized[:max_results],
        metadata={"source": "vendor_directory", "location_filter": location},
    )


async def _tool_search_marketplace(
    query: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    marketplaces: Optional[List[str]] = None,
    max_results: int = 8,
) -> ToolResult:
    """Search Amazon, eBay, Google Shopping in parallel via SourcingRepository."""
    from sourcing.repository import SourcingRepository

    repo = SourcingRepository()
    targets = marketplaces or ["amazon", "ebay", "google_shopping"]

    # Map user-facing names to SourcingRepository canonical provider names
    provider_map = {
        "amazon": "amazon",
        "ebay": "ebay",
        "google_shopping": "searchapi",
    }
    selected = [provider_map[t] for t in targets if t in provider_map]

    try:
        response = await repo.search_all_with_status(query, providers=selected)
    except Exception as e:
        logger.error("[ToolExec] search_marketplace failed: %s", e, exc_info=True)
        return ToolResult(error=f"Marketplace search failed: {e}")

    # Filter by price in Python (not all providers support price filtering natively)
    items = response.results
    if min_price is not None:
        items = [r for r in items if r.price and r.price >= min_price]
    if max_price is not None:
        items = [r for r in items if r.price and r.price <= max_price]

    normalized = normalize_results_for_provider("marketplace", items)
    cap = max_results * len(targets)

    return ToolResult(
        items=normalized[:cap],
        metadata={"source": "marketplace", "marketplaces": targets},
    )


def _dedupe_results(results: list[NormalizedResult]) -> list[NormalizedResult]:
    """Cross-tool domain-based deduplication."""
    seen_urls: set[str] = set()
    deduped: list[NormalizedResult] = []
    for r in results:
        url_key = r.url.lower().rstrip("/")
        if url_key not in seen_urls:
            seen_urls.add(url_key)
            deduped.append(r)
    return deduped
