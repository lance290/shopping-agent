# Tech Spec: BuyAnything Proactive Vendor Discovery

Status: Draft for implementation
Owner: Engineering
Product reference: `docs/active-dev/PRD-BuyAnything-Vendor-Coverage-Messaging.md`
Reference stack: current BuyAnything backend/frontend in this repo

---

## 1. Overview

This spec defines how to implement proactive vendor discovery on top of the current BuyAnything search stack.

The PRD is already locked on product behavior. The purpose of this spec is to answer how to build it using the current codebase, with minimal reinvention and with explicit technical boundaries.

Core principle:

- internal vendor DB search happens first for non-commodity vendor requests
- coverage is scored strictly
- if coverage is borderline or insufficient, live external vendor discovery is launched
- discovered vendors are normalized into the existing result stream
- strong candidates are persisted for offline enrichment
- dead-end requests create supply-building signals instead of stopping the user flow

This is not a replacement for the current sourcing stack. It is an extension of the existing `retrieval -> normalization -> scoring -> persistence -> SSE` pipeline, with a new strict sufficiency branch inserted before external vendor discovery.

---

## 2. Goals

- Reuse the current row-centered search architecture instead of creating a parallel system.
- Keep commodity/product flows on the existing marketplace stack.
- Make vendor discovery demand-driven and visible in the row UI.
- Keep scoring debuggable with heuristic-first logic.
- Preserve current SSE/store behavior where possible.
- Persist only strong discovered vendors; do not turn the vendor DB into a junk sink.

## 3. Non-Goals

- Reopening the PRD decision on whether discovery should happen.
- Replacing Amazon/Google/eBay commodity search.
- Building a full analyst dashboard in MVP.
- Full trust certification or compliance validation for newly discovered vendors.
- Full autonomous outreach to discovered vendors in this phase.

---

## 4. Reference Stack

This spec is anchored to these current modules:

- Request classification and row mutation:
  - `apps/backend/services/llm.py`
  - `apps/backend/routes/chat_helpers.py`
  - `apps/backend/routes/search_enriched.py`
- Internal row search orchestration:
  - `apps/backend/routes/rows_search.py`
  - `apps/backend/sourcing/service.py`
  - `apps/backend/sourcing/repository.py`
  - `apps/backend/sourcing/vendor_provider.py`
  - `apps/backend/sourcing/scorer.py`
- Typed search models:
  - `apps/backend/sourcing/models.py`
- Existing persistence primitives:
  - `apps/backend/models/rows.py`
  - `apps/backend/models/bids.py`
  - `apps/backend/models/admin.py`
- Existing vendor-gap escalation primitive:
  - `VendorCoverageGap` in `apps/backend/models/admin.py`
- Frontend streaming and row store:
  - `apps/frontend/app/components/Chat.tsx`
  - `apps/frontend/app/store-actions.ts`
  - `apps/frontend/app/utils/api-rows.ts`
- Existing offline discovery precedent:
  - `apps/backend/scripts/discover_vendors.py`
  - `apps/backend/scripts/discover_vendors_search.py`
  - `apps/backend/scripts/discover_vendors_config.py`

Important current constraint:

- `SourcingRepository.search_all_with_status()` still fans out providers in parallel.
- The PRD now requires strict DB-first sufficiency evaluation before live vendor discovery.
- Therefore the implementation must introduce a new orchestration layer for non-commodity vendor discovery requests instead of bolting discovery onto the existing "search everything at once" path.

---

## 5. Target Architecture

### 5.1 Components

| Component | Responsibility | Current stack | Change |
| --- | --- | --- | --- |
| Query classifier | Decide commodity vs vendor discovery path | `services/llm.py`, `search_intent.desire_tier`, `service_category` | Add explicit runtime classifier helper |
| Internal retrieval service | Retrieve internal vendor DB candidates only | `vendor_provider.py`, `service.py` | Reuse with DB-first branch |
| Coverage scorer | Score internal results against sufficiency model | partial in `scorer.py` | Add new `coverage.py` module |
| Discovery orchestrator | Run strict sufficiency branch, launch discovery, merge stream | none | New module |
| Clarification manager | Decide whether to ask a question vs continue low-confidence discovery | `services/llm.py`, chat routes | Add policy wrapper, not a new LLM engine |
| External source adapters | Query live external sources by discovery mode | offline scripts only, product providers exist | New discovery adapter layer |
| Extraction/normalization pipeline | Convert raw discovery results to canonical result shape | current normalizers only cover shopping/vendor DB | New discovery normalizer |
| Dedupe/merge engine | Merge DB vendors, discovered vendors, and source variants | partial bid/url dedupe only | New explicit merge layer |
| Streaming transport | Stream partial results into row UI | `/rows/{id}/search/stream`, SSE in `Chat.tsx` | Reuse event channel, extend payload |
| Persistence/enrichment | Save strong candidates for future reuse | `Vendor`, `Bid`, `VendorCoverageGap`, offline scripts | Add candidate table + enrichment queue |
| Observability | Track trigger rate, sufficiency quality, source yield | `sourcing/metrics.py`, logs | Expand metrics/event logging |

