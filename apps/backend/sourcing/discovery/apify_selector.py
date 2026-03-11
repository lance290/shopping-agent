"""LLM-driven Apify Actor selection.

Given a SearchIntent and the Actor registry, asks a cheap LLM to decide
which Actor(s) to run and with what parameters. The orchestrator then
hands those selections to the generic ApifyDiscoveryAdapter for execution.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from sourcing.discovery.adapters.apify import get_registry_for_prompt
from sourcing.models import SearchIntent

logger = logging.getLogger(__name__)


class ActorSelection(BaseModel):
    """One Actor the LLM wants to run."""
    actor_id: str = Field(description="Apify Actor ID from the registry")
    run_input: Dict[str, Any] = Field(description="Parameters to pass to the Actor")
    reason: str = Field(default="", description="Why this Actor was chosen")


class ActorSelectionResponse(BaseModel):
    """The full LLM response: zero or more Actors to run."""
    actors: List[ActorSelection] = Field(default_factory=list)
    skip_reason: str = Field(default="", description="If no Actors are needed, why not")


def _build_selection_prompt(
    query: str,
    intent: SearchIntent,
    discovery_mode: str,
    location_hint: str,
) -> str:
    registry_text = get_registry_for_prompt()

    intent_parts = [f"Query: \"{query}\""]
    if intent.product_name:
        intent_parts.append(f"Product: {intent.product_name}")
    if intent.product_category:
        intent_parts.append(f"Category: {intent.product_category}")
    if intent.search_strategies:
        intent_parts.append(f"Strategies: {', '.join(intent.search_strategies)}")
    if intent.source_archetypes:
        intent_parts.append(f"Preferred sources: {', '.join(intent.source_archetypes)}")
    if intent.execution_mode:
        intent_parts.append(f"Execution mode: {intent.execution_mode}")
    if location_hint:
        intent_parts.append(f"Location: {location_hint}")
    intent_parts.append(f"Discovery mode: {discovery_mode}")

    intent_summary = "\n".join(intent_parts)

    return f"""You are a data-source selector for a procurement search engine.
Given the user's search intent and a registry of available Apify data scrapers,
decide which scraper(s) — if any — would produce useful vendor/provider results
that organic web search alone would miss.

RULES:
- Pick 0, 1, or 2 Actors maximum. Do NOT pick Actors that would duplicate organic web results.
- Only pick an Actor if it genuinely adds value for THIS specific query.
- Fill in the run_input parameters correctly for the Actor.
- If the query is a simple commodity product (e.g. "AA batteries"), return zero Actors.
- For local services, prefer Google Maps. For bespoke/artisan goods, consider Instagram.
- For travel/hospitality, consider TripAdvisor. For vendor verification, consider Website Content Crawler.
- Include the user's location in search parameters when relevant.

AVAILABLE ACTORS:
{registry_text}

SEARCH INTENT:
{intent_summary}

Return ONLY valid JSON matching this schema:
{{
  "actors": [
    {{
      "actor_id": "actor/id-from-registry",
      "run_input": {{"param1": "value1"}},
      "reason": "brief explanation"
    }}
  ],
  "skip_reason": "if no actors needed, explain why"
}}"""


async def select_apify_actors(
    query: str,
    intent: SearchIntent,
    discovery_mode: str,
    location_hint: str = "",
) -> ActorSelectionResponse:
    """Ask the LLM which Apify Actors to run for this search."""
    prompt = _build_selection_prompt(query, intent, discovery_mode, location_hint)

    try:
        from services.llm_core import call_gemini
        text = await call_gemini(prompt, timeout=8.0)

        # Extract JSON from the response
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        parsed = json.loads(text)
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
        logger.warning("[ApifySelector] LLM actor selection failed: %s", e)
        return ActorSelectionResponse(skip_reason=f"LLM selection error: {e}")
