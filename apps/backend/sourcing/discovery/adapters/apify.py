"""Generic Apify adapter for vendor discovery.

The LLM selects which Apify Actor to run and with what parameters.
This adapter is a thin execution layer — it does not decide *what* to scrape.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from apify_client import ApifyClientAsync

from sourcing.discovery.adapters.base import DiscoveryBatch, DiscoveryCandidate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Actor Registry — describes available Actors so the LLM can pick one.
# Each entry tells the LLM what the Actor does, what params it accepts,
# and how to normalise its output into a DiscoveryCandidate.
# ---------------------------------------------------------------------------

ACTOR_REGISTRY: Dict[str, Dict[str, Any]] = {
    "compass/crawler-google-places": {
        "description": "Google Maps / Places scraper. Returns local businesses with ratings, reviews, phone, address, and website.",
        "best_for": ["local businesses", "service providers", "restaurants", "brokerages", "agents", "contractors"],
        "param_hints": {
            "searchStringsArray": "list[str] — search queries",
            "maxCrawledPlacesPerSearch": "int — max results per query (default 5)",
            "language": "str — language code (default 'en')",
        },
        "normalizer": "_normalize_google_maps",
    },
    "apify/instagram-scraper": {
        "description": "Instagram scraper. Returns posts, profiles, and hashtag results with images, captions, follower counts.",
        "best_for": ["boutique artisans", "luxury goods makers", "bespoke creators", "visual portfolios", "custom jewelry", "fashion designers"],
        "param_hints": {
            "search": "str — hashtag or keyword to search",
            "searchType": "str — 'hashtag' or 'user' (default 'hashtag')",
            "resultsLimit": "int — max results (default 10)",
        },
        "normalizer": "_normalize_instagram",
    },
    "apify/website-content-crawler": {
        "description": "Deep website crawler. Extracts full page text/markdown from a given URL. Use for vendor verification and contact extraction.",
        "best_for": ["vendor verification", "contact extraction", "deep enrichment of a known vendor URL"],
        "param_hints": {
            "startUrls": "list[dict] — [{url: 'https://...'}]",
            "maxCrawlPages": "int — max pages to crawl (default 3)",
            "crawlerType": "str — 'cheerio' (fast) or 'playwright' (JS-rendered)",
        },
        "normalizer": "_normalize_website_content",
    },
    "voyager/tripadvisor-scraper": {
        "description": "TripAdvisor scraper. Returns reviews, ratings, and business details for hospitality and travel services.",
        "best_for": ["hotels", "restaurants", "tour operators", "travel services", "yacht charters", "private chefs"],
        "param_hints": {
            "query": "str — search query",
            "maxItems": "int — max results (default 5)",
        },
        "normalizer": "_normalize_tripadvisor",
    },
}


def get_registry_for_prompt() -> str:
    """Return a compact description of the Actor registry for inclusion in an LLM prompt."""
    lines = []
    for actor_id, meta in ACTOR_REGISTRY.items():
        lines.append(f"- **{actor_id}**: {meta['description']}")
        lines.append(f"  Best for: {', '.join(meta['best_for'])}")
        params = "; ".join(f"`{k}`: {v}" for k, v in meta["param_hints"].items())
        lines.append(f"  Params: {params}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generic Adapter
# ---------------------------------------------------------------------------

class ApifyDiscoveryAdapter:
    """Executes any Apify Actor selected by the LLM and normalises the output."""

    adapter_id = "apify"
    # supported_modes is intentionally broad — the LLM decides relevance
    supported_modes = {
        "local_service_discovery",
        "luxury_brokerage_discovery",
        "destination_service_discovery",
        "uhnw_goods_discovery",
        "asset_market_discovery",
        "advisory_discovery",
    }

    def __init__(self) -> None:
        self.api_key = os.getenv("APIFY_API_TOKEN")

    async def run_actor(
        self,
        *,
        actor_id: str,
        run_input: Dict[str, Any],
        query: str,
        timeout_seconds: float = 60.0,
        max_results: int = 10,
    ) -> DiscoveryBatch:
        """Run an arbitrary Apify Actor and return normalised results."""
        start_t = time.time()

        if not self.api_key:
            logger.warning("[ApifyAdapter] APIFY_API_TOKEN not set, skipping")
            return self._error_batch(query, 0, "Missing APIFY_API_TOKEN")

        if actor_id not in ACTOR_REGISTRY:
            logger.warning("[ApifyAdapter] Unknown actor_id=%s, running anyway", actor_id)

        client = ApifyClientAsync(self.api_key)
        try:
            run = await client.actor(actor_id).call(
                run_input=run_input,
                timeout_secs=int(timeout_seconds),
            )
            items: List[Dict] = []
            if run and run.get("defaultDatasetId"):
                dataset = client.dataset(run["defaultDatasetId"])
                async for item in dataset.iterate_items():
                    items.append(item)
                    if len(items) >= max_results:
                        break

            normalizer_name = ACTOR_REGISTRY.get(actor_id, {}).get("normalizer", "_normalize_generic")
            normalizer = _NORMALIZERS.get(normalizer_name, _normalize_generic)
            candidates = normalizer(items, query=query)

            latency_ms = int((time.time() - start_t) * 1000)
            logger.info(
                "[ApifyAdapter] actor=%s query='%s' results=%d latency=%dms",
                actor_id, query, len(candidates), latency_ms,
            )
            return DiscoveryBatch(
                adapter_id=f"apify_{actor_id.replace('/', '_')}",
                query=query,
                results=candidates,
                status="ok",
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_t) * 1000)
            logger.error("[ApifyAdapter] actor=%s error: %s", actor_id, e, exc_info=True)
            return self._error_batch(query, latency_ms, str(e))

    # Legacy DiscoveryAdapter.search() interface for the orchestrator
    async def search(
        self,
        query: str,
        *,
        discovery_mode: str,
        timeout_seconds: float = 30.0,
        max_results: int = 5,
    ) -> DiscoveryBatch:
        """Fallback search method using Google Maps when no LLM selection is available."""
        return await self.run_actor(
            actor_id="compass/crawler-google-places",
            run_input={
                "searchStringsArray": [query],
                "language": "en",
                "maxCrawledPlacesPerSearch": max_results,
            },
            query=query,
            timeout_seconds=timeout_seconds,
            max_results=max_results,
        )

    @staticmethod
    def _error_batch(query: str, latency_ms: int, message: str) -> DiscoveryBatch:
        return DiscoveryBatch(
            adapter_id="apify",
            query=query,
            results=[],
            status="error",
            latency_ms=latency_ms,
            error_message=message,
        )


# ---------------------------------------------------------------------------
# Normalizers — one per Actor output schema → DiscoveryCandidate
# ---------------------------------------------------------------------------

def _domain_from_url(url: str) -> Optional[str]:
    try:
        return urlparse(url).netloc.lower().lstrip("www.") or None
    except Exception:
        return None


def _normalize_google_maps(items: List[Dict], *, query: str) -> List[DiscoveryCandidate]:
    candidates = []
    for item in items:
        title = item.get("title", "")
        url = item.get("website") or item.get("url") or ""
        if not title:
            continue
        trust_signals: Dict[str, Any] = {}
        if item.get("totalScore"):
            trust_signals["rating"] = item["totalScore"]
        if item.get("reviewsCount"):
            trust_signals["reviews_count"] = item["reviewsCount"]
        candidates.append(DiscoveryCandidate(
            adapter_id="apify_google_maps",
            query=query,
            title=title,
            url=url,
            source_url=item.get("url", ""),
            source_type="local_directory",
            snippet=item.get("description", "") or item.get("categoryName", ""),
            image_url=item.get("imageUrl"),
            phone=item.get("phoneUnformatted") or item.get("phone"),
            location_hint=item.get("address"),
            official_site=bool(item.get("website")),
            first_party_contact=bool(item.get("phone")),
            canonical_domain=_domain_from_url(url),
            raw_payload=item,
            trust_signals=trust_signals,
        ))
    return candidates


def _normalize_instagram(items: List[Dict], *, query: str) -> List[DiscoveryCandidate]:
    candidates = []
    for item in items:
        username = item.get("ownerUsername") or item.get("username") or ""
        display_name = item.get("ownerFullName") or item.get("fullName") or username
        url = f"https://instagram.com/{username}" if username else item.get("url", "")
        if not display_name:
            continue
        trust_signals: Dict[str, Any] = {}
        if item.get("followersCount"):
            trust_signals["followers"] = item["followersCount"]
        if item.get("likesCount"):
            trust_signals["likes"] = item["likesCount"]
        candidates.append(DiscoveryCandidate(
            adapter_id="apify_instagram",
            query=query,
            title=display_name,
            url=url,
            source_url=url,
            source_type="social_profile",
            snippet=item.get("caption", "") or item.get("biography", ""),
            image_url=item.get("displayUrl") or item.get("profilePicUrl"),
            official_site=False,
            first_party_contact=bool(item.get("externalUrl")),
            canonical_domain="instagram.com",
            raw_payload=item,
            trust_signals=trust_signals,
        ))
    return candidates


def _normalize_website_content(items: List[Dict], *, query: str) -> List[DiscoveryCandidate]:
    candidates = []
    for item in items:
        url = item.get("url", "")
        title = item.get("title") or item.get("metadata", {}).get("title") or url
        text = item.get("text") or item.get("markdown") or ""
        candidates.append(DiscoveryCandidate(
            adapter_id="apify_website_content",
            query=query,
            title=title,
            url=url,
            source_url=url,
            source_type="official_vendor_site",
            snippet=text[:500],
            canonical_domain=_domain_from_url(url),
            raw_payload=item,
            extraction_payload={"full_text": text},
        ))
    return candidates


def _normalize_tripadvisor(items: List[Dict], *, query: str) -> List[DiscoveryCandidate]:
    candidates = []
    for item in items:
        name = item.get("name", "")
        url = item.get("url") or item.get("webUrl") or ""
        if not name:
            continue
        trust_signals: Dict[str, Any] = {}
        if item.get("rating"):
            trust_signals["rating"] = item["rating"]
        if item.get("reviewsCount") or item.get("numberOfReviews"):
            trust_signals["reviews_count"] = item.get("reviewsCount") or item.get("numberOfReviews")
        candidates.append(DiscoveryCandidate(
            adapter_id="apify_tripadvisor",
            query=query,
            title=name,
            url=url,
            source_url=url,
            source_type="directory_or_aggregator",
            snippet=item.get("description", ""),
            image_url=item.get("image"),
            phone=item.get("phone"),
            location_hint=item.get("address") or item.get("addressObj", {}).get("street1"),
            first_party_contact=bool(item.get("phone")),
            canonical_domain=_domain_from_url(url),
            raw_payload=item,
            trust_signals=trust_signals,
        ))
    return candidates


def _normalize_generic(items: List[Dict], *, query: str) -> List[DiscoveryCandidate]:
    """Best-effort normalizer for unknown Actor schemas."""
    candidates = []
    for item in items:
        title = item.get("title") or item.get("name") or item.get("text", "")[:80] or "Unknown"
        url = item.get("url") or item.get("website") or item.get("link") or ""
        if not url:
            continue
        candidates.append(DiscoveryCandidate(
            adapter_id="apify_generic",
            query=query,
            title=title,
            url=url,
            source_url=url,
            source_type="directory_or_aggregator",
            snippet=item.get("description") or item.get("snippet") or "",
            phone=item.get("phone"),
            location_hint=item.get("address"),
            canonical_domain=_domain_from_url(url),
            raw_payload=item,
        ))
    return candidates


_NORMALIZERS = {
    "_normalize_google_maps": _normalize_google_maps,
    "_normalize_instagram": _normalize_instagram,
    "_normalize_website_content": _normalize_website_content,
    "_normalize_tripadvisor": _normalize_tripadvisor,
    "_normalize_generic": _normalize_generic,
}
