# Task Breakdown — enhancement-bug-report-triage

## task-001 — Data model + migration for triage fields
- **Description**: Add classification fields to BugReport model and ensure DB migration path is defined.
- **E2E flow**: Submit bug report → record persists with new classification fields (null initially).
- **Manual verification**:
  1. Submit a bug report via UI
  2. Inspect DB row for BugReport — fields exist and are null
- **Files**: `apps/backend/models.py`, migration files (if applicable)
- **Tests to write (after)**: model/migration sanity test (if pattern exists)
- **Dependencies**: none
- **Estimate**: 30–45m

## task-002 — LLM triage + routing logic in bugs.py
- **Description**: Add classification prompt and decision matrix inside `create_github_issue_task`.
- **E2E flow**: Submit report → background task classifies → routes to GH issue and/or email.
- **Manual verification**:
  1. Post a report with “dark mode request” → no GH issue, email sent
  2. Post a report with “crash on click” → GH issue created
  3. Post ambiguous report → GH issue + email
- **Files**: `apps/backend/routes/bugs.py`
- **Tests to write (after)**: triage routing unit test with mocked classifier
- **Dependencies**: task-001
- **Estimate**: 45m

## task-003 — Email notification for feature/low-confidence
- **Description**: Add triage notification email to `services/email.py` using Resend.
- **E2E flow**: feature request / low confidence → email sent to `masseyl@gmail.com`.
- **Manual verification**:
  1. Trigger email path (feature request) and confirm resend logs or provider
- **Files**: `apps/backend/services/email.py`
- **Tests to write (after)**: email payload unit test (mock Resend client)
- **Dependencies**: task-002
- **Estimate**: 30m

## task-004 — Tests + evidence capture
- **Description**: Add automated tests for triage decision matrix + notification triggers.
- **E2E flow**: Run tests → all pass.
- **Manual verification**:
  1. Run test suite
  2. Confirm triage tests cover bug/feature/low-confidence
- **Files**: `apps/backend/tests/test_bug_triage.py`
- **Tests to write (after)**: this task is test creation
- **Dependencies**: task-002, task-003
- **Estimate**: 30–45m
