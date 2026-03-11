# Luxury Sourcing Engine — Technical Specification

## 1. Purpose

This document defines the technical design for the Luxury Sourcing Engine, a source-first discovery system for executive assistants, chiefs of staff, concierge operators, and family office teams.

The system converts vague, high-variance sourcing requests into structured briefs, orchestrates multi-strategy discovery, extracts candidate entities from the web and memory, ranks them with a hybrid scoring model, and streams results back progressively.

This spec assumes the Luxury Sourcing Engine sits behind a front-door routing layer defined in `docs/active-dev/PRD-BuyAnything-Request-Triage-and-Fulfillment-Routing.md`. The sourcing engine is not the universal entry point for every BuyAnything request. It is one execution path selected when the request requires source-first discovery.

This spec also assumes trust instrumentation and learning-loop requirements from `docs/active-dev/PRD-BuyAnything-Trust-Metrics-and-Learning-Loop.md`. Those requirements should be integrated in a way that preserves the existing affiliate query constructors and affiliate-link generation pipeline rather than replacing them.

This spec expands the product PRD into an implementation-ready technical design against the proposed stack:

- **Backend:** FastAPI, Python, SQLAlchemy 2.x, PostgreSQL, Redis
- **Frontend:** Next.js 15, React, Zustand, Tailwind
- **AI/LLM:** OpenAI / OpenRouter with structured outputs
- **Transport:** SSE for progressive streaming, standard REST for CRUD
- **Search:** External search providers plus internal memory retrieval
- **Affiliate providers:** Amazon, eBay, Kayak, Kroger, Walmart
- **Async execution:** background worker pattern for non-blocking research jobs

---

## 2. Technical Goals

### 2.1 Primary goals

1. Accept freeform user requests and normalize them into structured briefs.
2. Run multiple discovery strategies in parallel without blocking the user interface.
3. Reduce token cost by filtering aggressively before LLM extraction.
4. Rank results using a hybrid model that does not rely exclusively on LLM judgment.
5. Preserve all useful research artifacts for reuse, auditing, and team memory.
6. Support progressive UX via streaming partial results as soon as they are useful.
7. Generalize across categories without building one-off hardcoded vertical workflows.
8. Route affiliate-covered commodity requests into the cheapest viable provider path before invoking sourcing.

### 2.2 Non-goals

1. Full end-to-end checkout for all categories.
2. Perfect automated verification for every niche in v1.
3. Hard dependency on one search provider.
4. Deep category-specific parsers for every long-tail luxury vertical.
5. Treating affiliate provider adapters and discovery/source adapters as interchangeable systems.

---

## 3. Architectural Principles

1. **Source-first architecture**  
   The system discovers and ranks source ecosystems before overfitting to object schemas.

2. **Asynchronous orchestration**  
   Requests must not block on long discovery or extraction steps.

3. **Filter early, extract late**  
   Use cheap deterministic pruning before expensive LLM passes.

4. **Hybrid scoring**  
   Deterministic trust and operational signals must anchor ranking.

5. **Progressive disclosure**  
   The UI should show structured brief, search progress, and candidates incrementally.

6. **Auditability**  
   Every surfaced recommendation should have a traceable reason stack.

7. **Extensibility**  
   New search adapters, extraction rules, ranking features, and source types should plug in cleanly.

8. **Route before research**  
   Choose the cheapest viable fulfillment path before invoking the expensive sourcing pipeline.

---

## 4. System Context

### 4.1 User flow

1. User submits a freeform request.
2. Backend performs request triage and creates a fulfillment plan.
3. Backend creates a research job and, when required, a structured brief.
4. Affiliate adapters and/or discovery strategies execute depending on the selected mode.
5. Search adapters collect candidate URLs/snippets for sourcing requests.
6. Gating/filtering removes low-value pages.
7. Remaining pages are fetched, parsed, chunked, and optionally extracted via LLM.
8. Candidate entities are normalized and scored.
9. Top results stream back progressively with provenance.
10. Research artifacts persist for later reuse.
11. User can annotate, save, export, or mark outcomes.

### 4.2 High-level components

- Request API
- Request Triage / Fulfillment Router
- Job Orchestrator
- Brief Structuring Service
- Query Strategy Engine
- Affiliate Adapter Layer
- Discovery / Source Adapter Layer
- URL/Content Gating Layer
- Page Fetch + Content Normalization Layer
- Entity Extraction Layer
- Ranking Engine
- Persistence Layer
- SSE Event Stream Layer
- Memory/Feedback Layer
- Admin/Observability Layer

---

## 5. Proposed Runtime Architecture

### 5.1 Backend services

