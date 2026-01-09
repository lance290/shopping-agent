# Build Log - task-001

## Changes Applied
- **Schema**: Added `user_id` foreign key to `AuthSession` in `apps/backend/models.py`.
- **Logic**: Updated `auth_verify` in `apps/backend/main.py` to:
  - Commit/refresh `User` creation to ensure an ID exists.
  - Populate `user_id` when creating `AuthSession`.
- **Tests**: Added `apps/backend/tests/test_auth_session_user_id.py` to verify the link.

## Verification Instructions
**Prerequisite**: Database must be running (Docker).

1. **Start Backend**: `docker compose up -d` (or `uvicorn main:app --reload` with local DB).
2. **Login Flow**:
   - `POST /auth/start` with email.
   - `POST /auth/verify` with code.
   - Inspect DB `auth_session` table to confirm `user_id` column is populated.
3. **Automated Test**:
   - Run `pytest apps/backend/tests/test_auth_session_user_id.py`

## Alignment check
- Moves us closer to North Star by establishing the `User` <-> `Session` link required for isolation.
