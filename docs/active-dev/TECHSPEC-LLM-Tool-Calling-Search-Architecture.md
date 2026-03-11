# Tech Spec: LLM Tool-Calling Search Architecture

**Status:** Draft
**Date:** 2026-03-11
**PRD:** PRD-LLM-Tool-Calling-Search-Architecture.md
**Estimated Effort:** 3-5 days (Phase 1)

---

## 1. Architecture Overview

### Current Flow (Being Replaced)

```
chat.py → make_unified_decision() → stores SearchIntent JSON on Row
  → _stream_search() → rows_search.py → SourcingService.search_for_row()
    → _parse_search_intent() → classify_search_path() → execution_mode_for_row()
      → route to one of:
        _search_vendor_discovery_path() → DiscoveryOrchestrator
        _search_hybrid_path() → both discovery + marketplace
        _search_affiliate_only() → marketplace providers only
```

**Problem:** 8+ layers between LLM understanding and actual search. Each layer can lose context.

### New Flow

```
chat.py → agent_search()
  → LLM receives user message + tool definitions
  → LLM outputs tool_calls: [
      { tool: "search_vendors", params: { query: "realtor", location: "Nashville, TN" } },
      { tool: "search_web", params: { query: "top realtors Nashville TN" } }
    ]
  → tool_executor runs tools in parallel
  → Results returned to LLM (optional: LLM refines)
  → Final results streamed to client
```

**Two files, one loop, no routing.**

---

## 2. Tool Definitions

Each tool is a JSON schema that Gemini's function-calling API understands. The LLM sees these schemas and decides which to call.

### 2.1 `search_vendors`

Search our internal vendor database. Wraps `VendorDirectoryProvider`.

```python
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
                "description": "What to search for. Short and focused, e.g. 'real estate agent', 'yacht charter', 'HVAC repair'. Do NOT include location here."
            },
            "location": {
                "type": "string",
                "description": "City, state, or region to filter by. e.g. 'Nashville, TN', 'San Diego, CA'. Omit if location doesn't matter."
            },
            "category": {
                "type": "string",
                "description": "Vendor category filter. e.g. 'real_estate', 'private_aviation', 'home_renovation', 'jewelry'. Omit for broad search."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return. Default 10.",
                "default": 10
            }
        },
        "required": ["query"]
    }
}
```

**Backend:** Calls `VendorDirectoryProvider.search()` with the query. If `location` is provided, appends it to the FTS query and boosts results with matching `store_geo_location`. If `category` is provided, adds a WHERE clause.

### 2.2 `search_marketplace`

Search commodity marketplaces (Amazon via Rainforest, eBay Browse, Google Shopping).

```python
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
                "description": "Product search query. e.g. 'Hermès Birkin bag', 'running shoes size 10', 'MacBook Pro M3'"
            },
            "min_price": {
                "type": "number",
                "description": "Minimum price in USD. Omit for no minimum."
            },
            "max_price": {
                "type": "number",
                "description": "Maximum price in USD. Omit for no maximum."
            },
            "marketplaces": {
                "type": "array",
                "items": { "type": "string", "enum": ["amazon", "ebay", "google_shopping"] },
                "description": "Which marketplaces to search. Default: all available."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results per marketplace. Default 8.",
                "default": 8
            }
        },
        "required": ["query"]
    }
}
```

**Backend:** Fans out to `RainforestProvider`, `EbayBrowseProvider`, `SearchAPIProvider` (Google Shopping) in parallel. Filters by price. Returns `NormalizedResult` list.

### 2.3 `search_web`

General web search for discovery, editorial content, niche sources.

```python
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
                "description": "Web search query. Be specific. e.g. 'best luxury real estate agents Nashville TN 2026', 'Hermès Birkin bag authenticated resellers'"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results. Default 10.",
                "default": 10
            }
        },
        "required": ["query"]
    }
}
```

**Backend:** Calls `GoogleCSEProvider` or `SerpAPI`. Returns title, URL, snippet, domain.

### 2.4 `run_apify_actor`

Run a specific Apify actor for specialized scraping.