#### API service (FastAPI)
Responsibilities:
- request intake
- front-door routing trigger
- CRUD for requests, briefs, candidates, notes
- SSE streaming endpoint
- auth/session enforcement
- admin endpoints

#### Routing service
Responsibilities:
- classify request domain
- choose execution mode
- select affiliate providers
- determine whether sourcing should be invoked
- emit routing reason codes

#### Orchestrator service
Responsibilities:
- break research into stages
- enqueue work units
- coordinate retries/timeouts
- publish stream events
- track state transitions

#### Worker service
Responsibilities:
- run affiliate adapters when execution mode includes affiliate retrieval
- run discovery/source adapters when execution mode includes sourcing
- fetch/parse pages
- run extraction
- compute ranking features
- persist intermediate artifacts

#### Memory service
Responsibilities:
- source history lookup
- domain trust retrieval
- prior successful query pattern retrieval
- feedback aggregation

### 5.2 Infra dependencies

#### PostgreSQL
System of record for:
- requests
- fulfillment plans
- briefs
- research jobs
- candidates
- source memory
- feedback
- research logs (lightweight)

#### Redis
Recommended for:
- job queue state
- pub/sub for stream fanout
- short-lived caching of search results/snippets
- short-lived caching of affiliate provider results
- rate-limit counters
- dedupe keys

#### Object storage (optional but recommended)
Used for:
- raw page snapshots
- cleaned markdown/text blobs
- export artifacts
- large structured extraction payloads

---

## 6. Backend Execution Model

### 6.1 Why background jobs are needed

SSE alone is not an execution model. It is only a transport mechanism.

Because discovery may take 10–90 seconds depending on the request and provider latency, the backend should treat each request as a **research job**. The API initiates the job, and workers perform the heavy lifting asynchronously.

The first decision is not how to search. The first decision is whether this request should use:

- `affiliate_only`
- `sourcing_only`
- `affiliate_plus_sourcing`

Recommended pattern:
- API creates `research_job`
- Worker consumes job and updates stage/status
- API SSE endpoint streams events from persisted state and/or Redis pub/sub

This avoids tying long work directly to one request thread.

### 6.2 Job stages

1. `queued`
2. `routing`
3. `structuring`
4. `planning`
5. `affiliate_searching`
6. `searching`
7. `gating`
8. `fetching`
9. `extracting`
10. `ranking`
11. `completed`
12. `failed`
13. `cancelled`

### 6.3 Retry policy

- Search adapter transient errors: retry up to 2 times with jittered backoff
- Page fetch timeout: retry once if domain not marked flaky
- LLM structured extraction: retry once with fallback prompt/model
- Stream publish failure: non-fatal if persisted event store exists

---

## 7. Detailed Pipeline Design

## 7.0 Stage 0 — Request Triage & Fulfillment Routing

### Goal
Decide whether the request should run through affiliate providers, the sourcing engine, or both.

### Inputs
- raw request text
- optional structured inputs from UI
- user/workspace context if available

### Outputs
- fulfillment plan
- classified domain
- execution mode
- chosen affiliate providers
- routing reason codes

### Execution modes
- `affiliate_only`
- `sourcing_only`
- `affiliate_plus_sourcing`

### Example domain buckets
- `commodity_product`
- `grocery`
- `travel`
- `marketplace_product`
- `service_or_specialist`
- `luxury_or_high_touch`
- `mixed_or_ambiguous`

### Router responsibilities
- detect whether the ask is catalog-searchable
- detect whether the ask is service- or relationship-driven
- determine whether prestige/discretion/specialist sourcing is required
- choose affiliate providers when applicable
- decide whether sourcing should run in parallel

### Output schema

```python
class FulfillmentPlanSchema(BaseModel):
    classified_domain: str
    execution_mode: Literal[
        "affiliate_only",
        "sourcing_only",
        "affiliate_plus_sourcing",
    ]
    affiliate_providers: list[str] = Field(default_factory=list)
    invoke_sourcing_engine: bool = False
    reason_codes: list[str] = Field(default_factory=list)
```

### Notes
- This stage should be cheap and fast.
- It should avoid invoking the sourcing engine for obvious commodity requests.
- It should preserve hybrid mode for mixed requests.

## 7.1 Stage 1 — Intake & Brief Structuring

### Inputs
- raw request text
- optional user-entered fields: budget, geography, deadline, discretion, prestige, category hint
- user/team context if available
- fulfillment plan from Stage 0

### Outputs
- structured brief
- candidate interpretations
- source archetype hints
- search strategy suggestions

### Responsibilities
- normalize request into `thing | person | place | experience | access`
- infer desired action (`buy`, `hire`, `book`, `compare`, `verify`, `shortlist`)
- identify hard constraints vs soft preferences
- infer likely missing variables
- generate first-pass ambiguity notes

