# Tasks - enhancement-ai-bug-fixer-diagnostics-redaction

> **Task list protection**: After approval, it is unacceptable to remove or edit tasks. Only `status` may change in `tasks.json`.

## Task Summary
| ID | Description | Estimate |
|---|-------------|----------|
| abf-diag-001 | Add client-side ring buffers (console + network failures) | 45m |
| abf-diag-002 | Add breadcrumbs capture (route + key UI actions) | 45m |
| abf-diag-003 | Implement client-side redaction (defense-in-depth) | 45m |
| abf-diag-004 | Implement server-side validation + redaction + truncation | 45m |
| abf-diag-005 | Ensure diagnostics are best-effort (failures don’t block submission) | 30m |
| abf-diag-006 | Include diagnostic summary in GitHub issue (top errors + last failed endpoint) | 45m |

---

## abf-diag-001 — Client-side ring buffers
- **E2E flow to build**
  - When diagnostics enabled, client collects last N console events and last N failed network request metadata.
- **Manual verification**
  - Trigger a console error
  - Trigger a failed request
  - Submit bug report; confirm payload includes diagnostic buffers
- **Files**
  - `apps/frontend/app/...` (diagnostics utility)
- **Tests to write AFTER**
  - Unit tests for ring buffer behavior (optional)
- **Dependencies**
  - None
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-diag-001/manual.md`
  - Automated: N/A
  - Human sign-off: Lance

## abf-diag-002 — Breadcrumbs capture
- **E2E flow to build**
  - Client captures last N route changes / major UI actions for repro context.
- **Manual verification**
  - Navigate between 2 pages and click a key button
  - Submit bug report
  - Verify breadcrumbs present
- **Files**
  - `apps/frontend/app/...` (breadcrumb tracker)
- **Tests to write AFTER**
  - Unit test for breadcrumb ring buffer (optional)
- **Dependencies**
  - `abf-diag-001`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-diag-002/manual.md`
  - Automated: N/A
  - Human sign-off: Lance

## abf-diag-003 — Client-side redaction
- **E2E flow to build**
  - Client redacts tokens/cookies/auth headers and truncates long values before submission.
- **Manual verification**
  - Force a request that would include an Authorization header
  - Submit bug report
  - Verify redacted fields are not present in payload
- **Files**
  - `apps/frontend/app/...` (redaction helper)
- **Tests to write AFTER**
  - Unit test for redaction rules
- **Dependencies**
  - `abf-diag-001`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-diag-003/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance

## abf-diag-004 — Server-side validation + redaction
- **E2E flow to build**
  - Server validates diagnostics schema, applies redaction again, truncates large payloads, stores metadata only for network requests.
- **Manual verification**
  - Submit report with diagnostics
  - Inspect stored diagnostics (DB) or returned summaries
  - Confirm secrets are removed
- **Files**
  - `apps/backend/main.py`
  - `apps/backend/...` (diagnostics validation/redaction module)
- **Tests to write AFTER**
  - Unit test with representative payload containing secrets
- **Dependencies**
  - `abf-diag-003`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-diag-004/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance

## abf-diag-005 — Best-effort diagnostics
- **E2E flow to build**
  - If diagnostics capture fails, bug report still submits successfully.
- **Manual verification**
  - Simulate diagnostics throw
  - Submit bug report
  - Verify receipt still shown
- **Files**
  - `apps/frontend/app/...` and/or `apps/backend/...`
- **Tests to write AFTER**
  - None
- **Dependencies**
  - `abf-diag-001`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-diag-005/manual.md`
  - Automated: N/A
  - Human sign-off: Lance

## abf-diag-006 — GitHub issue summary integration
- **E2E flow to build**
  - GitHub issue created from a bug report includes a safe diagnostics summary (top errors + last failed endpoint).
- **Manual verification**
  - Submit bug report with diagnostics enabled
  - Check GitHub issue contains summary of top errors + last failed endpoint
  - Verify no secrets in issue summary
- **Files**
  - `apps/backend/...` (issue formatter / diagnostics summarizer)
- **Tests to write AFTER**
  - Unit test: diagnostics summary formatting + safety
- **Dependencies**
  - `abf-diag-004`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-diag-006/manual.md`
  - Automated: unit test output
  - Human sign-off: Lance
