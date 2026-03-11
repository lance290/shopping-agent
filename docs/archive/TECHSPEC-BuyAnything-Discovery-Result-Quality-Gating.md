# Tech Spec: BuyAnything Discovery Result Quality Gating and LLM-Assisted Reranking

Status: Draft for implementation
Owner: Engineering
Product reference:
- `docs/active-dev/PRD-BuyAnything-Vendor-Coverage-Messaging.md`
- `docs/active-dev/PRD-BuyAnything-Location-Aware-Search.md`
- `docs/active-dev/TECHSPEC-BuyAnything-Proactive-Vendor-Discovery.md`

Reference stack: current BuyAnything backend/frontend in this repo

---

## 1. Overview

This spec defines the fix for low-quality BuyAnything vendor discovery results.

The current failure mode is not primarily caused by the LLM. It is caused by a dirty candidate pool entering reranking with false provenance and weak type classification.

Observed root issues in the current stack:

- `apps/backend/sourcing/discovery/adapters/organic.py` treats nearly every organic result as `official_site=True`
- the discovery pipeline does not reliably distinguish:
  - official vendor site
  - brokerage/agent site
  - marketplace/exchange
  - directory/aggregator
  - listing/inventory page
  - editorial/irrelevant content
- location-sensitive discovery modes do not apply strict enough pre-ranking gates
- the current ranker is being asked to sort candidates that should have been rejected earlier

This spec fixes that by introducing:

1. candidate type classification before ranking
2. evidence-driven provenance instead of assumed provenance
3. discovery-mode gating rules that reject invalid result types early
4. LLM-assisted reranking only after deterministic admissibility checks

Core principle:

- do not overfit to real estate
- do not let the LLM invent truth from junk inputs
- keep the system general across brokerage, luxury goods, marketplaces, local services, and asset markets

---

## 2. Goals

- Stop obviously wrong discovery results from reaching the row UI.
- Replace fake `official_site` confidence with evidence-backed provenance.
- Keep the fix general across:
  - real estate
  - whisky
  - sneakers
  - yacht charters
  - Gulfstreams / aircraft brokers
- Increase LLM influence in reranking without making it the source of truth.
- Preserve current BuyAnything commodity/provider flows.

## 3. Non-Goals

- Replacing commodity provider retrieval with an LLM answer engine.
- Reopening the broader proactive discovery architecture.
- Building a full trust/compliance engine for discovered vendors.
- Creating a category-specific one-off rules engine for Nashville realtors.

---

## 4. Reference Stack

This fix is anchored to these current modules:

- discovery adapters:
  - `apps/backend/sourcing/discovery/adapters/base.py`
  - `apps/backend/sourcing/discovery/adapters/organic.py`
- discovery orchestration:
  - `apps/backend/sourcing/discovery/orchestrator.py`
  - `apps/backend/sourcing/discovery/query_planner.py`
  - `apps/backend/sourcing/discovery/dedupe.py`
  - `apps/backend/sourcing/discovery/normalization.py`
- runtime routing:
  - `apps/backend/routes/rows_search.py`
  - `apps/backend/sourcing/service.py`
- current ranking and coverage:
  - `apps/backend/sourcing/scorer.py`
  - `apps/backend/sourcing/coverage.py`
- typed search models:
  - `apps/backend/sourcing/models.py`

---

## 5. Current Problem

### 5.1 Root cause

The current system is admitting candidates with false or weak provenance into the same pool as valid vendors.

Examples of the current failure:

- a listing page is treated as if it were a brokerage
- a national luxury portal is treated as if it were a local service vendor
- a generic organic result is marked `official_site=True` without first-party evidence
- irrelevant but high-gloss pages survive because the reranker sees rich keywords and prestige language

### 5.2 Why reranking alone is not enough

If the candidate pool contains bad result types, better ranking still produces polished bad results.

Therefore the fix must happen in this order:

1. classify candidate type
2. infer provenance from evidence
3. apply discovery-mode admissibility gates
4. then rerank the surviving pool

