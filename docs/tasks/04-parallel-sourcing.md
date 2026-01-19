# Task 04: Parallel Sourcing + Normalization

**Priority:** P1  
**Estimated Time:** 1 day  
**Dependencies:** None (can run in parallel with Tasks 01-03)  
**Outcome:** Faster search, unified Offer model with match scoring

---

## Objective

1. Refactor `SourcingRepository.search_all()` to run providers in parallel
2. Add per-provider timeouts to prevent slow providers from blocking
3. Normalize offer data into consistent schema
4. Lay groundwork for Planner/Worker pattern (future multi-agent)

---

## Current State

```python
# apps/backend/sourcing.py - SEQUENTIAL
async def search_all(self, query: str, **kwargs) -> List[SearchResult]:
    all_results = []
    for name, provider in self.providers.items():  # One at a time!
        try:
            results = await provider.search(query, **kwargs)
            all_results.extend(results)
        except Exception as e:
            print(f"Provider {name} failed: {e}")
    return all_results
```

**Problems:**
- Sequential execution — 5 providers × 1-3 seconds each = 5-15 seconds
- No timeout per provider — one slow provider blocks everything
- No deduplication — same product from multiple providers
- No match scoring — all results treated equally

---

## Target State

```python
# PARALLEL with timeouts
async def search_all(self, query: str, **kwargs) -> List[SearchResult]:
    tasks = [
        asyncio.wait_for(provider.search(query, **kwargs), timeout=3.0)
        for provider in self.providers.values()
    ]
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)
    # flatten, dedupe, normalize
```

**Benefits:**
- All providers run simultaneously — total time ≈ slowest provider (3s max)
- Failed providers don't block others
- Consistent data quality

---

## Implementation Steps

### Step 4.1: Refactor search_all() for Parallel Execution

**File:** `apps/backend/sourcing.py`

```python
import asyncio
from typing import List, Dict, Any

PROVIDER_TIMEOUT_SECONDS = 3.0  # Max wait per provider

class SourcingRepository:
    # ... existing __init__ ...
    
    async def search_all(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Search all providers in parallel with timeouts.
        
        Args:
            query: Search query string
            **kwargs: Additional params (gl, hl for locale)
        
        Returns:
            List of SearchResults from all successful providers
        """
        print(f"[SourcingRepository] search_all called with query: {query}")
        print(f"[SourcingRepository] Available providers: {list(self.providers.keys())}")
        
        # Create tasks with timeouts
        async def search_with_timeout(name: str, provider: SourcingProvider) -> List[SearchResult]:
            try:
                print(f"[SourcingRepository] Starting search with provider: {name}")
                results = await asyncio.wait_for(
                    provider.search(query, **kwargs),
                    timeout=PROVIDER_TIMEOUT_SECONDS
                )
                print(f"[SourcingRepository] Provider {name} returned {len(results)} results")
                return results
            except asyncio.TimeoutError:
                print(f"[SourcingRepository] Provider {name} timed out after {PROVIDER_TIMEOUT_SECONDS}s")
                return []
            except Exception as e:
                print(f"[SourcingRepository] Provider {name} failed: {e}")
                return []
        
        # Run all providers in parallel
        tasks = [
            search_with_timeout(name, provider)
            for name, provider in self.providers.items()
        ]
        results_lists = await asyncio.gather(*tasks)
        
        # Flatten results
        all_results = []
        for results in results_lists:
            all_results.extend(results)
        
        # Filter invalid URLs
        filtered_results = [
            r for r in all_results 
            if r.url and r.url.startswith(('http://', 'https://'))
        ]
        
        print(f"[SourcingRepository] Total results: {len(all_results)}")
        print(f"[SourcingRepository] Results with valid URL: {len(filtered_results)}")
        
        return filtered_results
```

- [ ] Import `asyncio` at top of file
- [ ] Add `PROVIDER_TIMEOUT_SECONDS` constant
- [ ] Refactor `search_all()` to use `asyncio.gather()`
- [ ] Add `search_with_timeout()` wrapper function
- [ ] Handle `TimeoutError` gracefully

**Test:** Search completes in ~3s regardless of slow providers

---

### Step 4.2: Add Deduplication

**File:** `apps/backend/sourcing.py`

```python
def deduplicate_results(results: List[SearchResult]) -> List[SearchResult]:
    """
    Remove duplicate offers based on URL or title+merchant.
    
    Keeps the first occurrence (assumes earlier providers are higher priority).
    """
    seen_urls = set()
    seen_titles = set()
    unique = []
    
    for r in results:
        # Normalize URL for comparison
        url_key = r.url.lower().rstrip('/')
        title_key = f"{r.title.lower()}|{r.merchant.lower()}"
        
        if url_key in seen_urls or title_key in seen_titles:
            continue
        
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        unique.append(r)
    
    return unique
```

Then in `search_all()`:

```python
# After filtering invalid URLs
deduplicated = deduplicate_results(filtered_results)
print(f"[SourcingRepository] After deduplication: {len(deduplicated)}")
return deduplicated
```

- [ ] Add `deduplicate_results()` function
- [ ] Call after filtering in `search_all()`

**Test:** Duplicate URLs/titles are removed

---

### Step 4.3: Normalize Price/Currency

**File:** `apps/backend/sourcing.py`

