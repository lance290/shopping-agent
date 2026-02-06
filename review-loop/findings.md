# Review Findings - Phase 3 Build-All (Pass 1)

## Summary
- **Files reviewed:** 22
- **Critical issues:** 4 (all fixed)
- **Medium issues:** 2 fixed, 2 deferred
- **False alarms:** 1

## CRITICAL — Fixed

### 1. Stripe v7 error class path ✅
- **File:** `routes/checkout.py:173`
- **Issue:** `stripe.error.SignatureVerificationError` — Stripe SDK v7+ removed `.error` namespace
- **Fix:** Changed to `stripe.SignatureVerificationError`

### 2. Webhook session management ✅
- **File:** `routes/checkout.py:229`
- **Issue:** `_handle_checkout_completed` created raw `sessionmaker(engine)` bypassing DI cleanup
- **Fix:** Changed to `async for db_session in get_session():`

### 3. N+1 in seller inbox ✅
- **File:** `routes/seller.py:148-173`
- **Issue:** Quote count query inside for-loop over rows
- **Fix:** Single `GROUP BY` batch query

### 4. N+1 in seller quotes ✅
- **File:** `routes/seller.py:199-225`
- **Issue:** `session.get(Row)` per quote in loop
- **Fix:** Batch `SELECT ... WHERE id IN (...)`

## MEDIUM — Fixed

### 5. DRY: getToken/authHeaders duplicated ✅
- **Files:** `seller/page.tsx`, `admin/page.tsx`
- **Fix:** Extracted to `utils/auth.ts`, pages import shared module

### 6. Admin stats inner imports ✅
- **File:** `routes/admin.py:6,14-18`
- **Issue:** `timedelta` and model imports inside function body
- **Fix:** Moved to module top level

## MEDIUM — Deferred

### 7. API proxy BACKEND_URL duplication
- All 6 new proxy routes repeat `const BACKEND_URL = ...`
- Pre-existing pattern across 15+ routes. Separate cleanup effort.

### 8. OfferTile Buy Now silent failure
- Non-ok checkout response shows no user feedback
- Needs toast/notification system (not yet in codebase)

## Verification
- Backend: 285 passed, 0 failed
- Frontend type-check: Only pre-existing errors