```python
RUN_APIFY_ACTOR = {
    "name": "run_apify_actor",
    "description": (
        "Run a specialized web scraper via Apify. Common actors:\n"
        "- 'compass~crawler' — Scrape Google Maps for local businesses\n"
        "- 'apify/instagram-scraper' — Instagram profiles/posts\n"
        "- 'maxcopell~tripadvisor' — TripAdvisor listings\n"
        "- 'apify/website-content-crawler' — Crawl any website\n"
        "Use when you need structured data from a specific platform "
        "that other tools don't cover."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "actor_id": {
                "type": "string",
                "description": "Apify actor ID. e.g. 'compass~crawler', 'apify/website-content-crawler'"
            },
            "run_input": {
                "type": "object",
                "description": "Input parameters for the actor. Varies by actor. For Google Maps: {searchStringsArray: ['realtors Nashville TN'], maxCrawledPlacesPerSearch: 10}"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return. Default 10.",
                "default": 10
            }
        },
        "required": ["actor_id", "run_input"]
    }
}
```

**Backend:** Wraps existing `ApifyDiscoveryAdapter.run_actor()`. Normalizes results using existing normalizer registry.

### 2.5 `search_apify_store`

Discover which Apify actors exist for a need. Used when the LLM isn't sure which actor to run.

```python
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
                "description": "What to search for in the Apify Store. e.g. 'Google Maps scraper', 'real estate listings', 'auction results'"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum actors to return. Default 5.",
                "default": 5
            }
        },
        "required": ["search_term"]
    }
}
```

**Backend:** Calls Apify Store API (`GET https://api.apify.com/v2/store?search=...`). Returns actor ID, name, description, stats.

---

## 3. Agent Loop

### 3.1 Core Loop (`sourcing/agent.py`)

```python
async def agent_search(
    *,
    row: Row,
    user_message: str,
    conversation_history: list[dict],
    max_iterations: int = 2,
    max_tool_calls: int = 3,
) -> AsyncGenerator[SearchEvent, None]:
    """
    LLM-driven search agent. The LLM decides which tools to call.
    Yields SearchEvent objects for SSE streaming.
    """
    messages = _build_initial_messages(row, user_message, conversation_history)
    tools = [SEARCH_VENDORS, SEARCH_MARKETPLACE, SEARCH_WEB, RUN_APIFY_ACTOR, SEARCH_APIFY_STORE]
    total_tool_calls = 0

    for iteration in range(max_iterations):
        # Ask LLM what to do
        response = await call_gemini_with_tools(
            messages=messages,
            tools=tools,
            timeout=15.0,
        )

        # If LLM returns text (no tool calls), we're done
        if response.text and not response.tool_calls:
            yield SearchEvent(type="agent_message", data={"text": response.text})
            break

        # Execute tool calls in parallel
        tool_calls = response.tool_calls[:max_tool_calls - total_tool_calls]
        total_tool_calls += len(tool_calls)

        results = await execute_tools_parallel(tool_calls)

        # Stream results to client as they complete
        for tool_call, result in zip(tool_calls, results):
            yield SearchEvent(
                type="tool_results",
                data={
                    "tool": tool_call.name,
                    "params": tool_call.params,
                    "results": [r.to_dict() for r in result.items],
                    "count": len(result.items),
                },
            )

        # Feed results back to LLM for next iteration
        messages.append(response.to_message())
        for tool_call, result in zip(tool_calls, results):
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result.to_json(),
            })

        if total_tool_calls >= max_tool_calls:
            break

    # Persist results as Bids on the Row
    yield SearchEvent(type="complete", data={})
```

### 3.2 System Prompt for the Agent

```python
AGENT_SYSTEM_PROMPT = """You are BuyAnything's search agent. Your job is to find
the best results for the user's request by calling the right tools.

RULES:
1. Call 1-3 tools per search. Prefer parallel calls when tools are independent.
2. For SERVICES (realtors, contractors, charters, etc.):
   - ALWAYS call search_vendors with a location if the user mentioned one
   - Consider run_apify_actor with Google Maps scraper for local businesses
3. For PRODUCTS (shoes, electronics, bags, etc.):
   - Call search_marketplace for buyable items
   - For luxury/rare items, ALSO call search_vendors (luxury resellers exist)
   - For very rare items (Birkin bags, limited editions), also call search_web
4. LOCATION is critical. If the user mentions a city/state/region, EVERY tool
   call that supports location MUST include it. Never drop location.
5. On REFINEMENT (user says "actually..." or "focus on..."), carry forward ALL
   context from the conversation. The user's original request + refinement = new search.
6. After seeing results, you may call additional tools if results are poor.
   But prefer to return what you have rather than making the user wait.

NEVER call tools with no parameters. Always include at least a query.
Prefer specific queries over broad ones.
"""
```

### 3.3 Initial Message Construction

```python
def _build_initial_messages(row, user_message, conversation_history):
    messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]

    # Include conversation history for context (refinement queries)
    for msg in conversation_history[-6:]:
        messages.append(msg)

    # Include row context if it exists (prior search results, constraints)
    if row:
        row_context = {
            "title": row.title,
            "is_service": row.is_service,
            "service_category": row.service_category,
            "desire_tier": row.desire_tier,
            "constraints": json.loads(row.choice_answers) if row.choice_answers else {},
        }
        messages.append({
            "role": "system",
            "content": f"Current request context: {json.dumps(row_context)}",
        })

    messages.append({"role": "user", "content": user_message})
    return messages
```

---

## 3.4 Shared Models (`sourcing/tools.py`)

These models are used across the agent, tool executor, and chat integration:

```python
@dataclass
class ToolCall:
    id: str          # UUID for tracking
    name: str        # e.g., "search_vendors"
    params: dict     # Tool-specific parameters

@dataclass
class ToolResult:
    items: list[NormalizedResult]  # Reuses existing NormalizedResult model
    metadata: dict = field(default_factory=dict)
    error: str | None = None

    def to_json(self) -> str:
        """Serialize for feeding back to LLM as function response."""
        return json.dumps({
            "results": [_result_summary(r) for r in self.items[:10]],
            "count": len(self.items),
            "error": self.error,
        })

@dataclass
class SearchEvent:
    type: str   # "tool_results" | "agent_message" | "complete"
    data: dict
```

**`_result_summary`**: Returns a compact dict (title, url, price, merchant) — NOT the full NormalizedResult — to keep token count low when feeding results back to the LLM for a second iteration.

**`_search_result_to_normalized`**: Converts `SearchResult` (provider format) to `NormalizedResult` (canonical format). The existing `normalize_results_for_provider()` in `sourcing/normalizers.py` already does this per-provider.

---

## 4. Tool Executor (`sourcing/tool_executor.py`)

Each tool is a thin wrapper around existing provider code. No routing, no gating, no reranking.

```python
async def execute_tools_parallel(tool_calls: list[ToolCall]) -> list[ToolResult]:
    """Execute multiple tool calls in parallel with timeout."""
    tasks = [_execute_single(tc) for tc in tool_calls]
    return await asyncio.gather(*tasks, return_exceptions=True)


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
            return ToolResult(items=[], error=f"Unknown tool: {tool_call.name}")
```

### 4.1 `_tool_search_vendors` Implementation

**Critical:** `VendorDirectoryProvider` requires a query embedding (vector) for cosine similarity search. The tool wrapper must call the provider's internal `_embed_texts` / `_build_embedding_concepts` flow. The simplest approach: pass the query through the provider's existing `search()` method which handles embedding internally.

```python
async def _tool_search_vendors(
    query: str,
    location: str | None = None,
    category: str | None = None,
    max_results: int = 10,
) -> ToolResult:
    """Search internal vendor database via VendorDirectoryProvider.

    The provider handles embedding, hybrid vector+FTS search, geo filtering
    internally. We just pass the right parameters.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    provider = VendorDirectoryProvider(db_url)

    # Build kwargs that VendorDirectoryProvider.search() expects
    kwargs: dict = {"limit": max_results}

    # vendor_query = clean intent, context_query = full context
    # This prevents query dilution (the root cause of the Nashville bug)
    if location:
        kwargs["context_query"] = f"{query} {location}"
    if category:
        kwargs["intent_payload"] = {"product_category": category}

    results: list[SearchResult] = await provider.search(query, **kwargs)

    return ToolResult(
        items=[_search_result_to_normalized(r) for r in results[:max_results]],
        metadata={"source": "vendor_directory", "location_filter": location},
    )
```

### 4.2 `_tool_search_marketplace` Implementation

**Note:** `SourcingRepository` uses canonical provider names internally. The alias map (`_PROVIDER_ALIASES`) maps `rainforest` → `amazon`, `ebay_browse` → `ebay`. Pass canonical names when filtering.

