# Tasks - enhancement-ai-bug-fixer-polish-routing-notifications

> **Task list protection**: After approval, it is unacceptable to remove or edit tasks. Only `status` may change in `tasks.json`.

## Task Summary
| ID | Description | Estimate |
|---|-------------|----------|
| abf-polish-001 | Add error boundary “Report Bug” entry point | 45m |
| abf-polish-002 | Add severity/category routing config (policy) | 45m |
| abf-polish-003 | Add high-severity notification sender (link-only) | 45m |
| abf-polish-004 | Add rate limiting/aggregation for notifications | 30m |

---

## abf-polish-001 — Error boundary entry point
- **E2E flow to build**
  - On a crash, the error UI offers a `Report Bug` entry point that opens the bug report flow.
- **Manual verification**
  - Force a crash route
  - Verify error UI shows `Report Bug`
  - Click it → bug report modal opens
- **Files**
  - `apps/frontend/app/.../error.tsx` (or equivalent)
  - Shared bug report modal entry wiring
- **Tests to write AFTER**
  - Playwright: crash page offers Report Bug
- **Dependencies**
  - UX modal exists (`feature-ai-bug-fixer-report-bug-ux`)
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-polish-001/manual.md`
  - Automated: Playwright output
  - Human sign-off: Lance

## abf-polish-002 — Routing config
- **E2E flow to build**
  - Routing policy exists for severity/category (even if Claude triggers every time) to drive notification priority and internal triage.
- **Manual verification**
  - Submit a High severity report
  - Verify routing decision recorded/logged
- **Files**
  - `apps/backend/...` or `apps/bff/...` (routing config)
- **Tests to write AFTER**
  - Unit test: routing rules
- **Dependencies**
  - Storage/status exists (`feature-ai-bug-fixer-storage-status`)
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-polish-002/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance

## abf-polish-003 — High-severity notifications
- **E2E flow to build**
  - High/Blocking bug reports trigger an internal notification containing Bug ID + link (no attachments).
- **Manual verification**
  - Configure notification destination (env)
  - Submit Blocking report
  - Verify notification received (or logged)
- **Files**
  - `apps/backend/...` (notification sender)
- **Tests to write AFTER**
  - Unit test: notification payload contains links only
- **Dependencies**
  - `abf-polish-002`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-polish-003/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance

## abf-polish-004 — Notification rate limiting
- **E2E flow to build**
  - Notification spam is prevented via rate limiting/aggregation.
- **Manual verification**
  - Submit 5 high severity reports quickly
  - Verify notifications are limited/aggregated
- **Files**
  - `apps/backend/...` (rate limiter)
- **Tests to write AFTER**
  - Unit test: rate limiter behavior
- **Dependencies**
  - `abf-polish-003`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-polish-004/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance
