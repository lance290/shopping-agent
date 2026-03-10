# Implementation PRD: Ranking Experiment Data Model, Shadow Logging, and Outcome Attribution

## 1. Executive Summary

This document defines the first implementation slice for the quantum reranker advancement program.

The purpose of this slice is to build the minimum viable ranking experimentation infrastructure required to answer one question with real evidence:

- when an experimental reranker sees the same candidate slate as the live baseline, would it have produced better outcomes?

This slice covers three concrete deliverables:

- a ranking experiment data model
- shadow-run logging inside the search pipeline
- attribution of clickout and selection outcomes back to rank positions

This is intentionally an **evaluation-first** implementation. It does not require changing the user-visible ranking order in the first phase.

---

## 2. Scope of This Implementation Slice

### In scope
- Define persistent models for ranking experiments and per-search ranking runs.
- Capture baseline and experimental rank positions for the same candidate slate.
- Log shadow reranker outputs from the existing search pipeline.
- Attribute clickout events and bid selections back to ranking runs and candidate ranks.
- Support offline replay and metric computation for baseline vs experiment comparisons.

### Out of scope
- Full dashboard or analyst UI.
- Learned reranker training pipeline.
- Hardware-backed quantum execution.
- Full purchase attribution beyond wiring to existing purchase/clickout event relationships.
- Global live ranking rollout logic beyond narrow future-readiness hooks.

---

## 3. Current State of the Codebase

The implementation must match the current backend realities.

### 3.1 Search path
The main search streaming path lives in:

- `apps/backend/routes/rows_search.py`

Relevant facts:

- candidates are streamed provider-by-provider
- quantum reranking currently happens inside `process_batch(...)`
- quantum scores are written into bid/result provenance
- persisted bids are created via `sourcing_service._persist_results(...)`

### 3.2 Clickout path
Outbound click tracking currently lives in:

- `apps/backend/routes/clickout.py`
- `apps/backend/models/social.py::ClickoutEvent`

Relevant facts:

- clickouts are logged asynchronously
- current query params include `row_id`, `bid_id`, `idx`, and `source`
- `ClickoutEvent` already stores `row_id`, `bid_id`, and `offer_index`
- this is useful but not sufficient for experiment attribution because it does not identify which ranking run produced that position

### 3.3 Selection path
Bid selection currently lives in:

- `apps/backend/routes/rows.py::select_row_option`

Relevant facts:

- selection is persisted by setting `Bid.is_selected`
- the endpoint currently returns status only
- no explicit ranking experiment event is stored when a user selects an option

### 3.4 Existing outcome models
The codebase already has:

- `ClickoutEvent`
- `PurchaseEvent`

These provide useful hooks, but neither currently captures ranking-run identity.

---

## 4. Problem Statement

Today, the system can compute experimental ranking signals, but it cannot answer the core product questions reliably:

- which candidate slate did the user actually see?
- what was the baseline position of the clicked or selected result?
- what would the experimental reranker have done with that same slate?
- did the experiment move successful results upward or downward?

Without that linkage, ranking work stays anecdotal.

---

## 5. Goals

### 5.1 Persist ranking runs in a replayable way
For each eligible search, the system should persist enough information to reconstruct the baseline and experimental ordering of the same candidate slate.

### 5.2 Capture shadow experimental results without changing UX
The live ranking remains stable while shadow rerankers run and log their outputs.

### 5.3 Tie user outcomes back to the exact ranking run
Clickouts and selections must be attributable to the specific run and candidate record the user acted on.

### 5.4 Keep the design additive and production-safe
All schema changes and implementation changes should be additive.

---

## 6. Product Decisions Locked by This PRD

### 6.1 Ranking experiments are per-run, not just per-query-shape
We must track the exact run that generated the visible candidate slate, not just broad search metadata.

### 6.2 The candidate slate is the unit of evaluation
A ranking run is only meaningful if we know the exact candidates it contained and how they were ordered.

### 6.3 Stable candidate identity is mandatory
A result must be attributable across baseline, experiment, clickout, and selection.

