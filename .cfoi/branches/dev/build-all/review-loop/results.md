# Review Loop Results - Phase 4 Build-All

**Reviewer:** Cascade  
**Date:** 2026-02-06  
**Scope:** 18 files across backend, BFF, frontend  
**Passes:** 2 (initial + re-review of fixes)

---

## Issues Found & Fixed

### 🔴 P0: Notification proxy routes missing cookie auth
- **Files:** `api/notifications/route.ts`, `api/notifications/count/route.ts`
- **Root cause:** Only extracted `Authorization` header, not `sa_session` cookie
- **Impact:** Browser-authenticated users would get 401 on notification endpoints
- **Fix:** Added `request.cookies.get('sa_session')?.value` fallback, matching `api/admin/growth/route.ts` pattern

### 🟡 P1: Notification failure kills quote submission
- **File:** `routes/seller.py` line 281-292
- **Root cause:** `create_notification()` called without try/except
- **Impact:** If notification DB insert fails, the seller's quote response would 500
- **Fix:** Wrapped in try/except with `logger.warning()` — notification is non-essential

### 🟡 P1: Lazy imports in function bodies (notifications.py)
- **File:** `routes/notifications.py` lines 67, 111
- **Root cause:** `from sqlalchemy import func` and `from sqlalchemy import update` inside function bodies
- **Impact:** Style violation, no circular import justification
- **Fix:** Moved both imports to file top

### 🟢 P2: print() instead of logger (auth.py)
- **File:** `routes/auth.py` line 541
- **Root cause:** `print()` used for error logging instead of structured logger
- **Fix:** Added `import logging` + `logger = logging.getLogger(__name__)`, replaced with `logger.warning()`

---

## Items Reviewed & Passed (no issues)

| File | Notes |
|------|-------|
| `routes/admin.py` (growth endpoint) | Clean. Admin-only, 8 queries acceptable for analytics. |
| `routes/checkout.py` (webhook) | Clean. closing_status correctly set, PurchaseEvent recorded. |
| `models.py` (Notification, Bid.closing_status) | Clean. Fields match migration. |
| `main.py` (router registration) | Clean. notifications_router registered. |
| `alembic migration` | Clean. Upgrade/downgrade symmetric. |
| `sourcing/normalizers/__init__.py` | Clean. eBay normalizer registered. |
| `bff/src/llm.ts` (RFP prompt) | Clean. Well-structured prompt. |
| `utils/auth.ts` (referral token) | Clean. SSR guard, localStorage cleanup. |
| `share/[token]/page.tsx` | Clean. Token stored correctly. |
| `api/admin/growth/route.ts` | Clean. Cookie + header auth. |
| `components/Chat.tsx` (Sell link) | Clean. Minimal change. |
| `components/Board.tsx` (Seller button) | Clean. Pre-existing lint warnings not ours. |
| `page.tsx` (mobile Sell tab) | Clean. Consistent with existing nav pattern. |

---

## Call Flow Integrity: VERIFIED

All 5 integration flows traced end-to-end:
1. ✅ Referral attribution: share page → localStorage → verifyAuth → auth.py → notification
2. ✅ Seller quote → buyer notification (now with try/except)
3. ✅ Growth metrics: proxy → admin endpoint → 8 queries
4. ✅ Notification API: proxy (now with cookie auth) → CRUD endpoints
5. ✅ Checkout → revenue: Stripe session → webhook → PurchaseEvent + closing_status

## Verdict: PASS (after 4 fixes)
