# PRD: Search & Display Architecture Fix

**Status**: Draft  
**Date**: 2026-02-15  
**Origin**: Deep codebase audit (16 root causes identified across backend filtering, SSE pipeline, scorer, and frontend display)  
**Priority**: P0 — fixes are prerequisites for Outreach and Quantum Re-Ranking PRDs to function correctly  
**Depends on**: PRD_Desire_Classification (desire_tier already implemented but not enforced)

---

## 1. The Problem (Spirit)

BuyAnything's core promise is: tell us what you want and we'll find it — from a $5 bathtub toy to a $50M yacht. The system *already* classifies user intent correctly (desire_tier works). But the classification signal **dissolves** before it reaches the user. Between the LLM saying "this is bespoke" and the user seeing results, the signal passes through 4 different filtering functions (each with different logic), a scorer that treats tier as a gentle suggestion, a streaming pipeline that silently drops results, and a frontend that treats every tile identically.

The result: a user searching for "custom diamond earrings, budget $50k+" sees $148 Amazon stud earrings alongside Tiffany & Co. — or worse, sees "No results found" because the streaming pipeline dropped everything.

### The Boat Test

A user types **"boat"**. This is ambiguous. The system should ask: *"Are you looking for a toy boat, a ski boat, or a yacht?"*

After refinement to **"mega yacht"**, the system should:
1. Reclassify to `high_value`
2. Drop ALL previous toy boat results
3. Skip Amazon/eBay entirely
4. Show yacht brokers from the vendor directory
5. NOT show "$0.00" prices — show "Request Quote"

After refinement to **"bathtub toy for my kid"**, the system should:
1. Reclassify to `commodity`
2. Drop ALL previous results
3. Search Amazon — it's perfect for this
4. Show results sorted by price, reviews, shipping speed
5. NOT show yacht brokers