### Implementation notes
- Use structured output schema with Pydantic
- Keep model/token budget light here
- This step should complete within ~1–3 seconds in normal conditions
- This stage should be skipped or minimized when the router selects `affiliate_only`

### Example structured brief schema

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class BudgetRange(BaseModel):
    low: Optional[float] = None
    high: Optional[float] = None
    currency: Optional[str] = "USD"

class StructuredBriefSchema(BaseModel):
    normalized_object: str
    request_type: Literal["thing", "person", "place", "experience", "access"]
    action_type: Literal["buy", "hire", "book", "locate", "compare", "verify", "shortlist"]
    geography: Optional[str] = None
    budget: Optional[BudgetRange] = None
    prestige_level: Optional[Literal["low", "medium", "high", "ultra"]] = None
    urgency: Optional[Literal["low", "medium", "high", "immediate"]] = None
    hard_constraints: dict = Field(default_factory=dict)
    soft_preferences: dict = Field(default_factory=dict)
    interpretations: list[str] = Field(default_factory=list)
    source_archetypes: list[str] = Field(default_factory=list)
    strategy_hints: list[str] = Field(default_factory=list)
```

---

## 7.2 Stage 2 — Strategy & Query Planning

### Goal
Create multiple search paths rather than one literal query.

This stage applies only when the routing layer selects `sourcing_only` or `affiliate_plus_sourcing`.

### Query families
Each request should generate 3–8 candidate query families, for example:
- direct intent
- official/institutional
- specialist/broker
- prestige/editorial
- local/regional
- alternative terminology
- verification-specific

### Strategy selection
Possible strategies:
- official-first
- market-first
- specialist-first
- prestige-first
- local-network-first
- hybrid

### Output objects
- list of search plans
- provider routing decisions
- priority order

### Example internal schema

```python
class QueryPlan(BaseModel):
    family_type: str
    query_text: str
    provider_priority: list[str]
    expected_source_types: list[str]
    weight: float = 1.0
```

### Notes
- Query planning should incorporate synonyms and alternate naming conventions
- Avoid sending all queries to all providers indiscriminately
- Enforce per-request provider budgets to control cost and rate limits

---

## 7.3 Stage 3 — Discovery via Search Adapters

### Responsibilities
- call search providers in parallel
- normalize results into a common result model
- dedupe identical or near-identical URLs
- attach provider metadata

### Important distinction
These adapters are discovery/source adapters, not affiliate provider adapters.

They should be kept separate from:
- Amazon
- eBay
- Kayak
- Kroger
- Walmart

### Adapter interface
Each provider adapter should implement a consistent interface.

```python
from typing import Protocol

class SearchAdapter(Protocol):
    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        ...
```

### Normalized search result model

```python
class SearchResult(BaseModel):
    provider: str
    query: str
    title: str
    url: str
    snippet: str | None = None
    rank: int
    domain: str
