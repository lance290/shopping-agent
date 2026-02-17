# Codebase Audit — Feb 17, 2026 (Updated Post-PRD-07 Fixes)

## Executive Summary

After the streaming lock fix + PRD-07 audit fixes, the platform is demo-ready. Original audit identified **38 findings** + 1 new critical bug found during demo testing. **9 fixed**, remainder triaged for post-demo.

### Fixes Applied (PRD-07)
- ✅ **B-1**: Guest user lookup unified to `dependencies.py` (`resolve_user_id` + `GUEST_EMAIL`)
- ✅ **B-4**: Debug `console.log` removed from `store.ts` and `api.ts` (9 statements)
- ✅ **B-7** (NEW): Public search crash fixed (`merchant` → `merchant_name`, `ChatContext`)
- ✅ **G-1**: Anonymous chat rate limited (10 req/min per IP via `check_rate_limit`)
- ✅ **G-2**: Streaming lock 60s timeout safety net
- ✅ **G-5**: React `ErrorBoundary` wrapping workspace page
- ✅ **D-6**: Provider status badge key no longer uses fragile index
- ✅ **DC-3**: `runSearchApi` unused wrapper removed from `api.ts`

---

## BUGS (6)

### B-1: `chat.py` guest user lookup not using `_resolve_user_id` helper (DRY + Bug risk)
- **File**: `apps/backend/routes/chat.py:261-275`
- **Issue**: The chat endpoint has its own inline guest user lookup (`guest@buy-anything.com`) instead of using the `_resolve_user_id()` helper we extracted in `rows_search.py`. If the guest email constant changes, chat.py won't follow.
- **Severity**: Medium
- **Fix**: Import and use `_resolve_user_id` from `rows_search.py`, or extract to a shared `dependencies.py`.

### B-2: `outreach.py` uses `session.execute()` instead of `session.exec()` (28 instances)
- **Files**: `routes/outreach.py` (12), `routes/quotes.py` (9), `routes/merchants.py` (4), `routes/admin.py` (2), `routes/notifications.py` (1)
- **Issue**: SQLModel's `session.execute()` returns raw SQLAlchemy `Row` objects, not model instances. This means `.scalar_one_or_none()` is needed instead of `.first()`. Inconsistent with the rest of the codebase which uses `session.exec()`.
- **Severity**: Low (works but fragile)
- **Fix**: Migrate to `session.exec()` for consistency.

### B-3: `datetime.utcnow()` deprecated — 104 occurrences
- **Files**: 45 files across the backend
- **Issue**: `datetime.utcnow()` is deprecated in Python 3.12+ in favor of `datetime.now(timezone.utc)`. Will produce warnings and eventually break.
- **Severity**: Low (no runtime impact yet on 3.11)
- **Fix**: Global find-replace in a future cleanup pass.

### B-4: `setRows` debug logging in production store
- **File**: `apps/frontend/app/store.ts:358-363`
- **Issue**: `console.log('[Store] setRows called with', rows.length, 'rows')` runs on every row load. Noisy in production.
- **Severity**: Low
- **Fix**: Remove or gate behind `process.env.NODE_ENV === 'development'`.

### B-5: `backendUrl` defined but never used in `api.ts`
- **File**: `apps/frontend/app/utils/api.ts:24`
- **Issue**: `const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'` is defined but all API calls go through `/api/*` proxy routes. Dead variable.
- **Severity**: None (lint warning)
- **Fix**: Remove the dead variable.

### B-6: Duplicate outreach systems
- **Files**: `routes/outreach.py` + `routes/outreach_campaigns.py` + `services/outreach_service.py`
- **Issue**: Two completely separate outreach implementations exist:
  1. **Old**: `outreach.py` uses `SellerQuote`, `OutreachEvent`, `VendorProfile` models with `services/email.py` + `services/vendors.py`
  2. **New**: `outreach_campaigns.py` uses `OutreachCampaign`, `OutreachMessage`, `OutreachQuote` models with `OutreachService`
- **Severity**: Medium — confusing, risk of data split
- **Fix**: Deprecate the old system. The campaign-based system is more complete.

---

## DRY VIOLATIONS (12)

### D-1: Guest user lookup pattern (3 locations)
- `chat.py:261-275` — inline
- `rows_search.py:145-157` — extracted to `_resolve_user_id()`
- `tests/test_anonymous_search.py` — test fixtures
- **Fix**: Share the helper, use `GUEST_EMAIL` constant everywhere.

### D-2: Bid-to-Offer hydration logic (3 locations)
- `store.ts:setRows()` lines 391-420
- `store.ts:updateRow()` lines 439-463
- Both do the same bid→offer merge with `existingByBidId` map
- **Fix**: Extract a shared `mergeRowBidsIntoResults(existingResults, bids)` helper.