### 5.2 New backend modules

Add these modules under `apps/backend/sourcing/`:

- `coverage.py`
  - strict coverage scoring
  - sufficiency evaluation
  - borderline vs insufficient branching
- `discovery/orchestrator.py`
  - top-level non-commodity vendor discovery flow
- `discovery/classifier.py`
  - commodity vs vendor-discovery runtime pathing
- `discovery/clarification.py`
  - clarification gating and stopping rules
- `discovery/adapters/base.py`
  - adapter protocol
- `discovery/adapters/{google_organic,google_maps,directory_site,...}.py`
  - individual live source adapters
- `discovery/query_planner.py`
  - request-shaped query building per discovery mode
- `discovery/extractors.py`
  - website/contact/thumbnail/provenance extraction
- `discovery/normalization.py`
  - canonical conversion into `NormalizedResult`
- `discovery/dedupe.py`
  - cross-source/vendor merge logic
- `discovery/persistence.py`
  - candidate persistence + enrichment queue writes
- `discovery/events.py`
  - stream event builders

### 5.3 New persistence models

Add these SQLModel tables:

- `DiscoveredVendorCandidate`
- `VendorEnrichmentQueueItem`

Reuse and extend:

- `VendorCoverageGap` for ops escalation and dead-end capture

Do not replace:

- `Vendor`
- `Bid`
- `Row`

### 5.4 Single integration seam

The vendor-discovery-path branch must live in one place only.

Locked MVP seam:

- `search_enriched.py` remains an enrichment-only layer
- `rows_search.py` is the single route-level dispatcher
- `SourcingService` is the orchestration facade called by `rows_search.py`
- `DiscoveryOrchestrator` is invoked only by `SourcingService`

That means:

- `search_enriched.py` may enrich query and intent, but must not decide discovery vs no discovery
- `rows_search.py` must not implement coverage scoring or adapter logic directly
- `vendor_provider.py` remains a retrieval provider, not an orchestrator

If path-selection logic appears anywhere other than `rows_search.py -> SourcingService -> DiscoveryOrchestrator`, the implementation is wrong.

---

## 6. End-to-End Flow

## 6.1 Entry points

Discovery-capable search can start from:

- `POST /api/search` via `apps/backend/routes/search_enriched.py`
- `POST /rows/{row_id}/search`
- `POST /rows/{row_id}/search/stream`
- chat flow via `apps/frontend/app/components/Chat.tsx` and backend SSE routes

All entry points should converge into one orchestration path for non-commodity vendor discovery requests.

Dispatch rule:

- all request shaping and intent extraction may happen before dispatch
- the first and only runtime branch between commodity search and vendor discovery happens inside `rows_search.py` when it calls `SourcingService`

## 6.2 High-level execution flow

1. Request enters with `row_id`, query, and optional `search_intent`.
2. Runtime classifier decides:
   - `commodity_marketplace_path`
   - `vendor_discovery_path`
3. If commodity:
   - continue current provider flow
4. If vendor discovery:
   - load row and intent
   - resolve location context if needed
   - run internal vendor retrieval only
   - score internal coverage
   - branch:
     - sufficient: return internal results only
     - borderline: show internal results immediately and start discovery in parallel
     - insufficient: start discovery immediately; ask clarification only if materially useful
5. External discovery fan-out runs by discovery mode.
6. Raw discovery results are canonicalized and normalized.
7. Dedupe/merge runs across:
   - existing internal vendor results
   - discovered candidates
   - multiple discovery adapters
   - official site vs directory/listing variants
8. Discovered results stream into the row UI.
9. Strong candidates are persisted:
   - row-visible bid/vendor state
   - candidate table
   - enrichment queue
10. If discovery remains weak:
   - create/update coverage gap record
   - emit status messaging
   - generate manual sourcing task payload

## 6.3 Sequence flow

```text
Request
  -> classify_search_path()
  -> if commodity: existing repository/provider flow
  -> if vendor_discovery:
       -> internal_vendor_search()
       -> coverage_score()
       -> if sufficient: persist + respond
       -> if borderline:
            -> persist internal results
            -> start discovery_orchestrator()
            -> stream discovered batches
       -> if insufficient:
            -> maybe emit 1 blocking clarification
            -> start discovery_orchestrator()
            -> normalize + dedupe + rerank each batch
            -> stream partial results
            -> persist strong candidates
            -> escalate if still weak
```

---

## 7. State Machine