```

### Discovery rules
- parallelize by provider and query family
- cap total raw URLs per request to avoid explosion
- dedupe by canonical URL and normalized domain path
- persist raw results for observability/debugging

### Recommended provider abstraction
Support at least:
- Tavily adapter
- SerpApi adapter
- Apify adapter (dynamic Actor discovery — see below)
- fallback search adapter
- internal memory adapter

### Apify dynamic Actor discovery

Apify provides ~2000+ prebuilt web scrapers ("Actors") for structured data from Google Maps, Instagram, TripAdvisor, Yelp, LinkedIn, and other sources. Instead of hardcoding which Actors to use, the system discovers them dynamically at runtime:

1. **LLM generates store search terms** — Given the intent, the LLM outputs 1–2 short terms (e.g., "google maps scraper", "tripadvisor reviews") or an empty list for commodity queries.
2. **Apify Store API search** — `GET /v2/store?search=...&sortBy=popularity` returns Actor metadata.
3. **LLM picks and parameterizes 0–2 Actors** — From the live results, the LLM selects Actors and fills in `run_input` parameters.
4. **Generic adapter executes** — Runs the selected Actor(s) and normalizes output via known normalizers (Google Maps, Instagram, TripAdvisor, website content) or a generic best-effort normalizer. When multiple Actors are selected, the orchestrator executes them concurrently.
5. **Standard pipeline** — Apify results flow through the same dedupe → classify → gate → rerank → normalize pipeline as organic results.

Apify is a discovery/source adapter, not an affiliate adapter. It must not run for `affiliate_only` execution mode. It degrades gracefully if `APIFY_API_TOKEN` is missing or the Store API is down.

---

## 7.4 Stage 4 — Pre-Extraction Gating

### Goal
Avoid spending LLM tokens on pages that are unlikely to help.

### Pass 1 — Zero-token gating
Signals:
- blocklisted domains
- unsupported content types
- duplicated URL patterns
- obvious mismatch in snippet/title
- low lexical overlap with brief terms
- low-trust domain and no compensating signals

### Pass 2 — Lightweight content gating
- fetch HTML
- extract plain text / markdown
- compute lexical density / semantic keyword overlap
- inspect entity hints such as location, category terms, role titles, price clues
- optionally use a tiny model/classifier if needed later

### Gating outputs
- `accepted`
- `rejected`
- `borderline`

### Acceptance heuristics
Examples:
- exact geography mention
- entity-role terms present
- contact/info density above threshold
- category-specific prestige markers present
- source memory score above threshold

### Design note
This gating layer is one of the most important cost-control levers in the system.

---

## 7.5 Stage 5 — Fetch, Parse, Normalize Content

### Responsibilities
- fetch accepted URLs
- follow a safe redirect policy
- normalize HTML to markdown/plain text
- extract metadata
- detect page type
- chunk content for extraction

### Libraries
- `httpx` for async fetch
- `readability-lxml` or equivalent for content extraction
- `BeautifulSoup` / `selectolax` for parsing
- optional markdown conversion utility

### Page types
- profile page
- listing page
- directory page
- article/editorial page
- homepage/service page
- search results page
- PDF or document page

### Metadata to capture
- final URL
- canonical URL
- title
- meta description
- visible contact info
- location strings
- timestamp clues
- page type guess
- fetch latency
- response code

### Storage
Store cleaned content in object storage or a large-text table depending on scale.

---

## 7.6 Stage 6 — Structured Entity Extraction

### Goal
Convert page content into candidate entities and evidence.

### Extraction outputs
- entity name
- entity type
- organization
- location
- contact info
- pricing clues
- credentials / awards / prestige markers
- fit assessment
- evidence excerpts
- verification requirements
- extraction confidence

### Suggested extraction design
1. Page classification pass (cheap if not already known)
2. Entity extraction pass for accepted content
3. Optional cross-page merge pass for duplicate entities

### Pydantic schema

```python
class ExtractedEntity(BaseModel):
    name: str
    entity_type: str
    organization: str | None = None
    location: str | None = None
    contact: dict = Field(default_factory=dict)
    pricing: dict = Field(default_factory=dict)
    credentials: list[str] = Field(default_factory=list)
    prestige_signals: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    verification_needed: list[str] = Field(default_factory=list)
    match_confidence: float = 0.0