```python
async def _tool_search_marketplace(
    query: str,
    min_price: float | None = None,
    max_price: float | None = None,
    marketplaces: list[str] | None = None,
    max_results: int = 8,
) -> ToolResult:
    """Search Amazon, eBay, Google Shopping in parallel."""
    repo = SourcingRepository()
    targets = marketplaces or ["amazon", "ebay", "google_shopping"]

    # Map user-facing names to SourcingRepository internal names.
    # SourcingRepository._PROVIDER_ALIASES: rainforest→amazon, ebay_browse→ebay
    # So we pass the canonical names directly (amazon, ebay, searchapi).
    provider_map = {
        "amazon": "amazon",
        "ebay": "ebay",
        "google_shopping": "searchapi",
    }

    selected = [provider_map[t] for t in targets if t in provider_map]

    response = await repo.search_all_with_status(
        query,
        providers=selected,
    )

    # Filter by price in Python (providers don't all support price filtering)
    items = response.results
    if min_price is not None:
        items = [r for r in items if r.price and r.price >= min_price]
    if max_price is not None:
        items = [r for r in items if r.price and r.price <= max_price]

    return ToolResult(
        items=[_search_result_to_normalized(r) for r in items[:max_results * len(targets)]],
        metadata={"source": "marketplace", "marketplaces": targets},
    )
```

---

## 5. Integration with Chat (`chat.py`)

### 5.1 Replace `_stream_search` Call

The existing `_stream_search` helper in `chat.py` calls the old pipeline. Replace it with the agent:

```python
# BEFORE (in chat.py)
async for batch in _stream_search(row.id, search_query, authorization):
    yield sse_event("search_results", {...})

# AFTER
async for event in agent_search(
    row=row,
    user_message=search_query,
    conversation_history=conversation_history,
):
    if event.type == "tool_results":
        # Convert tool results to bids and stream
        bids = await _persist_tool_results(session, row, event.data["results"])
        yield sse_event("search_results", {
            "row_id": row.id,
            "results": [bid_to_dict(b) for b in bids],
            "provider": event.data["tool"],
            "more_incoming": True,
        })
    elif event.type == "agent_message":
        yield sse_event("assistant_message", {"text": event.data["text"]})
    elif event.type == "complete":
        yield sse_event("search_results", {
            "row_id": row.id,
            "results": [],
            "more_incoming": False,
        })
```

### 5.2 Feature Flag

During rollout, use a feature flag to switch between old and new pipeline:

```python
USE_TOOL_CALLING_AGENT = os.getenv("USE_TOOL_CALLING_AGENT", "false").lower() == "true"
```

---

## 6. Gemini Function Calling Integration

**Important:** The codebase uses raw HTTP REST API via `httpx` (in `services/llm_core.py`), NOT the `google-generativeai` Python SDK. The new function calling integration follows the same pattern.

### 6.1 `call_gemini_with_tools`

New function added to `services/llm_core.py` (where `call_gemini` already lives):

```python
async def call_gemini_with_tools(
    messages: list[dict],
    tools: list[dict],
    timeout: float = 15.0,
) -> GeminiToolResponse:
    """
    Call Gemini REST API with function-calling enabled.
    Uses the same httpx pattern as existing call_gemini().
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        raise ValueError("No Gemini API key")

    model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    # Convert tool schemas to Gemini functionDeclarations format
    function_declarations = [
        {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
        }
        for tool in tools
    ]

    # Convert messages to Gemini contents format
    contents = _messages_to_gemini_contents(messages)

    payload = {
        "contents": contents,
        "tools": [{"functionDeclarations": function_declarations}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
        },
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

    return _parse_gemini_tool_response(data)
```

### 6.2 Message Format Conversion

Gemini REST API uses `contents` with `role` ("user", "model", "function") and `parts`:

```python
def _messages_to_gemini_contents(messages: list[dict]) -> list[dict]:
    """Convert OpenAI-style messages to Gemini contents format."""
    contents = []
    for msg in messages:
        role = msg["role"]
        if role == "system":
            # Gemini has no system role — prepend as user context
            contents.append({
                "role": "user",
                "parts": [{"text": msg["content"]}],
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood."}],
            })
        elif role == "user":
            contents.append({
                "role": "user",
                "parts": [{"text": msg["content"]}],
            })
        elif role == "assistant" or role == "model":
            contents.append({
                "role": "model",
                "parts": [{"text": msg.get("content", "")}],
            })
        elif role == "tool":
            # Function response format for Gemini
            contents.append({
                "role": "function",
                "parts": [{
                    "functionResponse": {
                        "name": msg["tool_name"],
                        "response": {"result": msg["content"]},
                    }
                }],
            })
    return contents
```

