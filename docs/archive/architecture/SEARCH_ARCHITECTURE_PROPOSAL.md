# Search Architecture Proposal

## Current State: What's Wrong

### Problem 1: No Structured Intent Extraction
Chat input goes through LLM (`triageProviderQuery`) but output is just a **string query**, not structured data. We lose:
- Product category
- Brand preferences  
- Price constraints (min/max)
- Feature requirements (color, size, material)
- Condition (new/used/refurbished)

**Current flow:**
```
User: "Bianchi road bike carbon frame under $5000"
       ↓
LLM: "Bianchi road bike carbon frame"  ← just a string, price lost
       ↓
Same string → ALL providers
```

### Problem 2: One Query Fits All
Every provider receives the **same query string**. But:
- **Amazon** works best with: `"Bianchi road bike"` (simple, let filters do the work)
- **Google Shopping** works best with: `"Bianchi carbon road bike buy"` (more descriptive)
- **eBay** works best with: `"Bianchi road bike carbon -accessories"` (exclude noise)

### Problem 3: Inline Result Parsing (No Adapters)
Each provider class (`RainforestAPIProvider`, `GoogleCustomSearchProvider`, etc.) has its own inline result parsing. This leads to:
- Duplicated normalization logic
- Inconsistent handling of missing fields
- Hard to test/maintain
- No separation between "fetch" and "normalize"

### Problem 4: Price as Text in Query
We were injecting `"price between 499 and 25000"` into the query string, which:
- Confuses Amazon search (returns zero results)
- Doesn't use provider-native price filters
- Gets stripped out anyway by sanitization

### Problem 5: No Result Aggregation Strategy
Results from multiple providers are just concatenated and sorted by a simple `match_score`. No:
- Duplicate detection across providers (same product, different URLs)
- Price comparison across merchants
- Quality scoring based on provider reliability

---

## Proposed Architecture

### Layer 1: Intent Extraction (LLM)
Extract **structured intent** from user input, not just a query string.

```typescript
interface SearchIntent {
  // Core product identification
  product_category: string;        // "road_bike"
  product_name?: string;           // "Bianchi"
  brand?: string;                  // "Bianchi"
  
  // Constraints (structured, not text)
  min_price?: number;
  max_price?: number;
  condition?: "new" | "used" | "refurbished" | "any";
  
  // Features (key-value)
  features: Record<string, string>;  // { frame_material: "carbon", bike_type: "road" }
  
  // Search hints
  keywords: string[];              // ["Bianchi", "road", "bike", "carbon"]
  exclude_keywords?: string[];     // ["accessories", "parts", "stickers"]
}
```

### Layer 2: Provider Query Adapters
Each provider has an **adapter** that translates `SearchIntent` → provider-specific query + params.

```typescript
interface ProviderQueryAdapter {
  id: string;
  buildQuery(intent: SearchIntent): ProviderQuery;
}

interface ProviderQuery {
  query_string: string;
  params: Record<string, any>;  // Provider-specific: price filters, category IDs, etc.
}
```

**Example: Amazon Adapter**
```typescript
const amazonAdapter: ProviderQueryAdapter = {
  id: "rainforest",
  buildQuery(intent) {
    // Amazon works best with simple queries + native filters
    const parts = [intent.brand, intent.product_category].filter(Boolean);
    return {
      query_string: parts.join(" "),
      params: {
        min_price: intent.min_price,
        max_price: intent.max_price,
        // Amazon-specific: category filtering
        category_id: mapCategoryToAmazonId(intent.product_category),
      }
    };
  }
};
```

**Example: Google Shopping Adapter**
```typescript
const googleShoppingAdapter: ProviderQueryAdapter = {
  id: "google_cse",
  buildQuery(intent) {
    // Google works better with more keywords
    const parts = [
      intent.brand,
      ...intent.keywords,
      "buy",  // Shopping signal
    ].filter(Boolean);
    
    // Exclude noise
    const excludes = (intent.exclude_keywords || []).map(k => `-${k}`);
    
    return {
      query_string: [...parts, ...excludes].join(" "),
      params: {}  // Google CSE doesn't have native price filters
    };
  }
};
```

### Layer 3: Provider Executors
Clean separation: just fetch, no normalization.

