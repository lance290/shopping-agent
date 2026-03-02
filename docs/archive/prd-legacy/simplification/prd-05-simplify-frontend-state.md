# PRD-05: Simplify Frontend State

## Business Outcome
- **Measurable impact:** Reduce state complexity in `store.ts` while preserving currently used streaming/status UX behavior.
- **Success criteria:** remove truly unused paths first, simplify identity/merge logic with regression tests, and avoid deleting fields that are still consumed by `Chat`/`RowStrip` render flows.
- **Target users:** Developers (simpler state management, fewer race conditions); users (offers display on correct rows, likes persist reliably).

## Scope
- **In-scope:**
  - Remove dead state fields from `store.ts`
  - Replace `getOfferStableKey()` with `bid.id` (stable identity)
  - Eliminate `mapBidToOffer()` by having the backend return data in the frontend's expected shape
  - Simplify the bid/offer merge logic in `setRows` and `updateRowOffers`
  - Move `detailPanelStore.ts` to `app/stores/detailPanelStore.ts` (keep as separate store — it's correctly scoped)
  - Remove dead `stores/` files (if not already done in PRD-02)
- **Out-of-scope:**
  - Rewriting the store from scratch (incremental simplification only)
  - Changing the Zustand library or store pattern
  - Adding new features or state
  - Backend API response shape changes beyond what's needed for `mapBidToOffer` elimination

## Current State (Evidence)

### `store.ts` — 599 LOC, 19 component imports

**State fields requiring second-pass reclassification:**

| Field | LOC | Evidence |
|-------|-----|---------|
| `searchResults: Offer[]` | ~20 | Legacy candidate for removal (verify no runtime readers outside tests). |
| `rowProviderStatuses` | ~30 | **Active** — consumed by `RowStrip` and updated by search-stream events. |
| `rowSearchErrors` | ~15 | **Active** — consumed by `RowStrip` error rendering and store tests. |
| `moreResultsIncoming` | ~10 | **Active** — used by `Chat` + `RowStrip` to coordinate streaming state. |
| `selectOrCreateRow` | ~40 | Appears mostly test/helper-driven; candidate for removal only after confirming no runtime caller paths. |

**Complex merge logic (~80 LOC):**
- `setRows()` merges incoming bids into `rowResults`, trying to preserve local state
- `updateRowOffers()` merges new offers with existing ones using `getOfferStableKey()`
- Race conditions occur when two search responses arrive out of order

### `getOfferStableKey()` — current behavior (second-pass corrected)

```typescript
function getOfferStableKey(offer: Offer): string {
  if (offer.bid_id) return `bid:${offer.bid_id}`;
  // then canonicalized clickout URL / raw URL / deterministic fallback tuple
}
```

This exists because offers can be in three states:
1. **Pre-persistence** — no `bid_id` yet (just arrived from search, not saved to DB)
2. **Post-persistence** — has `bid_id` (saved to DB)
3. **Liked** — needs to match by key to update the right offer

**Root cause:** The sourcing system returns results before persisting them as Bids. The frontend gets offers without IDs, then later gets the same offers with IDs, and must match them.

**Fix:** Ensure every offer has a stable ID before reaching the frontend. Either:
- Backend persists bids before returning them (they already do this in the main flow)
- Or assign a client-side UUID on first receipt and use it until `bid_id` arrives

### `mapBidToOffer()` — Client-Side Data Transform

The backend returns `Bid` objects. The frontend transforms them into `Offer` objects via `mapBidToOffer()`. This means:
- Two type definitions for the same entity
- Transform logic that can drift from backend shape
- Every field rename requires updating the transform

Second-pass note: this transform is still actively used in `store.ts` and tested. Removal is valid as a goal, but should be sequenced after API/type contract stabilization.

### `detailPanelStore.ts` — Correctly Scoped, Keep

This 121-LOC store manages the tile detail panel's open/close state and selected offer. It's imported by exactly 2 components (`OfferTile.tsx`, `TileDetailPanel.tsx`). This is a well-scoped, correctly separated store. **Keep it.**

## Target State

### Simplified `store.ts` (phase-driven, not hard LOC target)

```typescript
interface ShoppingState {
  // Core data
  rows: Row[];
  projects: Project[];
  rowResults: Record<number, Offer[]>;  // rowId → offers
  
  // Active state
  activeProjectId: number | null;
  activeRowId: number | null;
  isSearching: Record<number, boolean>;
  
  // Social
  comments: Record<number, Comment[]>;
  
  // Actions
  setRows: (rows: Row[]) => void;
  addRow: (row: Row) => void;
  updateRow: (id: number, updates: Partial<Row>) => void;
  removeRow: (id: number) => void;
  setRowOffers: (rowId: number, offers: Offer[]) => void;
  appendRowOffers: (rowId: number, offers: Offer[]) => void;
  toggleLike: (rowId: number, bidId: number) => void;
  // ... other essential actions
}
```

**Removed (only if verified unused):**
- `searchResults` (dead)
- `selectOrCreateRow` (duplicates LLM logic)
- `getOfferStableKey()` (replaced with `bid.id`)
- `mapBidToOffer()` (backend returns correct shape)

**Retain for now (active UX paths):**
- `rowProviderStatuses`
- `rowSearchErrors`
- `moreResultsIncoming`

### Offer Identity: Always Use `bid.id`

After this change:
1. Backend persists bids before returning search results (already happens in main flow)
2. Every offer in `rowResults` has a `bid_id` (non-optional after persistence)
3. Like toggle uses `bid_id` directly — no stable key lookup needed
4. Merge logic uses `bid_id` for deduplication — deterministic, no fallbacks

For the edge case of streaming results (offers arriving before persistence):
- Assign a temporary `client_id: string = crypto.randomUUID()` on first receipt
- Replace with `bid_id` once persistence confirms
- This is a single, deterministic fallback — not 4 strategies

## User Flow

No user flow change. The same data displays in the same way. The difference is:
- Likes reliably persist (stable identity)
- Offers reliably display on the correct row (simpler merge logic)
- No "wrong data on wrong row" from race conditions

## Business Requirements

### Authentication & Authorization
- No auth changes

### Monitoring & Visibility
- After change: monitor for "like not persisting" bug reports (should drop to zero)
- Monitor for "wrong row" bug reports (should drop to zero)

### Performance Expectations
- Marginal improvement — less computation in merge logic
- No new network calls

### Data Requirements
- Backend may need minor response shape adjustment to eliminate `mapBidToOffer()`
- No database changes

### UX & Accessibility
- No UI changes

### Privacy, Security & Compliance
- No changes

## Implementation Steps

### Step 1: Remove only verified-unused state fields

Start with `searchResults` and any other fields proven to have no runtime callers. Do not remove `moreResultsIncoming`, `rowProviderStatuses`, or `rowSearchErrors` until equivalent behavior exists.

### Step 2: Simplify offer identity

Replace `getOfferStableKey()` with `bid.id` usage. Add `client_id` as temporary fallback for pre-persistence offers.

### Step 3: Simplify merge logic

Rewrite `updateRowOffers` to use simple `bid_id`-based deduplication:
```typescript
setRowOffers: (rowId, newOffers) => {
  set(state => ({
    rowResults: { ...state.rowResults, [rowId]: newOffers }
  }));
},
appendRowOffers: (rowId, newOffers) => {
  set(state => {
    const existing = state.rowResults[rowId] || [];
    const existingIds = new Set(existing.map(o => o.bid_id));
    const unique = newOffers.filter(o => !existingIds.has(o.bid_id));
    return { rowResults: { ...state.rowResults, [rowId]: [...existing, ...unique] } };
  });
},
```

### Step 4: Eliminate `mapBidToOffer()`

Either:
- (A) Backend adds an endpoint that returns `Offer`-shaped responses directly
- (B) Frontend renames its `Offer` type to match `Bid` and removes the transform
- Option (B) is simpler and preferred.

### Step 5: Optionally refactor status/error state

If desired, fold provider/search state only after replacing current `RowStrip` + streaming UX dependencies and adding regression coverage.

## Dependencies
- **Upstream:** PRD-02 (dead stores/ files removed), PRD-04 (cleaner data model means simpler types)
- **Downstream:** None — this is the last frontend-focused effort

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Removing `searchResults` breaks a component we missed | High | `grep -rn "searchResults" apps/frontend/` before removal |
| Offer identity change causes likes to not match | High | Test: create row → search → like → reload → like persists |
| Simplifying merge logic causes duplicate offers | Medium | Test: trigger search → verify no duplicate tiles |
| `mapBidToOffer` removal changes API contract | Medium | If renaming types to match Bid, no API change needed |
| Provider status removal frustrates power users | Low | Can be re-added as a dev tools panel later if needed |

## Acceptance Criteria (Business Validation)
- [ ] `store.ts` complexity reduced with no regression in streaming/status UX
- [ ] `getOfferStableKey()` removed — all identity based on `bid.id`
- [ ] `mapBidToOffer()` removed — single type for bid/offer
- [ ] `searchResults` field removed from store
- [ ] `moreResultsIncoming` is either retained with tests or replaced with equivalent behavior
- [ ] `selectOrCreateRow` removed only after verifying no runtime usage
- [ ] Like toggle works: click heart → reload → heart still filled
- [ ] Correct row display: search 2 rows → offers appear on correct rows
- [ ] No duplicate tiles after search completes
- [ ] All existing frontend tests pass
- [ ] Manual smoke test: login → create row → see offers → like → click out → share

## Traceability
- **Parent PRD:** `docs/prd/simplification/parent.md`
- **Analysis:** `SIMPLIFICATION_PLAN.md` — Problem 5: Two Competing State Stores, Recurring Bug #2 (wrong data on wrong row), Recurring Bug #3 (likes not persisting)

---
**Note:** Technical implementation decisions are made during /plan and /task.