Use an explicit request-level state machine inside the discovery orchestrator. This does not require new `row.status` values in MVP; state can live in logs, SSE payloads, and candidate records.

### 7.1 States

- `classified`
- `internal_search_running`
- `coverage_evaluated`
- `sufficient`
- `borderline_discovery_running`
- `insufficient_discovery_running`
- `clarification_pending`
- `streaming_results`
- `persisting_candidates`
- `complete`
- `escalated`
- `failed_soft`

### 7.2 State transitions

- `classified -> internal_search_running`
- `internal_search_running -> coverage_evaluated`
- `coverage_evaluated -> sufficient`
- `coverage_evaluated -> borderline_discovery_running`
- `coverage_evaluated -> insufficient_discovery_running`
- `insufficient_discovery_running -> clarification_pending` only if request is too ambiguous and low-confidence discovery cannot proceed safely
- `borderline_discovery_running -> streaming_results`
- `insufficient_discovery_running -> streaming_results`
- `streaming_results -> persisting_candidates`
- `persisting_candidates -> complete`
- `streaming_results -> escalated` if final coverage remains weak
- any state -> `failed_soft` on source or normalization failure

### 7.3 MVP row-status rule

Do not introduce a broad new `row.status` enum in MVP. Continue to use current row statuses and expose discovery phase through:

- SSE event metadata
- `user_message`
- candidate provenance
- `rowSearchErrors` / store messaging path

This avoids a frontend-wide status migration.

---

## 8. Runtime Path Selection

### 8.1 Query classifier

Add `classify_search_path(search_intent, row)`:

- `commodity_marketplace_path`
  - `desire_tier in {commodity, considered}`
  - no strong service/high-value/advisory signal
- `vendor_discovery_path`
  - `desire_tier in {service, bespoke, high_value, advisory}`
  - or `is_service = true`
  - or `service_category` present

### 8.2 Pathing rules

- Commodity searches continue through current marketplace providers.
- Vendor discovery path does not call Amazon/Google Shopping/eBay as primary retrieval.
- Vendor discovery path starts with `vendor_directory` only.
- Live external discovery only begins after strict internal sufficiency evaluation.

### 8.3 Borderline case policy

This is mandatory and should not be left to the caller:

- persist and show strong internal results immediately
- start live discovery in parallel
- merge/rerank discovered results against internal results as they arrive
- never blank or replace the existing internal results while discovery is running

---

## 9. Component Design

## 9.1 Internal retrieval service

Reuse:

- `VendorDirectoryProvider.search()`
- `SourcingService.extract_vendor_query()`
- location-aware vendor search in `vendor_provider.py`

Required change:

- introduce `search_internal_vendors_only()` on `SourcingService`
- this path must bypass non-vendor providers
- this path must return both normalized results and vendor search metadata needed by the coverage scorer

Ownership rule:

- `SourcingService.search_internal_vendors_only()` owns internal vendor retrieval
- `DiscoveryOrchestrator` consumes that output but does not reimplement internal vendor search

## 9.2 Coverage scorer

Add `apps/backend/sourcing/coverage.py`.

Responsibilities:

- compute per-candidate `CoverageScore`
- classify request-level sufficiency
- explain why coverage is sufficient, borderline, or insufficient
- emit machine-readable debug data

Inputs:

- normalized internal vendor results
- `SearchIntent`
- row metadata
- vendor metadata from `raw_data`, `provenance`, and `Vendor`

Outputs:

- candidate scores
- sufficiency classification
- reasons / debug fields
- next action recommendation: `stop`, `discover_parallel`, `discover_now`, `ask_clarification`

## 9.3 Discovery orchestrator

Add `apps/backend/sourcing/discovery/orchestrator.py`.

Responsibilities:

- execute the state machine
- build discovery session context
- select discovery mode
- select adapters
- fan out adapter calls with bounded concurrency
- normalize batches
- merge/dedupe/rerank
- emit stream updates
- persist qualifying candidates
- escalate if still weak

This orchestrator becomes the main entry point for vendor-discovery-path searches.

## 9.4 Clarification manager

Clarification remains driven by the existing LLM stack, but the policy wrapper should be deterministic.

Add `DiscoveryClarificationManager`:

- inspects `SearchIntent.confidence`, missing fields, and discovery mode
- decides whether clarification is:
  - not needed
  - non-blocking follow-up
  - one blocking clarification
- enforces PRD guardrails:
  - max 2 clarifying questions before starting discovery
  - max 1 blocking clarification at a time
  - parallel low-confidence discovery where safe

This should not create a second conversational brain. It should wrap the existing `make_unified_decision()` behavior.

---

## 10. Data Contracts

## 10.1 Internal vendor result

Internal vendor search should continue to produce `SearchResult` and `NormalizedResult`, but vendor discovery requires additional metadata in `metadata` or `provenance`.