### D-3: Row delete cleanup pattern (2 locations)
- `store.ts:requestDeleteRow()` lines 286-301 and 322-336
- Both destructure `rowResults`, `rowProviderStatuses`, `rowSearchErrors` identically.
- **Fix**: Extract `cleanupRowState(state, rowId)`.

### D-4: Auth check boilerplate (every route)
- Every authenticated route has:
  ```python
  auth_session = await get_current_session(authorization, session)
  if not auth_session:
      raise HTTPException(status_code=401, detail="Not authenticated")
  user_id = auth_session.user_id
  ```
- 20+ route files repeat this 4-line pattern.
- **Fix**: Create a `get_authenticated_user_id` dependency that raises 401 automatically.

### D-5: `fetchWithAuth` wrapper adds no auth headers
- **File**: `apps/frontend/app/utils/api.ts:10-22`
- `getAuthToken()` always returns `''` because the cookie is HttpOnly. The wrapper exists but `fetchWithAuth` is just `fetch` with extra steps. Every API call goes through it for no reason.
- **Fix**: Either remove the wrapper or add actual session token forwarding from localStorage (if applicable).

### D-6: Provider status badge key includes index (fragile)
- **File**: `RowStrip.tsx:406` — `key={status.provider_id + idx}`
- Using index in key can cause incorrect reconciliation when providers reorder.
- **Fix**: Use `status.provider_id` alone (it should be unique per provider).

### D-7: Share link creation duplicated in RowStrip
- `handleShare` (line 300) and `handleCopySearchLink` (line 335) both construct fetch calls to `/api/shares` with identical auth header logic.
- **Fix**: Use the `createShareLink` helper from `api.ts` that already exists.

### D-8: LLM call patterns inconsistent
- `services/llm.py:call_gemini()` — Gemini-first, OpenRouter fallback
- But `sourcing/repository.py` and `scripts/` call OpenRouter directly for embeddings
- No unified embedding function
- **Fix**: Add `call_embedding()` to `services/llm.py` with the same fallback pattern.

### D-9: JSON parsing helpers scattered
- `safe_json_loads` in `utils/json_utils.py`
- `parseChoiceFactors`/`parseChoiceAnswers` in `store.ts`
- Inline `JSON.parse` with try/catch in 10+ places
- **Fix**: Standardize on the helpers.

### D-10: Price parsing duplicated in `rows_search.py`
- `_parse_price_value()` and `_extract_filters()` both parse price strings
- Similar logic exists in `sourcing/filters.py`
- **Fix**: Single price parsing utility.

### D-11: SSE event formatting
- `sse_event()` helper in `chat.py` but manual `f"data: {json.dumps(...)}\n\n"` in `rows_search.py`
- **Fix**: Share the `sse_event` helper.

### D-12: Row-to-dict serialization
- `row_to_dict()` in `chat.py`
- Manual dict construction in `rows.py`
- **Fix**: Single serializer on the model.

---

## GAPS (8)

### G-1: No rate limiting for anonymous chat
- The chat endpoint falls back to guest user but has no per-IP rate limiting. A bot could exhaust LLM credits.
- **Priority**: High for production

### G-2: No streaming lock timeout (FIXED in this session)
- Added 60s auto-release timeout safety net.

### G-3: No CSRF protection on state-changing anonymous endpoints
- Chat and search allow anonymous POST without CSRF tokens. Low risk since they don't mutate user data, but could be abused for credit exhaustion.
- **Priority**: Medium

### G-4: No pagination for rows/projects
- `fetchRowsFromDb` loads ALL rows. For power users with 100+ rows, this will be slow.
- **Priority**: Low (no power users yet)

### G-5: No error boundary in React tree
- If any component throws during render, the entire app crashes. No `ErrorBoundary` wrapper.
- **Priority**: Medium

### G-6: No retry logic for LLM calls in chat endpoint
- `make_unified_decision()` calls Gemini once. If it fails, the entire chat request fails. `call_gemini` has Gemini→OpenRouter fallback but no retry within each provider.
- **Priority**: Medium

### G-7: No health check endpoint exposed
- `observability/health.py` exists but isn't verified to be registered in Railway.
- **Priority**: Low

### G-8: No vendor data backup automation
- Manual `backup_vendors.py` script. No cron or scheduled backup.
- **Priority**: Medium (3K+ vendors at risk)

---

## DEAD CODE (7)

### DC-1: `selectOrCreateRow` in store — unused
- `store.ts:549-597` — complex row matching logic, but `Chat.tsx` uses the LLM decision engine instead. No component calls this.

### DC-2: `fetchLikesApi` — unused
- `api.ts:469-483` — likes are now fetched as part of search results (bids have `is_liked` flag).

### DC-3: `runSearchApi` wrapper — unnecessary
- `api.ts:177-184` — just calls `runSearchApiWithStatus` and discards the status. Only 0 external callers.

