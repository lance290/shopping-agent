# Tasks - feature-ai-bug-fixer-report-bug-ux

> **Task list protection**: After approval, it is unacceptable to remove or edit tasks. Only `status` may change in `tasks.json`.

## Task Summary
| ID | Description | Estimate |
|---|-------------|----------|
| abf-ux-001 | Add header/help “Report Bug” entry point | 30m |
| abf-ux-002 | Build Report Bug modal UI (screenshots + notes + optional fields) | 45m |
| abf-ux-003 | Client API + Next route handler `POST /api/bugs` forwarding to BFF | 45m |
| abf-ux-004 | Wire upload selection + submission to backend (happy path) | 45m |
| abf-ux-005 | Add Playwright E2E: submit report → receipt | 45m |
| abf-ux-006 | Add submission observability (success/failure + latency) | 30m |

---

## abf-ux-001 — Add header/help “Report Bug” entry point
- **E2E flow to build**
  - User sees `Report Bug` in header/help menu and can open the modal.
- **Manual verification**
  - Open app
  - Click `Report Bug`
  - Verify modal opens
- **Files**
  - `apps/frontend/app/...` (header/help UI component)
- **Tests to write AFTER**
  - None (covered by E2E task)
- **Dependencies**
  - None
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-ux-001/manual.md`
  - Automated: covered by `abf-ux-005`
  - Human sign-off: Lance

## abf-ux-002 — Build Report Bug modal UI
- **E2E flow to build**
  - User can attach 1+ images, enter notes, optionally fill expected/actual, select severity/category, toggle include diagnostics.
  - Submit button disabled until required fields satisfied.
- **Manual verification**
  - Open modal
  - Attach 2 images
  - Enter notes
  - Toggle include diagnostics
  - Verify submit enabled
- **Files**
  - `apps/frontend/app/...` (modal component + supporting UI)
- **Tests to write AFTER**
  - None (covered by E2E task)
- **Dependencies**
  - `abf-ux-001`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-ux-002/manual.md`
  - Automated: covered by `abf-ux-005`
  - Human sign-off: Lance

## abf-ux-003 — Client API + Next route handler `POST /api/bugs`
- **E2E flow to build**
  - Frontend calls `POST /api/bugs` and request is forwarded to BFF correctly.
- **Manual verification**
  - Submit the modal
  - Inspect network: request to `/api/bugs` returns 200/201
- **Files**
  - `apps/frontend/app/api/bugs/route.ts`
  - `apps/frontend/app/utils/api.ts`
- **Tests to write AFTER**
  - None (covered by E2E task)
- **Dependencies**
  - `abf-ux-002`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-ux-003/manual.md`
  - Automated: covered by `abf-ux-005`
  - Human sign-off: Lance

## abf-ux-004 — Wire upload selection + submission (happy path)
- **E2E flow to build**
  - User submits bug report and sees a receipt showing Bug ID + initial status.
- **Manual verification**
  - Submit a valid report
  - Verify receipt renders Bug ID and `Captured`
- **Files**
  - `apps/frontend/app/...` (submission handler + receipt UI)
- **Tests to write AFTER**
  - None (covered by E2E task)
- **Dependencies**
  - `abf-ux-003`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-ux-004/manual.md`
  - Automated: covered by `abf-ux-005`
  - Human sign-off: Lance

## abf-ux-005 — Playwright E2E: submit report → receipt
- **E2E flow to build**
  - Automated browser test covers opening modal, attaching screenshot, submitting, seeing receipt.
- **Manual verification**
  - Run Playwright suite
  - Confirm this test passes locally
- **Files**
  - `apps/frontend/...` Playwright test folder
- **Tests to write AFTER**
  - This task *is* the test
- **Dependencies**
  - `abf-ux-004`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-ux-005/manual.md`
  - Automated: `playwright` run output captured
  - Human sign-off: Lance

## abf-ux-006 — Submission observability
- **E2E flow to build**
  - Submission logs/metrics record success/failure and latency.
- **Manual verification**
  - Submit a report
  - Confirm logs/metrics include event with Bug ID correlation
- **Files**
  - `apps/frontend/app/...` or backend logging target (decide during implementation)
- **Tests to write AFTER**
  - None
- **Dependencies**
  - `abf-ux-004`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-ux-006/manual.md`
  - Automated: N/A
  - Human sign-off: Lance