### 6.3 Response Parsing

Gemini returns `functionCall` parts when it wants to call tools:

```python
@dataclass
class ToolCall:
    id: str          # Generated UUID for tracking
    name: str        # Tool name (e.g., "search_vendors")
    params: dict     # Tool parameters

@dataclass
class GeminiToolResponse:
    text: str | None
    tool_calls: list[ToolCall]

    def to_message(self) -> dict:
        """Convert to Gemini model message for conversation continuation."""
        parts = []
        if self.text:
            parts.append({"text": self.text})
        for tc in self.tool_calls:
            parts.append({
                "functionCall": {"name": tc.name, "args": tc.params}
            })
        return {"role": "model", "parts": parts}


def _parse_gemini_tool_response(data: dict) -> GeminiToolResponse:
    """Parse Gemini REST API response into structured tool calls."""
    candidates = data.get("candidates", [])
    if not candidates:
        return GeminiToolResponse(text=None, tool_calls=[])

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = []
    tool_calls = []

    for part in parts:
        if "text" in part:
            text_parts.append(part["text"])
        elif "functionCall" in part:
            fc = part["functionCall"]
            tool_calls.append(ToolCall(
                id=str(uuid.uuid4()),
                name=fc["name"],
                params=fc.get("args", {}),
            ))

    return GeminiToolResponse(
        text="\n".join(text_parts) if text_parts else None,
        tool_calls=tool_calls,
    )
```

### 6.4 No New Dependencies

This approach uses the existing `httpx` client and Gemini REST API key — no new packages needed. The `google-generativeai` SDK is NOT used.

---

## 7. Data Flow Diagram

```
┌─────────┐     ┌──────────────┐     ┌────────────────┐
│  User    │────▶│  chat.py     │────▶│  agent.py      │
│  "realtors   │  (SSE stream)  │     │  (agent loop)  │
│  Nashville"  │               │     │                │
└─────────┘     └──────┬───────┘     └───────┬────────┘
                       │                     │
                       │              ┌──────▼───────┐
                       │              │  Gemini API  │
                       │              │  (tool-call) │
                       │              └──────┬───────┘
                       │                     │
                       │         ┌───────────┼───────────┐
                       │         ▼           ▼           ▼
                       │   ┌──────────┐ ┌─────────┐ ┌─────────┐
                       │   │ search_  │ │ search_ │ │  run_   │
                       │   │ vendors  │ │  web    │ │ apify   │
                       │   └────┬─────┘ └────┬────┘ └────┬────┘
                       │        │            │           │
                       │        ▼            ▼           ▼
                       │   ┌──────────┐ ┌─────────┐ ┌─────────┐
                       │   │ Vendor   │ │ Google  │ │ Apify   │
                       │   │ DB+FTS   │ │ CSE     │ │ Cloud   │
                       │   └────┬─────┘ └────┬────┘ └────┬────┘
                       │        │            │           │
                       │        └────────────┼───────────┘
                       │                     ▼
                       │              ┌──────────────┐
                       │              │  Gemini sees │
                       │              │  all results │
                       │              │  → ranks     │
                       │              └──────┬───────┘
                       │                     │
                       ◀─────────────────────┘
                  (SSE: search_results events)
```

---

## 8. Files to Create / Modify

### New Files
| File | Purpose | Size Est. |
|------|---------|-----------|
| `sourcing/tools.py` | Tool JSON schema definitions + `ToolCall`, `ToolResult`, `SearchEvent` models | ~150 lines |
| `sourcing/tool_executor.py` | Tool implementations (thin wrappers around existing providers) | ~250 lines |
| `sourcing/agent.py` | Agent loop + system prompt + `agent_search()` entry point | ~200 lines |

### Modified Files
| File | Change |
|------|--------|
| `services/llm_core.py` | Add `call_gemini_with_tools()`, `_messages_to_gemini_contents()`, `_parse_gemini_tool_response()` |
| `routes/chat.py` | Add feature-flagged `agent_search` path alongside existing `_stream_search` |
| `routes/rows_search.py` | Add feature-flagged agent path for `search_streaming` endpoint |

