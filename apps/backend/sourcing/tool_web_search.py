"""Web search tool implementations — SerpAPI, SearchAPI, Google CSE, DuckDuckGo.

Extracted from tool_executor.py to keep individual tool files focused.
"""

from __future__ import annotations

import logging
import os
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from sourcing.models import NormalizedResult
from sourcing.tools import ToolResult

logger = logging.getLogger(__name__)


_NON_COMMERCIAL_DOMAINS: set[str] = {
    # News / media
    "nytimes.com", "washingtonpost.com", "bbc.com", "bbc.co.uk", "cnn.com",
    "theguardian.com", "reuters.com", "apnews.com", "usatoday.com",
    "nbcnews.com", "cbsnews.com", "abcnews.go.com", "foxnews.com",
    "npr.org", "bloomberg.com", "cnbc.com", "forbes.com", "fortune.com",
    "businessinsider.com", "insider.com", "vice.com", "vox.com",
    "huffpost.com", "dailymail.co.uk", "nypost.com", "newsweek.com",
    "time.com", "people.com", "tmz.com", "pagesix.com",
    # Article / blog / listicle / entertainment
    "wikipedia.org", "medium.com", "quora.com", "reddit.com",
    "buzzfeed.com", "boredpanda.com", "ranker.com",
    "robbreport.com", "luxurylearnings.com", "purseblog.com",
    "bagaholicboy.com", "buro247.com", "highsnobiety.com",
    "hypebeast.com", "complex.com", "gq.com", "vogue.com",
    "elle.com", "harpersbazaar.com", "cosmopolitan.com",
    "wmagazine.com", "instyle.com", "allure.com",
    # Social media
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "tiktok.com", "pinterest.com", "linkedin.com", "youtube.com",
    # Aggregators / listicles (not direct providers)
    "yelp.com", "tripadvisor.com", "trustpilot.com",
    "g2.com", "capterra.com", "glassdoor.com",
    # Regional news
    "fastnews.co.id", "euroweeklynews.com", "dailystar.co.uk",
    "mirror.co.uk", "thesun.co.uk", "express.co.uk",
}


def _is_non_commercial_url(url: str) -> bool:
    """Return True if a URL points to a non-commercial (news/article/blog) domain."""
    try:
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        return domain in _NON_COMMERCIAL_DOMAINS or any(
            domain.endswith("." + blocked) for blocked in _NON_COMMERCIAL_DOMAINS
        )
    except Exception:
        return False


async def _tool_search_web(
    query: str,
    max_results: int = 10,
) -> ToolResult:
    """General web search via SerpAPI or SearchAPI (engine=google, NOT shopping).

    SourcingRepository providers all use engine=google_shopping which is wrong
    for informational queries. This calls the APIs directly with engine=google.
    """
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
        for item in organic[:max_results * 2]:  # over-fetch to compensate for filtering
            url = normalize_url(item.get("link", ""))
            if _is_non_commercial_url(url):
                continue
            domain = extract_merchant_domain(url)
            normalized.append(NormalizedResult(
                title=item.get("title", "Unknown"),
                url=url,
                source=f"web_{provider_name}",
                merchant_name=domain or "Web",
                merchant_domain=domain,
                raw_data={"snippet": item.get("snippet", "")},
            ))
            if len(normalized) >= max_results:
                break

        if normalized:
            return ToolResult(
                items=normalized,
                metadata={"source": "web_search", "provider": provider_name},
            )
        logger.info("[ToolExec] search_web %s: all results filtered as non-commercial", provider_name)
        continue

    # Fallback: Google Custom Search Engine (free tier — 100 queries/day)
    cse_key = os.getenv("GOOGLE_CSE_API_KEY", "")
    cse_cx = os.getenv("GOOGLE_CSE_CX", "")
    if cse_key and cse_cx:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": cse_key,
                        "cx": cse_cx,
                        "q": query,
                        "num": min(max_results, 10),  # CSE max is 10 per request
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", [])
                if items:
                    normalized = []
                    for item in items[:max_results]:
                        url = normalize_url(item.get("link", ""))
                        if _is_non_commercial_url(url):
                            continue
                        domain = extract_merchant_domain(url)
                        normalized.append(NormalizedResult(
                            title=item.get("title", "Unknown"),
                            url=url,
                            source="web_google_cse",
                            merchant_name=domain or "Web",
                            merchant_domain=domain,
                            raw_data={"snippet": item.get("snippet", "")},
                        ))
                    if normalized:
                        return ToolResult(
                            items=normalized,
                            metadata={"source": "web_search", "provider": "google_cse"},
                        )
                logger.info("[ToolExec] search_web google_cse returned 0 items")
        except Exception as e:
            logger.warning("[ToolExec] search_web google_cse failed: %s", e)

    # Last resort: DuckDuckGo HTML API (no API key needed)
    try:
        ddg_results = await _ddg_html_search(query, max_results * 2)  # over-fetch for filtering
        if ddg_results:
            normalized = []
            for item in ddg_results:
                url = normalize_url(item["url"])
                if _is_non_commercial_url(url):
                    continue
                domain = extract_merchant_domain(url)
                normalized.append(NormalizedResult(
                    title=item.get("title", "Unknown"),
                    url=url,
                    source="web_duckduckgo",
                    merchant_name=domain or "Web",
                    merchant_domain=domain,
                    raw_data={"snippet": item.get("snippet", "")},
                ))
                if len(normalized) >= max_results:
                    break
            if normalized:
                return ToolResult(
                    items=normalized,
                    metadata={"source": "web_search", "provider": "duckduckgo"},
                )
        logger.info("[ToolExec] search_web duckduckgo returned 0 results")
    except Exception as e:
        logger.warning("[ToolExec] search_web duckduckgo failed: %s", e)

    return ToolResult(error="All web search providers failed")


async def _ddg_html_search(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """Scrape DuckDuckGo HTML search — zero API keys required."""
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        )
        resp.raise_for_status()

    results: List[Dict[str, str]] = []

    class DDGParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self._in_result_link = False
            self._in_snippet = False
            self._current: Dict[str, str] = {}

        def handle_starttag(self, tag, attrs):
            d = dict(attrs)
            cls = d.get("class", "")
            if tag == "a" and "result__a" in cls:
                self._in_result_link = True
                raw_href = d.get("href", "")
                # DDG wraps URLs: //duckduckgo.com/l/?uddg=<encoded_url>&...
                if "uddg=" in raw_href:
                    qs = parse_qs(urlparse(raw_href).query)
                    self._current["url"] = unquote(qs.get("uddg", [""])[0])
                else:
                    self._current["url"] = raw_href
            if tag == "a" and "result__snippet" in cls:
                self._in_snippet = True

        def handle_data(self, data):
            if self._in_result_link:
                self._current["title"] = self._current.get("title", "") + data
            if self._in_snippet:
                self._current["snippet"] = self._current.get("snippet", "") + data

        def handle_endtag(self, tag):
            if tag == "a" and self._in_result_link:
                self._in_result_link = False
            if tag == "a" and self._in_snippet:
                self._in_snippet = False
                if self._current.get("url"):
                    results.append(self._current)
                self._current = {}

    DDGParser().feed(resp.text)
    return results[:max_results]
