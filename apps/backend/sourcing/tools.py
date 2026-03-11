"""Tool definitions for the LLM tool-calling search agent.

Each tool is a JSON schema dict that Gemini's function-calling API understands.
Shared dataclass models (ToolCall, ToolResult, SearchEvent) are also defined here.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from sourcing.models import NormalizedResult


# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    id: str
    name: str
    params: dict[str, Any]


@dataclass
class ToolResult:
    items: list[NormalizedResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_json(self) -> str:
        """Compact serialization for feeding back to LLM as function response."""
        summaries = [_result_summary(r) for r in self.items[:10]]
        return json.dumps({
            "results": summaries,
            "count": len(self.items),
            "error": self.error,
        })


@dataclass
class SearchEvent:
    type: str   # "tool_results" | "agent_message" | "complete"
    data: dict[str, Any]


@dataclass
class GeminiToolResponse:
    text: Optional[str]
    tool_calls: list[ToolCall]
    raw_parts: list[dict[str, Any]] = field(default_factory=list)

    def to_message(self) -> dict:
        """Convert to Gemini model message for conversation continuation.

        Uses raw_parts when available to preserve thought_signature fields
        required by Gemini 3 for function-calling round-trips.
        """
        if self.raw_parts:
            return {"role": "model", "parts": self.raw_parts}
        parts: list[dict[str, Any]] = []
        if self.text:
            parts.append({"text": self.text})
        for tc in self.tool_calls:
            parts.append({
                "functionCall": {"name": tc.name, "args": tc.params},
            })
        return {"role": "model", "parts": parts}


def _result_summary(r: NormalizedResult) -> dict[str, Any]:
    """Compact dict for LLM consumption — keeps token count low."""
    d: dict[str, Any] = {
        "title": r.title,
        "url": r.url,
        "merchant": r.merchant_name,
    }
    if r.price is not None:
        d["price"] = r.price
    if r.rating is not None:
        d["rating"] = r.rating
    if r.shipping_info:
        d["shipping"] = r.shipping_info
    return d


# ---------------------------------------------------------------------------
# Tool JSON schemas (Gemini functionDeclarations format)
# ---------------------------------------------------------------------------

SEARCH_VENDORS = {
    "name": "search_vendors",
    "description": (
        "Search the BuyAnything vendor database for service providers, "
        "specialists, brokers, and local businesses. Use for services, "
        "bespoke items, high-value purchases, and any request where "
        "matching with a specific vendor matters. Supports location "
        "filtering and category filtering."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "What to search for. Short and focused, e.g. "
                    "'real estate agent', 'yacht charter', 'HVAC repair'. "
                    "Do NOT include location here."
                ),
            },
            "location": {
                "type": "string",
                "description": (
                    "City, state, or region to filter by. e.g. "
                    "'Nashville, TN', 'San Diego, CA'. Omit if location "
                    "doesn't matter."
                ),
            },
            "category": {
                "type": "string",
                "description": (
                    "Vendor category filter. e.g. 'real_estate', "
                    "'private_aviation', 'home_renovation', 'jewelry'. "
                    "Omit for broad search."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return. Default 10.",
            },
        },
        "required": ["query"],
    },
}

SEARCH_MARKETPLACE = {
    "name": "search_marketplace",
    "description": (
        "Search online marketplaces for products you can buy. Covers "
        "Amazon, eBay, and Google Shopping. Use for physical products, "
        "commodity items, electronics, clothing, etc. NOT for services "
        "or finding local vendors."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Product search query. e.g. 'Hermès Birkin bag', "
                    "'running shoes size 10', 'MacBook Pro M3'"
                ),
            },
            "min_price": {
                "type": "number",
                "description": "Minimum price in USD. Omit for no minimum.",
            },
            "max_price": {
                "type": "number",
                "description": "Maximum price in USD. Omit for no maximum.",
            },
            "marketplaces": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["amazon", "ebay", "google_shopping"],
                },
                "description": "Which marketplaces to search. Default: all available.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results per marketplace. Default 8.",
            },
        },
        "required": ["query"],
    },
}

SEARCH_WEB = {
    "name": "search_web",
    "description": (
        "Search the web via Google for information, reviews, directories, "
        "or niche marketplaces. Use when you need editorial content, "
        "'best of' lists, industry directories, or sources not covered "
        "by vendor DB or marketplaces. Good for discovery and research."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Web search query. Be specific. e.g. "
                    "'best luxury real estate agents Nashville TN 2026', "
                    "'Hermès Birkin bag authenticated resellers'"
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results. Default 10.",
            },
        },
        "required": ["query"],
    },
}

RUN_APIFY_ACTOR = {
    "name": "run_apify_actor",
    "description": (
        "Run a specialized web scraper via Apify. "
        "BEST actor (fast, reliable, 12-22s):\n"
        "- 'compass/crawler-google-places' — Google Maps local businesses. "
        "USE THIS for any local/service search.\n"
        "Other actors (use only if needed):\n"
        "- 'apify/website-content-crawler' — Crawl any website\n"
        "- 'voyager/tripadvisor-scraper' — TripAdvisor listings\n"
        "AVOID these (slow/flaky, timeout or fail):\n"
        "- 'webdatalabs/ebay-deal-finder' — times out, use search_marketplace instead\n"
        "- 'apidojo/tiktok-scraper' — fails immediately\n"
        "- 'lukaskrivka/google-maps-with-contact-details' — slow, use compass scraper instead\n"
        "Use when you need structured data from a specific platform "
        "that other tools don't cover."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "actor_id": {
                "type": "string",
                "description": (
                    "Apify actor ID. e.g. 'compass/crawler-google-places', "
                    "'apify/website-content-crawler'"
                ),
            },
            "run_input": {
                "type": "object",
                "description": (
                    "Input parameters for the actor. Varies by actor. "
                    "For Google Maps: {searchStringsArray: "
                    "['realtors Nashville TN'], maxCrawledPlacesPerSearch: 10}"
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return. Default 10.",
            },
        },
        "required": ["actor_id", "run_input"],
    },
}

SEARCH_APIFY_STORE = {
    "name": "search_apify_store",
    "description": (
        "Search the Apify Store to discover available web scrapers. "
        "Use this when you're not sure which Apify actor would help, "
        "or when the user's request involves a platform you haven't "
        "seen before. Returns a list of actors with descriptions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "search_term": {
                "type": "string",
                "description": (
                    "What to search for in the Apify Store. e.g. "
                    "'Google Maps scraper', 'real estate listings', "
                    "'auction results'"
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum actors to return. Default 5.",
            },
        },
        "required": ["search_term"],
    },
}

ALL_TOOLS = [
    SEARCH_VENDORS,
    SEARCH_MARKETPLACE,
    SEARCH_WEB,
    RUN_APIFY_ACTOR,
    SEARCH_APIFY_STORE,
]
