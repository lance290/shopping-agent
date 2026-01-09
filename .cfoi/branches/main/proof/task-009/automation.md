# Task-009 Automation Evidence

## Test Command
```bash
cd apps/frontend && npx playwright test e2e/auth-login-logout.spec.ts --reporter=list
```

## Test Results
- **Date**: 2026-01-09T07:45:00Z
- **Status**: ✅ PASSED
- **Tests**: 5/5 passed
- **Duration**: 7.2s

## Test Output
```
Running 5 tests using 1 worker

✓ 1 [chromium] › e2e/auth-login-logout.spec.ts:9:7 › Auth: Login and Logout › unauthenticated user is redirected from / to /login
✓ 2 [chromium] › e2e/auth-login-logout.spec.ts:14:7 › Auth: Login and Logout › login page shows email input initially
✓ 3 [chromium] › e2e/auth-login-logout.spec.ts:20:7 › Auth: Login and Logout › can enter email and request verification code
✓ 4 [chromium] › e2e/auth-login-logout.spec.ts:31:7 › Auth: Login and Logout › authenticated user is redirected from /login to /
✓ 5 [chromium] › e2e/auth-login-logout.spec.ts:47:7 › Auth: Login and Logout › logout clears session and redirects to login

5 passed (7.2s)
```

## Environment
- Backend: http://localhost:8000
- BFF: http://localhost:8080
- Frontend: http://localhost:3000
- Database: PostgreSQL via docker-compose.dev.yml
