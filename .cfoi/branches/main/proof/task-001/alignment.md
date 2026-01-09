# Alignment Check - task-001

## North Star Goals Supported
- **Goal Statement**: "Ensure each authenticated user can only see and operate on their own chats/searches/rows."
- **Support**: This task binds the active session to a specific `User` (via `user_id`), which is the prerequisite for checking ownership on all downstream data.

## Task Scope Validation
- **In scope**: 
  - Schema update: `AuthSession` gets `user_id`.
  - Logic update: Login flow mints session with `user_id`.
- **Out of scope**: 
  - Enforcing ownership on `Row` (next task).
  - Frontend changes (later task).

## Acceptance Criteria
- [ ] `AuthSession` table has `user_id` column (Foreign Key).
- [ ] New logins populate `user_id` in `AuthSession`.
- [ ] Existing `User` lookup logic in `/auth/me` can use `AuthSession.user_id` directly (optimization) or at least remains compatible.

## Approved by: Cascade
## Date: 2026-01-09
