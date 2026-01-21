# Tasks - feature-ai-bug-fixer-github-claude-trigger

> **Task list protection**: After approval, it is unacceptable to remove or edit tasks. Only `status` may change in `tasks.json`.

## Task Summary
| ID | Description | Estimate |
|---|-------------|----------|
| abf-gh-001 | Add root `CLAUDE.md` guardrails file | 30m |
| abf-gh-002 | Add backend GitHub client (auth + request helper) | 45m |
| abf-gh-003 | Implement issue creation on bug report submit | 45m |
| abf-gh-004 | Persist GitHub issue URL back onto bug report | 30m |
| abf-gh-005 | Add retry/backoff + observability for GitHub API failures | 45m |

---

## abf-gh-001 — Add root `CLAUDE.md` guardrails file
- **E2E flow to build**
  - Claude automation has guardrails available on default branch.
- **Manual verification**
  - Verify `CLAUDE.md` exists at repo root with required rules
- **Files**
  - `CLAUDE.md`
- **Tests to write AFTER**
  - N/A
- **Dependencies**
  - None
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-gh-001/manual.md`
  - Automated: N/A
  - Human sign-off: Lance

## abf-gh-002 — Backend GitHub client
- **E2E flow to build**
  - Backend can call GitHub REST API using token and repo config.
- **Manual verification**
  - Run a small dev-only call (or endpoint) to create a test issue in a sandbox repo
- **Files**
  - `apps/backend/...` (GitHub client module)
  - `apps/backend/main.py` (wiring)
- **Tests to write AFTER**
  - Unit test for request signing + response parsing (mocked)
- **Dependencies**
  - `abf-gh-001`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-gh-002/manual.md`
  - Automated: unit test run output
  - Human sign-off: Lance

## abf-gh-003 — Create GitHub issue on bug report submit
- **E2E flow to build**
  - Creating a bug report results in a private GitHub issue with required content blocks and trigger mechanism.
- **Manual verification**
  - Submit bug report
  - Confirm GitHub issue exists and includes notes + screenshot URLs + context + instruction block
- **Files**
  - `apps/backend/main.py`
  - `apps/backend/...` (issue formatter)
- **Tests to write AFTER**
  - API/integration test with mocked GitHub responses
- **Dependencies**
  - `abf-gh-002`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-gh-003/manual.md`
  - Automated: integration test output
  - Human sign-off: Lance

## abf-gh-004 — Persist issue URL to bug report
- **E2E flow to build**
  - Bug report record stores `github_issue_url` (and optional issue number/id) after creation.
- **Manual verification**
  - Submit bug report
  - Fetch bug report by ID
  - Verify `github_issue_url` present
- **Files**
  - `apps/backend/models.py`
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - API test: submit then verify stored URL
- **Dependencies**
  - `abf-gh-003`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-gh-004/manual.md`
  - Automated: api test output
  - Human sign-off: Lance

## abf-gh-005 — Retry/backoff + observability
- **E2E flow to build**
  - GitHub failures are retried with backoff; failures are visible and do not block bug capture.
- **Manual verification**
  - Temporarily set invalid token
  - Submit bug report
  - Verify bug capture still succeeds and status/error is visible for internal triage
- **Files**
  - `apps/backend/...` (retry/backoff wrapper)
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - Unit test: backoff on 429/5xx
- **Dependencies**
  - `abf-gh-003`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-gh-005/manual.md`
  - Automated: unit test run output
  - Human sign-off: Lance