### 6.4 Shadow logging happens at search completion boundaries, not only at click time
We should persist the run as soon as the candidate slate is known, rather than trying to reconstruct it later from click logs.

### 6.5 Attribution must prefer exact IDs over fuzzy reconstruction
The system should use `bid_id` or a stable candidate record identifier wherever possible.

---

## 7. Proposed Data Model

This PRD recommends adding new additive models rather than overloading existing event tables for all experiment logic.

### 7.1 `RankingExperiment`
Purpose:

- defines an experiment configuration that can be enabled in shadow, partial, or live mode

Recommended fields:

- `id`
- `name`
- `version`
- `description`
- `surface` — e.g. `search`
- `algorithm_family` — e.g. `baseline`, `quantum_reranker`, `cosine_reranker`, `learned_blend`
- `mode` — `shadow`, `interleaving`, `live`
- `enabled`
- `config_json`
- `created_at`
- `updated_at`

### 7.2 `RankingRun`
Purpose:

- one persisted evaluation run for one search request / candidate slate / experiment

Recommended fields:

- `id`
- `experiment_id`
- `user_id` nullable
- `session_id` nullable
- `row_id` nullable
- `request_id` or `search_trace_id` string
- `query_text`
- `normalized_query_text`
- `vendor_query` nullable
- `desire_tier` nullable
- `providers_json`
- `status` — `running`, `completed`, `failed`
- `candidate_count`
- `visible_candidate_count`
- `created_at`
- `completed_at`

Notes:

- `search_trace_id` should be generated once per user-visible search execution and reused across baseline and experimental runs.
- there should be one baseline `RankingRun` and one or more experimental `RankingRun`s per search trace.

### 7.3 `RankingRunCandidate`
Purpose:

- one persisted candidate within a given ranking run

Recommended fields:

- `id`
- `ranking_run_id`
- `bid_id` nullable
- `row_id` nullable
- `candidate_key` string
- `canonical_url` nullable
- `source`
- `provider_name` nullable
- `title`
- `merchant_name` nullable
- `is_persisted_bid`
- `baseline_rank` nullable
- `experiment_rank` nullable
- `display_rank` nullable
- `was_shown`
- `price` nullable
- `score_json`
- `provenance_json` nullable
- `created_at`

Notes:

- `candidate_key` is the stable identity fallback when `bid_id` is unavailable.
- recommended construction order for `candidate_key`:
  - `bid:{bid_id}` when available
  - normalized canonical URL
  - provider-specific stable item key
  - final deterministic fallback derived from source/title/url

### 7.4 `RankingOutcome`
Purpose:

- experiment-aware linkage between user outcomes and ranking candidates

Recommended fields:

- `id`
- `ranking_run_id`
- `ranking_run_candidate_id`
- `outcome_type` — `clickout`, `select`, `purchase`, `like`, `comment`, `quote_request`
- `user_id` nullable
- `session_id` nullable
- `row_id` nullable
- `bid_id` nullable
- `clickout_event_id` nullable
- `purchase_event_id` nullable
- `metadata_json`
- `created_at`

Notes:

- this table is the analytics join layer; it should not replace domain events like `ClickoutEvent`
- it should reference domain event ids where they exist

---

## 8. Relationship to Existing Models

### 8.1 `ClickoutEvent`
Current useful fields:

- `row_id`
- `bid_id`
- `offer_index`
- `source`

Required additive changes:

- optional `ranking_run_id`
- optional `ranking_run_candidate_id`
- optional `search_trace_id`

Rationale:

- `offer_index` alone is ambiguous across different ranking runs
- attaching exact ranking references turns clickouts into reliable ranking outcome data

### 8.2 `PurchaseEvent`
Current useful fields:

- `bid_id`
- `row_id`
- `clickout_event_id`

Recommended additive changes:

- optional `ranking_run_id`
- optional `ranking_run_candidate_id`
- optional `search_trace_id`

Rationale:

- purchases should inherit attribution from the original click or selection when possible

