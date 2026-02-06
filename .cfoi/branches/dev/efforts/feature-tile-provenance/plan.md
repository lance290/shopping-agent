<!-- PLAN_APPROVAL: pending -->

# Plan: Tile Provenance Data Pipeline

**Effort**: feature-tile-provenance
**Created**: 2026-02-06
**Aligned to North Star**: Persistence reliability, transparent provenance

---

## Problem Statement

The tile detail panel exists end-to-end (backend model → API endpoint → frontend slide-out), but **provenance data is never populated during search**. Every detail panel shows "Details unavailable" because:

1. `NormalizedResult` has no `provenance` field
2. `_persist_results()` in `sourcing/service.py` creates `Bid` without setting `provenance`
3. The normalizer only stores `{"provider_id": ...}` in `raw_data`

## Approach

### Phase A: Backend — Build provenance during normalization + persistence

**A1. Extend `NormalizedResult` with provenance fields**

Add optional fields to `NormalizedResult` in `sourcing/models.py`:
```python
provenance: Optional[Dict[str, object]] = Field(default_factory=dict)
```

This will carry structured provenance through the pipeline.

**A2. Build provenance in normalizers**

In `sourcing/normalizers/__init__.py` `_normalize_result()`, construct provenance from available data:

```python
provenance = {
    "product_info": {
        "title": result.title,
        "brand": None,  # extracted from title or provider data if available
        "specs": {}
    },
    "matched_features": [],  # populated from rating, shipping, reviews
    "source_provider": provider_id,
}
```

Build `matched_features` from concrete data:
- If `rating` > 4.0 → "Highly rated ({rating}★)"
- If `shipping_info` → shipping info text
- If `reviews_count` > 100 → "Popular ({reviews_count} reviews)"
- If price within budget → "Within your budget"
- If `match_score` > 0.7 → "Strong match for your search"

Provider-specific normalizers (rainforest, google_cse) are currently pass-throughs to `normalize_generic_results` — no separate modification needed.

**A3. Attach search intent context in `_persist_results()`**

In `sourcing/service.py`, when creating/updating bids:
- Load `Row.search_intent` to get `SearchIntent` (has `features`, `keywords`, `brand`)
- Merge search intent features into provenance's `matched_features`
- If `Row.chat_history` exists, extract last 2 relevant user messages as `chat_excerpts`
- Serialize provenance as JSON and set `Bid.provenance`

The method signature changes to accept `row` as a parameter (it's already loaded in `search_and_persist`).

**A4. Handle updates (existing bids)**

When updating existing bids in `_persist_results()`, also update the `provenance` field if new provenance data is available (don't overwrite with empty).

### Phase B: Frontend — Improve detail panel UX

**B1. Improve fallback message**

In `TileDetailPanel.tsx`, change "Details unavailable for this item" to "Based on your search" with the row title as context. This covers existing bids with null provenance.

**Note**: WattData/service provider bids bypass the normalization pipeline entirely (created in `routes/outreach.py`). They use the VendorContactModal instead of the detail panel, so they are unaffected by this effort.

**B2. Accessibility improvements**

- Add `tabIndex={0}` to each section heading for Tab navigation
- Add `aria-label` attributes to provenance sections
- Ensure focus trap within panel when open

### Phase C: Tests

**C1. Backend tests**
- Test `NormalizedResult` provenance field population
- Test `_persist_results()` creates bids with provenance JSON
- Test `BidWithProvenance` computed fields parse the new provenance
- Test provenance survives update (existing bid gets provenance)
- Test empty/null provenance gracefully handled

**C2. Frontend tests**
- Test detail panel renders matched features
- Test detail panel renders "Based on your search" fallback
- Test keyboard navigation (Tab, Escape)
- Test accessibility attributes present

---

## Technical Details

### Data Flow

```
SearchResult (from provider)
    ↓
_normalize_result() → NormalizedResult (+ provenance)
    ↓
_persist_results() → Bid (provenance = JSON of merged provenance + search intent)
    ↓
GET /bids/{id}?include_provenance=true → BidWithProvenance (computed fields)
    ↓
TileDetailPanel.tsx (renders sections)
```

### Provenance Schema

```json
{
  "product_info": {
    "title": "Blue Widget",
    "brand": "Acme",
    "specs": {"color": "blue", "size": "large"}
  },
  "matched_features": [
    "Highly rated (4.5★)",
    "Free shipping",
    "Within your budget",
    "Matches: blue, widget"
  ],
  "chat_excerpts": [
    {"role": "user", "content": "I need a blue widget under $50"},
    {"role": "assistant", "content": "Found several blue widgets..."}
  ]
}
```

### Files Modified

| File | Change |
|------|--------|
| `apps/backend/sourcing/models.py` | Add `provenance` field to `NormalizedResult` |
| `apps/backend/sourcing/normalizers/__init__.py` | Build provenance in `_normalize_result()` |
| `apps/backend/sourcing/normalizers/rainforest.py` | No change needed (pass-through) |
| `apps/backend/sourcing/normalizers/google_cse.py` | No change needed (pass-through) |
| `apps/backend/sourcing/service.py` | Merge search intent + chat into provenance in `_persist_results()` |
| `apps/frontend/app/components/TileDetailPanel.tsx` | Improve fallback, accessibility |
| `apps/backend/tests/test_provenance_pipeline.py` | New: pipeline tests |
| `apps/frontend/app/tests/tile-detail-panel.test.ts` | New: panel UX tests |

### Assumptions

1. `SearchResult` has no `raw_data` — `NormalizedResult.raw_data` only has `{provider_id}`. We build provenance from structured fields instead
1b. WattData/service provider bids bypass this pipeline — they are created directly in `routes/outreach.py` and use VendorContactModal, not TileDetailPanel
2. Chat excerpts are optional — many bids won't have relevant chat context
3. Provenance is append-only — once set, we don't strip fields on update
4. We don't add analytics tracking for panel opens in this effort (deferred)

### Risks

| Risk | Mitigation |
|------|-----------|
| Sparse provider data yields empty matched_features | "Based on your search" fallback always shows search query |
| Large chat_history causes oversized provenance JSON | Limit to last 2 user messages, truncate to 200 chars each |
| Performance: building provenance adds latency to search | Provenance construction is pure string ops, negligible (<1ms) |

### Success Criteria

- [ ] New bids have non-null `provenance` JSON after search
- [ ] Detail panel shows at least one matched feature for ≥80% of bids
- [ ] Panel loads in ≤300ms (bid is already in DB, single fetch)
- [ ] Tab key navigates between panel sections
- [ ] Escape key closes panel (already works)
- [ ] All existing tests pass + new tests pass
- [ ] Zero regressions in search flow
