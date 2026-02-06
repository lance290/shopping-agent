# Code Review Issues - Iteration 1

## Summary
- **Total Issues**: 10
- **Critical**: 2 (must fix)
- **Major**: 4 (should fix)
- **Minor**: 3 (nice to fix)
- **Nits**: 1 (optional polish)

## Critical Issues 🔴

### C1: `backend_url` undefined in `send_outreach_email` — runtime NameError
- **File**: `apps/backend/services/email.py:103`
- **Category**: Logic / Runtime Crash
- **Problem**: The unsubscribe link uses `{backend_url}` in the f-string, but `backend_url` is never defined in `send_outreach_email`'s scope. It's only a local var inside `get_tracking_pixel_url`. Any real outreach email will crash with `NameError: name 'backend_url' is not defined`.
- **Risk**: Complete failure of outreach email sending.
- **Fix**: Add `backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")` at the top of `send_outreach_email`, matching the pattern in `send_reminder_email`.

### C2: Merchant registration page calls BFF directly from browser
- **File**: `apps/frontend/app/merchants/register/page.tsx:42-43`
- **Category**: Security / Architecture
- **Problem**: `fetch(\`${backendUrl}/merchants/register\`)` calls BFF directly from the client using `NEXT_PUBLIC_BFF_URL`. This:
  1. Exposes internal service URL to the browser
  2. Will fail in production due to CORS (BFF isn't configured for cross-origin)
  3. Violates the established proxy pattern (shares, quotes all proxy through `/api/...`)
- **Risk**: Feature completely broken in production. Internal URL leak.
- **Fix**: Create `/api/merchants/register` Next.js API route to proxy to BFF, then call `/api/merchants/register` from the page.

## Major Issues 🟠

### M1: `close_handoff` endpoint has no authentication
- **File**: `apps/backend/routes/quotes.py:337-363`
- **Category**: Security
- **Problem**: Anyone who can guess a handoff_id integer can close the deal. No auth check.
- **Fix**: Add auth requirement or validate against a token.

### M2: Merchant search leaks email addresses in public API
- **File**: `apps/backend/routes/merchants.py:168-176`
- **Category**: Privacy / PII
- **Problem**: `GET /merchants/search` returns `email` in results with no auth required. Merchant emails are PII and shouldn't be in public search results.
- **Fix**: Remove `email` from search response dict.

### M3: DRY violation — `normalizeBaseUrl` + `BFF_URL` duplicated
- **File**: `apps/frontend/app/api/shares/route.ts:3-13` and `apps/frontend/app/api/shares/[token]/route.ts:3-13`
- **Category**: DRY
- **Problem**: Exact same `normalizeBaseUrl` function and `BFF_URL` constant duplicated in both files.
- **Fix**: Extract to a shared `utils/bff.ts` helper (or reuse existing proxy util if one exists).

### M4: Merchant search loads all merchants then filters in Python
- **File**: `apps/backend/routes/merchants.py:152-177`
- **Category**: Performance
- **Problem**: Loads ALL verified merchants from DB, then filters by category/area in Python. Won't scale.
- **Fix**: For MVP this is acceptable but add a TODO. Long-term: use LIKE/JSON queries or a categories join table.

## Minor Issues 🟡

### m1: `import json` inside function body
- **File**: `apps/backend/routes/outreach.py:405`
- **Category**: Convention
- **Suggestion**: Move to top of file with other imports.

### m2: GET `/unsubscribe` modifies state
- **File**: `apps/backend/routes/outreach.py:381`
- **Category**: REST Convention
- **Suggestion**: GET requests shouldn't modify state. Email scanners and link prefetchers can trigger GET requests, causing accidental unsubscribes. Should be POST (with GET rendering a confirmation page).

### m3: `ContractResponse` construction duplicated
- **File**: `apps/backend/routes/contracts.py:95-103` and `124-132`
- **Category**: DRY
- **Suggestion**: Extract `_contract_to_response(contract)` helper.

## Nits 🟢

### n1: `print()` instead of `logging` in contracts.py
- **File**: `apps/backend/routes/contracts.py:88-89`
- **Suggestion**: Use `logging.info()` for demo mode messages, matching other modules.

---

## Verdict: FAIL

Fix all Critical and Major issues, then re-run /review-loop.
