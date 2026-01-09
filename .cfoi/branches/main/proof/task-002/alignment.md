# Alignment Check - task-002

## North Star Goals Supported
- **Goal Statement**: "Ensure each authenticated user can only see and operate on their own chats/searches/rows."
- **Support**: This task enforces the core isolation logic: preventing cross-user access to `Row` data.

## Task Scope Validation
- **In scope**:
  - Add `user_id` to `Row` model.
  - Update `create_row` to assign ownership.
  - Update `read_rows`, `read_row`, `update_row`, `delete_row` to enforce ownership.
  - Return 404 for unauthorized access (avoid leakage).
- **Out of scope**:
  - Frontend updates (next task).
  - Migration of existing data (resetting DB instead).

## Acceptance Criteria
- [ ] `Row` table has `user_id`.
- [ ] `POST /rows` requires auth and sets `user_id`.
- [ ] `GET /rows` returns only user's rows.
- [ ] `GET /rows/{id}` returns 404 if row belongs to another user.
- [ ] `PATCH/DELETE` blocked for non-owners.

## Approved by: Cascade
## Date: 2026-01-09