**Today, neither scenario works correctly.** Old bids survive refinements (bug #11), cheap Amazon results outrank vendors (bug #4), vendor results are silently dropped by the streaming pipeline (bug #2), and the frontend shows everything identically regardless of tier.

### The Adjacent Intent Problem

A user searching for a **private jet** might also want:
- A book about buying private jets (informational)
- A jet charter service (alternative fulfillment)
- An aviation consultant (advisory)

The current system has no concept of "adjacent intent" — it runs one query and returns one flat list. This is a future capability (Phase 4), but the architecture should not preclude it.

---

## 2. Root Causes (16 Issues)

### Data Model
| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 1 | `Bid.price: float` is non-nullable — vendors stored as `0.0` | Every filter/display path needs special-casing for price=0 | Make `Optional[float] = None` |
| 15 | `Vendor` has no `price_range` or `tier_affinity` | Scorer can't distinguish yacht broker from toy store | Add `price_range_min`, `price_range_max`, `tier_affinity` |

### Filtering (4 copies, 4 behaviors)
| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 2 | Streaming path drops `price=0` results; non-streaming keeps them | Chat-initiated searches lose vendor results that refresh would keep | Single filter function |
| 12 | `service.py` treats min_price as aspirational; `rows.py` treats it as hard | Same bid passes in one path, fails in another | Tier-aware filter: commodity=hard, bespoke=skip |
| 3 | `skip_web_search` declared but `_filter_providers_by_tier` is a no-op | Amazon runs for private jet searches, returning toy planes | Actually gate providers by tier |

### Scoring
| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 4 | Scorer: tier_fit is additive 20%, not a gate | $148 Amazon earrings tie with Tiffany for bespoke query | Tier_fit as multiplier for non-matching sources |
| 9 | Vendors have weak metadata → low relevance scores | Keyword matching favors Amazon (rich titles) over vendors (company names) | Vendor relevance should use embedding similarity, not keyword match |

### Refinement Flow
| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 11 | `_update_row()` ignores `reset_bids` parameter | Old toy boat bids survive when user refines to "yacht" | Implement the delete |
| 13 | Constraint changes don't re-filter existing bids | Old bids with wrong color/size/price persist | Re-filter on constraint change |

### SSE Pipeline
| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 5 | URL filter in `search_streaming` drops `mailto:` vendors | Vendors without websites never appear | Allow `mailto:` URLs |
| 7 | 3 frontend paths race to write `rowResults` | Results flicker, get overwritten, show empty | Single authoritative path |

### Frontend Display
| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 6 | `is_service_provider` inconsistent with source-based detection | Vendor tiles show "$0.00" instead of "Request Quote" | Use `source` as ground truth, not `is_service_provider` flag |
| 8 | `desire_tier` doesn't reach frontend display logic | All tiles look identical regardless of tier | Use tier for sort, price visibility, button labels |
| 10 | No end-to-end "intention" signal | Tier is classified but not enforced | Flow tier through every layer |
| 16 | Sort defaults to "Featured" with no "Best Match" option | User can't sort by scorer relevance | Add `combined_score`-based sort |

### Future (not blocking)
| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 14 | No adjacent intent capability | Can't show "books about jets" alongside "jet vendors" | Multi-query per request (Phase 4) |

---

## 3. Technical Design

### Phase 1: Data Model Fixes (P0 — foundation)

#### 3.1.1 Make `Bid.price` nullable

**File**: `models/bids.py`

```python
# Before
price: float

# After
price: Optional[float] = None  # None = quote-based (no fixed price). 0.0 = actually free.
```

**Migration**:
```sql
-- Alembic migration
ALTER TABLE bid ALTER COLUMN price DROP NOT NULL;
ALTER TABLE bid ALTER COLUMN price SET DEFAULT NULL;
UPDATE bid SET price = NULL WHERE price = 0 AND source = 'vendor_directory';
```

**Cascade changes**:
- `Offer.price` in frontend `store.ts`: `number` → `number | null`
- `OfferTile.tsx`: render "Request Quote" when `price === null`, not when `price === 0`
- All 4 filter paths: `None` means "skip price filtering for this bid" (no special-casing needed)
- Scorer `_price_score`: `None` → return 0.5 (neutral), not 0.3

#### 3.1.2 Add vendor tier metadata

**File**: `models/bids.py` (Vendor class)

```python
# New fields
price_range_min: Optional[float] = None    # Typical minimum order/price
price_range_max: Optional[float] = None    # Typical maximum order/price
tier_affinity: Optional[str] = None        # commodity, considered, luxury, enterprise
```

**Migration**:
```sql
ALTER TABLE vendor ADD COLUMN price_range_min FLOAT;
ALTER TABLE vendor ADD COLUMN price_range_max FLOAT;
ALTER TABLE vendor ADD COLUMN tier_affinity VARCHAR(20);
```

This enables the scorer to match vendors to desire tiers: a yacht broker (`tier_affinity: "enterprise"`) scores high for `high_value` queries and low for `commodity` queries, even before keyword matching.

#### 3.1.3 Fix `_update_row` to honor `reset_bids`

**File**: `routes/chat.py`

```python
async def _update_row(session, row, title=None, constraints=None, reset_bids=False):
    if reset_bids:
        await session.exec(delete(Bid).where(Bid.row_id == row.id))
    # ... rest of existing logic
```

One line. Fixes the entire refinement flow.

---

### Phase 2: Single Filter Function (P1)

#### 3.2.1 Extract unified filter

**New file**: `sourcing/filters.py`

```python
from sourcing.constants import NON_SHOPPING_SOURCES, SERVICE_SOURCES

def should_include_result(
    price: Optional[float],
    source: str,
    desire_tier: Optional[str],
    min_price: Optional[float],
    max_price: Optional[float],
    is_service_provider: bool = False,
) -> bool:
    """Single source of truth for price/source filtering.
    
    Rules:
    - price=None (quote-based): ALWAYS include — cannot be price-filtered
    - source in exempt set: ALWAYS include — these are vendors/services
    - desire_tier in (service, bespoke, high_value): SKIP price filtering
    - Otherwise: apply min/max price as hard filters
    """
    # Quote-based results always pass
    if price is None:
        return True
    
    # Exempt sources always pass (vendor directory, google CSE, service providers)
    if source in NON_SHOPPING_SOURCES or source in SERVICE_SOURCES or is_service_provider:
        return True
    
    # Non-commodity tiers skip price filtering (vendors don't have fixed prices)
    if desire_tier in ("service", "bespoke", "high_value", "advisory"):
        return True
    
    # Commodity/considered: apply hard price filters
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    
    return True
```

#### 3.2.2 Replace all 4 filter locations

| Location | Current | After |
|----------|---------|-------|
| `rows.py:filter_bids_by_price` | Inline loop | Calls `should_include_result` per bid |
| `service.py:search_and_persist` | max_price only, min aspirational | Calls `should_include_result` |
| `rows_search.py` non-streaming (line 279) | Inline loop, keeps price=0 | Calls `should_include_result` |
| `rows_search.py` streaming (line 402) | Inline loop, drops price=0 | Calls `should_include_result` |

#### 3.2.3 Fix `mailto:` URL filtering

**File**: `sourcing/repository.py` line 1212

```python
# Before
if url[:4] != 'http':
    continue

# After
if url[:4] != 'http' and url[:7] != 'mailto:':
    continue
```

---

### Phase 3: Desire Tier as Routing Signal (P2)

#### 3.3.1 Actually gate providers by tier

**File**: `sourcing/repository.py` → `_filter_providers_by_tier`

```python
def _filter_providers_by_tier(self, providers, desire_tier=None):
    if not desire_tier:
        return providers
    
    WEB_PROVIDERS = {"rainforest", "serpapi", "valueserp", "searchapi", 
                     "google_shopping", "google_cse", "ticketmaster"}
    VENDOR_PROVIDERS = {"vendor_directory"}
    
    if desire_tier in ("service", "bespoke", "high_value"):
        # Vendor directory only — web search can't help
        return {k: v for k, v in providers.items() if k not in WEB_PROVIDERS}
    
    if desire_tier == "advisory":
        # No search at all (handled upstream, but safety net)
        return {}
    
    # commodity / considered: run everything
    return providers
```

#### 3.3.2 Scorer: tier_fit as multiplier

**File**: `sourcing/scorer.py`

```python
# Before (additive — tier is 20% of a sum)
combined = (rs * 0.40) + (tr * 0.20) + (ps * 0.15) + (qs * 0.15) + (db * 0.10)

# After (tier_fit is a multiplier on the base score)
base = (rs * 0.45) + (ps * 0.20) + (qs * 0.20) + (db * 0.15)
combined = base * (0.3 + 0.7 * tr)  # tr=1.0 → full score. tr=0.2 → 44% of score.
```

When `tr=0.2` (big box for bespoke query): `combined = base * 0.44` — a 56% penalty, not 16%.
When `tr=1.0` (vendor for bespoke query): `combined = base * 1.0` — full score.

This makes tier mismatch a real penalty without hard-excluding anything.

#### 3.3.3 Vendor relevance: use embedding distance, not keyword match

**File**: `sourcing/scorer.py` → `_relevance_score`

For `source="vendor_directory"`, the VendorDirectoryProvider already computes cosine distance. Pass this through as `match_score` and use it as the relevance signal instead of keyword matching:

```python
def _relevance_score(result, intent):
    # Vendor results: use embedding similarity (already computed)
    if result.source == "vendor_directory" and hasattr(result, "match_score") and result.match_score:
        # match_score from vendor_provider is 0-1 (higher = better match)
        return min(result.match_score, 1.0)
    
    # Web results: existing keyword matching logic
    # ...
```

#### 3.3.4 Pass tier to frontend display

**Already done**: `Row.desire_tier` is serialized in `row_to_dict()` and available in the frontend `Row` interface. The frontend just doesn't use it.

**File**: `RowStrip.tsx` — use `row.desire_tier` for:
- Default sort: `commodity` → "Price: Low to High"; `bespoke/high_value` → "Best Match"
- Price column visibility: hide for `service/bespoke/high_value` vendor tiles
- Button labels: "Buy Now" for commodity, "Request Quote" for service/bespoke

**File**: `store.ts` — add "Best Match" sort using `combined_score` from bid provenance:

```typescript
export type OfferSortMode = 'original' | 'price_asc' | 'price_desc' | 'best_match';
```

---

### Phase 4: SSE Pipeline & Stale Bid Cleanup (P3)

#### 3.4.1 Re-filter existing bids on constraint change

**File**: `routes/chat.py` → `update_row` action

When constraints change (even without title change), run `filter_bids_by_price` against existing bids and delete those that no longer match:

```python
if constraints and not title_changed:
    # Re-filter existing bids against new constraints
    existing_bids = await session.exec(
        select(Bid).where(Bid.row_id == row.id)
    )
    for bid in existing_bids.all():
        if not should_include_result(
            bid.price, bid.source, tier, 
            new_min_price, new_max_price, bid.is_service_provider
        ):
            await session.delete(bid)
    await session.commit()
```

#### 3.4.2 RowStrip auto-load respects `isSearching`

**File**: `RowStrip.tsx` → auto-load `useEffect`

Add guard: don't trigger `refresh()` while Chat SSE is actively streaming for this row.

```typescript
useEffect(() => {
  if (isActive && !isSearching && !hasMoreIncoming && offers.length === 0 && row.status !== 'archived') {
    refresh('all');
  }
}, [isActive, row.id, isSearching, hasMoreIncoming, offers.length]);
```

#### 3.4.3 Frontend: single authoritative path

The current architecture has 3 paths writing to `rowResults`. The fix (already partially implemented):

| Event | Behavior |
|-------|----------|
| Page load (`setRows`) | Hydrate from `row.bids` via `mapBidToOffer` |
| Chat SSE `search_results` | `appendRowResults` (never replace) |
| Chat SSE `done` | Re-fetch row from DB → `setRowResults` (authoritative replacement) |
| RowStrip `refresh` | Only fires if no SSE active. Uses `setRowResults`. |

The `done` event is the single source of truth. Everything else is optimistic/incremental.

---

### Phase 5: Adjacent Intent (Future)

Not in scope for this PRD, but the architecture should support it:

- LLM emits multiple queries: `[{query, type: "primary"}, {query, type: "informational"}, {query, type: "alternative"}]`
- Each query type maps to different providers and display sections
- Frontend shows: "Top Matches", "You Might Also Want", "Related Services"
- Enables: "books about buying a jet" alongside "jet charter operators"

---

## 4. Test Scenarios

### The Boat Scenario (refinement + tier change)

```
User: "boat"
→ System: asks "Are you looking for a toy boat, a ski boat, or a yacht?"

User: "mega yacht, budget $5M+"
→ desire_tier: high_value
→ Providers: vendor_directory ONLY (no Amazon)
→ Results: yacht brokers, marine dealers
→ Display: "Request Quote" buttons, no price column
→ Old results: NONE (reset_bids=true, title changed)

User: "actually just a bathtub toy for my kid"  
→ desire_tier: commodity
→ Providers: Amazon, eBay, Google Shopping (+ vendor directory but low-ranked)
→ Results: rubber ducks, toy boats, sorted by price
→ Display: prices, "Buy Now" buttons, star ratings
→ Old results: NONE (reset_bids=true, title changed)
```

### The Diamond Earrings Scenario (price filtering + vendor display)

```
User: "custom diamond earrings, budget $50k-$100k"
→ desire_tier: bespoke
→ Providers: vendor_directory ONLY
→ Results: Tiffany, Cartier, Harry Winston, James Allen
→ Price filter: SKIPPED (bespoke tier)
→ Display: "Request Quote" for vendor tiles (price=null, not $0.00)
→ Sort: "Best Match" (by embedding similarity + tier_fit)
```

### The Constraint Refinement Scenario (re-filtering without title change)

```
User: "diamond earrings"
→ desire_tier: considered
→ Results: mix of Amazon + vendors, various prices

User: "min budget $50k"
→ desire_tier changes to bespoke (LLM reclassifies)
→ Old Amazon bids ($148, $299): DELETED (re-filter on constraint change)
→ New search: vendor_directory only
→ Vendor bids: survive (price=null, exempt from price filter)
```

### The Private Jet Scenario (vendor-only + structured constraints)

```
User: "private jet from Teterboro to Aspen, March 15, 4 passengers"
→ desire_tier: service
→ Providers: vendor_directory ONLY
→ Constraints: {origin: "TEB", destination: "ASE", date: "2026-03-15", pax: 4}
→ Results: charter operators matching route/capacity
→ Display: "Request Quote", operator details, no price column
→ Adjacent intent (future): "Complete Guide to Private Jet Charter" (informational)
```

### The AA Batteries Scenario (commodity fast path)

```
User: "AA batteries"
→ desire_tier: commodity
→ Providers: ALL (Amazon, eBay, Google Shopping, vendor directory)
→ Results: Amazon Basics, Energizer, Duracell — sorted by price
→ Vendor results: ranked very low by tier_fit (commodity prefers big box)
→ Display: prices, ratings, "Buy Now" buttons, shipping info
```

---

## 5. Success Metrics

### Letter Metrics
- All 4 filter paths produce identical results for the same input (regression test)
- Zero "$0.00" prices displayed on vendor tiles
- `reset_bids` actually clears bids (unit test)
- `mailto:` vendor URLs no longer dropped (unit test)

### Spirit Metrics
- **The Boat Test**: refinement from "boat" to "yacht" shows ONLY yacht-relevant results within 3 seconds
- **The Diamond Test**: "custom diamond earrings, $50k budget" shows vendor tiles with "Request Quote", zero Amazon results
- **The Battery Test**: "AA batteries" shows Amazon results with prices, sorted by value, within 2 seconds
- **No more "No results found"**: for any query with vendor matches or web results, the user ALWAYS sees something

### Anti-Metrics (things that should NOT happen)
- Vendor tiles showing "$0.00"
- Amazon results appearing for private jet searches
- Old rubber duck bids appearing alongside yacht broker tiles
- "No results found" when the DB has bids for the row
- Frontend flickering between empty and populated states during SSE

---

## 6. Rollout Plan

### Phase 1: Data Model + Bug Fixes (2-3 days)
- Alembic migration: `Bid.price` nullable, Vendor tier fields
- Fix `_update_row` to honor `reset_bids` (1 line)
- Fix `mailto:` URL filtering (1 line)
- Fix `is_service_provider` consistency
- Update all tests

### Phase 2: Unified Filter (1-2 days)
- Create `sourcing/filters.py` with `should_include_result()`
- Replace all 4 inline filter loops
- Add tier-aware filtering logic
- Regression test: identical outputs for all paths

### Phase 3: Scorer + Provider Gating (2-3 days)
- `_filter_providers_by_tier`: actually gate web search for service/bespoke/high_value
- Scorer: tier_fit as multiplier
- Vendor relevance: use embedding distance
- Add "Best Match" sort to frontend

### Phase 4: Frontend Tier-Aware Display (1-2 days)
- Use `desire_tier` for default sort, price visibility, button labels
- SSE pipeline: guard RowStrip auto-load during active search
- Remove remaining `isServiceProvider`/`isVendorDirectory` hacks (use `price === null` instead)

### Phase 5: Adjacent Intent (Future — separate PRD)
- Multi-query per request
- Result type tags
- "Related" UI sections

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Alembic migration on live DB with nullable price change | Run during low-traffic window; migration is additive (no data loss) |
| Hard-gating web providers for service tier loses edge cases (e.g., eBay vintage item for "bespoke") | Scorer multiplier approach means web results CAN appear, just heavily demoted. Provider gating is configurable per tier. |
| Vendor directory too thin for some service categories | Graceful fallback: if vendor results < 2 AND desire_tier allows it, run web search as supplement |
| `reset_bids` deletes liked/selected bids on refinement | Protect liked/selected bids from reset: `DELETE FROM bid WHERE row_id = ? AND is_liked = false AND is_selected = false` |
| Frontend breaking due to `price: null` propagation | TypeScript will catch all access sites; use optional chaining `offer.price?.toFixed(2)` |
| Tier misclassification sends commodity to vendor-only path | Keep `desire_confidence` threshold; < 0.7 → run all providers as fallback |

---

## 8. Dependencies

- **Upstream**: PRD_Desire_Classification (implemented — desire_tier classification already in `make_unified_decision()`)
- **Downstream**: PRD_Autonomous_Outreach (needs working vendor display before outreach makes sense), PRD_Quantum_ReRanking (needs consistent scoring pipeline)
- **Parallel**: Vendor data enrichment (populating `tier_affinity`, `price_range_*` on existing vendors)

---

## 9. The Spirit Check

Before shipping any phase, ask:

> If a user says "mega yacht" and sees rubber ducks from Amazon — have we shipped anything of value?

> If a user says "AA batteries" and the system sends them to a yacht broker — have we shipped anything of value?

> If a user refines from "boat" to "yacht" and still sees toy boats — have we shipped anything of value?

> If a vendor has no price (because luxury doesn't work that way) and we show "$0.00" — have we respected the vendor?

The system should feel like a human concierge who *understands* the difference between these requests and responds accordingly — not a search box that runs the same pipeline for everything.
