"""Apify tool implementations — actor execution and store search.

Extracted from tool_executor.py to keep individual tool files focused.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from sourcing.models import NormalizedResult
from sourcing.tools import ToolResult

logger = logging.getLogger(__name__)


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
            timeout_seconds=90.0,
            max_results=max_results,
        )
    except Exception as e:
        logger.error("[ToolExec] run_apify failed: %s", e, exc_info=True)
        return ToolResult(error=f"Apify actor failed: {e}")

    if batch.status != "ok":
        return ToolResult(
            error=batch.error_message or f"Apify actor returned status: {batch.status}",
        )

    # Convert DiscoveryCandidate → NormalizedResult, skipping aggregator domains
    from sourcing.vendor_provider import AGGREGATOR_DOMAINS
    normalized = []
    for c in batch.results:
        domain = ""
        try:
            domain = urlparse(c.url).netloc.lower().removeprefix("www.")
        except Exception:
            pass
        if domain and domain in AGGREGATOR_DOMAINS:
            continue
        # Also check with www. prefix
        if domain and f"www.{domain}" in AGGREGATOR_DOMAINS:
            continue
        # Carry contact info through raw_data so _persist_results can
        # enrich vendor records (phone, email, website, location, description).
        raw_data: Dict[str, Any] = {}
        if getattr(c, "phone", None):
            raw_data["phone"] = c.phone
        if getattr(c, "email", None):
            raw_data["email"] = c.email
        if getattr(c, "location_hint", None):
            raw_data["location_hint"] = c.location_hint
        if getattr(c, "snippet", None):
            raw_data["description"] = c.snippet
        if c.url:
            raw_data["website"] = c.url

        normalized.append(NormalizedResult(
            title=c.title,
            url=c.url,
            source=f"apify_{actor_id}",
            merchant_name=c.title,
            merchant_domain=domain,
            image_url=getattr(c, "image_url", None),
            rating=c.trust_signals.get("rating") if hasattr(c, "trust_signals") else None,
            reviews_count=c.trust_signals.get("reviews_count") if hasattr(c, "trust_signals") else None,
            raw_data=raw_data,
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
