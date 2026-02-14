# Fixes Applied — Iteration 1

## C1: `search_vendors` NameError
- **File**: `apps/backend/routes/outreach.py`
- **Change**: Rewrote `search_vendors_endpoint` to query `VendorProfile` via SQL `ILIKE` instead of calling the removed in-memory function. Also added `session=Depends(get_session)`.
- **Tests**: py_compile passed.

## C2: pgvector import crash
- **File**: `apps/backend/models.py`
- **Change**: Wrapped `from pgvector.sqlalchemy import Vector` in try/except with a lightweight `UserDefinedType` stub fallback.
- **Tests**: py_compile passed.

## C3: Redundant `import json`
- **File**: `apps/backend/routes/outreach.py`
- **Change**: Removed `import json` from lines 138 and 480 (already imported at top).
- **Tests**: py_compile passed.

## M1: search endpoint reads from in-memory (fixed with C1)
- Combined with C1 fix.

## M2: vendor detail endpoint reads from in-memory
- **File**: `apps/backend/routes/outreach.py`
- **Change**: Rewrote `get_vendor_detail_endpoint` to query `VendorProfile` from DB. Removed unused `get_vendor_detail` import.
- **Tests**: py_compile passed.

## M5: Seed script doesn't update `updated_at`
- **File**: `apps/backend/scripts/seed_vendors.py`
- **Change**: Added `existing.updated_at = datetime.utcnow()` in update path. Added `from datetime import datetime` import.
- **Tests**: py_compile passed.

## M6: Stale docstring
- **File**: `apps/backend/scripts/seed_vendors.py`
- **Change**: Updated docstring from "sellers" to "VendorProfile directory".
- **Tests**: py_compile passed.

## M8: Silent success when no vendors have email
- **File**: `apps/backend/routes/outreach.py`
- **Change**: Added early return with `"status": "warning"` when `created_events` is empty after the vendor loop.
- **Tests**: py_compile passed.

## m1: Stale comment
- **File**: `apps/backend/routes/outreach.py:79`
- **Change**: Updated "mock WattData" → "VendorProfile directory".

## m4: Redundant slice
- **File**: `apps/backend/routes/outreach.py:432`
- **Change**: Removed `[:limit]` since DB query already has `.limit(limit)`.

## Deferred (acknowledged — deeper refactor needed):
- **M3**: `vendor_discovery.py` LocalVendorAdapter still uses in-memory `get_vendors()` — requires async session injection into adapter pattern.
- **M4**: `sourcing/repository.py` WattDataMockProvider still uses in-memory `get_vendors()` — requires same refactor.
- **M7**: No auth on `persist_vendors_for_row` — pre-existing issue, not introduced by cutover.
