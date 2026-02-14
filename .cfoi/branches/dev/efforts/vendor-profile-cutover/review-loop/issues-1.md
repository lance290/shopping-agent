# Code Review Issues — Iteration 1 (VendorProfile Cutover)

## Summary
- **Total Issues**: 17
- **Critical**: 3 (must fix)
- **Major**: 8 (should fix)
- **Minor**: 6 (nice to fix)
- **Nits**: 0

---

## Critical Issues 🔴

### C1: `search_vendors` not imported — NameError at runtime
- **File**: `apps/backend/routes/outreach.py:281`
- **Category**: Logic / Broken Endpoint
- **Problem**: `search_vendors` was removed from imports during the cutover, but `search_vendors_endpoint()` on line 281 still calls it. This endpoint **will crash with NameError** when hit.
- **Risk**: `GET /outreach/vendors/search` returns 500 for every request.
- **Fix**: Either re-import `search_vendors` (quick fix) or rewrite the endpoint to query `VendorProfile` from DB (proper fix).

### C2: `VendorProfile` imports `pgvector.sqlalchemy.Vector` at module level
- **File**: `apps/backend/models.py:8`
- **Category**: Dependency / Startup Crash
- **Problem**: `from pgvector.sqlalchemy import Vector` is at module top. If `pgvector` is not installed (e.g., in a test env, or CI without postgres extensions), **all model imports fail** and the entire app won't start.
- **Risk**: App startup failure in any environment missing pgvector.
- **Fix**: Use a conditional import or `sa.Column("embedding", sa.Text(), nullable=True)` fallback, or make the import try/except with a stub.

### C3: `import json` duplicated inside functions
- **File**: `apps/backend/routes/outreach.py:138,480`
- **Category**: Logic (minor) / Code Smell
- **Problem**: `json` is imported at line 5 (top of file) but also re-imported inside `trigger_outreach` (line 138) and `send_reminders` (line 480). While Python handles this gracefully, it signals incomplete editing and could mask future import errors.
- **Risk**: Low runtime risk, but indicates sloppy cutover that may hide other issues.
- **Fix**: Remove the redundant `import json` on lines 138 and 480.

---

## Major Issues 🟠

### M1: `search_vendors_endpoint` reads from in-memory dict, not VendorProfile DB
- **File**: `apps/backend/routes/outreach.py:270-287`
- **Category**: Incomplete Cutover
- **Problem**: Even after fixing C1 (importing `search_vendors`), this endpoint still queries the in-memory `VENDORS` dict. It's inconsistent with `get_vendors_for_category` which now reads from DB.
- **Fix**: Rewrite to query `VendorProfile` with SQL `ILIKE` or full-text search.

### M2: `get_vendor_detail_endpoint` reads from in-memory dict, not VendorProfile DB
- **File**: `apps/backend/routes/outreach.py:290-296`
- **Category**: Incomplete Cutover
- **Problem**: `get_vendor_detail()` still searches the in-memory `VENDORS` dict. After seed+cutover, the DB is the source of truth.
- **Fix**: Rewrite to query `VendorProfile` by company name.

### M3: `LocalVendorAdapter.find_sellers()` reads from in-memory dict
- **File**: `apps/backend/services/vendor_discovery.py:86-88`
- **Category**: Incomplete Cutover
- **Problem**: The vendor discovery adapter still calls `get_vendors()` which reads from `VENDORS` dict. Any caller using the adapter layer gets stale data.
- **Fix**: Update to accept a DB session and query `VendorProfile`. (Note: this is a deeper refactor since the adapter is sync-oriented.)

### M4: `WattDataMockProvider.search()` reads from in-memory dict
- **File**: `apps/backend/sourcing/repository.py:784-791`
- **Category**: Incomplete Cutover
- **Problem**: The sourcing pipeline's mock WattData provider still calls `get_vendors()` from the in-memory registry.
- **Fix**: Update to query VendorProfile from DB, or accept this as intentional dual-source during transition.

### M5: Seed script doesn't update `updated_at` on existing records
- **File**: `apps/backend/scripts/seed_vendors.py:83-93`
- **Category**: Data Integrity
- **Problem**: When updating an existing `VendorProfile`, the script updates fields but never sets `updated_at = datetime.utcnow()`. The `updated_at` will forever show the creation time.
- **Fix**: Add `existing.updated_at = datetime.utcnow()` in the update branch.

### M6: Stale docstring in seed script references "sellers"
- **File**: `apps/backend/scripts/seed_vendors.py:1-6`
- **Category**: Documentation / Misleading
- **Problem**: Docstring says "Never deletes existing sellers" but the model is now `VendorProfile`.
- **Fix**: Update docstring.

### M7: No route-level auth on vendor tile endpoints
- **File**: `apps/backend/routes/outreach.py:329-366,374-449`
- **Category**: Security
- **Problem**: `get_vendors_for_category` and `persist_vendors_for_row` have no authentication. While `persist_vendors_for_row` modifies data (creates Bids), it accepts any caller.
- **Risk**: Anyone can create Bid records for any row_id without authentication.
- **Fix**: Add `user: User = Depends(get_current_user)` or session-based auth.

### M8: `trigger_outreach` silently succeeds when all vendors lack email
- **File**: `apps/backend/routes/outreach.py:95-97,131-133`
- **Category**: Logic / Silent Failure
- **Problem**: If all `VendorProfile` records for a category have `contact_email=None`, the `continue` on line 97 skips them all. `created_events` ends up empty, `outreach_count=0`, but response says `"status": "success"` with `"vendors_contacted": 0`.
- **Fix**: Return a warning or 422 when no vendors had emails.

---

## Minor Issues 🟡

### m1: Stale comment "Get vendors from mock WattData"
- **File**: `apps/backend/routes/outreach.py:79`
- **Fix**: Update to "Get vendors from VendorProfile directory"

### m2: `persist_vendors_for_row` rich_fields hardcoded for aviation
- **File**: `apps/backend/routes/outreach.py:414-416`
- **Problem**: Keys like `fleet`, `jet_sizes`, `wifi`, `starlink` are aviation-specific. Category-agnostic cutover should accept generic extra fields.

### m3: `seed_vendors.py` maps `provider_type` → `specialties`
- **File**: `apps/backend/scripts/seed_vendors.py:89,102`
- **Problem**: Confusing naming — `provider_type` from Vendor dataclass maps to `specialties` in VendorProfile.

### m4: Redundant `vendors[:limit]` after `.limit(limit)` query
- **File**: `apps/backend/routes/outreach.py:365`
- **Fix**: Remove Python-side slice; DB already limits.

### m5: VendorProfile `embedding` type hint `List[float]` may cause serialization issues
- **File**: `apps/backend/models.py:93-96`
- **Problem**: pgvector returns numpy arrays or custom types; `List[float]` type hint may cause Pydantic validation errors.

### m6: Migration down_revision is a merge tuple
- **File**: `apps/backend/alembic/versions/f2c1a9d3e7b4:31`
- **Problem**: `down_revision = ("a7b8c9d0e1f2", "add_performance_indexes")` — this is a merge migration. Valid but complex; ensure both parent heads exist.

---

## Verdict: **FAIL**

Fix all Critical (C1-C3) and Major (M1-M8) issues, then re-run /review-loop.
