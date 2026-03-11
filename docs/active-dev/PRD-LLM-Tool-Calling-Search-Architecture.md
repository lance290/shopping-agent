# PRD: LLM Tool-Calling Search Architecture

**Status:** Draft
**Author:** Engineering
**Date:** 2026-03-11
**Priority:** P0 — Core search quality is broken

---

## 1. Problem Statement

BuyAnything's search pipeline consistently delivers poor or irrelevant results despite the LLM correctly understanding user intent. The root cause is architectural: the LLM classifies intent, then **deterministic code overrides, routes, and transforms** that intent through 8+ layers before any search actually happens. Each layer is a place where context gets lost.

### Observed Failures (March 2026)

| Query | Expected | Actual |
|-------|----------|--------|
| "Home renovations in Nashville" | Nashville-area contractors | First pass good, refinement lost location → national results |
| "Realtors in Nashville" | Nashville real estate agents | Poor/irrelevant results |
| ">$400k Birkin bag" | Luxury auction houses, Hermès resellers | "Chat processing failed" |
| General refinement queries | Preserved context from prior search | Location and constraints dropped |

### Root Cause: Too Many Layers

The current pipeline between "LLM understands intent" and "results arrive":

```
LLM classifies intent (good)
  → JSON stored on row
    → Parsed back into SearchIntent
      → Heuristics override execution_mode
        → Classifier routes to one of 3 paths
          → Query planner transforms queries
            → Adapter selection (hardcoded per mode)
              → Gating filters candidates
                → Reranker re-scores
                  → Scorer re-scores again
                    → Results finally arrive (bad)
```

**The LLM already knows what to do. We keep un-knowing it.**

### What the LLM Gets Right

When a user says "realtors in Nashville," the LLM correctly outputs:
- `execution_mode: "sourcing_only"`
- `search_strategies: ["specialist_first", "local_network_first"]`
- `location_context: { relevance: "vendor_proximity", targets: { service_location: "Nashville, TN" } }`
- `source_archetypes: ["brokerage", "local_directory", "association"]`

Then deterministic code:
1. Drops `confidence` to 0.0 (prompt bug, now fixed, but symptomatic)
2. Overrides relevance with heuristic fallback
3. Generates query variants that dilute the original intent
4. Selects adapters based on rigid mode, not what the LLM asked for
5. Applies gating that may filter out the best results

---

## 2. Proposed Solution: LLM as Search Orchestrator

**Give the LLM tools and let it drive search directly.**

Instead of: LLM classifies → code routes → code searches
Do: LLM decides → LLM calls tools → results come back

This is the standard tool-calling pattern used by modern AI assistants. The LLM receives the user's message and a set of tool definitions. It decides which tools to call, with what parameters. Tools execute and return results. The LLM can then call more tools or return final results.

### Tools the LLM Gets

| Tool | What It Does | When LLM Should Use It |
|------|-------------|----------------------|
| `search_vendors` | Query our internal vendor database (hybrid vector + FTS) | Services, specialists, local providers, brokers |
| `search_marketplace` | Amazon, eBay, Google Shopping | Commodity products, considered purchases |
| `search_web` | Google CSE / SerpAPI for general web results | Broad discovery, editorial content, niche marketplaces |
| `run_apify_actor` | Run any Apify actor (Google Maps, TripAdvisor, etc.) | Local businesses, reviews, specialized scrapers |
| `search_apify_store` | Find relevant Apify actors to run | When no existing tool covers the need |

### Key Design Principles

1. **LLM is authoritative.** No heuristic overrides. If the LLM calls `search_vendors` with `location: "Nashville, TN"`, that's what runs.
2. **Tools are thin wrappers.** Each tool is a simple function that calls an API and returns structured results. No routing, no gating, no reranking inside tools.
3. **LLM can call multiple tools.** "Birkin bag" → call `search_marketplace` (for listed items) AND `search_vendors` (for luxury resellers/auction houses) in parallel.
4. **LLM sees results and can refine.** If first results are poor, the LLM can call different tools or adjust parameters. This is the "agent loop."
5. **Location is a tool parameter, not a pipeline concept.** No more `LocationContext` → `LocationResolution` → `location_weight_profile` chain. The LLM passes `"Nashville, TN"` to the tool. Done.

---

## 3. User Experience

### Before (Current)
1. User: "Realtors in Nashville"
2. LLM: "I'll search for realtors in Nashville" (correct understanding)
3. Pipeline: classifies → routes to sourcing_only → query planner generates variants → vendor search runs with diluted query → gating filters → results are national, not Nashville