```json
{
  "source": "vendor_directory",
  "title": "Kumara Wilcoxon",
  "merchant": "Kumara Wilcoxon",
  "merchant_domain": "kumarawilcoxon.com",
  "url": "https://kumarawilcoxon.com",
  "image_url": "https://...",
  "match_score": 0.86,
  "metadata": {
    "location_mode": "service_area",
    "location_match": true,
    "geo_distance_miles": null,
    "service_category_match": true,
    "official_site": true
  },
  "provenance": {
    "vector_similarity": 0.71,
    "score": {},
    "vendor_status": "verified"
  }
}
```

## 10.2 Discovered vendor candidate

Add a typed runtime object:

```python
class DiscoveredVendorCandidate(BaseModel):
    candidate_id: str
    row_id: int
    discovery_session_id: str
    adapter_id: str
    discovery_mode: str
    query: str
    title: str
    vendor_name: str
    website_url: str
    canonical_domain: str
    source_url: str
    source_type: str  # official_site, directory, marketplace, map_listing
    snippet: Optional[str]
    image_url: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    location_hint: Optional[str]
    official_site: bool
    first_party_contact: bool
    raw_payload: dict
    extraction_payload: dict
    trust_signals: dict
```

## 10.3 Coverage score object

```python
class CoverageScore(BaseModel):
    candidate_id: str
    source: str
    semantic_fit: float
    geography_fit: float
    luxury_fit: Optional[float]
    contactability: float
    specialization_fit: float
    freshness: float
    source_credibility: float
    duplicate_penalty: float
    total_score: float
    missing_signals: list[str]
    reasoning: list[str]
```

## 10.4 Provenance metadata

Use a shared provenance shape for internal and discovered results:

```python
class ResultProvenance(BaseModel):
    source_provider: str
    discovery_mode: Optional[str]
    discovery_session_id: Optional[str]
    source_url: Optional[str]
    source_type: Optional[str]
    official_site: Optional[bool]
    first_party_contact: Optional[bool]
    trust_signals: dict
    score: dict
    dedupe_key: Optional[str]
    merged_into: Optional[str]
```

## 10.5 Stream update event

Do not create a brand new frontend protocol in MVP. Reuse the existing `search_results` event and extend its payload.

```json
{
  "event": "search_results",
  "row_id": 123,
  "phase": "internal_results|discovery_results|complete",
  "coverage_status": "sufficient|borderline|insufficient",
  "discovery_session_id": "uuid",
  "results": [],
  "provider_statuses": [],
  "more_incoming": true,
  "user_message": "I’m expanding the search beyond our current vendor database.",
  "deduped_count": 2,
  "suppressed_count": 1
}
```

## 10.6 Enrichment queue record

```python
class VendorEnrichmentQueueRecord(BaseModel):
    candidate_id: str
    row_id: int
    vendor_id: Optional[int]
    canonical_domain: str
    discovery_mode: str
    source_provider: str
    confidence: float
    completeness_score: float
    trust_score: float
    payload: dict
    status: str  # queued, processing, complete, failed
    retry_count: int
    next_attempt_at: Optional[datetime]
```

## 10.7 Manual sourcing escalation record

For MVP, reuse `VendorCoverageGap` as the primary persisted escalation record, with structured payload expansion.

Add or populate fields for:

```python
class ManualSourcingEscalationPayload(BaseModel):
    row_id: int
    discovery_session_id: str
    canonical_need: str
    geo_hint: Optional[str]
    discovery_mode: str
    reason: str  # insufficient_results, low_confidence, source_failures
    attempted_queries: list[str]
    attempted_adapters: list[str]
    top_candidate_summary: list[dict]
    dead_end_signature: str
```

---

## 11. Scoring Engine Design

## 11.1 Scoring location

Coverage scoring is separate from result ranking.

- `score_results()` in `apps/backend/sourcing/scorer.py` ranks results for user display.
- new `coverage.py` decides whether the internal vendor DB is strong enough.

Do not overload `score_results()` to make the sufficiency decision.

## 11.2 Coverage score formula

Use the PRD weights exactly in v1:

```text
score =
  semantic_fit * 0.30 +
  geography_fit * 0.20 +
  specialization_fit * 0.15 +
  source_credibility * 0.15 +
  contactability * 0.10 +
  freshness * 0.05 +
  luxury_fit * 0.10 when relevant
  - duplicate_penalty
```

When `luxury_fit` is not relevant:

- redistribute its weight to `semantic_fit` and `specialization_fit`

## 11.3 Dimension inputs