```

### Important rule
LLM extraction may identify claims and confidence, but it must not invent verification state or trust score. Those are computed separately.

---

## 7.7 Stage 7 — Candidate Consolidation

### Problem
The same person, broker, program, or item may appear across multiple pages and providers.

### Responsibilities
- merge duplicate entities
- union evidence and contact data
- maintain source provenance
- preserve multiple URLs per candidate

### Matching keys
- normalized name
- normalized organization
- geography
- phone/email match
- website/domain match
- optional semantic similarity threshold

### Output
A unified candidate record with linked evidence and provenance.

---

## 7.8 Stage 8 — Hybrid Ranking

### Ranking principle
Source trust and operational signals should anchor the ranking, while LLM semantic fit adds nuance.

In `affiliate_plus_sourcing` mode, preserve affiliate-provider and sourcing provenance through ranking and presentation.

Do not treat affiliate and sourced candidates as indistinguishable internally. Their origin, confidence, actionability, and verification state must remain available to ranking logic and UI rendering.

The frontend may present these results as a unified ranked list or as separate sections depending on the UX, but provenance must remain explicit and inspectable.

### Score components

#### A. Source trust score
Deterministic score derived from:
- source type tier
- memory history
- domain quality tier
- transparency/contact quality
- freshness clues

#### B. Match score
Combination of:
- lexical match to constraints
- LLM semantic fit
- geography fit
- budget fit
- role/category fit

#### C. Evidence density score
- amount of extractable information
- contact completeness
- number of corroborating mentions
- number of supporting evidence snippets

#### D. Actionability score
- direct contact path exists
- explicit service/listing fit
- current availability clues
- low friction next step

#### E. Penalties
- missing contact information
- stale page indicators
- excessive verification burden
- duplicate/redundant candidate
- mismatch between prestige need and source tier

### Example scoring formula

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

### Explainability requirement
Every candidate must store `why_selected` as structured reasons, for example:
- matched Nashville geography
- repeated across 3 trusted domains
- luxury-specific positioning language found
- direct seller representation contact present
- strong local brokerage affiliation

---

## 7.9 Stage 9 — Verification Classification

### Goal
Clearly separate what is discovered from what is verified.

### Verification states
- `unverified`
- `source_evidenced`
- `cross_source_consistent`
- `externally_confirmed`

### Examples of verification-needed fields
- current availability not confirmed
- credentials not confirmed externally
- price or budget fit not confirmed
- direct client-fit conversation still needed

### Important constraint
The system should never imply “verified” unless the evidence type justifies it.

---

## 7.10 Stage 10 — Persistence & Memory

### Persist immediately when useful
Store:
- raw request
- fulfillment plan
- structured brief
- search plans
- raw search results
- gated page decisions
- fetched content metadata
- extracted entities
- consolidated candidates
- ranking explanations
- user feedback
- outcomes

### Memory write-back
When a request completes, update source memory with:
- hit count
- surfaced count
- shortlisted count
- user-selected count
- contacted count
- outcome success signals

---

## 8. Data Model

## 8.1 Core tables

### `sourcing_requests`
Tracks the user-visible request.

Fields:
- `id` (uuid or bigint)
- `workspace_id`
- `user_id`
- `raw_text`
- `status`
- `created_at`
- `updated_at`
- `cancelled_at`
- `priority`
- `deadline_at`
- `request_metadata` (jsonb)

### `fulfillment_plans`
Tracks the front-door routing decision.

Fields:
- `id`
- `request_id`
- `classified_domain`
- `execution_mode`
- `affiliate_providers` (jsonb)
- `invoke_sourcing_engine`
- `reason_codes` (jsonb)
- `created_at`

### `structured_briefs`
Stores the normalized brief.

Fields:
- `id`
- `request_id`
- `normalized_object`
- `request_type`
- `action_type`
- `geography`
- `budget_low`
- `budget_high`
- `currency`
- `prestige_level`
- `urgency`
- `hard_constraints` (jsonb)
- `soft_preferences` (jsonb)
- `interpretations` (jsonb)
- `source_archetypes` (jsonb)
- `strategy_hints` (jsonb)
- `llm_model`
- `llm_latency_ms`

### `research_jobs`
Tracks asynchronous execution status.

Fields:
- `id`
- `request_id`
- `status`
- `stage`
- `attempt_count`
- `started_at`
- `completed_at`
- `error_code`
- `error_message`
- `worker_id`

### `query_plans`
Stores planned search queries.

Fields:
- `id`
- `request_id`
- `family_type`
- `query_text`
- `provider_priority` (jsonb)
- `expected_source_types` (jsonb)
- `weight`
- `status`

### `search_results_raw`
Raw results from providers.

Fields:
- `id`
- `request_id`
- `query_plan_id`
- `provider`
- `title`
- `url`
- `canonical_url`
- `domain`
- `snippet`
- `provider_rank`
- `dedupe_hash`
- `created_at`

This table should store discovery/source-adapter results only.

Affiliate-provider results should either live in a parallel raw results table or share a normalized result table with explicit `origin_type`.

### `page_fetches`
Tracks fetch/parse details.

Fields:
- `id`
- `request_id`
- `url`
- `canonical_url`
- `domain`
- `response_code`
- `content_type`
- `fetch_latency_ms`
- `page_type_guess`
- `gating_status`
- `gating_reasons` (jsonb)
- `content_storage_key`
- `text_length`
- `created_at`

### `candidate_entities`
Raw extracted entity-level records before consolidation.

Fields:
- `id`
- `request_id`
- `page_fetch_id`
- `name`
- `entity_type`
- `organization`
- `location`
- `contact` (jsonb)
- `pricing` (jsonb)
- `credentials` (jsonb)
- `prestige_signals` (jsonb)
- `claims` (jsonb)
- `evidence` (jsonb)
- `verification_needed` (jsonb)
- `match_confidence`
- `extraction_model`

### `candidate_groups`
Consolidated candidate entities shown to the user.

Fields:
- `id`
- `request_id`
- `display_name`
- `entity_type`
- `primary_organization`
- `primary_location`
- `merged_contact` (jsonb)
- `merged_pricing` (jsonb)
- `source_count`
- `overall_score`
- `source_trust_score`
- `match_score`
- `actionability_score`
- `verification_state`
- `why_selected` (jsonb)
- `recommended_next_action`

### `candidate_group_sources`
Join table linking groups to raw sources/entities.

Fields:
- `candidate_group_id`
- `candidate_entity_id`
- `page_fetch_id`
- `source_weight`

### `source_memory`
Persistent memory about domains and sources.

Fields:
- `id`
- `workspace_id`
- `domain`
- `source_name`
- `source_type`
- `source_subtype`
- `trust_score`
- `prestige_score`
- `success_count`
- `surface_count`
- `contact_success_count`
- `last_seen_at`
- `notes`

### `request_feedback`
User/team feedback loop.

Fields:
- `id`
- `request_id`
- `candidate_group_id`
- `user_id`
- `feedback_type`
- `score`
- `comment`
- `created_at`

### `request_events`
Append-only stream/audit events.

Fields:
- `id`
- `request_id`
- `event_type`
- `payload` (jsonb)
- `created_at`

---

## 8.2 SQLAlchemy design notes

- Prefer UUID primary keys if multi-tenant external exposure matters
- Use JSONB for flexible extraction payloads and constraints
- Add GIN indexes on selected JSONB fields if querying grows
- Use composite indexes for `workspace_id + domain`, `request_id + created_at`
- Keep raw blobs out of hot tables when possible

---

## 9. API Design

## 9.1 REST endpoints

### Create request
`POST /api/v1/sourcing/requests`

Request:
```json
{
  "raw_text": "Find the best real estate brokers in Nashville, TN to sell a $3MM mansion",
  "metadata": {
    "urgency": "high",
    "prestige": "high"
  }
}
```

Response:
```json
{
  "request_id": "req_123",
  "job_id": "job_123",
  "status": "queued"
}
```

### Get request
`GET /api/v1/sourcing/requests/{request_id}`

### List candidates
`GET /api/v1/sourcing/requests/{request_id}/candidates`

### Submit feedback
`POST /api/v1/sourcing/requests/{request_id}/feedback`

### Cancel request
`POST /api/v1/sourcing/requests/{request_id}/cancel`

---

## 9.2 SSE endpoint

### Endpoint
`GET /api/v1/sourcing/requests/{request_id}/stream`

### Event contract

#### `status_update`
```json
{
  "type": "status_update",
  "stage": "searching",
  "message": "Searching specialist and local sources"
}
```

#### `routing_decision`
```json
{
  "type": "routing_decision",
  "classified_domain": "commodity_product",
  "execution_mode": "affiliate_only",
  "affiliate_providers": ["amazon", "ebay", "walmart"],
  "reason_codes": ["catalog_searchable", "commodity_terms_detected"]
}
```

#### `brief_ready`
```json
{
  "type": "brief_ready",
  "brief": {
    "normalized_object": "real estate broker",
    "request_type": "person",
    "action_type": "hire",
    "geography": "Nashville, TN"
  }
}
```

#### `query_plan_ready`
```json
{
  "type": "query_plan_ready",
  "plans": [
    {"family_type": "specialist", "query_text": "Nashville luxury real estate broker seller"}
  ]
}
```

#### `candidate_found`
```json
{
  "type": "candidate_found",
  "candidate": {
    "id": "cand_1",
    "display_name": "Example Broker",
    "overall_score": 0.84,
    "why_selected": ["strong Nashville luxury focus", "direct contact path"],
    "verification_state": "source_evidenced"
  }
}
```

#### `complete`
```json
{
  "type": "complete",
  "request_id": "req_123",
  "candidate_count": 8
}
```

#### `error`
```json
{
  "type": "error",
  "message": "Search provider timeout",
  "recoverable": true
}
```

### SSE behavior requirements
- heartbeat every 10–15 seconds
- reconnect token or last-event-id support
- idempotent replay from `request_events` if client reconnects

---

## 10. Frontend Design

## 10.1 State management
Use Zustand store with slices such as:
- request metadata
- streaming connection state
- fulfillment plan
- structured brief
- live candidates
- research logs
- feedback state

### Suggested store shape

```ts
interface Candidate {
  id: string
  displayName: string
  overallScore: number
  whySelected: string[]
  verificationState: string
}

