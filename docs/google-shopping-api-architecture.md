# Google Shopping API Integration Architecture

**Document Version:** 1.0
**Author:** System Architecture Team
**Last Updated:** 2026-01-20
**Status:** Design Review

---

## Executive Summary

This document outlines the architectural design for integrating Google Shopping API into the Shopping Agent platform to automatically generate product bids for any e-commerce available product. The integration will leverage Google's Content API for Shopping to provide comprehensive, real-time product data across millions of merchants.

**Key Goals:**
1. Automatic bid generation for any searchable product
2. High-quality product data (images, pricing, merchant info)
3. Cost-effective implementation within API quotas
4. Seamless integration with existing row-based procurement system
5. Sub-5-second response time for search queries

---

## 1. Architecture Overview

### 1.1 System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Shopping Agent System                        │
│                                                                      │
│  ┌────────────┐    ┌─────────────┐    ┌──────────────────────┐    │
│  │  Frontend  │───▶│     BFF     │───▶│      Backend         │    │
│  │  (Next.js) │    │  (Fastify)  │    │     (FastAPI)        │    │
│  └────────────┘    └─────────────┘    └──────────────────────┘    │
│                                              │                       │
│                                              ▼                       │
│                                    ┌──────────────────┐             │
│                                    │ SourcingRepository│             │
│                                    └──────────────────┘             │
│                                              │                       │
│                    ┌─────────────────────────┼─────────────────┐   │
│                    │                         │                 │   │
│                    ▼                         ▼                 ▼   │
│            ┌──────────────┐        ┌──────────────┐  ┌──────────┐ │
│            │ Google       │        │  Rainforest  │  │  eBay    │ │
│            │ Shopping     │        │  API         │  │  Browse  │ │
│            │ Provider     │        │  (Amazon)    │  │  API     │ │
│            │  [NEW]       │        └──────────────┘  └──────────┘ │
│            └──────────────┘                                        │
└─────────────────────────────────────────────────────────────────────┘
                     │
                     ▼
         ┌────────────────────────┐
         │  Google Shopping API   │
         │  (Content API v2.1)    │
         └────────────────────────┘