| Dimension | Internal DB evidence | Discovered evidence |
| --- | --- | --- |
| semantic_fit | existing relevance score, vector similarity, title/category overlap | title/snippet/domain overlap, classifier assist if needed |
| geography_fit | `location_match`, `geo_distance_miles`, `store_geo_location` | extracted location hint, resolved geo, official service-area text |
| luxury_fit | vendor description, specialties, category, brand language, existing trust metadata | site copy, snippet, brand terms, model assist if ambiguous |
| contactability | vendor email/phone/site present | first-party email/phone/contact page extracted |
| specialization_fit | vendor category, specialties, description | site text, source category, model assist if weak |
| freshness | vendor updated_at, active site, recent listing signal | crawl success, active contact paths, recent snippet/date cues |
| source_credibility | verified vendor, official site, domain quality | official site, listing type, directory penalty, trust heuristics |
| duplicate_penalty | canonical domain duplicates | duplicate domain, aggregator/list page, same vendor via multiple adapters |

## 11.4 Missing-signal fallback

Default fallback scores:

- missing semantic evidence: `0.35`
- missing geography evidence when location matters: `0.20`
- missing contactability: `0.15`
- missing freshness: `0.40`
- missing luxury fit when relevant and ambiguous: invoke model assist once; else `0.30`
- missing source credibility: `0.30`

If critical required evidence is missing:

- mark `missing_signals`
- keep candidate eligible for streaming if `total_score >= 0.45`
- do not persist if persistence guardrails fail

## 11.5 Model-assisted classification

Model assist is allowed only for:

- luxury/exclusivity fit
- specialization fit when heuristics are weak
- source credibility for ambiguous pages

Model assist should:

- return bounded JSON
- never override deterministic hard negatives
- be logged as a separate signal in score debug output

Hard negatives always win:

- wrong geography for location-sensitive request
- obvious aggregator/list page where official site exists
- duplicate domain already represented by a stronger candidate

## 11.6 Sufficiency evaluation

After scoring internal vendor results:

- sufficient:
  - at least 3 results with `total_score >= 0.75`
  - and for high-value/location-sensitive requests at least 2 with `total_score >= 0.80`
- borderline:
  - 2 results with `total_score >= 0.75`
  - or 4 results with `total_score >= 0.65`
- insufficient:
  - anything below borderline
  - or top results dominated by duplicates, aggregators, wrong geography, or wrong specialization

## 11.7 Score logging

Every vendor-discovery-path request should log:

- request classification
- top internal candidate scores
- sufficiency classification
- reason codes
- whether discovery was triggered

Add structured log event:

- `event = "vendor_coverage_evaluated"`

---

## 12. Discovery Mode and Source Strategy

## 12.1 Discovery mode selector

Add `select_discovery_mode(search_intent, row)`:

- `local_service_discovery`
- `destination_service_discovery`
- `luxury_brokerage_discovery`
- `uhnw_goods_discovery`
- `advisory_discovery`
- `asset_market_discovery`

Mode selection should use:

- `desire_tier`
- `service_category`
- `location_context.relevance`
- key terms in `raw_input`, `product_name`, and `features`

## 12.2 Adapter stack by mode

| Discovery mode | Primary adapters | Secondary adapters |
| --- | --- | --- |
| local_service_discovery | maps/business listings, official-site organic search | curated local directories |
| destination_service_discovery | official venue/operator sites, destination management search | niche travel/luxury directories |
| luxury_brokerage_discovery | official brokerage sites, agent/team sites | luxury property directories as lead sources |
| uhnw_goods_discovery | official dealers, auction houses, recognized specialty marketplaces | authorized distributor listings |
| advisory_discovery | official firm sites, credential/membership directories | niche professional listings |
| asset_market_discovery | official broker/dealer sites, recognized market platforms | manufacturer-adjacent sources |

Do not implement one generic discovery stack and call it complete.

## 12.3 Query planning

Add `build_discovery_queries(search_intent, mode)`:

- 3 to 6 query variants max
- include location terms when relevant
- include tier terms when relevant:
  - `luxury`
  - `boutique`
  - `broker`
  - `authorized dealer`
  - `auction`
- avoid over-expanding with every feature in the request

Example:

```text
"sell luxury estate nashville"
-> "nashville luxury real estate agent"
-> "nashville boutique luxury real estate brokerage"
-> "nashville estate listing specialist"
```

## 12.4 Adapter implementation assumptions

MVP adapters are server-side only.

Allowed implementation modes:

- third-party search APIs for organic/maps/business discovery where available
- direct server-side HTTP fetch/scrape of official sites or directory pages returned by those searches
- internal proxy layers where needed for auth, retry, or secret handling

Disallowed in MVP:

- client-browser-mediated discovery
- browser automation as the default discovery path
- uncontrolled scraping without adapter-level timeout and rate-limit handling

Operational preference order:

1. API-backed discovery where practical
2. targeted server-side HTML fetch for returned URLs
3. directory extraction only as a lead source, never as the primary trust anchor