interface SourcingState {
  requestId?: string
  isSearching: boolean
  currentStage?: string
  statusText?: string
  fulfillmentPlan?: Record<string, unknown>
  brief?: Record<string, unknown>
  candidates: Candidate[]
  events: Array<Record<string, unknown>>
  error?: string
}
```

## 10.2 UX states

### Before search
- request input
- optional structured constraints
- saved examples

### In progress
- routing decision / selected mode
- structured brief preview
- “research in progress” dashboard
- current stage and latest source types being searched
- streaming candidate cards

### Completed
- shortlist view
- detailed operator view
- evidence / why surfaced drawer
- verification checklist
- notes / feedback actions

### Failure or partial completion
- show partial results if available
- show stage where failure occurred
- enable retry / continue search

---

## 11. Search Provider Abstraction

### Goals
- prevent lock-in
- allow provider fallback
- compare provider quality over time
- enforce budgets and rate limits

### Separation of concerns
The system must explicitly distinguish:

- **affiliate provider adapters**
  - inventory/offer-oriented
  - structured provider-specific query generation
  - monetizable clickout pathways
- **discovery/source adapters**
  - open-ended URL/domain discovery
  - specialist ecosystem exploration
  - sourcing-engine candidate generation
  - Apify dynamic Actor discovery (structured data from Google Maps, Instagram, TripAdvisor, etc.)

### Provider router rules
- each request gets a search budget
- provider choice can depend on query family
- local searches may prefer one provider, prestige/editorial another
- internal memory can be queried before or alongside external search

### Rate limiting
- per-provider rate limits
- per-workspace rate limits
- queue backpressure if budget exceeded

---

## 12. Cost Control Strategy

### 12.1 Major cost centers
- external search API volume
- page fetching/parsing
- LLM extraction and consolidation
- retries on flaky sources

### 12.2 Cost controls
1. strict cap on raw URLs per request
2. aggressive gating before extraction
3. low-cost model for structuring and page classification
4. only send top-N accepted pages to deep extraction
5. reuse cached raw results/snippets when recent enough
6. workspace-level daily budget limits
7. route commodity requests to affiliate-only mode when sourcing is unnecessary

### 12.3 Suggested defaults
- max query families: 6
- max raw URLs: 40
- max accepted pages for fetch/parse: 20
- max deep extraction pages: 8–12
- max candidate groups surfaced initially: 10
- max Apify Actors per request: 2
- max Apify results per Actor run: 10
- Apify Actor timeout: 60 seconds

---

## 13. Observability & Logging

### Metrics to capture
- intake latency
- structuring latency
- provider response latency
- fetch success rate
- extraction latency
- tokens per stage
- candidates extracted per request
- shortlist usefulness feedback
- stream disconnect rate

### Trust and outcome metrics to capture
- route selection rate by request type
- affiliate-only usefulness rate
- sourcing-only usefulness rate
- hybrid usefulness rate
- time to first useful result
- time to trusted option
- candidate save rate
- shortlist rate
- acted-on rate
- request resolution rate
- assistant override rate
- noisy result rate
- contact-readiness feedback rate
- premium-fit feedback rate
- source/domain trust trend over time

### Logs
- request/job state transitions
- provider failures
- fetch failures by domain
- extraction schema validation failures
- dedupe/consolidation outcomes
- feedback submissions
- request outcome transitions
- routing overrides and manual corrections

### Tracing
OpenTelemetry recommended for:
- request lifecycle tracing
- search provider calls
- worker stage timings
- LLM call spans
- route decision spans
- candidate feedback and outcome write-back spans

### Instrumentation requirement
Instrumentation should distinguish:

- commodity / affiliate requests
- sourcing requests
- hybrid requests

Trust analysis must not collapse these execution modes into one undifferentiated quality metric.

---

## 14. Security & Multi-Tenancy

### Requirements
- workspace isolation for requests and memory
- authenticated API endpoints
- authorization on request visibility
- encryption in transit and at rest via managed infra defaults
- audit trail for user actions and outcomes

### Sensitive data handling
Some requests may contain private lifestyle or family details. Therefore:
- avoid exposing full request text in broad internal logs
- redact secrets or unnecessary personal details from telemetry
- support configurable retention policies for raw page content and request notes
- minimize storage of sensitive freeform feedback where categorical feedback is sufficient
- ensure trust analytics can be computed without unnecessarily exposing principal-identifying details

---

## 15. Failure Modes & Fallbacks

### Common failure cases
1. search provider timeout
2. low-quality or sparse public search results
3. anti-bot or fetch-blocked pages
4. extraction schema mismatch
5. duplicate entities with conflicting info
6. stream disconnect

### Fallback strategies
- use cached prior source memory
- continue with partial result set
- retry with alternate provider
- mark candidate as low-confidence instead of failing the full job
- allow manual operator note enrichment

---

## 16. Recommended Repository Structure

```text
backend/
  app/
    api/
      v1/
        sourcing.py
    core/
      config.py
      logging.py
    db/
      base.py
      session.py
    models/
      sourcing.py
    schemas/
      sourcing.py
    services/
      sourcing/
        intake.py
        planner.py
        orchestrator.py
        ranking.py
        consolidation.py
        memory.py
        events.py
        trust_metrics.py
        feedback.py
      search/
        adapters/
          tavily.py
          serpapi.py
          apify.py
          fallback.py
        apify_selector.py
        router.py
      extraction/
        fetch.py
        normalize.py
        gating.py
        extractors.py
    workers/
      sourcing_worker.py
    utils/
      text.py
      urls.py
      dedupe.py