### 8.3 Selection behavior in `rows.py`
The current `select_row_option(...)` endpoint updates `Bid.is_selected` but does not create an experiment-aware outcome record.

Required additive behavior:

- create a `RankingOutcome` of type `select`
- attach the latest relevant visible ranking run candidate for the selected `bid_id`

---

## 9. Search Pipeline Design for Shadow Logging

### 9.1 Where to log runs
The shadow-run capture should be wired into:

- `apps/backend/routes/rows_search.py`

The right lifecycle is:

1. create a shared `search_trace_id` at the start of the search
2. create a baseline `RankingRun` record early
3. create experimental `RankingRun` record(s) for enabled shadow experiments
4. collect candidates as they are normalized and persisted
5. finalize run candidates after search completion when the visible slate is known

### 9.2 What counts as the baseline slate
The baseline run should represent the user-visible ordering that the frontend sees in the current system.

This means:

- rank after current normalization and baseline scoring
- rank after existing provider/bid filtering
- rank after any current quantum score enrichment that is not yet changing user-visible order must be recorded carefully

Important implementation rule:

- if the current code is already letting `blended_score` influence visible order somewhere, that must be called out explicitly
- the baseline run should reflect the true shipped behavior, not an idealized baseline

### 9.3 What counts as the experimental slate
The experiment run should use the same candidates as the baseline, then apply alternate ranking logic.

Examples:

- current quantum reranker in pure shadow mode
- improved reranker variant with different reduction/blending
- cosine-only semantic reranker

### 9.4 Candidate persistence timing
Candidate logging should happen after `Bid` persistence when available, so that `bid_id` can be used as the primary identity.

Recommended approach:

- collect a temporary in-memory slate during search
- after `sourcing_service._persist_results(...)` returns, map normalized results back to persisted bids
- write final `RankingRunCandidate` rows once `bid_id` values are known

### 9.5 Search trace propagation
Every user-visible search execution must have a trace id that can be propagated to:

- SSE payloads if needed by frontend
- clickout URLs
- selection requests
- downstream attribution logic

Recommended field name:

- `search_trace_id`

---

## 10. Outcome Attribution Design

### 10.1 Clickout attribution
Current clickout requests already include:

- `row_id`
- `bid_id`
- `idx`
- `source`

Required enhancement:

- also include `search_trace_id`
- include `ranking_run_id`
- include `ranking_run_candidate_id`

Recommended approach:

- when a result is rendered or turned into a clickout URL, attach the run and candidate ids from the baseline visible slate
- `routes/clickout.py` writes those ids into `ClickoutEvent`
- a companion `RankingOutcome` row of type `clickout` is created either directly during clickout logging or via async follow-up

### 10.2 Selection attribution
Selection currently happens via:

- `POST /rows/{row_id}/options/{option_id}/select`

Required enhancement:

- selection must resolve the visible ranking candidate associated with `option_id`
- create a `RankingOutcome` row of type `select`

Preferred lookup order:

1. exact `ranking_run_candidate_id` passed from frontend
2. latest baseline visible candidate for the same `bid_id` and active `search_trace_id`
3. latest baseline visible candidate for the same `bid_id` on that row

This ensures attribution remains robust even if the frontend payload is not immediately upgraded everywhere.

### 10.3 Purchase attribution
Where purchase events exist, attribution should flow through:

- exact `clickout_event_id` when present
- otherwise selected `bid_id` plus latest visible candidate context

### 10.4 Avoiding ambiguity across repeated searches
Users may run the same row search multiple times. Therefore:

- rank attribution should not rely on `row_id + bid_id` alone
- it should prefer `search_trace_id` or `ranking_run_candidate_id`

---

## 11. API and Frontend Contract Changes

### 11.1 Search response / result metadata
The frontend needs enough metadata to preserve attribution through user actions.

Each rendered offer should eventually carry:

- `search_trace_id`
- `ranking_run_id`
- `ranking_run_candidate_id`
- visible rank position

These can travel in provenance or dedicated response fields.

