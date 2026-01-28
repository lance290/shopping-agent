# Tasks - feature-email-auth

> **Rule**: It is unacceptable to remove or edit tasks after approval. In `tasks.json`, ONLY the `status` field may be changed.

## Task List (Click-First)

### task-001 — Backend models + hashing helpers
- **Goal**: Add backend auth data models (login codes + sessions) with hashing helpers
- **E2E flow**: Developer can start backend and DB initializes auth tables without breaking existing endpoints
- **Manual verification**:
  1. Start Postgres (`docker-compose.dev.yml`)
  2. Start backend
  3. Confirm backend starts successfully and existing `/health` and `/rows` endpoints still work
- **Files**:
  - `apps/backend/models.py`
  - `apps/backend/database.py`
- **Tests to write after**:
  - `apps/backend/tests/test_auth_models.py` (or equivalent)
- **Dependencies**: none
- **Estimate**: 35m
- **Error budget**: 3
- **Evidence**:
  - Manual: `.cfoi/branches/main/proof/task-001/manual.md`
  - Automated: backend unit tests referenced above

### task-002 — Backend Resend sender
- **Goal**: Implement Resend email sender utility (env-driven)
- **E2E flow**: Sending a code email via Resend succeeds (or fails clearly when misconfigured)
- **Manual verification**:
  1. Set `RESEND_API_KEY` and `FROM_EMAIL`
  2. Trigger a send to a test inbox
  3. Confirm email arrives from the configured FROM address
- **Files**:
  - `apps/backend/main.py`
- **Tests to write after**:
  - `apps/backend/tests/test_resend_sender.py` (mock `httpx`)
- **Dependencies**: task-001
- **Estimate**: 30m
- **Error budget**: 3
- **Evidence**:
  - Manual: `.cfoi/branches/main/proof/task-002/manual.md`
  - Automated: mocked sender test

### task-003 — Backend /auth/start
- **Goal**: Implement `POST /auth/start` (generate code, invalidate old, enforce lockout)
- **E2E flow**: User clicks “Send code” on `/login` and backend accepts unless in lockout
- **Manual verification**:
  1. `POST /auth/start` with a valid email → `{status: sent}`
  2. Request again → later verify proves old code invalidated
  3. Once lockout is reachable, confirm `429` during lockout
- **Files**:
  - `apps/backend/main.py`
  - `apps/backend/models.py`
- **Tests to write after**:
  - `apps/backend/tests/test_auth_start.py`
- **Dependencies**: task-001, task-002
- **Estimate**: 40m
- **Error budget**: 3
- **Evidence**:
  - Manual: `.cfoi/branches/main/proof/task-003/manual.md`
  - Automated: unit tests

### task-004 — Backend /auth/verify + /auth/me + /auth/logout
- **Goal**: Implement verification, session creation, session lookup, and logout revocation
- **E2E flow**: Correct code yields a session token; `/me` works; logout revokes
- **Manual verification**:
  1. `POST /auth/verify` with correct email+code returns `sessionToken`
  2. `GET /auth/me` with `Authorization: Bearer <token>` returns authenticated
  3. `POST /auth/logout` revokes token; `/me` returns `401`
  4. Wrong code 5 times triggers 45-minute lockout
- **Files**:
  - `apps/backend/main.py`
  - `apps/backend/models.py`
- **Tests to write after**:
  - `apps/backend/tests/test_auth_verify_and_lockout.py`
  - `apps/backend/tests/test_auth_sessions.py`
- **Dependencies**: task-001, task-003
- **Estimate**: 45m
- **Error budget**: 3
- **Evidence**:
  - Manual: `.cfoi/branches/main/proof/task-004/manual.md`
  - Automated: unit tests

### task-005 — BFF proxy routes
- **Goal**: Add `/api/auth/*` proxy routes to backend
- **E2E flow**: Frontend can call BFF auth endpoints and BFF forwards correctly
- **Manual verification**:
  1. Start BFF and backend
  2. `curl` BFF endpoints and confirm successful proxying
  3. Confirm `Authorization` header forwarding works for `/me` and `/logout`
