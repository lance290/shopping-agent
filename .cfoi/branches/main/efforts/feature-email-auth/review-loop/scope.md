# Review Scope - feature-email-auth

## Files to Review (Added/Modified for this effort)

### Backend
- `apps/backend/models.py` (modified) - Added auth models + hashing helpers
- `apps/backend/main.py` (modified) - Added Resend sender + auth endpoints

### BFF
- `apps/bff/src/index.ts` (modified) - Added auth proxy routes

### Frontend
- `apps/frontend/app/api/auth/start/route.ts` (added)
- `apps/frontend/app/api/auth/verify/route.ts` (added)
- `apps/frontend/app/api/auth/me/route.ts` (added)
- `apps/frontend/app/api/auth/logout/route.ts` (added)
- `apps/frontend/app/login/page.tsx` (added)
- `apps/frontend/middleware.ts` (added)
- `apps/frontend/playwright.config.ts` (modified)
- `apps/frontend/e2e/auth-login-logout.spec.ts` (added)

## Out of Scope (unchanged or unrelated to auth effort)
- `apps/backend/sourcing.py` - unrelated modification
- `apps/frontend/app/components/Board.tsx` - unrelated modification
- `apps/frontend/app/tests/chat-board-sync.test.ts` - different effort
- `apps/frontend/e2e/chat-board-sync.spec.ts` - different effort

## Review Started: 2026-01-08T23:21:00Z