---

## 13. Discovery Adapter Interface

## 13.1 Adapter protocol

```python
class DiscoveryAdapter(Protocol):
    adapter_id: str
    source_type: str
    supported_modes: set[str]

    async def search(
        self,
        query: str,
        *,
        row_id: int,
        discovery_mode: str,
        timeout_seconds: float,
        max_results: int,
    ) -> DiscoveryBatch: ...
```

```python
class DiscoveryBatch(BaseModel):
    adapter_id: str
    query: str
    results: list[DiscoveredVendorCandidate]
    status: str  # ok, timeout, error, exhausted, rate_limited
    latency_ms: int
    error_message: Optional[str]
```

## 13.2 Adapter responsibilities

- execute the source call
- return raw payload plus basic canonicalization
- extract canonical domain when possible
- record provenance:
  - adapter id
  - source url
  - listing type
  - rank in source
  - raw snippet/title

## 13.3 Rate limits, retries, and timeouts

Per adapter:

- timeout: 3 to 5 seconds default
- retry at most once on transport failure
- no retry on clear 4xx auth/config errors
- enforce bounded concurrency per request

## 13.4 Canonicalization rules

- normalize URL scheme
- strip tracking params where safe
- extract canonical domain
- prefer official-site URL over directory URL when both are known
- mark directory pages explicitly as `source_type = directory`

---

## 14. Deduplication and Merge Logic

This is a first-class subsystem, not an incidental filter.

## 14.1 Deduplication order

Run dedupe in this order:

1. exact canonical domain match
2. exact normalized website URL match
3. existing `Vendor.domain` match
4. same vendor name + same geography
5. directory page pointing to already-known official site

## 14.2 Canonical identity key

Use:

```text
canonical_identity = canonical_domain if present
else normalized_official_url
else normalized_vendor_name + normalized_geo_hint
```

## 14.3 Merge preference rules

When duplicates exist:

1. existing internal DB vendor wins over newly discovered duplicate
2. official site wins over directory/listing page
3. candidate with first-party contact info wins
4. higher trust score wins
5. richer media/contact payload is merged into surviving record

Name-collision rule:

- same-name same-geo is only a suggestive match
- it is not authoritative unless reinforced by domain, contact info, or explicit official-site linkage
- vanity domains, affiliate teams, and multi-office luxury brands must not be collapsed on name alone

## 14.4 Suppression behavior

- suppressed duplicates should not be shown as separate UI cards
- suppressed duplicates should still be logged for analytics
- merged provenance should record suppressed source ids

## 14.5 Current-store compatibility

Frontend store already dedupes by `bid_id` and then `url`.

Backend must not rely on frontend dedupe as the primary safeguard.

Backend should emit already-deduped result batches so:

- ordering remains stable
- official-site preference is enforced
- internal/discovered duplicate collisions are resolved before UI

---

## 15. Result Normalization

## 15.1 Canonical result target

Discovered vendors must normalize into `NormalizedResult` so they can flow through the existing persistence and display stack.

Required normalized fields:

- `title`
- `url`
- `canonical_url`
- `source`
- `merchant_name`
- `merchant_domain`
- `image_url`
- `raw_data`
- `provenance`

For service/vendor discovery:

- `price = null`
- `currency = "USD"`
- `rating` and `reviews_count` optional
- contact info stored in `raw_data` and copied into downstream persistence

## 15.2 Source naming

Use stable source ids:

- `vendor_directory`
- `vendor_discovery_google_organic`
- `vendor_discovery_google_maps`
- `vendor_discovery_directory`

Avoid anonymous generic source names like `search`.

---

## 16. Streaming and Frontend Behavior

## 16.1 Transport

Reuse `/rows/{row_id}/search/stream` and the existing SSE handling in `Chat.tsx`.

Do not create a parallel websocket or polling stack in MVP.

## 16.2 Event format

Continue using `search_results` events. Add:

- `phase`
- `coverage_status`
- `discovery_session_id`
- `suppressed_count`

This minimizes frontend churn because `Chat.tsx` already appends results and respects `more_incoming`.

## 16.3 Update cadence

- emit one event per completed internal/discovery batch
- do not emit per-candidate singleton events unless a source only returns one candidate
- final event must include `more_incoming = false`

## 16.4 Loading states

Use current store behavior:

- `setMoreResultsIncoming(rowId, true)` when discovery starts
- `appendRowResults()` for incoming batches
- `setIsSearching(false)` only on final completion event
- keep streaming lock semantics intact

## 16.5 Ordering and reranking

During discovery:

- internal strong results stay visible
- new discovered results are reranked against current results before each emitted batch
- reordering is allowed only at batch boundaries, not every single candidate

## 16.6 Provenance labeling

