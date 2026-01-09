# Alignment Check - task-007

## North Star Goals Supported
- **Goal Statement**: "Ensure each authenticated user can only see and operate on their own chats/searches/rows."
- **Support**: This operational task ensures the database schema is clean and consistent with the new code (avoiding "it works on my machine" due to migration drift), and provides the final verification that the entire system (backend + frontend + BFF) meets the isolation requirements.

## Task Scope Validation
- **In scope**:
  - Resetting local database (wiping old non-isolated data).
  - Running full E2E suite on clean DB.
- **Out of Scope**:
  - Production deployment (separate workflow).

## Acceptance Criteria
- [ ] Database reset successfully.
- [ ] All tests (backend + frontend) pass on clean DB.
- [ ] Manual smoke test confirms login and row creation work.

## Approved by: Cascade
## Date: 2026-01-09