- **Files**:
  - `apps/bff/src/index.ts`
- **Tests to write after**:
  - `apps/bff/src/index.test.ts` (or equivalent)
- **Dependencies**: task-004
- **Estimate**: 30m
- **Error budget**: 3
- **Evidence**:
  - Manual: `.cfoi/branches/main/proof/task-005/manual.md`
  - Automated: unit tests

### task-006 — Frontend Next API auth handlers (cookie)
- **Goal**: Next route handlers that set/clear `sa_session` HTTP-only cookie and proxy via BFF
- **E2E flow**: Browser receives HTTP-only cookie on verify; `/api/auth/me` reflects state
- **Manual verification**:
  1. Start frontend + BFF + backend
  2. Send code then verify code
  3. Confirm `Set-Cookie` for `sa_session` is present and `httpOnly`
  4. Call `/api/auth/me` and confirm authenticated
  5. Call `/api/auth/logout` and confirm cookie cleared
- **Files**:
  - `apps/frontend/app/api/auth/start/route.ts`
  - `apps/frontend/app/api/auth/verify/route.ts`
  - `apps/frontend/app/api/auth/me/route.ts`
  - `apps/frontend/app/api/auth/logout/route.ts`
- **Tests to write after**:
  - `apps/frontend/app/tests/auth-api.test.ts`
- **Dependencies**: task-005
- **Estimate**: 45m
- **Error budget**: 3
- **Evidence**:
  - Manual: `.cfoi/branches/main/proof/task-006/manual.md`
  - Automated: unit tests

### task-007 — Frontend /login page UI
- **Goal**: Add `/login` page with email + code steps and cooldown messaging
- **E2E flow**: User logs in via `/login` and is redirected to `/`
- **Manual verification**:
  1. Navigate to `/login`
  2. Enter email and click “Send code"
  3. Enter code and click “Verify"
  4. Confirm redirect to `/`
  5. Trigger lockout and confirm UI shows lockout state
- **Files**:
  - `apps/frontend/app/login/page.tsx`
- **Tests to write after**:
  - `apps/frontend/app/tests/login-page.test.tsx`
- **Dependencies**: task-006
- **Estimate**: 40m
- **Error budget**: 3
- **Evidence**:
  - Manual: `.cfoi/branches/main/proof/task-007/manual.md`
  - Automated: unit tests

### task-008 — Middleware route protection
- **Goal**: Protect `/` with middleware and redirect `/login` → `/` when authenticated
- **E2E flow**: Logged-out users are redirected to `/login`; logged-in users bypass /login
- **Manual verification**:
  1. Clear cookies and navigate to `/` → redirected to `/login`
  2. Login successfully and navigate to `/login` → redirected to `/`
- **Files**:
  - `apps/frontend/middleware.ts`
- **Tests to write after**:
  - `apps/frontend/app/tests/middleware-auth.test.ts`
- **Dependencies**: task-006, task-007
- **Estimate**: 25m
- **Error budget**: 3
- **Evidence**:
  - Manual: `.cfoi/branches/main/proof/task-008/manual.md`
  - Automated: unit tests

### task-009 — Playwright config + E2E auth test
- **Goal**: Make Playwright baseURL configurable and add E2E login/logout test
- **E2E flow**: Playwright runs against configurable baseURL and covers login/logout
- **Manual verification**:
  1. Set `PLAYWRIGHT_BASE_URL` (or similar) to local frontend URL
  2. Run Playwright locally
  3. Confirm test passes
- **Files**:
  - `apps/frontend/playwright.config.ts`
  - `apps/frontend/e2e/auth-login-logout.spec.ts`
- **Tests to write after**:
  - (The E2E test is the deliverable)
- **Dependencies**: task-008
- **Estimate**: 45m
- **Error budget**: 3
- **Evidence**:
  - Manual: `.cfoi/branches/main/proof/task-009/manual.md`
  - Automated: Playwright run output

## Review Notes
- All tasks are scoped to <45 minutes.
- Tasks are ordered to build a working end-to-end flow first, then lock it in with tests.
