# Alignment Check - task-005

## North Star Goals Supported
- **Goal Statement**: "Ensure each authenticated user can only see and operate on their own chats/searches/rows."
- **Support**: To reliably verify isolation (north star acceptance checkpoint), we need deterministic E2E tests. This task enables those tests by providing a way to mint test sessions without relying on email delivery infrastructure.

## Task Scope Validation
- **In scope**:
  - Add `POST /test/mint-session` endpoint.
  - Guard endpoint with `E2E_TEST_MODE=1` environment variable check.
  - Create user and session logic.
- **Out of Scope**:
  - Enabling this in production.

## Acceptance Criteria
- [ ] Endpoint exists at `/test/mint-session`.
- [ ] Returns 404/403 if `E2E_TEST_MODE` is not set.
- [ ] Returns session token if mode is enabled.
- [ ] Creates user if email doesn't exist.

## Approved by: Cascade
## Date: 2026-01-09
