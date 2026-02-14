# Code Review Issues — Iteration 2 (Post-Fix Re-Review)

## Summary
- **Total Issues**: 4
- **Critical**: 0
- **Major**: 2 (deferred — deeper refactor, pre-existing)
- **Minor**: 2 (cosmetic)
- **Nits**: 0

---

## Major Issues 🟠 (Deferred — Not Introduced by Cutover)

### M3: `LocalVendorAdapter.find_sellers()` still reads in-memory `VENDORS`
- **File**: `apps/backend/services/vendor_discovery.py:86-88`
- **Category**: Incomplete Cutover (deferred)
- **Status**: Acknowledged. Requires async session injection into the adapter abstraction. Will be addressed when vendor_discovery is refactored for pgvector semantic retrieval (TODO #20).

### M4: `WattDataMockProvider.search()` still reads in-memory `VENDORS`
- **File**: `apps/backend/sourcing/repository.py:784-791`
- **Category**: Incomplete Cutover (deferred)
- **Status**: Acknowledged. The sourcing pipeline's mock provider still uses `get_vendors()`. Same refactor scope as M3.

---

## Minor Issues 🟡

### m2: `persist_vendors_for_row` rich_fields keys are aviation-specific
- **File**: `apps/backend/routes/outreach.py:482-484`
- **Problem**: Hardcoded keys `fleet`, `jet_sizes`, `wifi`, `starlink` are aviation-specific. Non-blocking since unknown keys are simply ignored (`.get()` returns None).
- **Suggestion**: Future refactor to store all non-standard keys generically.

### m3: `seed_vendors.py` maps `provider_type` → `specialties`
- **File**: `apps/backend/scripts/seed_vendors.py:89,102`
- **Problem**: Field name mismatch is confusing but functional.
- **Suggestion**: Add inline comment clarifying the mapping.

---

## Verdict: **PASS_WITH_SUGGESTIONS**

All Critical and Major issues from iteration 1 are resolved.
Remaining Major items (M3, M4) are pre-existing architectural decisions documented in the PRD as out-of-scope for this cutover.
No new issues introduced by the fixes.
