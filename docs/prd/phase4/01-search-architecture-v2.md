# PRD: Search Architecture v2 Migration

**Status:** ~75% Implemented — see Implementation Status below  
**Author:** AI Assistant  
**Created:** 2026-01-29  
**Last Updated:** 2026-02-06 (gap analysis pass)  

---

## 1. Executive Summary

### 1.0 Implementation Status (as of 2026-02-06)

> **Most of this PRD is already built.** The 5-layer architecture was implemented during Phase 3.
> The remaining work is scoped under "What's Left" below.

| PRD Layer | Status | Current Code |
|-----------|--------|-------------|
| L1: Intent Extraction | ✅ Done | `apps/bff/src/intent/index.ts` — LLM + heuristic fallback |
| L2: Provider Adapters | ⚠️ Partial | `sourcing/adapters/` — Rainforest + Google CSE. **No eBay adapter.** |
| L3: Executors | ✅ Done | `sourcing/executors/base.py` — parallel with timeout/status |
| L4: Normalizers | ✅ Done | Per-provider normalization in `sourcing/repository.py` |
| L5: Aggregator/Scoring | ❌ Not built | No `combined_score`, `relevance_score`, `price_score`, `quality_score` |
| DB: SearchIntent column | ✅ Done | `Row.search_intent`, `Row.provider_query_map` |
| DB: Bid metadata | ✅ Done | `Bid.canonical_url`, `source_payload`, `normalized_at` |
| Streaming search | ✅ Done | `POST /rows/{row_id}/search/stream` SSE endpoint |
| Metrics tracking | ✅ Done | `sourcing/metrics.py` |

**What's left to build:**
1. **eBay adapter + executor** — provider referenced but not implemented
2. **Result scoring/ranking** — `combined_score` = f(relevance, price, quality) — zero scoring logic exists
3. **Currency normalization** — `NormalizedResult` has `price_original`/`currency_original` but never populated
4. **Low-confidence behavior** — PRD says "if confidence < 0.6, ask clarification" — not implemented
5. **Cleanup** — old `sourcing.py` still exists alongside new `sourcing/` package

### 1.1 Problem Statement (Original — now partially resolved)
~~The current search architecture passes a single text query string to all providers, losing structured intent.~~

**Updated problem:** The 5-layer pipeline is in place but results are **unranked** — there's no quality scoring to surface the best matches first. Additionally, eBay is not connected, currency is US-only, and ambiguous queries trigger search immediately instead of asking for clarification.

### 1.2 Solution Overview
~~Migrate to a 5-layer architecture that:~~
Complete the existing 5-layer architecture by adding:
1. ~~Extracts **structured intent** from user input via LLM~~ ✅ Done
2. ~~Uses **provider-specific query adapters** to optimize queries per provider~~ ⚠️ Add eBay
3. ~~Separates **execution** (fetch) from **normalization** (parse)~~ ✅ Done
4. **Aggregates and ranks** results using intent-aware scoring — **NOT DONE**
5. ~~Persists structured data for debugging and refinement~~ ✅ Done

### 1.3 Success Metrics
| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Search success rate | ~60% | >90% | % of searches returning >0 results |
| Result relevance | Unknown | >80% click-through on top 5 | Analytics tracking |
| Price filter accuracy | ~40% | >95% | % of results within user's price range |
| Provider coverage | 1-2 providers | All configured providers return results | Provider status tracking |

### 1.4 Non-Goals
- **Deduplication** is explicitly NOT a goal — users may want same product from multiple merchants for price comparison and negotiation
- Real-time price updates (out of scope)
- User reviews/sentiment analysis (future enhancement)

---

## 2. Current Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│    Frontend     │ ───► │      BFF        │ ───► │    Backend      │
│                 │      │                 │      │                 │
│ User types:     │      │ triageProvider  │      │ SourcingRepo    │
│ "bikes under    │      │ Query() →       │      │ .search_all()   │
│  $5000"         │      │ "bikes"         │      │                 │
│                 │      │ (string only)   │      │ Same string to  │
│                 │      │                 │      │ ALL providers   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