### After (Tool-Calling)
1. User: "Realtors in Nashville"
2. LLM calls: `search_vendors(query="real estate agent", location="Nashville, TN", category="real_estate")` + `run_apify_actor(actor="google-maps-scraper", params={query: "realtors Nashville TN"})` (parallel)
3. Results: Nashville realtors from our DB + Google Maps listings
4. LLM: presents combined results, all Nashville-relevant

### Refinement Preserves Context
1. User: "Actually, focus on luxury homes over $2M"
2. LLM (has full conversation context) calls: `search_vendors(query="luxury real estate agent", location="Nashville, TN", price_range="2000000+")` + `search_web(query="luxury real estate agents Nashville TN homes over 2M")`
3. Nashville is preserved because the LLM has conversation memory — no JSON serialization/deserialization lossy pipeline.

---

## 4. What Changes

### Removed (Entire Layers)
- `sourcing/discovery/classifier.py` — LLM decides, no classifier needed
- `sourcing/discovery/query_planner.py` — LLM writes its own queries
- `sourcing/discovery/gating.py` — LLM picks relevant tools, no gating
- `sourcing/discovery/llm_rerank.py` — LLM can rank in its response
- `sourcing/discovery/classification.py` — source type classification folded into tool results
- `sourcing/discovery/orchestrator.py` — LLM IS the orchestrator
- `sourcing/discovery/apify_selector.py` — folded into `search_apify_store` tool
- `sourcing/reranker.py` — LLM ranks results directly
- `sourcing/location.py` (most of it) — location is a tool parameter
- `sourcing/discovery/adapters/organic.py` — replaced by `search_web` tool
- Execution mode routing in `sourcing/service.py`

### Kept (Thin Tool Implementations)
- `sourcing/vendor_provider.py` — becomes the `search_vendors` tool backend
- `sourcing/providers_marketplace.py` — becomes `search_marketplace` tool backend
- `sourcing/providers_search.py` — becomes `search_web` tool backend
- `sourcing/discovery/adapters/apify.py` — becomes `run_apify_actor` tool backend
- `sourcing/scorer.py` — simplified, used within tools to compute basic scores
- `sourcing/models.py` — `NormalizedResult` stays as the common result format
- `sourcing/repository.py` — provider registry stays

### New
- `sourcing/tools.py` — Tool definitions (function schemas for LLM)
- `sourcing/tool_executor.py` — Executes tool calls, returns results
- `sourcing/agent.py` — Agent loop: LLM → tools → results → LLM → done

---

## 5. Scope and Phasing

### Phase 1: Tool-Calling Agent (This PR)
- Define 5 tools with JSON schemas
- Implement tool executor that wraps existing providers
- New agent loop in `sourcing/agent.py`
- Wire into `chat.py` → `_stream_search` path
- Keep existing pipeline as fallback (feature flag)
- **Success metric:** Nashville realtors query returns Nashville results

### Phase 2: Remove Old Pipeline
- Delete classifier, gating, reranker, orchestrator
- Clean up `service.py` routing
- Remove `SearchIntent` serialization/deserialization
- **Success metric:** Codebase is 40% smaller, no regressions

### Phase 3: Multi-Turn Agent
- LLM can inspect results and refine (call tools again)
- Streaming results as tools complete
- Budget-aware (token/API cost tracking per search)
- **Success metric:** Refinement queries preserve all context

---

## 6. Constraints and Guardrails

1. **Budget cap per search.** Max 3 tool calls per search turn. Max $0.02 LLM cost per search.
2. **Timeout.** Each tool call max 15s. Total search max 30s.
3. **No infinite loops.** Agent loop max 2 iterations (call tools → see results → optionally call more → done).
4. **Safety.** Tools cannot modify data. Read-only search operations.
5. **Fallback.** If tool-calling LLM fails, fall back to simple keyword search against vendor DB + marketplace.

---

## 7. Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Location-aware queries return local results | ~30% | >90% |
| "Chat processing failed" rate | ~10% | <1% |
| Refinement queries preserve context | ~40% | >95% |
| P95 search latency | ~8s | <6s (parallel tool calls) |
| Lines of routing/classification code | ~2,000 | ~200 |

---

## 8. Risks

| Risk | Mitigation |
|------|-----------|
| LLM makes bad tool choices | Provide clear tool descriptions; log all tool calls for analysis |
| Higher LLM token cost | Use Gemini Flash for tool-calling (cheap); budget cap |
| Tool calls are slow | Parallel execution; aggressive timeouts |
| Regression on commodity searches | Keep affiliate providers as a tool; A/B test |
| LLM hallucinates tool parameters | Strict JSON schema validation on tool inputs |
