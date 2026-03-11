"""Tool executor — thin wrappers that route ToolCall objects to existing providers.

Each _tool_* function calls existing provider code and returns ToolResult.
No routing, no gating, no reranking — just pass-through to providers.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from sourcing.models import NormalizedResult
from sourcing.normalizers import normalize_results_for_provider
from sourcing.tools import ToolCall, ToolResult

logger = logging.getLogger(__name__)


async def execute_tools_parallel(
    tool_calls: list[ToolCall],
    timeout_per_tool: float = 30.0,
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
# Individual tool implementations
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

    # vendor_query = clean intent, context_query = full context with location
    # This prevents query dilution (the root cause of the Nashville bug)
    if location:
        kwargs["context_query"] = f"{query} {location}"
    if category:
        kwargs["intent_payload"] = {"product_category": category}

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


async def _tool_search_web(
    query: str,
    max_results: int = 10,
) -> ToolResult:
    """General web search via SerpAPI or SearchAPI (engine=google, NOT shopping).

    SourcingRepository providers all use engine=google_shopping which is wrong
    for informational queries. This calls the APIs directly with engine=google.
    """
    import httpx
    from sourcing.repository import SearchResult, extract_merchant_domain, normalize_url

    # Try APIs in order until one works
    attempts = [
        ("serpapi", "SERPAPI_API_KEY", "https://serpapi.com/search", "organic_results"),
        ("searchapi", "SEARCHAPI_API_KEY", "https://www.searchapi.io/api/v1/search", "organic_results"),
    ]

    for provider_name, env_key, base_url, results_key in attempts:
        api_key = os.getenv(env_key, "")
        if not api_key:
            continue

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "us",
            "hl": "en",
            "num": max_results,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("[ToolExec] search_web %s failed: %s", provider_name, e)
            continue

        organic = data.get(results_key, [])
        if not organic:
            logger.info("[ToolExec] search_web %s returned 0 organic results", provider_name)
            continue

        normalized = []
        for item in organic[:max_results]:
            url = normalize_url(item.get("link", ""))
            domain = extract_merchant_domain(url)
            normalized.append(NormalizedResult(
                title=item.get("title", "Unknown"),
                url=url,
                source=f"web_{provider_name}",
                merchant_name=domain or "Web",
                merchant_domain=domain,
                raw_data={"snippet": item.get("snippet", "")},
            ))

        return ToolResult(
            items=normalized,
            metadata={"source": "web_search", "provider": provider_name},
        )

    return ToolResult(error="No web search API key configured or all returned 0 results")


_APIFY_BLOCKLIST: set[str] = {
    "webdatalabs/ebay-deal-finder",       # times out with 0 results
    "apidojo/tiktok-scraper",             # fails immediately
    "lukaskrivka/google-maps-with-contact-details",  # slow, use compass scraper
}


async def _tool_run_apify(
    actor_id: str,
    run_input: Optional[Dict[str, Any]] = None,
    max_results: int = 10,
) -> ToolResult:
    """Run an Apify actor and normalize results."""
    if actor_id in _APIFY_BLOCKLIST:
        return ToolResult(
            error=f"Actor '{actor_id}' is blocklisted (known slow/flaky). "
                  "Use an alternative actor or a different tool.",
        )

    from sourcing.discovery.adapters.apify import ApifyDiscoveryAdapter

    adapter = ApifyDiscoveryAdapter()
    effective_input = run_input or {}

    try:
        batch = await adapter.run_actor(
            actor_id=actor_id,
            run_input=effective_input,
            query=actor_id,
            timeout_seconds=30.0,
            max_results=max_results,
        )
    except Exception as e:
        logger.error("[ToolExec] run_apify failed: %s", e, exc_info=True)
        return ToolResult(error=f"Apify actor failed: {e}")

    if batch.status != "ok":
        return ToolResult(
            error=batch.error_message or f"Apify actor returned status: {batch.status}",
        )

    # Convert DiscoveryCandidate → NormalizedResult
    normalized = []
    for c in batch.results:
        domain = ""
        try:
            domain = urlparse(c.url).netloc.lower().removeprefix("www.")
        except Exception:
            pass
        normalized.append(NormalizedResult(
            title=c.title,
            url=c.url,
            source=f"apify_{actor_id}",
            merchant_name=c.title,
            merchant_domain=domain,
            image_url=getattr(c, "image_url", None),
            rating=c.trust_signals.get("rating") if hasattr(c, "trust_signals") else None,
            reviews_count=c.trust_signals.get("reviews_count") if hasattr(c, "trust_signals") else None,
        ))

    return ToolResult(
        items=normalized[:max_results],
        metadata={"source": f"apify_{actor_id}"},
    )


async def _tool_search_apify_store(
    search_term: str,
    max_results: int = 5,
) -> ToolResult:
    """Search Apify Store for available actors."""
    from sourcing.discovery.adapters.apify import search_apify_store

    try:
        actors = await search_apify_store(search_term, limit=max_results)
    except Exception as e:
        logger.error("[ToolExec] search_apify_store failed: %s", e, exc_info=True)
        return ToolResult(error=f"Apify Store search failed: {e}")

    # Return actor metadata as NormalizedResult-like items for consistency
    normalized = []
    for a in actors:
        normalized.append(NormalizedResult(
            title=a.get("title", a.get("actor_id", "Unknown")),
            url=f"https://apify.com/{a.get('actor_id', '')}",
            source="apify_store",
            merchant_name="Apify",
            merchant_domain="apify.com",
            raw_data={
                "actor_id": a.get("actor_id"),
                "description": a.get("description"),
                "total_users": a.get("total_users"),
                "total_runs": a.get("total_runs"),
                "pricing": a.get("pricing"),
            },
        ))

    return ToolResult(
        items=normalized[:max_results],
        metadata={"source": "apify_store", "search_term": search_term},
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
