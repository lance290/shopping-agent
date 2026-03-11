# Authoritative LLM Search and Reranking Plan

## Goal

Make the LLM authoritative for two decisions that brittle heuristics currently break:

1. **Execution mode** — whether a request should use affiliate providers, source-first sourcing, or both (aligning with the triage PRD's `affiliate_only`, `sourcing_only`, `affiliate_plus_sourcing`).
2. **Search strategy** — within the sourcing engine, which discovery strategies apply (aligning with PRD §15: official-first, market-first, specialist-first, prestige-first, local-network-first, or a combination).

For requests where deterministic ranking is weak (custom-vendor, local, high-risk), add a cheaper structured LLM pass that contributes scoring inputs to the existing hybrid ranking model — not replacing it.

## Problem Summary

The current pipeline often gets the intent right, then loses quality downstream because deterministic routing and ranking logic override or dilute that understanding.

Observed failures:

- High-budget luxury requests can still surface commodity marketplace results such as eBay.
- Local broker or realtor requests can rank national or out-of-market vendors above local specialists.
- Brand pages or non-actionable sites can survive when the user actually needs a contactable broker, agent, or vendor.

## Relationship to Existing Docs

This plan operates within the architecture defined by:

- **Triage PRD** (`PRD-BuyAnything-Request-Triage-and-Fulfillment-Routing.md`) — defines execution modes and the front-door routing layer.
- **Luxury Sourcing Engine PRD** (`luxury_sourcing_engine_prd.md`) — defines search strategies, source archetypes, ranking criteria, and the source-first philosophy.
- **Tech Spec** (`luxury_sourcing_engine_tech_spec.md`) — defines the pipeline stages, hybrid scoring formula, adapter separation, and cost controls.

This plan does not replace those documents. It addresses a specific failure mode: the LLM's valid structured intent being overridden by brittle downstream heuristics, resulting in misrouting and poor ranking.

## Target Architecture

```text
LLM parses request
-> outputs execution_mode + search_strategies + source_archetypes
-> service layer selects adapter family (affiliate vs discovery/source) from execution_mode
-> within sourcing, strategies shape query family generation and provider routing
-> retrieval gathers candidates from the selected adapter family
-> deterministic hard filters remove invalid candidates
-> hybrid scoring (source trust + match + evidence + actionability + memory)
-> for high-risk/local/custom flows: cheap LLM reranker contributes additional scoring inputs
-> final ranked list is persisted and displayed
```

## Core Decisions

### 1. The LLM becomes authoritative for execution mode and strategy selection

Extend the structured intent to include:

- `execution_mode`: `affiliate_only` | `sourcing_only` | `affiliate_plus_sourcing` — maps directly to triage PRD §7.2.
- `search_strategies`: one or more of `official_first`, `market_first`, `specialist_first`, `prestige_first`, `local_network_first` — maps to PRD §15.
- `source_archetypes`: inferred source types such as `brokerage`, `association`, `registry`, `curated_marketplace`, `editorial_ranking`, `local_directory`, `prior_trusted_source` — maps to PRD §11.3.

Rules:

- If the LLM returns a valid execution mode and strategies with acceptable confidence, downstream code must use them directly.
- Heuristics remain fallback-only behavior for missing, invalid, or low-confidence intent.
- Token-based overrides (e.g., bare "broker" flipping the discovery mode) must not override a valid LLM-produced decision.
- The LLM's strategy selection should connect to existing `desire_tier`, `service_category`, and `location_context.relevance` fields already in the codebase.

### 2. Adapter families must be separated

This aligns with tech spec §11 ("Separation of concerns").

**Affiliate provider adapters** (structured commerce/travel retrieval):

- Amazon / Rainforest
- eBay
- Kayak
- Kroger
- Walmart

**Discovery/source adapters** (open-ended sourcing):

- `vendor_directory` (internal)
- SerpAPI / Tavily / web discovery
- internal memory retrieval
- broker, agent, specialist, or direct-vendor sources

Selection rule:

- `affiliate_only` → affiliate adapters only.
- `sourcing_only` → discovery/source adapters only.
- `affiliate_plus_sourcing` → both, with explicit provenance preserved per tech spec §7.8.

### 3. Deterministic scoring anchors ranking; LLM reranker adds signal

Per tech spec §7.8 and §19.2: "Source trust and operational signals should anchor the ranking" and "do not make LLMs the sole source of trust ranking."

The existing hybrid scoring formula (tech spec §7.8) remains the primary ranking mechanism:

```text
overall_score =
  0.30 * source_trust
+ 0.30 * semantic_match
+ 0.15 * geography_fit
+ 0.10 * evidence_density
+ 0.10 * actionability
+ 0.05 * memory_boost
- penalties
```

The cheap LLM reranker is an **additional scoring input** for specific high-risk flows, not a replacement for this formula. Its output contributes to `semantic_match`, `actionability`, and penalty components rather than overriding the combined score.

### 4. Search strategies shape query families and source archetypes

Per PRD §11.4, the system should generate multiple query families (direct intent, official/institutional, specialist/broker, prestige/editorial, local/regional, alternative terminology, verification-specific).

The LLM's selected strategies should influence:

- Which query families are generated (per tech spec §7.2).
- Which source archetypes are expected (per PRD §11.3).
- Provider routing within the sourcing engine.

Example: Nashville $3MM mansion broker → strategies = `specialist_first` + `prestige_first` + `local_network_first` → query families emphasize specialist, local, and prestige/editorial queries.

### 5. Hard constraints stay deterministic

The LLM should not override:

- explicit budget bounds
- explicit geo/radius constraints
- dedupe rules
- malformed or unsafe URLs
- system safety rules

## Proposed Rollout

### Phase 1: Authoritative routing

Objective:

- Stop the search stack from second-guessing valid structured intent.

Changes:

- Extend the structured intent schema with `execution_mode`, `search_strategies` (list), and `source_archetypes` (list), all with confidence.
- Update `classify_search_path` and `select_discovery_mode` so the LLM's execution mode and strategies are trusted first.
- Restrict heuristic routing to fallback-only behavior when structured intent is present and confident.
- Remove or neutralize unsafe one-token routing triggers such as bare `broker` overriding intent.
- Wire `search_strategies` to existing `desire_tier`, `service_category`, and `location_context.relevance` so they reinforce rather than conflict.

Expected impact:

- High-value and service requests stop accidentally taking commodity/affiliate paths.
- Real-estate and local-market requests stop being misrouted by generic token matches.

### Phase 2: Adapter-family enforcement

Objective:

- Prevent adapter-family bleed between affiliate and discovery/source paths.

Changes:

- In `sourcing/service.py`, select adapters from the LLM-chosen execution mode only.
- `sourcing_only` must not silently include affiliate marketplace providers (Amazon, eBay, etc.).
- `affiliate_only` must not silently include discovery-only vendor sources.
- `affiliate_plus_sourcing` runs both with explicit provenance preserved per tech spec §7.8.
- Connect LLM-selected `search_strategies` to query family generation (tech spec §7.2): different strategies produce different query families.
- Connect LLM-selected `source_archetypes` to expected source types in gating (tech spec §7.4).

Expected impact:

- Luxury/sourcing requests do not surface eBay-style results unless explicitly intended.
- Discovery flows stay focused on brokers, agents, and direct vendors.
- Query families are shaped by strategy, improving recall quality.

### Phase 3: Cheap LLM reranker as scoring input

Objective:

- Supplement weak deterministic scoring dimensions for ambiguous, local, or high-risk searches — not replace the hybrid scoring model.

Scope:

Apply only to flows where deterministic scoring is weakest:

- `sourcing_only` or `affiliate_plus_sourcing` execution modes
- `desire_tier` in `high_value`, `advisory`, `service`, `bespoke`
- `location_context.relevance` in `service_area` or `vendor_proximity`
- explicit local-market or specialist searches

Candidate set:

- top-N normalized candidates after retrieval and hard filters
- N should stay small enough to control latency and cost (per tech spec §12.3 defaults)

Structured output per candidate (feeds into hybrid scoring components):

- `include` — hard gate for clearly wrong candidates
- `reason_codes` — structured explanation per tech spec §7.8 explainability requirement
- `request_fit_score` → contributes to `semantic_match` component
- `local_fit_score` → contributes to `geography_fit` component
- `contactability_score` → contributes to `actionability` component
- `luxury_fit_score` → contributes to `source_trust` or penalty component
- `candidate_type_label` — structured candidate-type classification for gating

Integration with existing scoring:

The reranker outputs are not a replacement score. They feed into the tech spec §7.8 hybrid formula as adjusted component inputs. The combined `overall_score` still follows the weighted formula.

Expected impact:

- Local brokerages outrank national portals when locality matters.
- Contactable vendors outrank brand pages when the user needs a human.
- Luxury and advisory flows stop treating commodity results as equivalent.

### Phase 4: Regression replay and tuning

Objective:

- Lock in the fixes against known bad searches.

Initial replay set:

- `>$400k` luxury request should not return eBay unless execution mode is `affiliate_only` or `affiliate_plus_sourcing`.
- `realtors in Nashville` should rank Nashville brokerages and agents above national or California vendors.
- Brand-homepage-only results should be demoted when brokerage or direct contact is required.
- Query families for local specialist searches should include local/regional and specialist/broker families, not just generic commodity queries.

## Implementation Targets

Structured intent and LLM contract:

- `apps/backend/services/llm.py` — add `execution_mode`, `search_strategies`, `source_archetypes` to structured output schema
- `apps/backend/services/llm_models.py` — Pydantic models for new intent fields
- `apps/backend/sourcing/models.py` — extend `SearchIntent` with new fields

Routing and strategy enforcement:

- `apps/backend/sourcing/discovery/classifier.py` — trust LLM execution mode first, heuristics as fallback only
- `apps/backend/sourcing/service.py` — enforce adapter-family selection from execution mode

Query family generation:

- `apps/backend/sourcing/service.py` or query planner — connect `search_strategies` to query family generation per tech spec §7.2

Adapter-family selection:

- `apps/backend/sourcing/service.py` — enforce affiliate vs discovery adapter separation
- `apps/backend/sourcing/repository.py` — provider routing respects execution mode

Candidate reranking:

- new module for cheap structured LLM reranker (e.g., `apps/backend/sourcing/reranker.py`)
- integrate after normalization and hard filters, before final hybrid scoring
- reranker outputs feed into existing score components, not replace them

Gating:

- `apps/backend/sourcing/discovery/gating.py` — use `source_archetypes` and `candidate_type_label` from reranker

Scoring:

- `apps/backend/sourcing/scorer.py` — accept reranker inputs as optional component adjustments
- `apps/backend/sourcing/location.py` — `local_fit_score` from reranker can supplement geo scoring

Testing:

- routing regression tests (execution mode selection)
- strategy-to-query-family regression tests
- adapter-family isolation tests
- locality regression tests
- reranker contract tests for include/exclude behavior
- reranker-to-hybrid-scoring integration tests

## Non-Goals

- Replacing deterministic retrieval with full LLM retrieval
- Letting the LLM bypass hard budget or geo constraints
- Making the LLM the sole source of trust ranking (per tech spec §19.2)
- Running expensive reranking on every affiliate-only commodity search
- Running the reranker on flows where deterministic scoring is already strong

## Success Criteria

- The system respects LLM-selected execution mode and search strategies when intent is valid and confident.
- Affiliate providers do not leak into sourcing-only flows unless execution mode is `affiliate_plus_sourcing`.
- Discovery/source adapters do not run for `affiliate_only` requests.
- Local specialist searches rank local specialists ahead of semantically similar national results.
- High-value requests do not surface low-fit marketplaces by default.
- Query families reflect the selected strategies (e.g., local-network-first generates local/regional queries).
- Reranker outputs integrate with, not replace, the hybrid scoring formula.
- Logs make it easy to see:
  - LLM-selected execution mode and strategies
  - adapter family used
  - query families generated
  - reranker scoring inputs
  - exclusion reasons
  - provenance of each result (affiliate vs discovery vs memory)

## Recommended First Implementation Slice

Start with:

1. Phase 1: authoritative LLM routing (execution mode + strategies + source archetypes)
2. Phase 2: adapter-family enforcement + strategy-to-query-family connection

Then add:

3. Phase 3: cheap LLM reranker as additional scoring input to hybrid model

This sequencing separates misrouting problems from ranking problems and makes the next debugging pass much easier.

## Appendix: Terminology Mapping

| This plan | Triage PRD | Sourcing PRD §15 | Tech spec §7.0 |
|-----------|-----------|-------------------|----------------|
| `execution_mode` | execution mode | — | execution mode |
| `affiliate_only` | affiliate_only | — | affiliate_only |
| `sourcing_only` | sourcing_only | — | sourcing_only |
| `affiliate_plus_sourcing` | affiliate_plus_sourcing | — | affiliate_plus_sourcing |
| `search_strategies` | — | Strategy A–F | strategy selection |
| `source_archetypes` | — | §11.3 source types | §7.1 expected_source_types |
| `desire_tier` (existing) | — | prestige_level | — |
| `location_context.relevance` (existing) | — | geography relevance | — |