---

## 6. Architecture Changes

### 6.1 New modules

Add these modules under `apps/backend/sourcing/discovery/`:

- `classification.py`
  - candidate type classification
  - provenance inference
  - evidence extraction helpers
- `gating.py`
  - discovery-mode admissibility rules
  - location and trust floor checks
- `llm_rerank.py`
  - LLM-assisted reranking over already-admissible candidates
- `debug.py`
  - structured per-session audit records for why candidates were accepted, rejected, or demoted

### 6.2 Integration seam

This fix must be inserted in one place only:

- `DiscoveryOrchestrator` remains the top-level owner of live discovery batches
- adapter output must pass through:
  - classification
  - gating
  - normalization
  - optional LLM rerank
  - persistence/streaming

Locked seam:

`adapter.search() -> classification -> gating -> normalization -> LLM rerank -> rows_search stream/persist`

Do not spread type filtering across:

- adapter modules
- `rows_search.py`
- `scorer.py`

The orchestrator should own the pipeline.

---

## 7. Candidate Type System

### 7.1 Candidate types

Each discovered result must be classified into exactly one primary type:

- `official_vendor_site`
- `brand_site`
- `brokerage_or_agent_site`
- `marketplace_or_exchange`
- `directory_or_aggregator`
- `listing_or_inventory_page`
- `editorial_or_irrelevant`

Optional subtypes may be added later, but MVP should keep this set small and stable.

For MVP, the distinction between `official_vendor_site` and `brand_site` is:

- `official_vendor_site`: the primary site of the actual seller, broker, operator, advisor, or service provider being matched
- `brand_site`: a first-party brand/manufacturer site that is authoritative for the product or brand, but may not itself be the transacting seller for the user request

If classification confidence between those two types is weak in MVP, the system may collapse them operationally into a shared trust tier for gating while still preserving the raw label for debugging.

### 7.2 Provenance fields

Replace the current loose provenance assumptions with explicit fields:

```python
class DiscoveryClassification:
    candidate_type: str
    confidence: float
    official_site: bool
    first_party_contact: bool
    location_evidence: list[str]
    service_category_evidence: list[str]
    trust_signals: dict
    rejection_reasons: list[str]
```

### 7.3 Evidence inputs

Classification should use:

- URL/domain patterns
- page title
- snippet text
- query/result alignment
- contact evidence in snippet or fetched page
- path clues such as `/agents/`, `/team/`, `/listing/`, `/properties/`, `/inventory/`
- marketplace/listing language such as:
  - `for sale`
  - `listing`
  - `inventory`
  - `view property`
  - `auction lot`
  - `marketplace`
- first-party clues such as:
  - brand/team naming
  - contact page language
  - official domain
  - repeated company name across title/domain

V1 should be heuristic-first with optional model-assisted classification only for borderline cases.

---

## 8. Discovery-Mode Gating

### 8.1 Allowed result types by discovery mode

| Discovery mode | Preferred types | Allowed fallback types | Reject by default |
| --- | --- | --- | --- |
| `local_service_discovery` | `official_vendor_site`, `brokerage_or_agent_site` | `directory_or_aggregator` | `editorial_or_irrelevant` |
| `luxury_brokerage_discovery` | `brokerage_or_agent_site`, `official_vendor_site` | `marketplace_or_exchange` | `listing_or_inventory_page`, `editorial_or_irrelevant` |
| `uhnw_goods_discovery` | `official_vendor_site`, `marketplace_or_exchange`, `brand_site` | `directory_or_aggregator` | `editorial_or_irrelevant` |
| `asset_market_discovery` | `brokerage_or_agent_site`, `marketplace_or_exchange`, `official_vendor_site` | `directory_or_aggregator` | `editorial_or_irrelevant` |
| `destination_service_discovery` | `official_vendor_site`, `brokerage_or_agent_site` | `marketplace_or_exchange`, `directory_or_aggregator` | `editorial_or_irrelevant` |
| `advisory_discovery` | `official_vendor_site`, `brokerage_or_agent_site` | `directory_or_aggregator` | `listing_or_inventory_page`, `editorial_or_irrelevant` |

