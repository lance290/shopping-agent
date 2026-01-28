# Tasks - enhancement-ai-bug-fixer-verification-loop

> **Task list protection**: After approval, it is unacceptable to remove or edit tasks. Only `status` may change in `tasks.json`.

## Task Summary
| ID | Description | Estimate |
|---|-------------|----------|
| abf-verify-001 | Define webhook authentication + payload contract (GitHub + Railway) | 45m |
| abf-verify-002 | Implement GitHub webhook endpoint: PR opened → `pr_created` | 45m |
| abf-verify-003 | Implement preview URL update: Railway webhook (or fallback hook) → `preview_ready` | 45m |
| abf-verify-004 | Implement GitHub webhook endpoint: PR merged → `shipped` | 30m |
| abf-verify-005 | Update reporter status UI to show PR/preview/shipped | 45m |

---

## abf-verify-001 — Webhook auth + contracts
- **E2E flow to build**
  - Webhook endpoints reject unsigned/invalid requests.
- **Manual verification**
  - POST invalid signature → 401/403
  - POST valid signature → 200
- **Files**
  - `apps/backend/main.py`
  - `apps/backend/...` (webhook verification helpers)
- **Tests to write AFTER**
  - Unit test: signature verification
- **Dependencies**
  - None
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-verify-001/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance

## abf-verify-002 — GitHub PR opened webhook
- **E2E flow to build**
  - Receiving PR opened event updates bug report status to `pr_created` and stores PR URL if available.
- **Manual verification**
  - Send sample PR opened payload
  - Fetch bug report → status `pr_created`
- **Files**
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - Unit test: payload mapping
- **Dependencies**
  - `abf-verify-001`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-verify-002/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance

## abf-verify-003 — Preview URL update
- **E2E flow to build**
  - When preview URL is available, bug report stores it and status becomes `preview_ready`.
- **Manual verification**
  - POST sample Railway payload (or internal fallback endpoint)
  - Fetch bug report → preview URL present and clickable
- **Files**
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - Unit test: preview URL update
- **Dependencies**
  - `abf-verify-001`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-verify-003/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance

## abf-verify-004 — GitHub PR merged webhook
- **E2E flow to build**
  - PR merged event updates bug report status to `shipped`.
- **Manual verification**
  - POST sample PR merged payload
  - Fetch bug report → status `shipped`
- **Files**
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - Unit test: merged mapping
- **Dependencies**
  - `abf-verify-002`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-verify-004/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance

## abf-verify-005 — Reporter status UI updates
- **E2E flow to build**
  - Reporter status view shows PR created, preview ready (with link), and shipped.
- **Manual verification**
  - View a report in each state (seed or update)
  - Confirm UI reflects state and link works
- **Files**
  - `apps/frontend/app/...`
- **Tests to write AFTER**
  - Playwright: status progression display
- **Dependencies**
  - `abf-verify-003`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-verify-005/manual.md`
  - Automated: Playwright output
  - Human sign-off: Lance
