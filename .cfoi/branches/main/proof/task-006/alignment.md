# Alignment Check - task-006

## North Star Goals Supported
- **Goal Statement**: "Ensure each authenticated user can only see and operate on their own chats/searches/rows."
- **Support**: This is the authoritative E2E test that proves the system meets the "user_data_isolated" threshold defined in the DoD.

## Task Scope Validation
- **In scope**:
  - Create `apps/frontend/e2e/user-data-isolation.spec.ts`.
  - Use `request` context to interact with Backend/BFF APIs directly (API-level E2E).
  - Verify isolation logic (A cannot see B).
- **Out of Scope**:
  - UI-based testing (clicking buttons) - API test is sufficient and faster for auth logic verification.

## Acceptance Criteria
- [ ] Test passes deterministically.
- [ ] Confirms User A can see their own row.
- [ ] Confirms User B sees empty list.
- [ ] Confirms User B cannot GET/PATCH/DELETE User A's row.

## Approved by: Cascade
## Date: 2026-01-09