### 8.2 Location gating

Location-sensitive modes must apply deterministic gates before ranking:

- if `location_relevance` is `vendor_proximity` or `service_area`, require at least one of:
  - exact city/state evidence in snippet/title/domain/page
  - structured geo evidence from fetched page
  - canonical service-area evidence
- if no location evidence exists, candidate may remain only as a low-confidence fallback
- if local matches exist, non-local candidates must be suppressed

For `endpoint` requests:

- location gates apply to service capability, not vendor headquarters proximity

### 8.3 Trust floor

Before a candidate is allowed into reranking, it must pass a minimum trust floor:

- valid URL/domain
- candidate type is not rejected by mode
- not obviously editorial/noise
- not obviously duplicate of a stronger candidate

For high-risk modes (`luxury_brokerage_discovery`, `asset_market_discovery`, `advisory_discovery`):

- candidates must also show either:
  - first-party contact evidence, or
  - strong domain/title alignment with the vendor identity, or
  - marketplace/exchange legitimacy evidence

---

## 9. LLM-Assisted Reranking

### 9.1 Role of the LLM

The LLM should become more influential in reranking, but only after gating.

The LLM is allowed to help decide:

- subtle fit to user request
- specialization quality
- luxury/exclusivity fit
- whether a candidate feels like the right kind of vendor for the request

The LLM is not allowed to override:

- hard rejects from gating
- missing trust floor
- explicit location exclusions when local matches exist

### 9.2 Inputs to LLM rerank

The reranker should receive:

- full normalized candidate list after gating
- search intent
- relevant row context / clarified constraints
- candidate classification
- provenance/trust metadata
- location evidence

### 9.3 Output contract

```python
class DiscoveryRerankDecision:
    candidate_id: str
    llm_score: float
    fit_summary: str
    specialization_score: float
    trust_adjustment: float
    should_demote: bool
    should_exclude: bool
    exclusion_reason: str | None
```

### 9.4 Final score blend

Final discovered-candidate score should use:

```text
final_score =
  admissibility_pass
  * (
      heuristic_fit * 0.45
      + llm_fit * 0.35
      + trust_score * 0.10
      + location_score * 0.10
    )
```

Notes:

- `admissibility_pass` is binary; failed candidates never enter ranking
- weights are config-driven defaults, not a product contract, and may be tuned without changing the architecture
- LLM influence is meaningful, but not dominant over hard evidence
- if LLM reranking times out, errors, or is unavailable, the system must fall back to gated heuristic ranking only

---

## 10. Adapter Changes

### 10.1 Organic adapter behavior

`apps/backend/sourcing/discovery/adapters/organic.py` must stop defaulting to:

- `source_type="official_site"`
- `official_site=True`

Instead it should emit raw discovery candidates with minimal assumptions:

```python
DiscoveryCandidate(
    source_type="unknown",
    official_site=False,
    ...
)
```

The adapter’s job is retrieval, not trust inference.

### 10.2 Optional shallow fetch

V1 may do a shallow follow-up fetch for top-N raw organic candidates to improve classification before final gating:

- title tag
- meta description
- visible contact cues
- basic page path / canonical URL

Default MVP budget:

- fetch at most top `3-5` raw candidates per adapter batch
- run only when the raw candidate is not already confidently classifiable from snippet/domain evidence
- do not block streaming of already-admissible candidates on slower shallow fetches

This should be:

- bounded
- timeout-limited
- best-effort only

It should not block all streaming.

---

## 11. Data Contracts

### 11.1 DiscoveryCandidate additions

Extend `DiscoveryCandidate` in `adapters/base.py`:

```python
class DiscoveryCandidate:
    adapter_id: str
    query: str
    title: str
    url: str
    source_url: str
    source_type: str
    snippet: str | None
    image_url: str | None
    email: str | None
    phone: str | None
    canonical_domain: str | None
    location_hint: str | None
    official_site: bool
    first_party_contact: bool
    raw_payload: dict
    trust_signals: dict
    classification: dict | None
```

