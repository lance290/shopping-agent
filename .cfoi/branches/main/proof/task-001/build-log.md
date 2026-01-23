# Build Log - task-001

## Changes Applied
- **Baseline test + environment fixes** to enable clean verification before implementation:
  - Added missing backend deps in `apps/backend/pyproject.toml` (pyjwt, pytest, pytest-asyncio, pytest-cov, python-multipart).
  - Fixed `apps/backend/tests/conftest.py` to use `ASGITransport` for `httpx.AsyncClient`.
  - Updated `apps/backend/tests/test_rows_authorization.py` to use unique session tokens and assert soft-delete behavior.
  - Fixed `tools/verify-implementation.sh` to avoid invalid `local` usage.

## Verification Instructions
**Prerequisite**: Backend + frontend running locally.

1. **Frontend**: `cd apps/frontend && npm run dev`
2. **Backend**: `cd apps/backend && uv run uvicorn main:app --reload --port 8000`
3. **Run baseline verification** (from repo root):
   - `CFOI_TEST_COMMAND="cd apps/backend && uv run pytest" CFOI_COVERAGE_COMMAND="cd apps/backend && uv run pytest --cov" ./tools/verify-implementation.sh`

## Alignment check
- Establishes a clean, verified baseline for the click-first walkthrough in task-001.
