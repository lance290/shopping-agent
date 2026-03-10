"""Server-side organic discovery adapter using configured search APIs."""

from __future__ import annotations

import os
import time
from typing import Any, List

import httpx

from sourcing.discovery.adapters.base import DiscoveryAdapter, DiscoveryBatch, DiscoveryCandidate
from sourcing.discovery.extractors import canonical_domain, extract_contact_hints


class OrganicDiscoveryAdapter(DiscoveryAdapter):
    adapter_id = "google_organic"
    supported_modes = {
        "local_service_discovery",
        "destination_service_discovery",
        "luxury_brokerage_discovery",
        "uhnw_goods_discovery",
        "advisory_discovery",
        "asset_market_discovery",
    }

    async def search(
        self,
        query: str,
        *,
        discovery_mode: str,
        timeout_seconds: float,
        max_results: int,
    ) -> DiscoveryBatch:
        started = time.monotonic()
        try:
            results = await _search_organic(query, max_results=max_results, timeout_seconds=timeout_seconds)
            latency_ms = int((time.monotonic() - started) * 1000)
            return DiscoveryBatch(self.adapter_id, query, results, "ok", latency_ms)
        except Exception as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            return DiscoveryBatch(self.adapter_id, query, [], "error", latency_ms, str(exc)[:160])


async def _search_organic(query: str, *, max_results: int, timeout_seconds: float) -> List[DiscoveryCandidate]:
    serpapi_key = os.getenv("SERPAPI_API_KEY", "")
    searchapi_key = os.getenv("SEARCHAPI_API_KEY", "")
    scaleserp_key = os.getenv("SCALESERP_API_KEY", "")

    if serpapi_key:
        payload = await _get_json(
            "https://serpapi.com/search",
            {"engine": "google", "q": query, "api_key": serpapi_key, "num": max_results, "gl": "us", "hl": "en"},
            timeout_seconds,
        )
        items = payload.get("organic_results", [])
    elif searchapi_key:
        payload = await _get_json(
            "https://www.searchapi.io/api/v1/search",
            {"engine": "google", "q": query, "api_key": searchapi_key, "num": max_results, "gl": "us", "hl": "en"},
            timeout_seconds,
        )
        items = payload.get("organic_results", [])
    elif scaleserp_key:
        payload = await _get_json(
            "https://api.scaleserp.com/search",
            {"q": query, "api_key": scaleserp_key, "num": max_results, "gl": "us", "hl": "en"},
            timeout_seconds,
        )
        items = payload.get("organic_results", [])
    else:
        return []

    results: List[DiscoveryCandidate] = []
    for item in items[:max_results]:
        url = str(item.get("link") or item.get("url") or "").strip()
        if not url:
            continue
        title = str(item.get("title") or "").strip() or url
        snippet = str(item.get("snippet") or "").strip()
        email, phone = extract_contact_hints(snippet)
        results.append(
            DiscoveryCandidate(
                adapter_id="google_organic",
                query=query,
                title=title,
                url=url,
                source_url=url,
                source_type="unknown",
                snippet=snippet,
                image_url=item.get("thumbnail"),
                email=email,
                phone=phone,
                official_site=False,
                first_party_contact=bool(email or phone),
                canonical_domain=canonical_domain(url),
                raw_payload=item if isinstance(item, dict) else {"value": item},
                trust_signals={"result_rank": len(results) + 1},
            )
        )
    return results


async def _get_json(url: str, params: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}