### DC-4: Old outreach models (`SellerQuote`, `OutreachEvent`, `VendorProfile`)
- In `models/marketplace.py` — superseded by `models/outreach.py` campaign system.

### DC-5: `services/email.py` and `services/vendors.py`
- Used only by old `outreach.py`. The new campaign system uses `OutreachService`.

### DC-6: `routes/seller.py`, `routes/checkout.py`
- Seller quote submission and checkout routes — these are stub/placeholder implementations.

### DC-7: `routes/stripe_connect.py`
- Stripe Connect onboarding routes — not wired to any frontend flow.

---

## TECH DEBT (5)

### TD-1: Pydantic V1 validators in `auth.py`
- `@validator('phone')` — deprecated, should use `@field_validator`.
- Already flagged by pytest warnings.

### TD-2: `model.dict()` → `model.model_dump()` in `rows.py`
- Pydantic V2 deprecation warning on every PATCH.

### TD-3: `@app.on_event("startup"/"shutdown")` deprecated
- `main.py:269, 306` — should use lifespan event handlers.

### TD-4: Store is a monolith (598 lines)
- `store.ts` handles everything: rows, projects, results, UI state, delete undo.
- **Recommendation**: Split into slices: `rowResultsSlice`, `projectSlice`, `uiSlice`.

### TD-5: `RowStrip.tsx` is 546 lines
- Handles rendering, sorting, like/select/comment/share/copy — too many responsibilities.
- **Recommendation**: Extract handlers into a `useRowStripActions(row)` hook.

---

## Architecture Diagram (Current)

```
Frontend (Next.js 15 + Zustand)
├── page.tsx (workspace — chat + board)
├── Chat.tsx → SSE → /api/chat → chat.py
│   ├── acquireStreamingLock / releaseStreamingLock (60s timeout)
│   ├── appendRowResults (APPEND, safe during SSE)
│   └── setRowResults (REPLACE, blocked by streaming lock)
├── Board.tsx → RowStrip.tsx → OfferTile.tsx
│   ├── updateRowOffer (targeted mutation, always safe)
│   └── auto-load guard (isSearching + moreResultsIncoming + streamingRowIds)
├── store.ts (Zustand — single source of truth)
│   ├── rowResults: Record<number, Offer[]>
│   ├── streamingRowIds: Record<number, boolean>  ← NEW
│   └── updateRowOffer: targeted mutation          ← NEW
└── api.ts (all backend calls via /api/* proxy)

Backend (FastAPI + SQLModel + PostgreSQL)
├── routes/ (26 files)
│   ├── chat.py (LLM decision → SSE stream)
│   ├── rows_search.py (streaming + non-streaming search)
│   ├── rows.py (CRUD)
│   └── 23 more route files
├── services/
│   ├── llm.py (Gemini → OpenRouter fallback)
│   └── outreach_service.py (campaign system)
├── sourcing/
│   ├── repository.py (5 providers: SerpAPI, Rainforest, Google CSE, SearchAPI, Vendor Directory)
│   ├── service.py (search + persist + score)
│   └── scorer.py (multi-signal scoring)
└── models/ (6 domain modules)
```

---

## Prioritized Fix List (Demo Day)

| # | Finding | Status | Commit |
|---|---------|--------|--------|
| 1 | G-1: Rate limit anonymous chat | ✅ Done | `6531abe` |
| 2 | B-1: Unify guest user lookup | ✅ Done | `6531abe` |
| 3 | B-4: Remove debug logging | ✅ Done | `6531abe` |
| 4 | G-5: Add React ErrorBoundary | ✅ Done | `6531abe` |
| 5 | B-7: Public search crash (merchant_name, ChatContext) | ✅ Done | `891be79` |
| 6 | G-2: Streaming lock 60s timeout | ✅ Done | `0409b39` |
| 7 | D-6: Provider badge key fix | ✅ Done | `6531abe` |
| 8 | DC-3: Remove runSearchApi wrapper | ✅ Done | `6531abe` |

## Remaining (Post-Demo)

| # | Finding | Effort | Priority |
|---|---------|--------|----------|
| 1 | D-2: Extract bid hydration helper | 30m | Medium |
| 2 | D-4: Auth check boilerplate (20+ routes) | 1h | Medium |
| 3 | TD-4: Split store into slices | 2h | Low |
| 4 | B-6: Deprecate old outreach system | 1h | Medium |
| 5 | DC-1,2,4-7: Remove remaining dead code | 1h | Low |
| 6 | B-2: session.execute→session.exec migration | 2h | Low |
| 7 | B-3: datetime.utcnow migration (104 files) | 2h | Low |
| 8 | TD-1,2,3: Pydantic V2 + lifespan migration | 1h | Low |
| 9 | B-5: backendUrl removal (blocked by e2e test ref) | 5m | Low |
