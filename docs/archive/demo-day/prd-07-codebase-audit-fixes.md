# PRD-07: Codebase Audit Fixes — Stability & Reliability

## Business Outcome
- Measurable impact: Zero crashes, zero silent failures, zero result-display bugs during investor demo
- Success criteria: All 38 audit findings triaged; P0 items fixed and tested; P1 items documented for post-demo
- Target users: Demo audience (stability), development team (maintainability), anonymous visitors (no white-screen crashes)

## Scope
- In-scope (P0 — must fix before demo):
  - Rate limit anonymous chat to prevent LLM credit exhaustion (G-1)
  - Unify guest user lookup to single helper (B-1, D-1)
  - Remove production debug logging (B-4)
  - Add React ErrorBoundary to prevent white-screen crashes (G-5)
  - Remove dead `backendUrl` variable (B-5)
  - Extract shared bid-to-offer hydration helper (D-2)
  - Remove dead code: unused API helpers, unused store methods (DC-1, DC-2, DC-3)
- In-scope (P1 — fix if time permits):
  - Deduplicate share link creation in RowStrip (D-7)
  - Deduplicate row delete cleanup pattern (D-3)
  - Fix provider status badge key to not use index (D-6)
- Out-of-scope (post-demo):
  - `datetime.utcnow()` migration (B-3, 104 files — too risky before demo)
  - `session.execute()` → `session.exec()` migration (B-2, 28 instances — low risk, low priority)
  - Store slice decomposition (TD-4 — architectural, no demo impact)
  - Old outreach system deprecation (B-6 — needs product decision)
  - Pydantic V1 → V2 migration (TD-1, TD-2 — no demo impact)

## User Flow
No user-facing flow changes. All fixes are internal reliability improvements that prevent:
1. White-screen crash if a component throws during render
2. Silent result wipe during SSE streaming (already fixed — this PRD adds the safety timeout)
3. LLM credit exhaustion from bot traffic on anonymous chat
4. Stale guest user references if the guest email constant changes

## Business Requirements

### Authentication & Authorization
- Anonymous chat rate limit: max 10 requests per 15 minutes per IP (configurable)
- Guest user lookup must use shared `_resolve_user_id()` helper from `rows_search.py`
- `GUEST_EMAIL` constant must be defined once and imported everywhere

### Monitoring & Visibility
- Remove `console.log` debug statements from production store
- Streaming lock timeout logs a warning when auto-releasing (already done)
- Rate limit rejections should return 429 with human-readable message

### Performance Expectations
- No performance regression from any fix
- ErrorBoundary should render a fallback UI, not a blank page
- Dead code removal reduces bundle size slightly

### Privacy, Security & Compliance
- Rate limiting prevents abuse of LLM API credits
- No PII changes
- ErrorBoundary fallback must not expose stack traces in production

## Technical Requirements

### T-1: Rate limit anonymous chat (G-1)
- Backend: Add IP-based rate limiting to `/api/chat` for unauthenticated users
- Use existing `check_rate_limit()` from `routes/rate_limit.py`
- Key: `chat:guest:{ip}` with limit of 10 requests per 15 minutes
- Authenticated users: existing per-user rate limiting applies

### T-2: Unify guest user lookup (B-1, D-1)
- Move `_resolve_user_id()` and `GUEST_EMAIL` from `rows_search.py` to `dependencies.py`
- Update `chat.py` to import and use the shared helper
- Update `rows_search.py` to import from `dependencies.py`
- Single constant, single function, three consumers

### T-3: Remove production debug logging (B-4)
- Remove `console.log('[Store] setRows called with...')` from `store.ts`
- Remove `console.log('[API] Running search...')` and similar verbose logs from `api.ts`
- Keep error-level logs (`console.error`)

### T-4: Add React ErrorBoundary (G-5)
- Create `components/ErrorBoundary.tsx` with:
  - Catches render errors in child tree
  - Shows user-friendly fallback: "Something went wrong. Refresh to try again."
  - Logs error to console (no external reporting for MVP)
- Wrap the main workspace layout in ErrorBoundary
- Wrap each RowStrip in its own ErrorBoundary (isolate per-row crashes)

### T-5: Remove dead code (B-5, DC-1, DC-2, DC-3)
- `api.ts`: Remove `backendUrl`, `fetchLikesApi`, `runSearchApi`
- `store.ts`: Remove `selectOrCreateRow`
- Verify no callers remain before each removal

### T-6: Extract bid hydration helper (D-2)
- Extract `mergeBidsIntoResults(existingResults, bids)` from duplicated logic in:
  - `store.ts:setRows()` (lines 391-420)
  - `store.ts:updateRow()` (lines 439-463)
- Both call sites use the extracted helper

### T-7 (P1): Deduplicate share link creation (D-7)
- RowStrip `handleShare` and `handleCopySearchLink` both construct inline fetch calls
- Replace with `createShareLink()` from `api.ts`

### T-8 (P1): Fix provider status badge key (D-6)
- Change `key={status.provider_id + idx}` to `key={status.provider_id}`
- provider_id should be unique per provider in a row's statuses

## Dependencies
- Upstream: Streaming lock fix (completed — PRD N/A, done in this session)
- Upstream: All PRDs 00-06 (this is a stabilization pass on top)
- Downstream: Demo prep (PRD-06) — stability is a prerequisite for a clean demo

## Risks & Mitigations
- Dead code removal breaks something → Run full test suite after each removal; revert if tests fail
- Rate limiting blocks legitimate demo usage → Set generous limits (10/15min) and test with demo queries
- ErrorBoundary swallows useful errors → Log all caught errors to console; only suppress in UI

## Acceptance Criteria (Business Validation)
- [ ] Anonymous chat returns 429 after 10 requests in 15 minutes (test with curl)
- [ ] `GUEST_EMAIL` is defined in exactly one file, imported by all consumers
- [ ] No `console.log` statements in `store.ts` or `api.ts` (only `console.error`)
- [ ] React ErrorBoundary catches a simulated render error and shows fallback UI
- [ ] `selectOrCreateRow`, `fetchLikesApi`, `runSearchApi`, `backendUrl` are removed
- [ ] `mergeBidsIntoResults` helper exists and is used by both `setRows` and `updateRow`
- [ ] All existing tests pass (255 frontend, 406 backend)
- [ ] No TypeScript errors (`npx tsc --noEmit` clean except pre-existing test file issues)

## Traceability
- Parent PRD: `docs/active-dev/demo-day/parent.md`
- Audit report: `docs/active-dev/2026-02-17-codebase-audit-v2.md`
- Product North Star: `.cfoi/branches/dev/product-north-star.md`

---
**Note:** This PRD addresses findings from the Feb 17 codebase audit. Items marked P1 are best-effort before demo; items marked out-of-scope are documented for the post-demo sprint.
