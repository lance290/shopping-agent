# Codebase Audit - February 17, 2026

## Scope
- Repository: `shopping-agent`
- Audited areas: backend, frontend, tests, static checks, CI workflow

## Findings (Prioritized)

### High
1. Session expiry is not enforced during auth checks.
   - `apps/backend/dependencies.py:35`
   - `apps/backend/models/auth.py:72`
   - Cleanup exists but is not wired into app runtime (`apps/backend/security/session_cleanup.py`).

2. Production DB SSL verification is disabled.
   - `apps/backend/database.py:28`
   - `apps/backend/database.py:29`

### Medium
3. Global exception audit logging path likely fails due session handling pattern.
   - `apps/backend/main.py:238`
   - `apps/backend/database.py:116`

4. Frontend type-check is failing and CI does not enforce lint/type failures.
   - Type errors in:
     - `apps/frontend/tests/vendor-tiles-persistence.test.ts:29`
     - `apps/frontend/tests/vendor-tile-display.test.ts:98`
   - CI behavior:
     - `.github/workflows/ci.yml:183`
     - `.github/workflows/ci.yml:193`

5. Auth start route imports rate limiting but does not apply it.
   - `apps/backend/routes/auth.py:301`
   - `apps/backend/routes/auth.py:304`
   - Limiter definition:
     - `apps/backend/routes/rate_limit.py:12`

6. SMS fallback path can report success when provider credentials/SDK are absent.
   - `apps/backend/routes/auth.py:119`
   - `apps/backend/routes/auth.py:123`

### Low
7. Duplicated auth proxy paths with inconsistent cookie/session behavior.
   - `apps/frontend/app/api/auth/verify/route.ts:22`
   - `apps/frontend/app/api/proxy/[...path]/route.ts:59`
   - `apps/frontend/middleware.ts:9`

8. Backend static-analysis debt is high.
   - `uv run ruff check . --statistics`:
     - 914 total issues
     - 466 `E501`, 210 `I001`, 154 `F401`, others

## Validation Results
- Backend tests: `398 passed, 1 xfailed` (`uv run pytest -q`)
- Frontend unit tests: `245 passed, 2 skipped` (`pnpm test`)
- Frontend type-check: failed (`pnpm type-check`)
- Frontend lint: passes with warnings (`pnpm lint`)

## Notes
- Workspace local change existed before/after audit:
  - `docker-compose.dev.yml`