frontend/
  app/
    sourcing/
      page.tsx
      [requestId]/page.tsx
  components/
    sourcing/
      RequestForm.tsx
      BriefPanel.tsx
      CandidateCard.tsx
      ResearchTimeline.tsx
      VerificationChecklist.tsx
    stores/
      sourcingStore.ts
  lib/
    sse.ts
    api.ts

### Next-sprint integration note
Trust metrics should be integrated primarily through:

- event emission around existing request/routing/search flows
- request and candidate feedback capture
- source-memory write-back
- admin/internal reporting

They should not require replacing the current affiliate provider query-construction or affiliate-link generation path.

---

## 17. Implementation Plan

## Phase 1 — Core skeleton
Deliverables:
- DB models
- fulfillment plan model
- request create/read endpoints
- request triage / routing service
- structured brief generation
- research job record creation
- basic SSE stream infrastructure
- request event taxonomy for trust instrumentation

## Phase 2 — Search orchestration
Deliverables:
- query planner
- affiliate vs discovery adapter separation
- provider adapter abstraction
- Apify dynamic Actor discovery and LLM-driven selection
- normalized raw result storage
- zero-token gating
- provider-level trust instrumentation hooks

## Phase 3 — Fetch, extraction, ranking
Deliverables:
- page fetch/normalize pipeline
- extraction schemas
- candidate consolidation
- hybrid ranking v1
- streaming candidate events
- candidate action instrumentation (`shown`, `clicked`, `saved`, `dismissed`, `acted_on`)

