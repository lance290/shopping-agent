# Tasks — enhancement-user-data-isolation

> ⚠️ **Task list protection**: After approval, do not edit task descriptions/order in `tasks.json`. Only update `status` fields.

## Task Breakdown

### task-001 — Backend: add `user_id` to `AuthSession` and mint sessions with `user_id`
- **E2E flow**: After login verification, session is tied to a User via `user_id`
- **Manual verification**
  - Ensure backend boots
  - Login via `/auth/start` + `/auth/verify`
  - Confirm `/auth/me` works with the issued token
- **Files**
  - `apps/backend/models.py`
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - `apps/backend/tests/test_auth_session_user_id.py` (new)
- **Dependencies**: none
- **Estimate**: 35m
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/task-001/manual.md`
  - Automated: backend test(s) above
  - Owner sign-off: Lance

---

### task-002 — Backend: add `user_id` ownership to `Row` + enforce auth + ownership on `/rows` endpoints
- **E2E flow**: Authenticated user can CRUD only their own rows; cross-user access returns 404
- **Manual verification**
  - With an authenticated token, create a row
  - List rows and confirm only your rows appear
  - Attempt to access a different user’s row ID and confirm 404
  - Confirm unauthenticated requests to `/rows` return 401
- **Files**
  - `apps/backend/models.py`
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - `apps/backend/tests/test_rows_authorization.py` (new)
- **Dependencies**
  - task-001
- **Estimate**: 45m
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/task-002/manual.md`
  - Automated: backend test(s) above
  - Owner sign-off: Lance

---

### task-003 — BFF: forward Authorization for `/api/rows` and ensure chat tool row creation respects auth
- **E2E flow**: Frontend sends Authorization to BFF; BFF forwards to backend; chat `createRow` cannot bypass auth
- **Manual verification**
  - With cookie-based session, load app and confirm requests list loads
  - Create a row via chat; confirm it is created successfully
  - Call BFF `/api/rows` without Authorization and confirm 401
- **Files**
  - `apps/bff/src/index.ts`
  - `apps/bff/src/llm.ts`
- **Tests to write AFTER**
  - `apps/bff/src/index.test.ts` (extend if test harness exists)
- **Dependencies**
  - task-002
- **Estimate**: 40m
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/task-003/manual.md`
  - Automated: as applicable
  - Owner sign-off: Lance

---

### task-004 — Frontend (Next API): attach Authorization from `sa_session` cookie for `/api/rows` and `/api/chat`
- **E2E flow**: Logged-in user can fetch/create/update/delete rows and chat can create rows with auth
- **Manual verification**
  - Login in browser
  - Confirm Requests sidebar shows only your rows
  - Create a new request via chat and confirm it appears
  - Confirm no session token is exposed to JS (HTTP-only cookie)
- **Files**
  - `apps/frontend/app/api/rows/route.ts`
  - `apps/frontend/app/api/chat/route.ts`
  - `apps/frontend/app/api/auth/constants.ts`
- **Tests to write AFTER**
  - `apps/frontend/e2e/user-data-isolation.spec.ts` (new)
- **Dependencies**
  - task-003
- **Estimate**: 30m
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/task-004/manual.md`
  - Automated: Playwright
  - Owner sign-off: Lance

---

### task-005 — Backend: add `E2E_TEST_MODE`-only endpoint to mint sessions for Playwright isolation tests
- **E2E flow**: Automated tests can obtain distinct user tokens without relying on email delivery
- **Manual verification**
  - Set `E2E_TEST_MODE=1` locally
  - Call endpoint to mint a token for user A and user B
  - Confirm endpoint is disabled when `E2E_TEST_MODE` is not set
- **Files**
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - `apps/backend/tests/test_e2e_mint_endpoint.py` (new)
- **Dependencies**
  - task-001
- **Estimate**: 35m
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/task-005/manual.md`
  - Automated: backend test(s) above
  - Owner sign-off: Lance

---

### task-006 — Playwright: add E2E coverage for cross-user isolation (list/get/patch/delete)
- **E2E flow**: User A creates a row; User B cannot list it nor access it by ID; write attempts are blocked
- **Manual verification**
  - Run the new Playwright spec locally
  - Confirm it passes deterministically
- **Files**
  - `apps/frontend/e2e/user-data-isolation.spec.ts`
- **Tests to write AFTER**
  - (this task is the test)
- **Dependencies**
  - task-004
  - task-005
- **Estimate**: 45m
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/task-006/manual.md`
  - Automated: Playwright
  - Owner sign-off: Lance

---

### task-007 — Operational: reset DB (dev + Railway) and capture evidence that isolation is active
- **E2E flow**: Fresh DB has correct schema and isolation behavior is verified end-to-end
- **Manual verification**
  - Reset local DB (docker volume) and restart services
  - Reset Railway Postgres (acceptable data loss)
  - Confirm login works and each account sees only its own rows
- **Files**
  - N/A
- **Tests to write AFTER**: none
- **Dependencies**
  - task-002
  - task-006
- **Estimate**: 30m
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/task-007/manual.md`
  - Automated: N/A
  - Owner sign-off: Lance