### 11.2 NormalizedResult provenance additions

Discovered results should include:

- `candidate_type`
- `classification_confidence`
- `official_site`
- `first_party_contact`
- `location_evidence`
- `trust_signals`
- `admissibility_status`
- `rejection_reasons`
- `llm_rerank_summary`

### 11.3 Debug artifact

Each discovery session should emit a structured audit bundle:

```python
class DiscoveryAuditRecord:
    discovery_session_id: str
    query: str
    discovery_mode: str
    candidate_url: str
    candidate_type: str
    admissible: bool
    rejection_reasons: list[str]
    heuristic_scores: dict
    llm_scores: dict | None
    final_score: float | None
```

This should be loggable and searchable.

---

## 12. Execution Flow

### 12.1 Batch flow

For each external batch:

1. adapter returns raw candidates
2. classifier assigns type and provenance
3. gating rejects invalid candidates
4. dedupe merges obvious duplicates
5. normalization produces `NormalizedResult`
6. LLM rerank runs on survivors only
7. final score order is computed
8. stream results
9. persist only candidates above persistence threshold

### 12.2 Borderline coverage behavior

If internal coverage is borderline:

- show internal DB results immediately
- start discovery in parallel
- merge/rerank discovered results against internal results as they arrive
- suppress discovered candidates that are worse duplicates of existing internal vendors

### 12.3 Insufficient coverage behavior

If internal coverage is insufficient:

- start discovery immediately
- ask at most one blocking clarification if it materially changes discovery mode or geography
- continue low-confidence discovery in parallel when safe

---

## 13. Persistence Rules

### 13.1 Row-visible results

A discovered candidate may become row-visible only if:

- it passed gating
- it survived dedupe
- it has a final score at or above the configured row-visibility threshold

Default MVP row-visibility threshold:

- `final_score >= 0.55`

This threshold is config-driven and should be logged with the session for debugging and tuning.

### 13.2 Candidate persistence

Persist to `DiscoveredVendorCandidate` only if:

- admissible
- confidence above threshold
- not obvious junk
- valid domain
- enough completeness for later enrichment

### 13.3 Canonical vendor promotion

Do not promote directly to canonical `Vendor` synchronously for:

- luxury brokerage
- advisory
- aircraft/yacht/asset-market

Those remain post-enrichment only.

---

## 14. Testing Plan

Add tests for:

- organic adapter no longer sets `official_site=True` by default
- classification distinguishes:
  - brokerage site vs listing page
  - marketplace vs editorial result
  - official vendor site vs directory
- location-sensitive discovery suppresses non-local candidates when local matches exist
- LLM rerank cannot resurrect hard-rejected candidates
- same-name same-geo but different real vendor is not over-merged
- real-estate mode rejects property listing pages as primary vendor matches
- goods/asset modes still allow valid marketplaces where appropriate

Representative request coverage:

- sell mansion in Nashville
- buy rare whisky collection
- buy sneakers
- charter yacht in the Mediterranean
- buy Gulfstream G650

---

## 15. Rollout

### Phase 1

- stop false `official_site` labeling
- add classification + gating
- keep current heuristic ranking

### Phase 2

- add LLM rerank for gated survivors
- add debug artifact logging

### Phase 3

- tune thresholds and discovery-mode rules from production traces

---

## 16. Success Criteria

Primary:

- major reduction in obviously wrong discovered vendors reaching rows
- higher precision for location-sensitive vendor discovery
- lower rate of listing/editorial pages being shown as vendors

Secondary:

- improved user acceptance of discovered vendors
- improved persistence quality of discovered candidates
- lower manual cleanup burden during enrichment

---

## 17. Closing Principle

The fix is not to make the LLM answer everything.

The fix is to stop lying to the ranking layer about what kind of candidate we found, then let the LLM help choose among valid candidates.