The UI should remain unified, but provenance should be available:

- existing internal vendor
- newly sourced vendor
- discovered from official site
- discovered from directory lead

In MVP, this can remain subtle metadata rather than a new visible badge system.

## 16.7 Duplicate suppression behavior

If a candidate is merged/suppressed:

- do not emit a second card
- if richer data arrives for an existing result, emit an update through the next batch or final authoritative reload

---

## 17. Persistence and Enrichment

## 17.1 Persistence policy

There are three levels:

- transient candidate
  - may stream to the UI
  - not persisted
- persisted candidate
  - passes persistence threshold of `total_score >= 0.65`
  - saved to `DiscoveredVendorCandidate`
- promoted vendor
  - candidate is strong enough to create or enrich a `Vendor`
  - may also create a row-visible `Bid`

Important guardrail:

- `DiscoveredVendorCandidate` is not the same thing as `Vendor`
- streaming visibility is not the same thing as canonical promotion
- the system must default to preserving uncertainty rather than eagerly creating canonical `Vendor` rows

## 17.2 Row-visible persistence

For strong discovered vendors:

- stream results immediately regardless of persistence
- persist `DiscoveredVendorCandidate` first
- only create a row-visible `Bid` in-request if one of these is true:
  - the candidate matches an existing `Vendor` by canonical domain
  - the candidate passes promotion-lite guardrails:
    - `total_score >= 0.80`
    - `official_site = true`
    - `first_party_contact = true` or explicit contact page exists
    - not suppressed as duplicate
    - canonical domain is valid

Additional high-risk rule:

- for luxury brokerage, advisory, aircraft/yacht/asset-market, and other high-value discovery modes, new canonical vendor promotion must default to post-enrichment only
- in those modes, in-request persistence may still create a row-visible `Bid` from a persisted candidate, but should not create a new canonical `Vendor` row unless it is enriching an already-known vendor by exact domain match

Default rule:

- do not create a new canonical `Vendor` row synchronously during request handling
- in-request canonical `Vendor` creation is allowed only for exact-match enrichment of an already-known vendor or an explicitly approved future phase

This keeps the current row UI reusable without turning the canonical vendor table into a landfill.

## 17.3 Candidate table

`DiscoveredVendorCandidate` should store:

- raw source payload
- extraction payload
- canonical domain
- trust metadata
- request linkage
- enrichment status
- dedupe linkage to `Vendor` if one exists

## 17.4 Enrichment queue

Persist queue items only when:

- candidate score >= 0.65
- completeness guardrails pass
- canonical domain is valid
- candidate is not a suppressed duplicate

Promotion from `DiscoveredVendorCandidate` to canonical `Vendor` should happen asynchronously after enrichment, not by default in the user request path.

Queue destination:

- `VendorEnrichmentQueueItem`

Downstream worker can later:

- crawl official site
- normalize contact/location
- geocode
- generate embeddings
- generate search vector
- upgrade vendor trust metadata

## 17.5 Idempotency

Idempotency keys:

- candidate persistence: `row_id + canonical_domain + discovery_session_id`
- enrichment queue: `candidate_id`
- vendor promotion: `canonical_domain`

## 17.6 Retry behavior

- candidate persistence: retry once in-request; then log and continue streaming
- enrichment queue worker: exponential backoff up to 5 attempts
- vendor promotion failure must not break user-visible results

---

## 18. Escalation Design

## 18.1 Escalation trigger

Escalate only when:

- final discovery coverage remains insufficient
- or all sources fail / rate limit out
- or clarification is still unresolved after guardrails are exhausted

## 18.2 Escalation outputs

Produce all of these:

- update/create `VendorCoverageGap`
- mark dead-end archetype signature
- persist attempted queries and adapters
- include top weak candidates for analyst context

## 18.3 Ops review compatibility

The current `VendorCoverageGap` admin flow remains the MVP review surface.

Do not build a second ops escalation table unless `VendorCoverageGap` proves structurally insufficient.

---

## 19. Async Boundaries

## 19.1 Must happen in-request

- request classification
- internal vendor retrieval
- strict coverage scoring
- sufficient/borderline/insufficient branch decision
- first-pass discovery kickoff when required
- SSE emission of internal results and discovery batches
- persistence of qualifying `DiscoveredVendorCandidate` rows

## 19.2 May happen post-response

- enrichment queue processing
- canonical `Vendor` promotion
- embedding generation
- search-vector generation
- geocoding/contact cleanup beyond the minimal request-time path
- ops reporting email/digest generation

## 19.3 Best-effort only

- additional low-priority source fan-out after the user already has good results
- secondary trust enrichment
- noncritical thumbnail/logo improvements
- analyst-friendly summary generation beyond required escalation payloads

Latency rule:

