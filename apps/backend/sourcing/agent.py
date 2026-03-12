"""LLM tool-calling search agent.

The agent receives a user message + conversation history, asks Gemini which
tools to call, executes tools in parallel, and yields SearchEvent objects
for SSE streaming. The LLM can optionally inspect results and call more
tools (up to max_iterations).

This replaces the classifier → gating → orchestrator → reranker pipeline
with a single LLM-driven loop.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from sourcing.tool_executor import execute_tools_parallel, _dedupe_results
from sourcing.tools import (
    ALL_TOOLS,
    GeminiToolResponse,
    SearchEvent,
    ToolCall,
    ToolResult,
)

logger = logging.getLogger(__name__)

USE_TOOL_CALLING_AGENT = (
    os.getenv("USE_TOOL_CALLING_AGENT", "false").lower() == "true"
)


AGENT_SYSTEM_PROMPT = """You are BuyAnything's search agent. Your job is to find \
the best results for the user's request by calling the right tools.

RULES:
1. Call 1-3 tools per search. Prefer parallel calls when tools are independent.
2. For SERVICES (realtors, contractors, charters, camps, lessons, etc.):
   - ALWAYS call search_vendors — our vendor DB has service providers, brokers, \
and local businesses (NOT product brands/manufacturers).
   - Include location if the user mentioned one.
   - Consider run_apify_actor with Google Maps scraper for local businesses.
   - If calling search_web for services, search for ACTUAL provider websites \
(e.g. "tennis camp San Diego enroll") NOT listicles or aggregators \
(e.g. avoid "best tennis camps" which returns Yelp/TripAdvisor lists).
3. For PRODUCTS (shoes, electronics, gift cards, etc.):
   - Call search_marketplace for buyable items (Amazon, eBay, Google Shopping).
   - For luxury/rare/bespoke items (Birkin bags, limited editions, vintage watches):
     * Call search_web to find authenticated resellers, consignment shops, and \
specialty dealers — this is the BEST source for luxury product sourcing.
     * CRITICAL: Your search_web query MUST include commercial intent words like \
"buy", "for sale", "shop", or "price". Example: "buy Hermès Birkin bag authenticated" \
not just "Hermès Birkin bag". We are a SHOPPING app — never return articles, \
news, or blog posts. Only return pages where the user can actually BUY or \
INQUIRE about the product.
     * Call search_marketplace too (eBay often has luxury items).
     * Do NOT call search_vendors for products — it has service providers, not \
product resellers. It does NOT have retailers or shops.
4. LOCATION is critical. If the user mentions a city/state/region, EVERY tool \
call that supports location MUST include it. Never drop location.
5. On REFINEMENT (user says "actually..." or "focus on..."), carry forward ALL \
context from the conversation. The user's original request + refinement = new search.
6. After seeing results, you may call additional tools if results are poor. \
But prefer to return what you have rather than making the user wait.

NEVER call tools with no parameters. Always include at least a query.
Prefer specific queries over broad ones."""


def _build_initial_messages(
    row_context: Optional[Dict[str, Any]],
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """Build the initial message list for the agent LLM call."""
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
    ]

    # Include recent conversation history for refinement context
    if conversation_history:
        for msg in conversation_history[-6:]:
            messages.append(msg)

    # Include row context if available
    if row_context:
        messages.append({
            "role": "system",
            "content": f"Current request context: {json.dumps(row_context)}",
        })

    messages.append({"role": "user", "content": user_message})
    return messages


async def agent_search(
    *,
    user_message: str,
    row_context: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    max_iterations: int = 2,
    max_tool_calls: int = 3,
) -> AsyncGenerator[SearchEvent, None]:
    """LLM-driven search agent. Yields SearchEvent objects for SSE streaming.

    Parameters
    ----------
    user_message : str
        The user's search query or refinement.
    row_context : dict, optional
        Context from the Row (title, is_service, service_category, etc.).
    conversation_history : list[dict], optional
        Recent chat messages for refinement context.
    max_iterations : int
        Max LLM call rounds (tool-call → results → optional 2nd round).
    max_tool_calls : int
        Max total tool calls across all iterations.
    """
    from services.llm_core import call_gemini_with_tools

    messages = _build_initial_messages(row_context, user_message, conversation_history)
    total_tool_calls = 0
    all_results = []

    for iteration in range(max_iterations):
        logger.info(
            "[Agent] Iteration %d/%d, %d tool calls so far",
            iteration + 1, max_iterations, total_tool_calls,
        )

        # Ask LLM what to do
        response: GeminiToolResponse = await call_gemini_with_tools(
            messages=messages,
            tools=ALL_TOOLS,
            timeout=15.0,
        )

        # If LLM returns text with no tool calls, we're done
        if response.text and not response.tool_calls:
            logger.info("[Agent] LLM returned text, no tool calls — done")
            yield SearchEvent(
                type="agent_message",
                data={"text": response.text},
            )
            break

        # If no tool calls and no text, something went wrong
        if not response.tool_calls:
            logger.warning("[Agent] LLM returned neither text nor tool calls")
            yield SearchEvent(
                type="agent_message",
                data={"text": "I wasn't able to determine the right search approach. Let me try a basic search."},
            )
            break

        # Cap tool calls at budget
        remaining_budget = max_tool_calls - total_tool_calls
        tool_calls = response.tool_calls[:remaining_budget]
        total_tool_calls += len(tool_calls)

        logger.info(
            "[Agent] Executing %d tool calls: %s",
            len(tool_calls),
            [tc.name for tc in tool_calls],
        )

        # Execute tool calls in parallel
        results: List[ToolResult] = await execute_tools_parallel(tool_calls)

        # Stream results to client as each tool completes
        for tool_call, result in zip(tool_calls, results):
            if result.error:
                logger.warning(
                    "[Agent] Tool %s error: %s", tool_call.name, result.error,
                )
            all_results.extend(result.items)
            yield SearchEvent(
                type="tool_results",
                data={
                    "tool": tool_call.name,
                    "params": tool_call.params,
                    "results": [r.model_dump() for r in result.items],
                    "count": len(result.items),
                    "error": result.error,
                },
            )

        # Feed results back to LLM for potential second iteration
        messages.append(response.to_message())
        for tool_call, result in zip(tool_calls, results):
            messages.append({
                "role": "tool",
                "tool_name": tool_call.name,
                "content": result.to_json(),
            })

        if total_tool_calls >= max_tool_calls:
            logger.info("[Agent] Tool call budget exhausted (%d/%d)", total_tool_calls, max_tool_calls)
            break

    # Dedupe across tools
    deduped = _dedupe_results(all_results)
    logger.info(
        "[Agent] Done. %d total results, %d after dedupe",
        len(all_results), len(deduped),
    )

    yield SearchEvent(
        type="complete",
        data={
            "total_results": len(deduped),
            "tool_calls_used": total_tool_calls,
        },
    )
