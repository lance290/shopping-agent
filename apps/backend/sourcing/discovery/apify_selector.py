"""LLM-driven Apify Actor selection with dynamic Store discovery.

Instead of a hardcoded registry, the system:
1. Asks the LLM to generate 1-2 short Apify Store search terms from the intent
2. Hits the Apify Store API to discover relevant Actors
3. Asks the LLM to pick from the live results and fill in parameters

The orchestrator hands those selections to ApifyDiscoveryAdapter for execution.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from sourcing.discovery.adapters.apify import (
    format_store_results_for_prompt,
    search_apify_store,
)
from sourcing.models import SearchIntent

logger = logging.getLogger(__name__)


class ActorSelection(BaseModel):
    """One Actor the LLM wants to run."""
    actor_id: str = Field(description="Apify Actor ID (username/name)")
    run_input: Dict[str, Any] = Field(description="Parameters to pass to the Actor")
    reason: str = Field(default="", description="Why this Actor was chosen")


class ActorSelectionResponse(BaseModel):
    """The full LLM response: zero or more Actors to run."""
    actors: List[ActorSelection] = Field(default_factory=list)
    skip_reason: str = Field(default="", description="If no Actors are needed, why not")


def _build_intent_summary(
    query: str,
    intent: SearchIntent,
    discovery_mode: str,
    location_hint: str,
) -> str:
    parts = [f"Query: \"{query}\""]
    if intent.product_name:
        parts.append(f"Product: {intent.product_name}")
    if intent.product_category:
        parts.append(f"Category: {intent.product_category}")
    if intent.search_strategies:
        parts.append(f"Strategies: {', '.join(intent.search_strategies)}")
    if intent.source_archetypes:
        parts.append(f"Preferred sources: {', '.join(intent.source_archetypes)}")
    if intent.execution_mode:
        parts.append(f"Execution mode: {intent.execution_mode}")
    if location_hint:
        parts.append(f"Location: {location_hint}")
    parts.append(f"Discovery mode: {discovery_mode}")
    return "\n".join(parts)


# ---- Step 1: LLM generates store search terms ----------------------------

def _build_search_terms_prompt(intent_summary: str) -> str:
    return f"""You are helping a procurement search engine find the best data scrapers.
Given this search intent, generate 1-2 short search terms to find relevant
scrapers in the Apify Store (a marketplace of web scraping tools).

RULES:
- Each term should be 2-4 words describing the TYPE of data source needed.
- Think about what structured data would complement organic web search.
- Examples: "google maps scraper", "instagram business", "tripadvisor reviews", "linkedin company", "yelp restaurants"
- If the query is a simple commodity product (batteries, shoes, etc.), return an empty list — no scraper needed.
- Do NOT include the user's specific query terms. Focus on the data source type.

SEARCH INTENT:
{intent_summary}

Return ONLY a JSON array of search terms (or empty array):
["term1", "term2"]"""


# ---- Step 2: LLM picks from discovered Actors ----------------------------

def _build_selection_prompt(
    intent_summary: str,
    discovered_actors: str,
) -> str:
    return f"""You are a data-source selector for a procurement search engine.
You've been given search results from the Apify Store (a marketplace of web scrapers).
Decide which scraper(s) — if any — would produce useful vendor/provider results
that organic web search alone would miss.

RULES:
- Pick 0, 1, or 2 Actors maximum.
- Only pick an Actor if it genuinely adds NEW value beyond organic web search for THIS query.
- You must provide the correct run_input parameters for the Actor. Infer them from the
  Actor's description/title. Common patterns:
  - Search-based actors: {{"search": "query", "maxResults": 5}} or {{"searchStringsArray": ["query"], "maxCrawledPlacesPerSearch": 5}}
  - URL-based actors: {{"startUrls": [{{"url": "https://..."}}], "maxCrawlPages": 3}}
- Include the user's location in search parameters when the Actor supports it and it's relevant.
- Prefer Actors with more users/runs (they're more reliable).

DISCOVERED ACTORS FROM APIFY STORE:
{discovered_actors}

SEARCH INTENT:
{intent_summary}

Return ONLY valid JSON:
{{
  "actors": [
    {{
      "actor_id": "username/actor-name",
      "run_input": {{"param": "value"}},
      "reason": "brief explanation"
    }}
  ],
  "skip_reason": "if no actors needed, explain why"
}}"""


def _extract_json(text: str) -> Any:
    """Extract JSON from an LLM response that may include markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


async def select_apify_actors(
    query: str,
    intent: SearchIntent,
    discovery_mode: str,
    location_hint: str = "",
) -> ActorSelectionResponse:
    """Two-step LLM flow: generate store search terms → discover → pick Actors."""
    from services.llm_core import call_gemini

    intent_summary = _build_intent_summary(query, intent, discovery_mode, location_hint)

    # Step 1: Ask LLM for store search terms
    try:
        terms_text = await call_gemini(
            _build_search_terms_prompt(intent_summary),
            timeout=6.0,
        )
        search_terms = _extract_json(terms_text)
        if not isinstance(search_terms, list) or not search_terms:
            logger.info("[ApifySelector] LLM returned no search terms for query='%s'", query)
            return ActorSelectionResponse(skip_reason="LLM determined no scraper needed")
    except Exception as e:
        logger.warning("[ApifySelector] Step 1 (search terms) failed: %s", e)
        return ActorSelectionResponse(skip_reason=f"Search term generation failed: {e}")

    logger.info("[ApifySelector] Store search terms for '%s': %s", query, search_terms)

    # Step 2: Search the Apify Store
    all_actors: List[Dict[str, Any]] = []
    seen_ids: set = set()
    for term in search_terms[:2]:
        results = await search_apify_store(str(term), limit=5)
        for actor in results:
            if actor["actor_id"] not in seen_ids:
                seen_ids.add(actor["actor_id"])
                all_actors.append(actor)

    if not all_actors:
        logger.info("[ApifySelector] No actors found in store for terms=%s", search_terms)
        return ActorSelectionResponse(skip_reason="No relevant Actors found in Apify Store")

    # Step 3: Ask LLM to pick from discovered Actors
    try:
        discovered_text = format_store_results_for_prompt(all_actors)
        selection_text = await call_gemini(
            _build_selection_prompt(intent_summary, discovered_text),
            timeout=8.0,
        )
        parsed = _extract_json(selection_text)
        response = ActorSelectionResponse(**parsed)

        if response.actors:
            logger.info(
                "[ApifySelector] Selected %d actor(s) for query='%s': %s",
                len(response.actors),
                query,
                [a.actor_id for a in response.actors],
            )
        else:
            logger.info(
                "[ApifySelector] No actors selected for query='%s': %s",
                query,
                response.skip_reason,
            )
        return response

    except Exception as e:
        logger.warning("[ApifySelector] Step 3 (actor selection) failed: %s", e)
        return ActorSelectionResponse(skip_reason=f"Actor selection failed: {e}")