**Key Files:**
- `apps/bff/src/llm.ts` — `triageProviderQuery()` generates query string
- `apps/backend/sourcing.py` — `SourcingRepository` with inline provider implementations
- `apps/backend/routes/rows_search.py` — Search endpoint with post-filtering

---

## 3. Target Architecture

### 3.1 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                 │
│  "Bianchi road bike carbon frame under $5000"                       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 1: INTENT EXTRACTION (BFF)                  │
│  LLM extracts structured SearchIntent:                              │
│  {                                                                  │
│    product_category: "road_bike",                                   │
│    brand: "Bianchi",                                                │
│    max_price: 5000,                                                 │
│    features: { frame_material: "carbon" },                          │
│    keywords: ["Bianchi", "road", "bike", "carbon"]                  │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
┌───────────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│ LAYER 2: AMAZON       │ │ LAYER 2: GOOGLE   │ │ LAYER 2: EBAY     │
│ QUERY ADAPTER         │ │ QUERY ADAPTER     │ │ QUERY ADAPTER     │
│                       │ │                   │ │                   │
│ query: "Bianchi road  │ │ query: "Bianchi   │ │ query: "Bianchi   │
│        bike"          │ │  carbon road bike │ │  road bike carbon │
│ params:               │ │  buy"             │ │  -accessories"    │
│   max_price: 5000     │ │ params: {}        │ │ params:           │
│   category: sporting  │ │                   │ │   max_price: 5000 │
└───────────────────────┘ └───────────────────┘ └───────────────────┘
                    │              │              │
                    ▼              ▼              ▼
┌───────────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│ LAYER 3: AMAZON       │ │ LAYER 3: GOOGLE   │ │ LAYER 3: EBAY     │
│ EXECUTOR              │ │ EXECUTOR          │ │ EXECUTOR          │
│ (Rainforest API)      │ │ (CSE API)         │ │ (Browse API)      │
│                       │ │                   │ │                   │
│ Returns: raw JSON     │ │ Returns: raw JSON │ │ Returns: raw JSON │
└───────────────────────┘ └───────────────────┘ └───────────────────┘
                    │              │              │
                    ▼              ▼              ▼
┌───────────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│ LAYER 4: AMAZON       │ │ LAYER 4: GOOGLE   │ │ LAYER 4: EBAY     │
│ NORMALIZER            │ │ NORMALIZER        │ │ NORMALIZER        │
│                       │ │                   │ │                   │
│ Extracts: title,      │ │ Extracts: title,  │ │ Extracts: title,  │
│ price, image, rating  │ │ price (from meta) │ │ price, shipping   │
└───────────────────────┘ └───────────────────┘ └───────────────────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 5: RESULT AGGREGATOR                        │
│                                                                     │
│  1. Apply post-filters (price range for non-native providers)       │
│  2. Score: relevance + price + quality                              │
│  3. Rank and return all results                                     │
│  NO DEDUPLICATION - show all listings for negotiation               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Requirements

### 4.1 Layer 1: Intent Extraction

#### 4.1.1 SearchIntent Schema

```typescript
interface SearchIntent {
  // Core identification
  product_category: string;           // "road_bike", "laptop"
  taxonomy_version?: string;          // e.g., "shopping_v1"
  category_path?: string[];           // ["Sports & Outdoors", "Cycling", "Road Bikes"]
  product_name?: string;              // "MacBook Pro 14"
  brand?: string;                     // "Bianchi", "Apple"
  model?: string;                     // "Oltre XR4"
  
  // Price constraints
  min_price?: number;                 // In USD
  max_price?: number;                 // In USD
  price_flexibility?: "strict" | "flexible";
  
  // Condition
  condition?: "new" | "used" | "refurbished" | "any";
  
  // Features (key-value)
  features: Record<string, string | string[]>;
  
  // Search optimization
  keywords: string[];
  exclude_keywords?: string[];
  
  // Metadata
  confidence: number;                 // 0-1
  raw_input: string;                  // Original input
}
```

#### 4.1.2 Implementation Location
- **Primary:** BFF (`apps/bff/src/intent/extractor.ts`) — has LLM access
- **Fallback:** Heuristic parser when LLM unavailable

#### 4.1.3 Acceptance Criteria
| ID | Requirement |
|----|-------------|
| L1-01 | Intent extraction returns valid JSON matching schema |
| L1-02 | Price extracted as numbers ("under $500" → max_price=500) |
| L1-03 | Brand separated from category |
| L1-04 | Fallback heuristic works when LLM unavailable |
| L1-05 | Confidence reflects input quality |
| L1-06 | taxonomy_version set when category_path provided |

---

### 4.2 Layer 2: Provider Query Adapters

#### 4.2.1 ProviderQueryAdapter Interface

```python
class ProviderQueryAdapter(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str: pass
    
    @abstractmethod
    def build_query(self, intent: SearchIntent) -> ProviderQuery: pass
    
    def supports_native_price_filter(self) -> bool:
        return False
```

#### 4.2.2 Provider-Specific Strategies

| Provider | Query Strategy | Native Filters |
|----------|---------------|----------------|
| **Amazon (Rainforest)** | Short keywords, let API filter | price, category |
| **Google CSE** | Descriptive + "buy" keyword | none (post-filter) |
| **eBay** | Keywords with exclusions | price, condition |

#### 4.2.3 Acceptance Criteria
| ID | Requirement |
|----|-------------|
| L2-01 | Amazon adapter uses native price filters |
| L2-02 | Google adapter includes shopping signal keywords |
| L2-03 | eBay adapter handles condition filters |
| L2-04 | Registry returns all registered adapters |

---

### 4.3 Layer 3: Provider Executors

#### 4.3.1 ProviderExecutor Interface

```python
class ProviderExecutor(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str: pass
    
    @abstractmethod
    async def execute(self, query: ProviderQuery) -> ProviderExecutionResult: pass
```

#### 4.3.2 ProviderExecutionResult

```python
@dataclass
class ProviderExecutionResult:
    provider_id: str
    status: str  # "ok", "error", "timeout", "rate_limited", "exhausted"
    results: List[RawProviderResult]
    error_message: Optional[str]
    latency_ms: int
```

#### 4.3.3 Acceptance Criteria
| ID | Requirement |
|----|-------------|
| L3-01 | Executor returns raw JSON without normalization |
| L3-02 | Timeout handled gracefully |
| L3-03 | Rate limit / quota exhausted detected |
| L3-04 | All executors run in parallel |
| L3-05 | Latency tracked per provider |

---

### 4.4 Layer 4: Result Normalizers

#### 4.4.1 NormalizedResult Schema

```python
@dataclass
class NormalizedResult:
    # Required
    title: str
    url: str
    source: str
    
    # Price
    price: Optional[float]
    currency: str = "USD"
    price_original: Optional[float]
    currency_original: Optional[str]
    canonical_url: Optional[str]
    
    # Merchant
    merchant_name: str
    merchant_domain: str
    
    # Media
    image_url: Optional[str]
    
    # Quality signals
    rating: Optional[float]
    reviews_count: Optional[int]
    
    # Shipping
    shipping_info: Optional[str]
    
    # Debug
    raw_data: Dict[str, Any]
```

#### 4.4.2 Acceptance Criteria
| ID | Requirement |
|----|-------------|
| L4-01 | Price extracted correctly per provider |
| L4-02 | Missing price is None, not 0 |
| L4-03 | Image URLs normalized |
| L4-04 | raw_data preserved for debugging |
| L4-05 | Batch normalization skips failures |

---

### 4.5 Layer 5: Result Aggregator

#### 4.5.1 Scoring Weights

```python
relevance_weight = 0.4   # Keyword match
price_weight = 0.3       # Closer to target = better
quality_weight = 0.3     # Reviews/ratings
```

#### 4.5.2 Post-Filtering Rules
- Apply price filter ONLY for providers without native support
- Keep results with unknown price (price=None)
- Honor `price_flexibility` setting

#### 4.5.3 NO DEDUPLICATION
Results from different merchants for the same product are intentionally kept separate to support:
- Price comparison across merchants
- Negotiation opportunities on certain platforms
- Different shipping/availability options

Exact duplicate URLs within a single provider should be collapsed (same provider_id + canonical_url).

#### 4.5.4 Acceptance Criteria
| ID | Requirement |
|----|-------------|
| L5-01 | Results sorted by combined_score descending |
| L5-02 | Post-filter applied for non-native providers |
| L5-03 | Unknown price results kept |
| L5-04 | Price flexibility honored |
| L5-05 | No deduplication applied |
| L5-06 | Provider stats accurate |

---

## 5. API Contract

### 5.1 Search Request (Unchanged)

```json
POST /api/search
{
  "rowId": 123,
  "query": "optional override",
  "providers": ["rainforest", "google_cse"]
}
```

**Query precedence rules:**
- If `query` is provided, it replaces the chat text as the `raw_input` for intent extraction.
- `query` does **not** bypass intent extraction; it only changes the input.
- If `query` is omitted, intent extraction uses (in order): latest chat message → row title → choice_answers.

### 5.2 Search Response (Enhanced)

```json
{
  "results": [
    {
      "title": "Bianchi Oltre XR4 Disc",
      "url": "https://...",
      "source": "rainforest_amazon",
      "price": 4999.00,
      "currency": "USD",
      "merchant_name": "Amazon",
      "merchant_domain": "amazon.com",
      "image_url": "https://...",
      "rating": 4.7,
      "reviews_count": 23,
      "shipping_info": "Free Prime Delivery",
      "relevance_score": 0.85,
      "price_score": 0.72,
      "quality_score": 0.88,
      "combined_score": 0.81
    }
  ],
  "provider_stats": [
    {
      "provider_id": "rainforest",
      "status": "ok",
      "result_count": 15,
      "latency_ms": 1234
    }
  ],
  "total_results": 15,
  "price_range": [2500, 8500],
  "providers_succeeded": 2,
  "providers_failed": 0,
  "user_message": null
}
```

---

## 6. Database Changes

### 6.1 New Column

```sql
ALTER TABLE rows ADD COLUMN search_intent JSONB;
```

### 6.2 Migration File

```python
# alembic/versions/xxxx_add_search_intent.py
def upgrade():
    op.add_column('rows', sa.Column('search_intent', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('rows', 'search_intent')
```

### 6.3 Search Result Persistence (Bids)

#### 6.3.1 Canonical URL
Each normalized result must include a `canonical_url` for stable upserts.

Canonicalization rules:
- lowercase
- strip tracking params (`utm_*`, `gclid`, `fbclid`)
- trim trailing slashes
- normalize scheme/host (`http` → `https`, strip `www.`)

#### 6.3.2 Bid Upsert Rules
On every search:
- Lookup existing Bid by `(row_id, source, canonical_url)`
- If found: update price, image, title, seller, shipping, and keep `is_selected`
- If not found: create new Bid
- Always set `bid.normalized_at` and store `search_intent_version`

#### 6.3.3 Bid Metadata Storage
Add bid-level metadata fields for traceability:

```sql
ALTER TABLE bids ADD COLUMN canonical_url TEXT;
ALTER TABLE bids ADD COLUMN source_payload JSONB;
ALTER TABLE bids ADD COLUMN normalized_at TIMESTAMP;
ALTER TABLE bids ADD COLUMN search_intent_version TEXT;
```

### 6.4 Provider Query Audit Trail
Persist provider-specific queries to debug mismatches:

```sql
ALTER TABLE rows ADD COLUMN provider_query_map JSONB;
```

Structure:

```json
{
  "rainforest": {"query_string": "Bianchi road bike", "params": {"max_price": 500000}},
  "google_cse": {"query_string": "Bianchi carbon road bike buy", "params": {}}
}
```

### 6.5 Category Taxonomy & Mapping
Define a stable taxonomy for `product_category` and `category_path`.

Requirements:
- Taxonomy versioned (e.g., `shopping_v1`)
- Mapping functions per provider (e.g., Amazon category IDs)
- Unknown categories fall back to keyword-only search

### 6.6 Currency Normalization
All scoring and filtering uses USD. Store original values to avoid data loss.

Rules:
- `price_original`/`currency_original` store raw values
- `price` is converted to USD using daily FX table
- If conversion fails, set `price` to `None` and keep original fields

### 6.7 Latency Budget & Partial Results
Define a clear SLA for the search pipeline:
- Provider timeout: 6–8 seconds
- Overall request timeout: 10–12 seconds
- Return partial results when at least one provider succeeds

### 6.8 Low-Confidence Behavior
If `intent.confidence < 0.6`:
- Ask a clarification question before running search, OR
- Run a broad search but flag the UI with “results may be broad; refine?”

---

## 7. File Structure

```
apps/backend/
├── sourcing/
│   ├── __init__.py
│   ├── models.py              # All dataclasses
│   ├── intent/
│   │   ├── __init__.py
│   │   ├── extractor.py       # Receives intent from BFF
│   │   └── heuristic.py       # Fallback parser
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py            # ABC
│   │   ├── amazon.py
│   │   ├── google_cse.py
│   │   ├── ebay.py
│   │   └── registry.py
│   ├── executors/
│   │   ├── __init__.py
│   │   ├── base.py            # ABC
│   │   ├── rainforest.py
│   │   ├── google_cse.py
│   │   ├── ebay.py
│   │   └── orchestrator.py
│   ├── normalizers/
│   │   ├── __init__.py
│   │   ├── base.py            # ABC
│   │   ├── amazon.py
│   │   ├── google_cse.py
│   │   ├── ebay.py
│   │   └── registry.py
│   ├── aggregator.py
│   └── service.py             # Orchestrates all layers
├── routes/
│   └── rows_search.py         # Uses SourcingService
└── sourcing.py                # DEPRECATED

apps/bff/src/
├── intent/
│   ├── extractor.ts           # LLM extraction
│   └── types.ts               # TypeScript interfaces
└── llm.ts                     # Updated prompts
```

---

## 8. Implementation Phases

### Phase 1: Foundation (3-4 days) — ✅ DONE
**Status:** Complete. `sourcing/models.py` with SearchIntent, ProviderQuery, NormalizedResult, ProviderStatusSnapshot. DB columns added.

---

### Phase 2: Intent Extraction (2-3 days) — ✅ DONE
**Status:** Complete. `apps/bff/src/intent/index.ts` with LLM + heuristic. `apps/bff/src/types.ts` with TypeScript interfaces. BFF passes intent to backend, stored in `Row.search_intent`.

---

### Phase 3: Provider Adapters (2-3 days) — ⚠️ PARTIAL
**Status:** Rainforest + Google CSE adapters done. **eBay adapter not implemented.**

**Remaining:**
1. Implement `EbayQueryAdapter` in `sourcing/adapters/ebay.py`
2. Register in `sourcing/adapters/__init__.py`
3. Write unit tests

---

### Phase 4: Executors & Normalizers (3-4 days) — ✅ DONE
**Status:** Complete. `sourcing/executors/base.py` runs providers in parallel with timeout/status. Normalizers integrated into provider classes in `sourcing/repository.py`.

---

### Phase 5: Aggregator & Integration (2-3 days) — ⚠️ PARTIAL
**Status:** `SourcingService` orchestrates search+persist. `rows_search.py` uses it. Provider stats in response. **But no scoring/ranking.**

**Remaining:**
1. Implement `ResultAggregator` with `combined_score` = f(relevance, price, quality)
2. Add `relevance_score`, `price_score`, `quality_score`, `combined_score` to search response
3. Sort results by `combined_score` descending
4. Implement low-confidence behavior (confidence < 0.6 → ask clarification)
5. Populate `price_original`/`currency_original` on NormalizedResult for non-USD
6. Integration tests for scoring

---

### Phase 6: Cleanup & Rollout (2-3 days) — ❌ NOT STARTED
**Goal:** Remove legacy code, deploy.

**Tasks:**
1. Deprecate old `sourcing.py` (still exists alongside `sourcing/` package)
2. Update frontend to use new response fields (scores)
3. Deploy to staging
4. A/B test (if infrastructure supports)
5. Deploy to production
6. Remove deprecated code

**Exit Criteria:**
- Production traffic on new architecture
- Monitoring confirms improved metrics
- Old code removed

---

## 8.5 Cross-Cutting Concerns (Gap Fill — 2026-02-06)

### Authentication & Authorization
- Search endpoints require buyer authentication (existing `get_current_session()` in `rows_search.py`).
- Rate limiting applied (existing `rate_limit.py`).

### Billing & Entitlements
- No billing for search in MVP. Future: premium users may get higher rate limits or priority provider access.

### UX & Accessibility
- Search results rendering is handled by PRD 07 (Workspace). This PRD covers backend/BFF only.
- Error states must surface provider failures clearly (existing `provider_statuses` in response).

### Data Requirements
- Already defined in sections 3-5. Key: `Row.search_intent`, `Row.provider_query_map`, `Bid` fields for normalized results.

### Privacy, Security & Compliance
- Redaction policy in section 11.2: strip PII from `raw_input`, hash user IDs, no API keys in logs.
- Provider API keys stored in backend `.env`, never sent to frontend.

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM extraction fails frequently | Poor intent → poor results | Robust heuristic fallback |
| Provider API changes | Normalization breaks | Defensive parsing, version pinning |
| Increased latency from multiple layers | Slower searches | Parallel execution, caching |
| Over-filtering removes valid results | Empty results | Keep unknown-price items, flexible thresholds |

---

## 10. Testing Strategy

### 10.1 Unit Tests
- Intent extraction with various inputs
- Each adapter with various intents
- Each normalizer with various raw data
- Aggregator scoring logic

### 10.2 Integration Tests
- BFF → Backend intent passing
- Full search flow with mocked providers
- Provider timeout/error handling

### 10.3 E2E Tests
- Real provider calls (limited)
- Price filter accuracy
- UI displays enhanced response fields

---

## 11. Monitoring & Observability

### 11.1 Metrics to Track
- `search_intent_extraction_success_rate`
- `search_intent_extraction_latency_ms`
- `provider_execution_latency_ms` (per provider)
- `provider_success_rate` (per provider)
- `post_filter_drop_rate` (% filtered out)
- `average_combined_score`

### 11.2 Logging
- Log SearchIntent on every search
- Log ProviderQuery per adapter
- Log ProviderExecutionResult per executor
- Log aggregation stats

**Redaction policy:**
- Strip emails, phone numbers, addresses from `raw_input`
- Hash user IDs in logs
- Do not log raw API keys or auth headers

---

## 12. Rollback Plan

1. Feature flag `USE_NEW_SOURCING_ARCHITECTURE`
2. If issues detected, flip flag to `false`
3. Old `sourcing.py` remains functional during transition
4. Database column is additive (no rollback needed)

---

## 13. Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Foundation | 3-4 days | Interfaces, models, migration |
| 2. Intent Extraction | 2-3 days | LLM extraction working |
| 3. Provider Adapters | 2-3 days | Optimized queries per provider |
| 4. Executors & Normalizers | 3-4 days | Clean fetch/parse separation |
| 5. Aggregator & Integration | 2-3 days | End-to-end working |
| 6. Cleanup & Rollout | 2-3 days | Production deployment |

**Total: ~15-20 days**

---

## 14. Appendix

### 14.1 Example Intent Extraction Prompt

```
You are extracting structured product search intent from a user query.

Input: "Looking for a Bianchi carbon road bike, budget $4000-6000"

Output valid JSON matching this schema:
{
  "product_category": string,
  "taxonomy_version": string,
  "category_path": string[],
  "brand": string | null,
  "model": string | null,
  "min_price": number | null,
  "max_price": number | null,
  "price_flexibility": "strict" | "flexible",
  "condition": "new" | "used" | "refurbished" | "any",
  "features": Record<string, string>,
  "keywords": string[],
  "exclude_keywords": string[],
  "confidence": number (0-1),
  "raw_input": string
}

Rules:
- Extract price as numbers ONLY, never include currency symbols
- "under $X" → max_price: X
- "over $X" → min_price: X
- "$X-Y" → min_price: X, max_price: Y
- "budget around X" → price_flexibility: "flexible"
- Separate brand from product category
- confidence < 0.7 if ambiguous
```

### 14.2 Provider API Reference

| Provider | API | Docs |
|----------|-----|------|
| Amazon | Rainforest API | https://www.rainforestapi.com/docs |
| Google | Custom Search JSON API | https://developers.google.com/custom-search |
| eBay | Browse API | https://developer.ebay.com/api-docs/buy/browse |