```python
def normalize_price(price: Any, currency: str = "USD") -> tuple[float, str]:
    """
    Normalize price to float and standardize currency.
    
    Handles:
        - String prices: "$49.99", "49.99 USD"
        - Int/float prices: 49.99, 4999 (cents)
        - Missing prices: returns 0.0
    """
    if price is None:
        return 0.0, currency
    
    if isinstance(price, str):
        # Remove currency symbols and whitespace
        cleaned = price.replace('$', '').replace('£', '').replace('€', '').strip()
        # Extract first number
        import re
        match = re.search(r'[\d,]+\.?\d*', cleaned)
        if match:
            return float(match.group().replace(',', '')), currency
        return 0.0, currency
    
    if isinstance(price, (int, float)):
        return float(price), currency
    
    return 0.0, currency
```

- [ ] Add `normalize_price()` function
- [ ] Apply in each provider's search method (or in post-processing)

**Test:** Various price formats normalized correctly

---

### Step 4.4: Add Match Score (Basic)

**File:** `apps/backend/sourcing.py`

Add `match_score` to `SearchResult`:

```python
class SearchResult(BaseModel):
    # ... existing fields ...
    match_score: float = 0.0  # 0-1, how well this matches the query
```

Basic scoring function:

```python
def compute_match_score(result: SearchResult, query: str) -> float:
    """
    Compute a basic relevance score for a search result.
    
    Factors:
        - Title contains query words
        - Has image
        - Has rating
        - Has reviews
        - Price is present
    
    Returns: 0.0 - 1.0
    """
    score = 0.0
    query_words = set(query.lower().split())
    title_words = set(result.title.lower().split())
    
    # Title relevance (0-0.4)
    overlap = len(query_words & title_words)
    if query_words:
        score += 0.4 * (overlap / len(query_words))
    
    # Has image (0.15)
    if result.image_url:
        score += 0.15
    
    # Has rating (0.15)
    if result.rating and result.rating > 0:
        score += 0.15
    
    # Has reviews (0.15)
    if result.reviews_count and result.reviews_count > 0:
        score += 0.15
    
    # Has price (0.15)
    if result.price and result.price > 0:
        score += 0.15
    
    return min(score, 1.0)
```

Apply in `search_all()`:

```python
# After deduplication
for result in deduplicated:
    result.match_score = compute_match_score(result, query)

# Sort by match score
deduplicated.sort(key=lambda r: r.match_score, reverse=True)
```

- [ ] Add `match_score` field to `SearchResult`
- [ ] Add `compute_match_score()` function
- [ ] Apply scoring and sort in `search_all()`

**Test:** Results sorted by relevance, scores make sense

---

### Step 4.5: Update Frontend Store for match_score

**File:** `apps/frontend/app/store.ts`

```typescript
export interface Offer {
  // ... existing fields ...
  match_score?: number;  // ADD THIS
}
```

- [ ] Add `match_score` to `Offer` interface

**Test:** TypeScript compiles

---

### Step 4.6: Visual Match Score in OfferTile (Optional)

**File:** `apps/frontend/app/components/OfferTile.tsx`

```tsx
{offer.match_score && offer.match_score > 0.7 && (
  <div className="absolute top-1 right-1 bg-green-500 text-white text-xs px-1 rounded">
    Best Match
  </div>
)}
```

- [ ] Add visual indicator for high-scoring offers (optional)

---

### Step 4.7: Add Performance Metrics Logging

**File:** `apps/backend/sourcing.py`

```python
import time

async def search_all(self, query: str, **kwargs) -> List[SearchResult]:
    start_time = time.time()
    
    # ... existing parallel search code ...
    
    elapsed = time.time() - start_time
    print(f"[SourcingRepository] Search completed in {elapsed:.2f}s")
    print(f"[SourcingRepository] Provider breakdown: ...")  # Add per-provider timing
    
    return deduplicated
```

- [ ] Add timing metrics
- [ ] Log per-provider performance (for optimization)

**Test:** Logs show search time < 4s with parallel execution

---

## Acceptance Criteria

- [ ] All providers run in parallel
- [ ] Per-provider timeout of 3 seconds
- [ ] Slow/failing providers don't block others
- [ ] Duplicate results removed
- [ ] Results sorted by `match_score`
- [ ] Total search time ≈ slowest provider (not sum)

---

## Performance Targets

| Metric | Before | After |
|--------|--------|-------|
| Search time (5 providers) | 5-15s | 3-4s |
| Duplicate rate | ~20% | 0% |
| Results sorted by relevance | No | Yes |

---

## Future: Planner/Worker Pattern (Phase 2)

The PRD describes a more sophisticated multi-agent architecture:

```
Planner (LLM) → decides which providers to hit
    ↓
Workers (tasks) → parallel provider calls
    ↓
Evaluator (LLM) → normalize, enrich, score
    ↓
Aggregator → final Offer list
```

This task lays the groundwork. The Planner would:
1. Analyze query to determine relevant providers
2. Generate query variants per provider
3. Set budget/timeout per provider

**Defer to Phase 2** when we have more providers and need smarter routing.

---

## Files Changed

| File | Action |
|------|--------|
| `apps/backend/sourcing.py` | Refactor `search_all()`, add helpers |
| `apps/frontend/app/store.ts` | Add `match_score` to Offer |
| `apps/frontend/app/components/OfferTile.tsx` | Optional match indicator |