### 11.2 Clickout URL generation
Clickout URLs should include the ranking attribution metadata needed by `routes/clickout.py`.

### 11.3 Selection API payload
Selection requests should be allowed to include optional ranking attribution fields.

Recommended additive request fields:

- `search_trace_id`
- `ranking_run_id`
- `ranking_run_candidate_id`

The endpoint should remain backward-compatible if the fields are absent.

---

## 12. Implementation Plan

### Step 1: Add additive schema for ranking experiments
Implement:

- `RankingExperiment`
- `RankingRun`
- `RankingRunCandidate`
- `RankingOutcome`

Also add optional ranking reference fields to existing outcome models where justified.

### Step 2: Add search trace generation and shadow-run logging
Implement in `rows_search.py`:

- search trace creation
- baseline run creation
- experiment run creation for enabled shadow experiments
- candidate logging after bid persistence
- run finalization

### Step 3: Propagate attribution metadata to frontend-visible offers
Ensure rendered offers carry enough metadata to survive clickout and selection actions.

### Step 4: Extend clickout logging
Update `routes/clickout.py` to accept and persist ranking attribution ids.

### Step 5: Extend selection logging
Update `routes/rows.py::select_row_option` to create `RankingOutcome` rows tied to ranking candidates.

### Step 6: Add purchase linkage where available
Ensure downstream purchase events inherit ranking attribution when possible.

### Step 7: Build initial evaluation queries or scripts
Create basic reports for:

- clicked result baseline rank distribution
- selected result baseline rank distribution
- experimental rank improvement for clicked/selected results

---

## 13. Acceptance Criteria

### AC-1 Ranking runs are persisted for eligible searches
For an eligible search, the backend stores at least one baseline ranking run and one shadow experiment run.

### AC-2 Candidate slates are replayable
Each ranking run stores enough candidate-level data to reconstruct ordering and scores later.

### AC-3 Clickouts are attributable to ranking runs
A clickout event can be traced to a specific ranking run and ranking candidate.

### AC-4 Selections are attributable to ranking runs
A bid selection can be traced to a specific ranking run and ranking candidate.

### AC-5 Attribution survives repeated searches on the same row
Repeated searches on the same row do not collapse into ambiguous rank data.

### AC-6 Backward compatibility is preserved
Existing clickout and selection flows continue to work even before every caller sends ranking attribution metadata.

---

## 14. Risks and Mitigations

### 14.1 Risk: Mapping normalized results back to persisted bids is imperfect
Mitigation:

- use `bid_id` whenever available
- define deterministic candidate keys
- log mapping failures explicitly

### 14.2 Risk: Clickout logging is async and could lose attribution context
Mitigation:

- pass all attribution ids directly into the route query params
- avoid relying on in-memory transient state in the async logger

### 14.3 Risk: Selection attribution becomes ambiguous when users search repeatedly
Mitigation:

- prefer exact `ranking_run_candidate_id`
- otherwise use `search_trace_id`
- only fall back to latest visible candidate as a last resort

### 14.4 Risk: Run logging adds too much write volume
Mitigation:

- begin with selected surfaces and shadow-enabled experiments only
- keep candidate payloads compact
- store essential fields first, richer diagnostics later

---

## 15. Open Questions

- Should `RankingOutcome` be the canonical experiment analytics table, or should clickout/select outcomes be derived purely from joins on existing event tables plus new reference fields?
- Should baseline and experiment runs be stored as separate `RankingRun` records or as one run with multiple rank columns? Separate runs are cleaner for versioning, but one run may be simpler to query.
- Which backend layer should own candidate-key generation so it stays consistent across providers?
- Should experiment eligibility start with all searches or just affiliate-heavy searches first?

---

## 16. Recommended Build Order

1. Schema and model definitions.
2. Search trace generation and baseline run persistence.
3. Shadow experiment run persistence.
4. Candidate-level logging after bid persistence.
5. Clickout attribution fields and logging.
6. Selection attribution logging.
7. Initial offline evaluation report.

This order gives measurable value quickly while keeping production behavior unchanged.