```typescript
interface ProviderExecutor {
  id: string;
  execute(query: ProviderQuery): Promise<RawProviderResult[]>;
}

interface RawProviderResult {
  raw_data: any;  // Provider-specific JSON
  source: string;
}
```

### Layer 4: Result Normalizers (Collectors)
Each provider has a **normalizer** that converts raw results → unified format.

```typescript
interface ResultNormalizer {
  provider_id: string;
  normalize(raw: RawProviderResult): NormalizedResult;
}

interface NormalizedResult {
  // Core fields (required)
  title: string;
  url: string;
  source: string;
  
  // Price (structured)
  price: number | null;
  currency: string;
  
  // Merchant
  merchant_name: string;
  merchant_domain: string;
  
  // Media
  image_url: string | null;
  
  // Quality signals
  rating: number | null;
  reviews_count: number | null;
  
  // Metadata
  raw_data: any;  // For debugging
}
```

### Layer 5: Result Aggregator
Combine, dedupe, and rank results from all providers.

```typescript
interface ResultAggregator {
  aggregate(
    results: NormalizedResult[],
    intent: SearchIntent
  ): AggregatedResults;
}

interface AggregatedResults {
  results: RankedResult[];
  provider_stats: ProviderStats[];
  
  // Insights
  price_range: { min: number; max: number };
  top_merchants: string[];
}

interface RankedResult extends NormalizedResult {
  relevance_score: number;
  price_score: number;       // Lower = better deal
  quality_score: number;     // Reviews/ratings
  combined_score: number;
}
```

---

## Data Flow (Proposed)

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                 │
│  "Bianchi road bike carbon frame under $5000"                       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 1: INTENT EXTRACTION                        │
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
│ price, image, rating, │ │ price (from meta),│ │ price, shipping,  │
│ reviews, etc.         │ │ image, etc.       │ │ seller, etc.      │
└───────────────────────┘ └───────────────────┘ └───────────────────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 5: RESULT AGGREGATOR                        │
│                                                                     │
│  1. Deduplicate (same product across merchants)                     │
│  2. Apply post-filters (price range from intent)                    │
│  3. Score: relevance + price + quality                              │
│  4. Rank and return top N                                           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        UNIFIED RESULTS                               │
│  Normalized, ranked, ready for UI                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Define Contracts (Week 1)
1. Define `SearchIntent` interface
2. Define `ProviderQuery`, `RawProviderResult`, `NormalizedResult` interfaces
3. Define adapter/executor/normalizer interfaces

### Phase 2: Intent Extraction (Week 1-2)
1. Create LLM prompt that outputs structured `SearchIntent`
2. Add fallback heuristic parser for when LLM fails
3. Write tests with various user inputs

### Phase 3: Refactor Providers (Week 2-3)
1. Create `adapters/` folder with per-provider query builders
2. Create `normalizers/` folder with per-provider result parsers
3. Refactor existing providers to use new structure
4. Keep backwards compatibility during transition

### Phase 4: Result Aggregator (Week 3)
1. Implement deduplication (fuzzy title matching, same ASIN/UPC)
2. Implement relevance scoring using intent keywords
3. Implement price scoring (penalize outliers)
4. Implement quality scoring (reviews/ratings)

### Phase 5: Integration & Testing (Week 4)
1. Wire up new architecture to existing endpoints
2. A/B test old vs new
3. Remove legacy code paths

---

## Benefits

1. **Better results**: Provider-optimized queries return more relevant products
2. **Maintainable**: Clear separation of concerns, easy to add new providers
3. **Testable**: Each layer can be unit tested independently
4. **Debuggable**: Structured intent + raw data preserved for debugging
5. **Extensible**: Easy to add LLM-powered features (e.g., "find similar", "explain why this result")

---

## Questions for Review

1. Should intent extraction happen in BFF (TypeScript) or Backend (Python)?
   - **Recommendation**: BFF, since it already has LLM integration
   
2. Should we keep provider execution in Backend or move to BFF?
   - **Recommendation**: Backend, for security (API keys) and caching
   
3. How aggressive should deduplication be?
   - **Option A**: Fuzzy title matching only
   - **Option B**: Same product across merchants (show "available at X, Y, Z")

4. Priority order for implementation?
   - **Recommendation**: Start with Rainforest (Amazon) since it's the primary provider