- the user flow should complete and stream usable results without waiting for post-response enrichment or canonical promotion

---

## 20. Observability

Extend `apps/backend/sourcing/metrics.py` with discovery-specific metrics.

## 20.1 Required structured events

- `vendor_discovery_classified`
- `vendor_coverage_evaluated`
- `vendor_discovery_started`
- `vendor_discovery_adapter_complete`
- `vendor_discovery_candidate_persisted`
- `vendor_discovery_escalated`

## 20.2 Required counters/gauges

- discovery trigger rate
- sufficiency classifications by mode
- false-positive discovery rate
- false-negative sufficiency rate
- clarification rate
- discovery source yield by mode
- candidate persistence rate
- duplicate suppression rate
- escalation volume
- dead-end category/geography signatures

## 20.3 Debug logging

For every vendor discovery request, log:

- classifier output
- discovery mode
- top internal vendor scores
- sufficiency decision
- adapters selected
- queries attempted
- number of raw results
- number normalized
- number suppressed
- number persisted

## 20.4 Audit bundle

Every discovery session must have one stable `discovery_session_id`.

That id ties together:

- classification decision
- sufficiency score output
- adapter calls and statuses
- suppression/merge decisions
- persistence decisions
- escalation output if any

MVP auditability requirement:

- emit structured logs for every step using the same `discovery_session_id`
- persist a final summary bundle for escalated sessions and persisted candidates

Minimum final audit summary fields:

- why discovery triggered
- why each top candidate survived, was suppressed, or was merged
- why a candidate persisted or did not persist
- why escalation did or did not happen

This must be searchable by `row_id` and `discovery_session_id`.

---

## 21. Operational Constraints

## 21.1 Latency budgets

- internal vendor sufficiency pass: target p95 <= 1.5s after request enters search
- first streamed discovery batch: target p95 <= 4s after insufficient/borderline decision
- total discovery window per request: soft cap 15s

## 21.2 Clarification limits

- max 2 clarifying questions before discovery starts
- max 1 blocking clarification at a time

## 21.3 Source fan-out

- max 3 adapters concurrently in MVP
- max 6 query variants per request

## 21.4 Fail-soft behavior

If discovery sources fail:

- keep internal results visible if any
- emit status messaging
- persist coverage gap
- do not blank the row or return an empty replace unless there were truly no usable results

---

## 22. Rollout Plan

## Phase 1: Internal sufficiency scoring

- add `coverage.py`
- run strict internal vendor sufficiency evaluation
- shadow-log decisions without discovery

## Phase 2: Discovery orchestrator in shadow mode

- adapter fan-out runs
- no user-visible streaming yet
- compare discovered candidates to escalated gaps

## Phase 3: User-visible streaming

- emit discovered vendor batches through existing SSE path
- preserve current store semantics

## Phase 4: Persistence and enrichment

- persist strong candidates
- queue for enrichment
- promote canonical vendors only after enrichment and promotion guardrails pass

## Phase 5: Ops and quality tuning

- improve source strategy by discovery mode
- refine trust heuristics
- tune coverage thresholds from production data

---

## 23. Testing Requirements

Add tests for:

- classifier path selection
- strict sufficiency scoring and threshold branching
- borderline behavior
- clarification guardrails
- adapter timeout and retry behavior
- canonicalization and dedupe
- same-name same-geo but different real vendor does not collapse without domain/contact reinforcement
- official-site preference over directory results
- mixed internal/discovered ranking
- SSE payload contract
- candidate persistence thresholds
- escalation payload generation

Prefer the current testing pattern:

- backend unit tests under `apps/backend/tests`
- frontend store/SSE tests under `apps/frontend/app/tests`

---

## 24. Implementation Notes

- Reuse the current `SearchIntent` contract; do not invent a second request schema.
- Reuse `NormalizedResult` as the display/persistence boundary.
- Reuse SSE and the row store rather than adding a new client transport.
- Reuse `VendorCoverageGap` for ops escalation in MVP.
- Factor code out of `scripts/discover_vendors.py` only where it is truly reusable for request-time discovery. Do not call the batch script directly from live search.
- Keep synchronous writes to canonical `Vendor` rows behind explicit promotion guardrails; candidate persistence is the default, canonical promotion is the later step.
- Do not reopen product questions already settled by the PRD. The core build work is orchestration, scoring mechanics, adapters, dedupe, persistence, and instrumentation.

---

## 25. Final Build Decision

The system should be implemented as a strict extension of the current BuyAnything stack:

- classify the request
- run internal vendor DB search first
- score sufficiency strictly
- only then branch into live vendor discovery
- normalize, dedupe, rerank, stream, persist, and escalate using the same row-centered architecture

This keeps the current product surface intact while turning missing supply into a repeatable fulfillment, learning, and asset-building loop.