Note: `services/gemini_tools.py` is NOT created as a separate file. The function-calling logic lives in `services/llm_core.py` alongside the existing `call_gemini()` to stay DRY with shared API key handling and circuit-breaker logic.

### Files to Delete (Phase 2)
| File | Reason |
|------|--------|
| `sourcing/discovery/classifier.py` | LLM decides, no classifier |
| `sourcing/discovery/query_planner.py` | LLM writes queries |
| `sourcing/discovery/gating.py` | No gating — LLM picks tools |
| `sourcing/discovery/llm_rerank.py` | LLM ranks results directly |
| `sourcing/discovery/classification.py` | Folded into tool results |
| `sourcing/discovery/orchestrator.py` | LLM IS the orchestrator |
| `sourcing/discovery/apify_selector.py` | Folded into tools |
| `sourcing/reranker.py` | LLM ranks in response |

---

## 9. Testing Strategy

### Unit Tests
- Each tool executor function tested independently with mocked providers
- Agent loop tested with mocked Gemini responses (predetermined tool calls)
- Tool schema validation tests

### Integration Tests
- "Realtors in Nashville" → agent calls `search_vendors` with location
- "Birkin bag" → agent calls `search_marketplace` + `search_web`
- "HVAC repair near me" → agent calls `search_vendors` + `run_apify_actor`
- Refinement: "Actually focus on luxury" → location preserved in follow-up tool calls

### Regression Tests
- All existing test scenarios from `test_discovery_quality_gating.py` reimplemented against agent
- A/B comparison: same queries through old pipeline vs new agent

---

## 10. Rollout Plan

1. **Day 1-2:** Implement `tools.py`, `tool_executor.py`, `services/gemini_tools.py`
2. **Day 2-3:** Implement `agent.py` with agent loop
3. **Day 3-4:** Wire into `chat.py` behind feature flag
4. **Day 4-5:** Integration tests, manual testing of key scenarios
5. **Day 5:** Deploy with `USE_TOOL_CALLING_AGENT=true` to staging
6. **Day 6+:** Monitor, fix edge cases, gradually roll to production

### Rollback
Set `USE_TOOL_CALLING_AGENT=false` → instantly reverts to old pipeline. Zero risk.

---

## 11. Cost Estimation

| Component | Cost per Search |
|-----------|----------------|
| Gemini Flash (tool-calling prompt, ~2K tokens in + ~500 out) | ~$0.001 |
| Gemini Flash (optional 2nd iteration, ~3K tokens in) | ~$0.002 |
| Apify actor run (when used) | ~$0.01-0.05 |
| Marketplace API calls (Rainforest, eBay) | existing cost |
| **Total per search** | **~$0.003-0.05** |

Current cost per search (with reranker + discovery LLM calls): ~$0.01-0.03
**Net cost change: approximately neutral.**

---

## 12. Open Questions

### Resolved

1. ~~**Gemini model choice**~~ → Use `gemini-3-flash-preview` (matches existing `GEMINI_MODEL` env var). Upgrade path: change env var.
2. ~~**Result deduplication**~~ → Domain-based dedupe in `tool_executor.py` after all tools return. `SourcingRepository` already dedupes per-provider; cross-tool dedupe is new.
3. ~~**Bid persistence**~~ → Reuse existing `_persist_bids` from `rows_search.py`. The agent yields `SearchEvent(type="tool_results")` → chat.py converts to Bids via existing path.
4. ~~**Streaming granularity**~~ → Per-tool-completion for perceived speed. Each tool result yields an SSE event immediately.
5. ~~**SDK vs REST API**~~ → REST API via `httpx`, matching existing `llm_core.py` pattern. No new SDK dependency.

### Open

1. **VendorDirectoryProvider geo search:** The provider already has sophisticated geo filtering (lat/lon radius, geo_terms, service_area). The tool's `location` string parameter needs to be parsed into the provider's expected geo format. Options: (a) let the provider's FTS handle it (simple, good enough for Phase 1), (b) geocode the location string to lat/lon for radius search (better, Phase 2).
2. **Conversation history token budget:** Passing last 6 messages to the agent could get expensive. Consider truncation or summarization if conversations are long.
3. **Error recovery in agent loop:** If all tool calls fail (network error, API down), should the agent retry, fall back to keyword search, or return an error? Current spec: return error. Consider: automatic fallback to `SourcingRepository.search_all()` as safety net.