```

### 1.2 Integration Strategy

**Approach:** Add Google Shopping as a new `SourcingProvider` in the existing provider pattern

**Rationale:**
- Leverages existing parallel sourcing architecture
- Minimal disruption to current codebase
- Easy to enable/disable via environment configuration
- Consistent error handling and timeout management
- Natural deduplication with other providers

---

## 2. Google Shopping API Selection

### 2.1 API Comparison

| API Option | Best For | Cost | Limitations |
|------------|----------|------|-------------|
| **Content API for Shopping** | Direct access to Shopping data | **FREE** (with quotas) | Requires merchant verification |
| **Shopping API (deprecated)** | Legacy integrations | Free | Being sunset |
| **Custom Search API** | General product search | $5/1000 queries after 100/day | Limited to 10 results |
| **SerpAPI/SearchAPI** | Quick start, no setup | $50-75/5000 queries | Third-party costs |

### 2.2 Recommended Approach: Content API for Shopping

**Primary:** Content API for Shopping v2.1
**Fallback:** SerpAPI/SearchAPI (already implemented)

**Rationale:**
1. **Cost-effective:** Free tier with generous quotas (10,000 QPD)
2. **Data Quality:** Direct access to Google Shopping merchant data
3. **Comprehensive:** Product details, prices, images, merchant info, reviews
4. **Real-time:** Up-to-date pricing and availability
5. **Scalable:** Can handle production traffic within quotas

**Content API Quotas:**
- 10,000 queries per day (QPD) - FREE tier
- Can request increases up to 100,000 QPD
- Rate limit: 300 queries per minute per user

---

## 3. Technical Design

### 3.1 Component Architecture

```python
# New Provider Class
class GoogleShoppingProvider(SourcingProvider):
    """
    Google Content API for Shopping integration.
    Searches Google Shopping merchant catalog for products.
    """

    def __init__(
        self,
        api_key: str,
        country: str = "US",
        language: str = "en",
        merchant_id: Optional[str] = None
    ):
        self.api_key = api_key
        self.country = country
        self.language = language
        self.merchant_id = merchant_id
        self.base_url = "https://shoppingcontent.googleapis.com/content/v2.1"

        # Cache for product details to minimize API calls
        self._product_cache: Dict[str, Tuple[SearchResult, float]] = {}
        self._cache_ttl = 3600  # 1 hour

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Search Google Shopping for products matching query.

        Args:
            query: Search term
            **kwargs: Additional filters (price_min, price_max, brand, etc.)

        Returns:
            List of SearchResult objects
        """
        pass
```

### 3.2 API Request Structure

**Endpoint:** `GET https://shoppingcontent.googleapis.com/content/v2.1/products`

**Request Parameters:**
```python
params = {
    "key": self.api_key,
    "q": query,  # Search query
    "maxResults": 50,  # Max 50 per request
    "country": "US",
    "language": "en",
    "fields": "items(id,title,description,link,imageLink,price,brand,condition,availability,mpn,gtin)",
}
```

**Response Mapping to SearchResult:**
```python
SearchResult(
    title=item["title"],
    price=float(item["price"]["value"]),
    currency=item["price"]["currency"],
    merchant=item.get("brand") or "Google Shopping",
    url=item["link"],
    merchant_domain=extract_merchant_domain(item["link"]),
    image_url=item.get("imageLink"),
    rating=None,  # Not in basic response
    reviews_count=None,
    shipping_info=self._parse_shipping(item.get("shipping")),
    source="google_shopping_api",
    match_score=0.0,  # Computed later
)
```

### 3.3 Enhanced Search with Product Ratings API

For products with review data:

**Endpoint:** `GET https://shoppingcontent.googleapis.com/content/v2.1/products/{productId}/productreviews`

**Usage:**
```python
async def _enrich_with_reviews(self, product_id: str) -> Optional[Dict]:
    """Fetch review aggregates for a product."""
    url = f"{self.base_url}/products/{product_id}/productreviews"
    response = await client.get(url, params={"key": self.api_key})

    if response.status_code == 200:
        data = response.json()
        return {
            "rating": data.get("averageRating"),
            "reviews_count": data.get("numberOfReviews"),
        }
    return None
```

---

## 4. Implementation Plan

### 4.1 Phase 1: Core Integration (Week 1)

**Deliverables:**
1. `GoogleShoppingProvider` class in `sourcing.py`
2. Basic search functionality with Content API
3. Response mapping to `SearchResult` interface
4. Provider registration in `SourcingRepository`
5. Environment variable configuration

**Tasks:**
- [ ] Create Google Cloud Project and enable Shopping API
- [ ] Obtain API key and configure quotas
- [ ] Implement `GoogleShoppingProvider.search()` method
- [ ] Add response parsing and error handling
- [ ] Register provider in repository initialization
- [ ] Add env vars: `GOOGLE_SHOPPING_API_KEY`, `GOOGLE_SHOPPING_COUNTRY`

**Code Location:**
```
apps/backend/sourcing.py
  - Add GoogleShoppingProvider class (lines 500-600)
  - Register in SourcingRepository.__init__ (line 575)
```

### 4.2 Phase 2: Enhanced Features (Week 2)

**Deliverables:**
1. Product review enrichment
2. Advanced filtering (price range, brand, condition)
3. Result caching strategy
4. Merchant reputation scoring

**Tasks:**
- [ ] Implement review data fetching
- [ ] Add price range filtering
- [ ] Build in-memory cache with TTL
- [ ] Add merchant rating aggregation
- [ ] Optimize match scoring algorithm

### 4.3 Phase 3: Performance Optimization (Week 3)

**Deliverables:**
1. Response time < 2 seconds for typical queries
2. Intelligent caching and quota management
3. Batch request optimization
4. Monitoring and alerting

**Tasks:**
- [ ] Implement Redis caching for search results
- [ ] Add quota tracking and throttling
- [ ] Batch review enrichment requests
- [ ] Add Prometheus metrics for API calls
- [ ] Set up quota alerts in Google Cloud Console

### 4.4 Phase 4: Production Hardening (Week 4)

**Deliverables:**
1. Comprehensive error handling
2. Fallback strategies
3. A/B testing framework
4. Documentation and runbooks

**Tasks:**
- [ ] Implement circuit breaker pattern
- [ ] Add graceful degradation for quota exhaustion
- [ ] Create feature flag for provider toggle
- [ ] Write runbook for quota management
- [ ] Add integration tests with mocked responses

---

## 5. API Authentication and Rate Limiting

### 5.1 Authentication Strategy

**Approach:** API Key Authentication (simplest for public product data)

**Configuration:**
```bash
# .env
GOOGLE_SHOPPING_API_KEY=AIza...your-key
GOOGLE_SHOPPING_COUNTRY=US
GOOGLE_SHOPPING_LANGUAGE=en
GOOGLE_SHOPPING_ENABLED=true
```

**Alternative (OAuth2 for authenticated endpoints):**
```python
# For merchants with their own product catalog
class GoogleShoppingAuthProvider(GoogleShoppingProvider):
    def __init__(self, credentials_path: str):
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/content']
        )
```

### 5.2 Rate Limiting Strategy

**Quotas:**
- 10,000 queries per day (free tier)
- 300 queries per minute per user
- Quota resets at midnight Pacific Time

**Implementation:**
```python
class QuotaManager:
    """Track and enforce API quota limits."""

    def __init__(self, daily_limit: int = 10000, per_minute_limit: int = 300):
        self.daily_limit = daily_limit
        self.per_minute_limit = per_minute_limit
        self._daily_usage = 0
        self._minute_usage = 0
        self._minute_start = time.time()
        self._day_start = datetime.now(timezone.utc).date()

    async def check_quota(self) -> bool:
        """Check if we can make another API call."""
        self._reset_if_needed()

        if self._daily_usage >= self.daily_limit:
            return False
        if self._minute_usage >= self.per_minute_limit:
            await asyncio.sleep(1.0)  # Wait for rate limit window
            return await self.check_quota()

        return True

    def increment(self):
        """Record an API call."""
        self._daily_usage += 1
        self._minute_usage += 1
```

**Cost Optimization:**
1. **Cache aggressively:** 1-hour TTL for search results
2. **Batch enrichment:** Fetch reviews only for top 10 results
3. **Quota monitoring:** Alert at 80% daily usage
4. **Fallback strategy:** Use SerpAPI when quota exhausted
5. **Smart deduplication:** Share results across similar queries

---

## 6. Data Mapping and Transformation

### 6.1 Google Shopping Response → Offer Interface

**Source Schema (Google Content API):**
```json
{
  "id": "online:en:US:1234567890",
  "title": "Montana State Bobcats T-Shirt",
  "description": "Official NCAA licensed apparel...",
  "link": "https://shop.example.com/product/123",
  "imageLink": "https://cdn.example.com/image.jpg",
  "price": {
    "value": "29.99",
    "currency": "USD"
  },
  "brand": "Nike",
  "condition": "new",
  "availability": "in stock",
  "shipping": [{
    "country": "US",
    "service": "Standard",
    "price": { "value": "0", "currency": "USD" }
  }],
  "mpn": "ABC123",
  "gtin": "123456789012"
}
```

**Target Schema (Offer Interface):**
```typescript
interface Offer {
  title: string;                    // → item.title
  price: number;                    // → parseFloat(item.price.value)
  currency: string;                 // → item.price.currency
  merchant: string;                 // → item.brand || extract from link
  url: string;                      // → item.link
  image_url: string | null;         // → item.imageLink
  rating: number | null;            // → [fetch separately] or null
  reviews_count: number | null;     // → [fetch separately] or null
  shipping_info: string | null;     // → parse item.shipping
  source: string;                   // → "google_shopping_api"
  merchant_domain?: string;         // → extract_merchant_domain(item.link)
  click_url?: string;               // → /api/clickout?url=...
  match_score?: number;             // → compute_match_score()
  bid_id?: number;                  // → null (auto-generated)
  is_selected?: boolean;            // → false
}
```

### 6.2 Transformation Logic

```python
def map_google_product_to_search_result(item: Dict) -> SearchResult:
    """Transform Google Shopping product to SearchResult."""

    # Price parsing
    price_obj = item.get("price", {})
    price_value = price_obj.get("value", "0")
    try:
        price = float(str(price_value).replace(",", ""))
    except ValueError:
        price = 0.0

    currency = price_obj.get("currency", "USD")

    # URL normalization
    url = normalize_url(item.get("link", ""))

    # Merchant extraction (prefer brand, fallback to domain)
    merchant = item.get("brand") or extract_merchant_domain(url)

    # Shipping info parsing
    shipping_info = None
    shipping_list = item.get("shipping", [])
    if shipping_list and len(shipping_list) > 0:
        ship = shipping_list[0]
        ship_price = ship.get("price", {})
        if ship_price.get("value") == "0" or ship_price.get("value") == 0:
            shipping_info = "Free shipping"
        else:
            ship_val = ship_price.get("value")
            ship_cur = ship_price.get("currency", currency)
            shipping_info = f"Shipping {ship_cur} {ship_val}"

    # Condition badge
    condition = item.get("condition", "new")
    availability = item.get("availability", "")

    return SearchResult(
        title=item.get("title", "Unknown Product"),
        price=price,
        currency=currency,
        merchant=merchant,
        url=url,
        merchant_domain=extract_merchant_domain(url),
        image_url=item.get("imageLink"),
        rating=None,  # Enriched separately
        reviews_count=None,
        shipping_info=shipping_info,
        source="google_shopping_api",
        match_score=0.0,  # Computed after
    )
```

---

## 7. Caching and Refresh Strategy

### 7.1 Multi-Layer Caching Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Caching Layers                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  L1: In-Memory Cache (Frontend)                             │
│  ┌──────────────────────────────────────┐                   │
│  │ rowResults: Record<rowId, Offer[]>   │                   │
│  │ TTL: Session lifetime                │                   │
│  │ Size: ~50 rows × 20 offers           │                   │
│  └──────────────────────────────────────┘                   │
│                      ↓                                       │
│  L2: Application Cache (Backend)                            │
│  ┌──────────────────────────────────────┐                   │
│  │ Python dict with TTL                 │                   │
│  │ TTL: 1 hour for product searches     │                   │
│  │ Key: hash(query + filters)           │                   │
│  │ Size: ~1000 cached queries           │                   │
│  └──────────────────────────────────────┘                   │
│                      ↓                                       │
│  L3: Redis Cache (Shared)                                   │
│  ┌──────────────────────────────────────┐                   │
│  │ Persistent cache across instances    │                   │
│  │ TTL: 6 hours for product data        │                   │
│  │ TTL: 24 hours for enriched reviews   │                   │
│  │ Eviction: LRU                        │                   │
│  └──────────────────────────────────────┘                   │
│                      ↓                                       │
│  L4: Google Shopping API (Source of Truth)                  │
│  ┌──────────────────────────────────────┐                   │
│  │ Real-time product data               │                   │
│  │ 10,000 QPD quota                     │                   │
│  └──────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Cache Implementation

```python
from typing import Optional, List
import hashlib
import json
import time

class SearchCache:
    """In-memory cache for Google Shopping searches with TTL."""

    def __init__(self, ttl: int = 3600):
        self._cache: Dict[str, Tuple[List[SearchResult], float]] = {}
        self._ttl = ttl

    def _make_key(self, query: str, **kwargs) -> str:
        """Generate cache key from query and filters."""
        filter_str = json.dumps(kwargs, sort_keys=True)
        combined = f"{query}|{filter_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get(self, query: str, **kwargs) -> Optional[List[SearchResult]]:
        """Retrieve cached results if not expired."""
        key = self._make_key(query, **kwargs)

        if key not in self._cache:
            return None

        results, timestamp = self._cache[key]

        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            return None

        return results

    def set(self, query: str, results: List[SearchResult], **kwargs):
        """Store search results in cache."""
        key = self._make_key(query, **kwargs)
        self._cache[key] = (results, time.time())

    def invalidate(self, query: str, **kwargs):
        """Remove specific query from cache."""
        key = self._make_key(query, **kwargs)
        if key in self._cache:
            del self._cache[key]

    def clear_expired(self):
        """Remove all expired entries (periodic cleanup)."""
        now = time.time()
        expired = [
            key for key, (_, ts) in self._cache.items()
            if now - ts > self._ttl
        ]
        for key in expired:
            del self._cache[key]
```

### 7.3 Refresh Strategy

**Trigger Conditions:**
1. **User-initiated:** Click "Refresh" button on row
2. **TTL expiration:** Cache expires after 1 hour
3. **Price change alert:** Webhook from Google (if available)
4. **Scheduled:** Nightly refresh of active rows

**Refresh Logic:**
```python
async def refresh_row_offers(row_id: int, force: bool = False):
    """
    Refresh offers for a specific row.

    Args:
        row_id: Row to refresh
        force: Bypass cache and fetch fresh data
    """
    row = await db.get_row(row_id)

    # Check cache unless force refresh
    if not force:
        cached = cache.get(row.title, **row.choice_answers)
        if cached:
            return cached

    # Fetch fresh data from all providers
    results = await sourcing_repo.search_all(
        row.title,
        providers=["google_shopping", "ebay", "rainforest"],
        **row.choice_answers
    )

    # Update cache
    cache.set(row.title, results, **row.choice_answers)

    # Persist to database as bids
    await db.upsert_bids(row_id, results)

    return results
```

---

## 8. Cost Optimization Strategies

### 8.1 Quota Management

**Daily Budget Allocation:**
```
Total: 10,000 QPD (free tier)

Breakdown:
- User searches:     7,000 QPD (70%) - priority traffic
- Auto-refresh:      2,000 QPD (20%) - background updates
- Review enrichment: 1,000 QPD (10%) - optional enhancement
```

**Cost per Search Analysis:**
```
Scenario 1: Basic Search
- 1 search query = 1 API call
- Cost: FREE within quota
- Beyond quota: ~$0.004/query (estimated)

Scenario 2: Search + Review Enrichment
- 1 search + 10 review calls = 11 API calls
- Recommended: Cache reviews for 24 hours
- Batch enrichment: Only top 5 results

Scenario 3: Real-time Price Monitoring
- 100 active rows × 4 refreshes/day = 400 QPD
- Within budget, sustainable
```

### 8.2 Intelligent Caching

**Cache Strategy by Query Type:**

| Query Pattern | Cache TTL | Rationale |
|---------------|-----------|-----------|
| Popular products (iPhone, Nike shoes) | 30 minutes | Prices change frequently |
| Niche products (Montana State shirt) | 2 hours | Less volatile |
| Out of stock items | 24 hours | Rarely comes back quickly |
| Seasonal items | 6 hours | Moderate price changes |

**Implementation:**
```python
def get_cache_ttl(result: SearchResult) -> int:
    """Determine optimal cache TTL based on product characteristics."""

    # Out of stock: cache longer
    if "out of stock" in result.title.lower():
        return 86400  # 24 hours

    # High-demand merchants: cache shorter
    if result.merchant_domain in ["amazon.com", "walmart.com", "target.com"]:
        return 1800  # 30 minutes

    # Default: 1 hour
    return 3600
```

### 8.3 Query Optimization

**De-duplication:**
```python
# Before: Multiple similar queries
"Montana State shirts blue XL"
"Montana State blue shirts XL"
"Blue Montana State shirts XL"

# After: Normalize to single query
normalize_query("montana state shirts blue xl")
→ Cache hit: 2 API calls saved
```

**Incremental Filtering:**
```python
# Strategy: Broad search + client-side filtering
# Instead of:
#   - Query 1: "Montana State shirt blue" (1 API call)
#   - Query 2: "Montana State shirt red" (1 API call)
#   - Query 3: "Montana State shirt gold" (1 API call)

# Do this:
#   - Query 1: "Montana State shirt" (1 API call)
#   - Filter client-side by color
# Savings: 2 API calls per refinement
```

### 8.4 Fallback Strategy

**Tiered Provider Approach:**
```
Priority 1: Redis Cache (0 cost, <10ms)
           ↓ miss
Priority 2: Google Shopping API (FREE within quota)
           ↓ quota exceeded
Priority 3: SerpAPI/SearchAPI (paid, unlimited)
           ↓ error
Priority 4: Mock Provider (testing fallback)
```

**Implementation:**
```python
async def search_with_fallback(query: str) -> List[SearchResult]:
    """Search with intelligent fallback chain."""

    # Check cache first
    cached = redis_cache.get(query)
    if cached:
        return cached

    # Try Google Shopping if quota available
    if quota_manager.can_make_request():
        try:
            results = await google_provider.search(query)
            if results:
                redis_cache.set(query, results, ttl=3600)
                return results
        except QuotaExceededError:
            logger.warning("Google Shopping quota exceeded, falling back")

    # Fallback to paid provider
    try:
        results = await serpapi_provider.search(query)
        redis_cache.set(query, results, ttl=1800)
        return results
    except Exception as e:
        logger.error(f"All providers failed: {e}")

    # Last resort: mock data for testing
    return await mock_provider.search(query)
```

---

## 9. User Experience Flow

### 9.1 Auto-Bidding Trigger Scenarios

**Scenario 1: Row Creation (Primary)**
```
User: "I need Montana State shirts"
  ↓
LLM: Calls createRow tool
  ↓
Backend: Creates row with status='sourcing'
  ↓
Backend: Triggers search_all() with Google Shopping enabled
  ↓
Frontend: Displays RequestTile + loading placeholders
  ↓
Backend: Returns results in <3 seconds
  ↓
Frontend: Populates OfferTiles with Google Shopping results
```

**Scenario 2: Manual Refresh**
```
User: Clicks "Refresh" icon on row
  ↓
Frontend: Shows spinner on tiles
  ↓
API: POST /api/search with rowId and providers=['google_shopping']
  ↓
Backend: Bypasses cache (force=true), fetches fresh data
  ↓
Frontend: Updates tiles with new prices and availability
```

**Scenario 3: Choice Factor Refinement**
```
User: Updates "Color" from "Any" to "Blue" in RequestTile
  ↓
Frontend: Calls PATCH /api/rows/:id with choice_answers
  ↓
Backend: Re-runs search with new filters
  ↓
Backend: Returns filtered results (may use cache if available)
  ↓
Frontend: Updates OfferTiles with refined results
```

**Scenario 4: Background Refresh**
```
Cron Job: Every 6 hours
  ↓
Backend: Identifies rows with status='open' and last_updated > 6h
  ↓
Backend: Batch refresh top 100 active rows
  ↓
Backend: Updates database with new prices
  ↓
WebSocket (future): Push updates to connected clients
```

### 9.2 UI Indicators for Source Attribution

**OfferTile Badges:**

```typescript
// Source badge configuration
const SOURCE_BADGES = {
  google_shopping_api: {
    label: "Google Shopping",
    icon: GoogleIcon,
    color: "blue",
    tooltip: "Verified by Google Shopping"
  },
  rainforest_amazon: {
    label: "Amazon",
    icon: AmazonIcon,
    color: "orange",
    tooltip: "Amazon product"
  },
  ebay_browse: {
    label: "eBay",
    icon: EbayIcon,
    color: "red",
    tooltip: "eBay listing"
  },
  manual: {
    label: "Seller Bid",
    icon: HandshakeIcon,
    color: "green",
    tooltip: "Direct seller offer"
  }
};

// In OfferTile component
<div className="absolute top-2 right-2">
  <Badge
    variant={SOURCE_BADGES[offer.source].color}
    icon={SOURCE_BADGES[offer.source].icon}
  >
    {SOURCE_BADGES[offer.source].label}
  </Badge>
</div>
```

**Visual Hierarchy:**
```
┌─────────────────────────────────────────┐
│  Montana State Shirts - Blue XL         │
├─────────────────────────────────────────┤
│  🔷 Google Shopping    ⭐ Best Match     │  ← Source + Quality badges
│                                          │
│  [Product Image]                         │
│                                          │
│  Official NCAA Montana State Bobcats...  │
│  $29.99                                  │
│  nike.com  ⭐ 4.8 (2.3k reviews)         │
│  🚚 Free shipping                        │
│                                          │
│  [Select Deal]                           │
└─────────────────────────────────────────┘
```

### 9.3 Auto-Bid vs Manual Bid Differentiation

**Database Schema:**
```sql
-- Bids table already has 'source' column
SELECT * FROM bids WHERE row_id = 123;

id | row_id | source                | price | merchant      | is_selected
---|--------|----------------------|-------|---------------|------------
1  | 123    | google_shopping_api  | 29.99 | nike.com      | false
2  | 123    | ebay_browse          | 24.99 | ebayseller123 | false
3  | 123    | manual_seller        | 27.00 | local_shop    | true  ← Manual bid
```

**UI Distinction:**

```typescript
const isManuallBid = offer.source === 'manual' || offer.source.includes('seller');

<OfferTile
  offer={offer}
  variant={isManualBid ? 'seller' : 'auto'}
  badges={[
    isManualBid && { icon: Handshake, label: 'Negotiable', color: 'green' },
    offer.match_score > 0.7 && { icon: Star, label: 'Best Match' }
  ]}
/>
```

**Sort Priority:**
1. Selected offers (any source)
2. Manual seller bids (prioritize human relationships)
3. High match score auto-bids (>0.7)
4. Other auto-bids (sorted by price or rating)

---

## 10. Image Handling and CDN Strategy

### 10.1 Image Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Image Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Google Shopping API                                         │
│  ┌────────────────┐                                          │
│  │ imageLink URL  │                                          │
│  └────────────────┘                                          │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────┐                       │
│  │  Option 1: Direct Passthrough    │ (Simplest)            │
│  │  Frontend → Google CDN directly  │                       │
│  └──────────────────────────────────┘                       │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────┐                       │
│  │  Option 2: Proxy + Cache         │ (Recommended)         │
│  │  Frontend → Backend → Google CDN │                       │
│  │  + Redis cache for 24h           │                       │
│  └──────────────────────────────────┘                       │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────┐                       │
│  │  Option 3: Download + Upload     │ (Future/Scale)        │
│  │  Backend → Download → S3/GCS     │                       │
│  │  Frontend → CloudFront CDN       │                       │
│  └──────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 Recommended Approach: Proxy + Cache

**Rationale:**
1. **Reliability:** Merchant images can be slow or unavailable
2. **Privacy:** Prevent direct tracking of user via image requests
3. **Consistency:** Uniform loading experience
4. **Optimization:** Resize and compress on-the-fly

**Implementation:**

**Backend Proxy Endpoint:**
```python
# apps/backend/main.py

@app.get("/api/images/proxy")
async def proxy_image(url: str = Query(...), width: int = 300, height: int = 300):
    """
    Proxy and cache product images with optional resizing.

    Args:
        url: Original image URL from Google Shopping
        width: Target width in pixels
        height: Target height in pixels

    Returns:
        Cached or proxied image
    """
    cache_key = f"img:{hashlib.sha256(url.encode()).hexdigest()}:{width}x{height}"

    # Check Redis cache
    cached = await redis.get(cache_key)
    if cached:
        return Response(content=cached, media_type="image/jpeg")

    # Fetch from origin
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=5.0)
        response.raise_for_status()

        # Optional: Resize with Pillow
        from PIL import Image
        from io import BytesIO

        img = Image.open(BytesIO(response.content))
        img.thumbnail((width, height), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        img_bytes = buffer.getvalue()

        # Cache for 24 hours
        await redis.setex(cache_key, 86400, img_bytes)

        return Response(content=img_bytes, media_type="image/jpeg")
```

**Frontend Usage:**
```typescript
// In OfferTile component
const proxyImageUrl = offer.image_url
  ? `/api/images/proxy?url=${encodeURIComponent(offer.image_url)}&width=300&height=300`
  : null;

<img
  src={proxyImageUrl}
  alt={offer.title}
  loading="lazy"
  className="w-full h-full object-contain"
/>
```

### 10.3 Future: Full CDN Solution (Phase 2)

**For Production Scale (>10k products):**

```python
async def upload_to_cdn(image_url: str, product_id: str) -> str:
    """
    Download image and upload to our CDN (S3 + CloudFront).

    Returns:
        CDN URL for permanent hosting
    """
    # Download original
    async with httpx.AsyncClient() as client:
        response = await client.get(image_url)
        img_bytes = response.content

    # Upload to S3
    s3_key = f"products/{product_id}/{uuid.uuid4()}.jpg"
    s3_client.put_object(
        Bucket=os.getenv("AWS_S3_BUCKET"),
        Key=s3_key,
        Body=img_bytes,
        ContentType="image/jpeg",
        CacheControl="max-age=31536000"  # 1 year
    )

    # Return CloudFront URL
    cdn_base = os.getenv("CLOUDFRONT_DOMAIN")
    return f"https://{cdn_base}/{s3_key}"
```

---

## 11. Affiliate Link Integration

### 11.1 Google Shopping Affiliate Options

**Option 1: Google Affiliate Network (Deprecated)**
- Formerly Commission Junction integration
- No longer available for new partners

**Option 2: Skimlinks Universal Fallback**
- Already implemented in `affiliate.py`
- Works with Google Shopping URLs automatically
- Commission: 3-10% depending on merchant

**Option 3: Direct Merchant Affiliate Programs**
- Parse merchant domain from Google Shopping URL
- Match against registered affiliate handlers (Amazon, eBay)
- Apply specific affiliate tags per merchant

### 11.2 Integration with LinkResolver

**Current Flow:**
```typescript
// OfferTile component
const clickUrl = offer.click_url ||
  `/api/clickout?url=${encodeURIComponent(offer.url)}&row_id=${rowId}&source=${offer.source}`;

<a href={clickUrl} target="_blank" rel="noopener noreferrer">
```

**Backend Clickout Handler:**
```python
# apps/backend/main.py

@app.get("/api/out")
async def clickout(
    url: str = Query(...),
    row_id: Optional[int] = None,
    idx: int = 0,
    source: str = "unknown",
    user: User = Depends(get_current_user)
):
    """
    Redirect to product URL with affiliate tracking.
    Logs click for analytics.
    """
    # Extract merchant domain
    merchant_domain = extract_merchant_domain(url)

    # Build context
    context = ClickContext(
        user_id=user.id,
        row_id=row_id,
        offer_index=idx,
        source=source,
        merchant_domain=merchant_domain
    )

    # Resolve affiliate link
    resolved = link_resolver.resolve(url, context)

    # Log click event
    await db.log_click(
        user_id=user.id,
        row_id=row_id,
        url=url,
        final_url=resolved.final_url,
        handler=resolved.handler_name,
        affiliate_tag=resolved.affiliate_tag
    )

    # Redirect
    return RedirectResponse(url=resolved.final_url, status_code=302)
```

### 11.3 Google Shopping-Specific Handler

**New Handler for Google Shopping URLs:**
```python
class GoogleShoppingAffiliateHandler(AffiliateHandler):
    """
    Handle Google Shopping product URLs.

    Google Shopping URLs contain merchant tracking params.
    We preserve these and append our own tracking.
    """

    def __init__(self, merchant_id: Optional[str] = None):
        self.merchant_id = merchant_id or os.getenv("GOOGLE_MERCHANT_ID", "")

    @property
    def name(self) -> str:
        return "google_shopping"

    @property
    def domains(self) -> List[str]:
        return ["google.com", "shopping.google.com"]

    def transform(self, url: str, context: ClickContext) -> ResolvedLink:
        """
        Add Google Shopping tracking parameters.

        Example URL transformation:
        Original: https://www.nike.com/t/air-max-90
        Transformed: https://www.nike.com/t/air-max-90?utm_source=google_shopping&utm_campaign=123
        """
        if not self.merchant_id:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False
            )

        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # Add tracking parameters
            query_params['utm_source'] = ['google_shopping']
            query_params['utm_medium'] = ['cpc']
            query_params['utm_campaign'] = [self.merchant_id]
            query_params['gclid'] = [f'sa_{context.user_id}_{context.row_id}']

            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))

            return ResolvedLink(
                final_url=new_url,
                handler_name=self.name,
                affiliate_tag=self.merchant_id,
                rewrite_applied=True
            )
        except Exception as e:
            return ResolvedLink(
                final_url=url,
                handler_name=self.name,
                rewrite_applied=False,
                metadata={"error": str(e)}
            )
```

---

## 12. Technical Considerations

### 12.1 API Quotas and Cost

**Free Tier Limits:**
- 10,000 queries per day
- 300 queries per minute
- Resets daily at midnight PT

**Production Estimates:**

| User Scenario | QPD Usage | % of Quota |
|---------------|-----------|------------|
| 100 users × 10 searches/day | 1,000 | 10% |
| 500 rows × 2 auto-refreshes/day | 1,000 | 10% |
| 100 enrichment calls (reviews) | 100 | 1% |
| **Total Daily Usage** | **2,100** | **21%** |

**Capacity:**
- Current design supports ~400 active users/day
- At scale (1000+ users), request quota increase to 100,000 QPD

**Cost Beyond Free Tier:**
- Google Shopping API: Contact sales (typically $0.003-0.005/query)
- Fallback (SerpAPI): $0.015/query
- Recommendation: Stay within free tier with caching

### 12.2 Response Time Targets

**Performance Requirements:**

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Single product search | <2s | <5s |
| Search with review enrichment | <3s | <7s |
| Cached query | <100ms | <500ms |
| Background refresh | <10s | <30s |

**Optimization Strategies:**

1. **Parallel Provider Calls:**
```python
# Run Google Shopping + eBay + Amazon in parallel
tasks = [
    google_provider.search(query),
    ebay_provider.search(query),
    amazon_provider.search(query)
]
results = await asyncio.gather(*tasks, return_exceptions=True)
# Total time: max(provider_times) instead of sum(provider_times)
```

2. **Streaming Results:**
```python
# Return results as they arrive (future enhancement)
async def search_streaming(query: str):
    async for provider_name, results in parallel_search_streaming(query):
        yield {
            "provider": provider_name,
            "results": results,
            "timestamp": time.time()
        }
```

3. **Timeouts:**
```python
PROVIDER_TIMEOUT_SECONDS = 8.0  # Fail fast if provider is slow
```

### 12.3 Error Handling and Fallback

**Error Categories:**

| Error Type | Handling Strategy | User Experience |
|------------|-------------------|-----------------|
| Quota Exceeded | Switch to fallback provider (SerpAPI) | Transparent, slight delay |
| API Timeout | Return cached results if available | Show stale data warning |
| Invalid API Key | Log error, use mock provider | Admin alert, show test data |
| Network Error | Retry 3x with exponential backoff | Loading spinner, then error toast |
| Malformed Response | Skip provider, aggregate others | Fewer results, no error |

**Implementation:**
```python
class GoogleShoppingProvider(SourcingProvider):
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        try:
            # Attempt API call
            results = await self._make_request(query, **kwargs)
            return results

        except QuotaExceededError as e:
            logger.error(f"Google Shopping quota exceeded: {e}")
            # Fallback to cache or alternative provider
            cached = self._cache.get(query)
            if cached:
                logger.info("Returning cached results due to quota")
                return cached
            raise  # Let SourcingRepository handle fallback

        except httpx.TimeoutException:
            logger.warning(f"Google Shopping timeout for query: {query}")
            # Return empty, don't crash the whole search
            return []

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("Google Shopping API key invalid or expired")
                # Critical error, alert admin
                await alert_admin("Google Shopping API authentication failed")
            return []

        except Exception as e:
            logger.exception(f"Unexpected error in Google Shopping search: {e}")
            return []
```

### 12.4 Product Matching Accuracy

**Challenge:**
User query: "Montana State shirt blue XL"
Google Shopping returns: 1000+ results

**Matching Strategy:**

1. **Query Preprocessing:**
```python
def preprocess_query(query: str, choice_answers: Dict) -> str:
    """
    Enhance query with choice factor constraints.

    Example:
        Query: "Montana State shirt"
        Choice Answers: {size: "XL", color: "blue"}
        Output: "Montana State shirt XL blue"
    """
    tokens = [query]

    # Append size
    if "size" in choice_answers:
        tokens.append(choice_answers["size"])

    # Append color
    if "color" in choice_answers and choice_answers["color"] != "any":
        tokens.append(choice_answers["color"])

    # Append brand
    if "brand" in choice_answers:
        tokens.append(choice_answers["brand"])

    return " ".join(tokens)
```

2. **Post-Filter by Attributes:**
```python
def filter_by_choice_factors(
    results: List[SearchResult],
    choice_answers: Dict
) -> List[SearchResult]:
    """
    Filter results that don't match user requirements.
    """
    filtered = []

    for result in results:
        # Check size in title or description
        if "size" in choice_answers:
            size = choice_answers["size"].upper()
            if size not in result.title.upper():
                continue

        # Check color
        if "color" in choice_answers and choice_answers["color"] != "any":
            color = choice_answers["color"].lower()
            if color not in result.title.lower():
                continue

        # Check price range
        if "max_price" in choice_answers:
            if result.price > choice_answers["max_price"]:
                continue

        filtered.append(result)

    return filtered
```

3. **Semantic Matching (Future):**
```python
# Use embeddings to find semantically similar products
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def compute_semantic_score(query: str, result: SearchResult) -> float:
    """Compute semantic similarity between query and result."""
    query_embedding = model.encode(query)
    result_text = f"{result.title} {result.description}"
    result_embedding = model.encode(result_text)

    # Cosine similarity
    similarity = cosine_similarity([query_embedding], [result_embedding])[0][0]
    return float(similarity)
```

4. **Confidence Scoring:**
```python
def compute_match_score_enhanced(
    result: SearchResult,
    query: str,
    choice_answers: Dict
) -> float:
    """
    Enhanced match scoring with multiple signals.

    Factors:
        - Title relevance (40%)
        - Attribute matches (30%)
        - Price fit (10%)
        - Image quality (10%)
        - Merchant reputation (10%)
    """
    score = 0.0

    # Title relevance (existing logic)
    title_score = compute_basic_title_match(result.title, query)
    score += 0.4 * title_score

    # Attribute matches
    attr_score = 0.0
    for key, value in choice_answers.items():
        if str(value).lower() in result.title.lower():
            attr_score += 1.0
    if choice_answers:
        attr_score /= len(choice_answers)
    score += 0.3 * attr_score

    # Price fit (prefer near budget if specified)
    if "max_price" in choice_answers:
        max_price = choice_answers["max_price"]
        if result.price <= max_price:
            # Better score for prices using 80-100% of budget
            price_score = min(result.price / max_price, 1.0)
            score += 0.1 * price_score
    else:
        score += 0.1  # No preference

    # Image quality
    if result.image_url:
        score += 0.1

    # Merchant reputation (prefer well-known merchants)
    trusted_merchants = ["amazon", "walmart", "target", "nike", "bestbuy"]
    if any(m in result.merchant_domain for m in trusted_merchants):
        score += 0.1

    return min(score, 1.0)
```

---

## 13. Monitoring and Observability

### 13.1 Key Metrics

**API Performance Metrics:**
```python
# Prometheus metrics
google_shopping_requests_total = Counter(
    'google_shopping_requests_total',
    'Total Google Shopping API requests',
    ['status', 'provider']
)

google_shopping_request_duration_seconds = Histogram(
    'google_shopping_request_duration_seconds',
    'Google Shopping API request duration',
    ['provider']
)

google_shopping_quota_remaining = Gauge(
    'google_shopping_quota_remaining',
    'Remaining daily quota'
)

google_shopping_cache_hits_total = Counter(
    'google_shopping_cache_hits_total',
    'Cache hit rate'
)
```

**Dashboard Panels:**
1. Requests per minute (RPM)
2. Average response time (P50, P95, P99)
3. Error rate by type
4. Quota usage (current vs. limit)
5. Cache hit rate
6. Cost per search (estimated)

### 13.2 Alerting Rules

```yaml
# alerts.yml
groups:
  - name: google_shopping
    interval: 30s
    rules:
      - alert: GoogleShoppingQuotaHigh
        expr: google_shopping_quota_remaining < 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Google Shopping quota running low"
          description: "Less than 1000 queries remaining today"

      - alert: GoogleShoppingHighErrorRate
        expr: |
          rate(google_shopping_requests_total{status="error"}[5m])
          / rate(google_shopping_requests_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Google Shopping error rate > 10%"

      - alert: GoogleShoppingSlowResponses
        expr: |
          histogram_quantile(0.95,
            rate(google_shopping_request_duration_seconds_bucket[5m])
          ) > 5.0
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Google Shopping P95 latency > 5 seconds"
```

### 13.3 Logging Strategy

```python
import structlog

logger = structlog.get_logger()

async def search(self, query: str, **kwargs) -> List[SearchResult]:
    """Search with comprehensive logging."""

    request_id = str(uuid.uuid4())

    logger.info(
        "google_shopping_search_start",
        request_id=request_id,
        query=query,
        filters=kwargs
    )

    start_time = time.time()

    try:
        results = await self._make_request(query, **kwargs)

        duration = time.time() - start_time

        logger.info(
            "google_shopping_search_success",
            request_id=request_id,
            query=query,
            result_count=len(results),
            duration_seconds=duration
        )

        return results

    except Exception as e:
        duration = time.time() - start_time

        logger.error(
            "google_shopping_search_error",
            request_id=request_id,
            query=query,
            error=str(e),
            error_type=type(e).__name__,
            duration_seconds=duration
        )

        raise
```

---

## 14. Security Considerations

### 14.1 API Key Management

**Storage:**
```bash
# .env (never committed)
GOOGLE_SHOPPING_API_KEY=AIza...your-key

# Production: Use secrets manager
# AWS Secrets Manager, Google Secret Manager, or Vault
```

**Rotation Strategy:**
```python
class RotatingAPIKey:
    """Support for multiple API keys with automatic rotation."""

    def __init__(self, keys: List[str]):
        self.keys = keys
        self.current_index = 0
        self.failure_counts = {key: 0 for key in keys}

    def get_key(self) -> str:
        """Get current API key."""
        return self.keys[self.current_index]

    def rotate(self):
        """Rotate to next key after quota or error."""
        self.current_index = (self.current_index + 1) % len(self.keys)
        logger.info(f"Rotated to API key #{self.current_index + 1}")

    def mark_failure(self, key: str):
        """Track failures for circuit breaker."""
        self.failure_counts[key] += 1
        if self.failure_counts[key] > 10:
            logger.error(f"API key has >10 failures: {key[:10]}...")
```

### 14.2 Rate Limiting User Requests

**Prevent abuse:**
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/api/search")
@limiter.limit("30/minute")  # 30 searches per minute per user
async def search(
    request: Request,
    body: SearchRequest,
    user: User = Depends(get_current_user)
):
    """Search endpoint with rate limiting."""
    pass
```

### 14.3 Data Privacy

**Handling Sensitive Queries:**
```python
def anonymize_query_for_logging(query: str) -> str:
    """
    Remove potentially sensitive information from logs.

    Examples:
        "John Smith's birthday gift" → "[NAME]'s birthday gift"
        "Buy prescription for 123-45-6789" → "Buy prescription for [SSN]"
    """
    # Remove names (basic regex, improve with NER)
    query = re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]', query)

    # Remove SSN
    query = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', query)

    # Remove credit cards
    query = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CC]', query)

    return query
```

---

## 15. Testing Strategy

### 15.1 Unit Tests

```python
# apps/backend/tests/test_google_shopping.py

import pytest
from unittest.mock import AsyncMock, patch
from sourcing import GoogleShoppingProvider, SearchResult

@pytest.fixture
def provider():
    return GoogleShoppingProvider(api_key="test_key")

@pytest.fixture
def mock_google_response():
    return {
        "items": [
            {
                "id": "1",
                "title": "Montana State Bobcats T-Shirt",
                "link": "https://example.com/product/1",
                "price": {"value": "29.99", "currency": "USD"},
                "imageLink": "https://cdn.example.com/img.jpg",
                "brand": "Nike",
            }
        ]
    }

@pytest.mark.asyncio
async def test_search_success(provider, mock_google_response):
    """Test successful search returns mapped results."""

    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.json.return_value = mock_google_response
        mock_get.return_value.status_code = 200

        results = await provider.search("Montana State shirts")

        assert len(results) == 1
        assert results[0].title == "Montana State Bobcats T-Shirt"
        assert results[0].price == 29.99
        assert results[0].source == "google_shopping_api"

@pytest.mark.asyncio
async def test_search_quota_exceeded(provider):
    """Test quota exceeded handling."""

    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.status_code = 429
        mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Quota exceeded", request=None, response=mock_get.return_value
        )

        with pytest.raises(QuotaExceededError):
            await provider.search("test query")

@pytest.mark.asyncio
async def test_search_with_cache(provider):
    """Test cache hit returns cached results without API call."""

    # Warm cache
    cached_results = [
        SearchResult(
            title="Cached Product",
            price=19.99,
            currency="USD",
            merchant="Test",
            url="https://test.com",
            merchant_domain="test.com",
            source="google_shopping_api"
        )
    ]
    provider._cache.set("test query", cached_results)

    # Should not make API call
    with patch('httpx.AsyncClient.get') as mock_get:
        results = await provider.search("test query")

        assert len(results) == 1
        assert results[0].title == "Cached Product"
        mock_get.assert_not_called()
```

### 15.2 Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_search():
    """Test complete search flow from API to database."""

    # Create test user and row
    user = await create_test_user()
    row = await create_test_row(user_id=user.id, title="Montana State shirt")

    # Trigger search
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/sourcing/search",
            json={"query": "Montana State shirt", "rowId": row.id},
            headers={"Authorization": f"Bearer {user.token}"}
        )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert len(data["results"]) > 0

    # Verify results contain Google Shopping offers
    sources = [r["source"] for r in data["results"]]
    assert "google_shopping_api" in sources

    # Verify results were persisted as bids
    bids = await db.get_bids(row_id=row.id)
    assert len(bids) > 0
```

### 15.3 Load Testing

```python
# locust_load_test.py
from locust import HttpUser, task, between

class ShoppingAgentUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def search_product(self):
        """Simulate product search."""
        self.client.post(
            "/api/search",
            json={
                "query": "Montana State shirts",
                "providers": ["google_shopping"]
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(1)
    def refresh_row(self):
        """Simulate row refresh."""
        self.client.post(
            "/api/search",
            json={
                "query": "laptops",
                "rowId": 123,
                "providers": ["google_shopping"]
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )

    def on_start(self):
        """Login and get token."""
        response = self.client.post("/api/auth/start", json={"email": "test@example.com"})
        self.token = response.json()["token"]
```

**Run:**
```bash
locust -f locust_load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10
```

---

## 16. Rollout Plan

### 16.1 Feature Flag Strategy

```python
# Feature flag configuration
GOOGLE_SHOPPING_ENABLED = os.getenv("GOOGLE_SHOPPING_ENABLED", "false").lower() == "true"
GOOGLE_SHOPPING_ROLLOUT_PERCENTAGE = int(os.getenv("GOOGLE_SHOPPING_ROLLOUT_PERCENTAGE", "0"))

def should_use_google_shopping(user_id: int) -> bool:
    """
    Determine if user should get Google Shopping results.

    Supports gradual rollout: 0% → 10% → 50% → 100%
    """
    if not GOOGLE_SHOPPING_ENABLED:
        return False

    if GOOGLE_SHOPPING_ROLLOUT_PERCENTAGE >= 100:
        return True

    # Consistent hash-based rollout
    user_hash = int(hashlib.sha256(f"user_{user_id}".encode()).hexdigest()[:8], 16)
    return (user_hash % 100) < GOOGLE_SHOPPING_ROLLOUT_PERCENTAGE
```

### 16.2 Rollout Phases

**Phase 1: Internal Testing (Week 1)**
- Enable for internal users only (user_id < 100)
- Monitor error rates and response times
- Validate result quality manually

**Phase 2: Beta Users (Week 2)**
- Rollout to 10% of users
- Collect feedback via in-app survey
- Monitor quota usage and costs

**Phase 3: Gradual Rollout (Week 3-4)**
- 10% → 25% → 50% → 75% → 100%
- Ramp up based on metrics:
  - Error rate < 1%
  - P95 latency < 3s
  - User satisfaction > 80%

**Phase 4: Full Availability (Week 5)**
- Enable for all users
- Make Google Shopping default provider
- Document lessons learned

### 16.3 Rollback Criteria

**Automatic Rollback Triggers:**
1. Error rate > 5% for 10 minutes
2. P95 latency > 10 seconds for 5 minutes
3. Quota exhausted before 6pm daily
4. User complaints > 10 in 1 hour

**Rollback Process:**
```bash
# Emergency rollback
export GOOGLE_SHOPPING_ENABLED=false
# Restart services
kubectl rollout restart deployment/backend -n production

# Or gradual rollback
export GOOGLE_SHOPPING_ROLLOUT_PERCENTAGE=0
```

---

## 17. Success Metrics

### 17.1 Technical KPIs

| Metric | Target | Current Baseline |
|--------|--------|------------------|
| Search response time (P95) | <3s | ~2s (SerpAPI) |
| Error rate | <1% | <0.5% |
| Cache hit rate | >60% | N/A |
| Quota utilization | <80% daily | N/A |
| Image load time | <1s | ~1.5s |

### 17.2 Product KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Offers per row | ≥10 | Avg offers from Google Shopping |
| Result relevance | >80% match score | User feedback + algo score |
| User satisfaction | >4.0/5.0 | Post-search survey |
| Conversion rate | >5% | Clickout → purchase |
| Cost per search | <$0.01 | Within free quota |

### 17.3 Business KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Affiliate revenue | +20% | Google Shopping clicks × commission |
| User retention | +10% | More searches per user |
| Time to first offer | <5s | Faster sourcing → happy users |
| Product catalog size | 10M+ | Addressable products via Google |

---

## 18. Future Enhancements

### 18.1 Phase 2 Features

1. **Price Tracking and Alerts**
   - Monitor saved products for price drops
   - Email alerts when price drops below threshold
   - Historical price charts

2. **Advanced Filtering**
   - Filter by seller rating
   - Filter by shipping speed
   - Filter by return policy

3. **Personalized Rankings**
   - Learn user preferences (brand, merchant, price range)
   - Re-rank results based on past selections
   - Collaborative filtering

4. **Multi-Currency Support**
   - Detect user location
   - Display prices in local currency
   - Real-time exchange rates

### 18.2 Phase 3 Features

1. **Google Merchant Center Integration**
   - Become a merchant ourselves
   - List user RFP requests as "products"
   - Receive bids from sellers via Google Shopping

2. **Image Search**
   - Upload product image
   - Google Vision API → extract product details
   - Search Google Shopping by image

3. **Voice Search**
   - "Hey agent, find me Montana State shirts under $30"
   - Speech-to-text → Google Shopping search

4. **AR Try-On**
   - Leverage Google Shopping AR features
   - Virtual try-on for clothing/accessories

---

## 19. Architecture Decision Records (ADRs)

### ADR-001: Use Content API for Shopping over Third-Party Scrapers

**Status:** Accepted

**Context:**
Need to integrate Google Shopping for auto-bidding. Options:
1. Content API for Shopping (official)
2. SerpAPI/SearchAPI (third-party scraper)
3. Custom web scraping

**Decision:**
Use Content API for Shopping as primary, with SerpAPI as fallback.

**Rationale:**
- Official API: No TOS violations
- Better data quality: Direct from Google
- Free tier: 10,000 QPD sufficient for MVP
- Scalable: Can request quota increases

**Consequences:**
- Requires Google Cloud account setup
- Need to manage API quotas
- Fallback to SerpAPI for overflow

---

### ADR-002: Proxy Images Through Backend vs Direct CDN

**Status:** Accepted

**Context:**
Google Shopping returns image URLs hosted by merchants. Options:
1. Direct passthrough (frontend → merchant CDN)
2. Proxy through backend (frontend → backend → merchant CDN)
3. Download and host (frontend → our CDN)

**Decision:**
Implement proxy with caching (Option 2).

**Rationale:**
- Privacy: Prevent merchant tracking
- Reliability: Merchants may rate-limit or block
- Performance: Add caching layer
- Flexibility: Can add resizing/optimization

**Consequences:**
- Additional backend load (mitigated by caching)
- Increased storage (Redis for cached images)
- More control over UX

---

### ADR-003: Integrate as SourcingProvider vs Separate Service

**Status:** Accepted

**Context:**
How to integrate Google Shopping into architecture. Options:
1. Add as new `SourcingProvider` in existing pattern
2. Create separate microservice
3. Direct API calls from frontend

**Decision:**
Implement as `GoogleShoppingProvider` in existing pattern.

**Rationale:**
- Consistency: Follows existing provider pattern
- Simplicity: No new services to deploy
- Parallel execution: Automatic with current design
- Deduplication: Natural with existing logic

**Consequences:**
- Couples to existing sourcing.py module
- Shares timeout and error handling with other providers
- Easier to test and maintain

---

## 20. Open Questions and Risks

### 20.1 Open Questions

1. **Should we request Merchant Center access for higher quotas?**
   - Pros: 100k QPD, access to merchant APIs
   - Cons: Requires business verification, takes 2-4 weeks

2. **How to handle products not in Google Shopping?**
   - Example: Local services, B2B products
   - Solution: Keep other providers (eBay, manual bids)

3. **What's the optimal cache TTL for different product categories?**
   - Electronics: 30 min (fast-moving prices)
   - Clothing: 2 hours (stable prices)
   - Books: 6 hours (very stable)

4. **Should we enrich all results with reviews or just top 10?**
   - Trade-off: Data quality vs API quota usage

### 20.2 Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Quota exceeded | Medium | High | Implement aggressive caching, fallback to SerpAPI |
| Google changes API | Low | High | Monitor API changelog, maintain fallback providers |
| Poor result quality | Medium | Medium | Implement post-filtering, user feedback loop |
| Slow response times | Low | Medium | Set timeouts, use parallel fetching, cache aggressively |
| Affiliate integration issues | Medium | Low | Test with small $ transactions first |

---

## 21. Summary and Next Steps

### 21.1 Executive Summary

This architecture integrates Google Content API for Shopping as a new sourcing provider, enabling automatic generation of high-quality product bids. The design:

1. Leverages existing provider pattern for minimal disruption
2. Operates within free API quotas via intelligent caching
3. Achieves <3s response time with parallel fetching
4. Provides comprehensive product data (images, prices, reviews)
5. Integrates seamlessly with affiliate link system

**Expected Impact:**
- 10x more products available (1M → 10M+)
- 30% faster sourcing (<5s → <3s)
- 20% higher affiliate revenue (more quality options)
- Zero marginal cost within free tier

### 21.2 Immediate Next Steps

**Week 1:**
1. [ ] Create Google Cloud project
2. [ ] Enable Shopping Content API
3. [ ] Obtain API key
4. [ ] Implement `GoogleShoppingProvider` class
5. [ ] Write unit tests
6. [ ] Deploy to staging

**Week 2:**
7. [ ] Internal testing with team
8. [ ] Integrate image proxy endpoint
9. [ ] Add review enrichment
10. [ ] Performance optimization
11. [ ] Deploy to production (10% rollout)

**Week 3:**
12. [ ] Monitor metrics and user feedback
13. [ ] Gradual rollout to 50%
14. [ ] Implement advanced filtering
15. [ ] Full rollout to 100%

---

## Appendices

### Appendix A: API Endpoint Reference

```
Google Shopping Content API v2.1

Base URL: https://shoppingcontent.googleapis.com/content/v2.1

Endpoints:
- GET /products
  List products matching search query

- GET /products/{productId}
  Get details for specific product

- GET /products/{productId}/productreviews
  Get review aggregates for product

- GET /productstatuses/{productId}
  Check product availability status
```

### Appendix B: Environment Variables

```bash
# Google Shopping API
GOOGLE_SHOPPING_API_KEY=AIza...your-key
GOOGLE_SHOPPING_COUNTRY=US
GOOGLE_SHOPPING_LANGUAGE=en
GOOGLE_SHOPPING_ENABLED=true
GOOGLE_SHOPPING_ROLLOUT_PERCENTAGE=100
GOOGLE_MERCHANT_ID=optional-merchant-id

# Quotas and Limits
GOOGLE_SHOPPING_DAILY_QUOTA=10000
GOOGLE_SHOPPING_MINUTE_QUOTA=300
SOURCING_PROVIDER_TIMEOUT_SECONDS=8.0

# Caching
GOOGLE_SHOPPING_CACHE_TTL=3600
REDIS_URL=redis://localhost:6379/0
```

### Appendix C: Code Examples

See complete implementation in:
- `/Volumes/PivotNorth/Shopping Agent/apps/backend/sourcing.py` (line 500+)
- `/Volumes/PivotNorth/Shopping Agent/apps/backend/affiliate.py` (GoogleShoppingAffiliateHandler)
- `/Volumes/PivotNorth/Shopping Agent/apps/frontend/app/components/OfferTile.tsx` (source badges)

---

**Document End**

For questions or clarifications, contact: architecture@shoppingagent.com