## Phase 4 — Memory and feedback
Deliverables:
- source memory updates
- request feedback endpoints
- memory-boost ranking inputs
- request replay / prior similar results
- lightweight feedback taxonomy for requests and candidates
- trust metric aggregation jobs
- outcome write-back for successful and failed requests

## Phase 5 — Hardening
Deliverables:
- retry/backoff policies
- metrics and tracing
- rate limits and quotas
- retention controls
- admin views
- quality dashboards by route type, provider, and source domain

---

## 18. Open Engineering Decisions

1. **Worker framework choice**  
   Celery, RQ, Dramatiq, Arq, or lightweight Postgres/Redis-backed job runner.

2. **Content storage choice**  
   DB large text vs object storage for page snapshots.

3. **Optional vector retrieval**  
   Whether to embed source memory / past requests for semantic recall.

4. **Domain authority signal**  
   Whether to integrate external authority metrics or use internal heuristic tiers only.

5. **Headless browser support**  
   Whether to add Playwright later for JS-heavy domains.

6. **Trust metric storage model**  
   Whether to use append-only event rows only, aggregated rollup tables, or both.

7. **Outcome capture UX**  
   How much explicit assistant feedback should be requested versus inferred behaviorally.

---

## 19. Recommendations

### 19.1 Strong recommendations for v1
- add a front-door routing layer before sourcing
- add `research_jobs`; do not use SSE as the only long-running execution mechanism
- use Redis for pub/sub and ephemeral state even if Postgres is the source of truth
- start with deterministic source tiers instead of overcomplicated external authority APIs
- keep extraction schemas flexible with JSONB + typed top-level fields
- persist `why_selected` and `gating_reasons` as structured data from day one
- instrument trusted outcomes, not just clicks or session activity
- separate trust metrics by execution mode (`affiliate_only`, `sourcing_only`, `affiliate_plus_sourcing`)
- preserve the current affiliate query-construction and affiliate-link pipeline while adding trust instrumentation around it

### 19.2 Do not do this in v1
- do not build dozens of vertical-specific DB tables
- do not make LLMs the sole source of trust ranking
- do not block the request thread on full discovery
- do not attempt universal verification automation

---

## 20. Example: Nashville Broker Request Execution Trace

### Raw request
“Find the best real estate brokers in Nashville, TN to sell my client’s $3MM mansion.”

### System flow
1. `sourcing_request` created
2. worker enters `structuring`
3. structured brief returns:
   - request_type = person
   - action_type = hire
   - normalized_object = real estate broker
   - geography = Nashville, TN
   - budget_high context = 3000000 property value
   - prestige_level = high
4. planner creates query families:
   - specialist
   - local
   - prestige/editorial
5. search adapters return raw URLs
6. gating drops irrelevant generic pages
7. fetch/normalize accepts broker profiles, local luxury brokerage pages, editorial top-agent pages
8. extraction yields multiple broker entities
9. consolidation merges duplicates across pages
10. ranking boosts candidates with:
    - strong Nashville signals
    - seller-side positioning
    - direct contact info
    - luxury market language
11. candidate cards stream to UI
12. request completes and source memory updates

---

## 21. Conclusion

The right implementation is not a static directory and not a pure LLM agent. It is an orchestrated research pipeline with deterministic controls, structured extraction, hybrid ranking, progressive UX, and reusable institutional memory.

That combination makes the system practical, cost-aware, explainable, and extensible enough to support “find almost anything ethical” for high-expectation operators.

