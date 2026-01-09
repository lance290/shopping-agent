# Build Log - task-002

## Changes Applied
- **Schema**: Added `user_id` to `Row` model in `apps/backend/models.py`.
- **Endpoints**: Updated `apps/backend/main.py`:
  - `POST /rows`: Now requires auth, sets `user_id` from session.
  - `GET /rows`: Requires auth, filters by `user_id`.
  - `GET /rows/{id}`, `PATCH`, `DELETE`: Requires auth + ownership check (returns 404 if not owned).
- **Tests**: Created `apps/backend/tests/test_rows_authorization.py` verifying cross-user isolation.

## Verification Instructions
**Prerequisite**: DB Reset required (schema change).

1. **Reset DB**: `docker compose -f docker-compose.dev.yml down -v && docker compose -f docker-compose.dev.yml up -d postgres`
2. **Run Tests**: `cd apps/backend && pytest tests/test_rows_authorization.py`
3. **Manual Check**:
   - Login as User A.
   - Create Row.
   - Login as User B.
   - Verify `GET /rows` returns empty list.
   - Verify `GET /rows/{id_of_A}` returns 404.

## Alignment Check
- Directly implements the North Star goal of "Authenticated users can only read and modify their own chats/searches/rows".
