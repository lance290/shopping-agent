# PRD-03a: Critical Security Fixes (Phase 1)

**Status:** Ready for Implementation
**Priority:** P0 — CRITICAL
**Effort:** ~2 hours total
**Base Branch:** dev

---

## Overview

Three critical security vulnerabilities identified in the Shopping Agent code review. Each is a focused, well-scoped fix that can be implemented and verified independently.

All changes target the `apps/backend/` directory. Frontend changes are minimal (CSP nonce propagation only).

---

## Issue 1: Implement Nonce-Based Content Security Policy

**Current State:** CSP header allows `unsafe-inline` and `unsafe-eval`, enabling XSS attacks. CVSS 7.5 (HIGH).

**Required Changes:**

1. Create or update `apps/backend/security/headers.py`:
   - Add `generate_csp_nonce()` using `secrets.token_urlsafe(16)`
   - Update `SecurityHeadersMiddleware` to generate a per-request nonce
   - Set CSP header with `'nonce-{nonce}'` instead of `'unsafe-inline'` and `'unsafe-eval'`
   - Expose nonce via `request.state.csp_nonce` and `X-CSP-Nonce` response header

2. Update frontend to use nonce for any inline scripts:
   - Read nonce from response header or meta tag
   - Add `nonce` attribute to any `<script>` tags

**Acceptance Criteria:**
- CSP header contains NO `unsafe-inline` or `unsafe-eval`
- All inline scripts use nonce attribute
- CSP nonce regenerates per request (never reused)
- Frontend renders without CSP violations in browser console
- Existing functionality (auth, search, chat) works with new CSP

**Test Verification:**
```bash
curl -I http://localhost:8000/health | grep -i content-security-policy
# Must NOT contain unsafe-inline or unsafe-eval
# Must contain nonce-
```

---

## Issue 2: Enable CSRF Protection in All Environments

> **Depends on**: Implement Nonce-Based Content Security Policy

**Current State:** CSRF middleware is disabled in dev and staging environments. Only production has CSRF enabled. CVSS 7.3 (HIGH).

**Required Changes:**

1. In `apps/backend/main.py`:
   - Change CSRF conditional from `if CSRF_SECRET and IS_PRODUCTION` to `if CSRF_SECRET`
   - Add startup warning log if `CSRF_SECRET_KEY` is not set
   - Add startup error/raise if production and `CSRF_SECRET_KEY` is missing

2. Ensure `.env.example` documents `CSRF_SECRET_KEY` with generation instructions:
   - `openssl rand -hex 32`

3. In frontend `apps/frontend/app/utils/api.ts` (if not already present):
   - Ensure all state-changing requests (POST, PUT, PATCH, DELETE) include `X-CSRF-Token` header
   - Read CSRF token from cookie `csrf_token`

**Acceptance Criteria:**
- CSRF middleware enabled in dev, staging, AND production
- POST without CSRF token returns 403 Forbidden
- POST with valid CSRF token succeeds
- `CSRF_SECRET_KEY` documented in `.env.example`
- All frontend mutating requests include CSRF header

**Test Verification:**
```bash
# Should fail with 403 (no CSRF token)
curl -X POST http://localhost:8000/auth/start \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# Should succeed with valid token
curl -X POST http://localhost:8000/auth/start \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <token>" \
  -H "Cookie: csrf_token=<token>" \
  -d '{"email":"test@example.com"}'
```

---

## Issue 3: Fix Session Cookie Security Configuration

**Current State:** Session cookies are missing `samesite="strict"` in production. CVSS 6.8 (MEDIUM).

**Required Changes:**

1. In `apps/backend/routes/auth.py`, find `response.set_cookie` for `sa_session`:
   - Set `samesite="strict"` in ALL environments
   - Set `secure=True` only in production (detect via `RAILWAY_ENVIRONMENT` or `ENVIRONMENT=production`)
   - Confirm `httponly=True` is already set
   - Set `path="/"`

2. Search for any other `set_cookie` calls in the backend and apply the same policy.

**Acceptance Criteria:**
- Session cookie has `SameSite=Strict` in all environments
- Session cookie has `Secure=True` in production only
- Session cookie has `HttpOnly=True` (already set, verify)
- No other cookies are missing security attributes

**Test Verification:**
```bash
# After login, inspect Set-Cookie header
curl -i -X POST http://localhost:8000/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"verification_id":"...", "code":"123456"}' \
  | grep -i set-cookie
# Must contain: SameSite=Strict; HttpOnly
```

---

## Issue 4: Add Security Regression Tests for P0 Fixes

> **Depends on**: Implement Nonce-Based Content Security Policy
> **Depends on**: Enable CSRF Protection in All Environments
> **Depends on**: Fix Session Cookie Security Configuration

**Current State:** No dedicated security tests exist. The 3 fixes above need regression tests to prevent re-introduction.

**Required Changes:**

1. Create `apps/backend/tests/test_security_headers.py`:
   - Test CSP header present and contains `nonce-`
   - Test CSP header does NOT contain `unsafe-inline` or `unsafe-eval`
   - Test nonce changes between requests

2. Create `apps/backend/tests/test_security_csrf.py`:
   - Test POST without CSRF token → 403
   - Test POST with invalid CSRF token → 403
   - Test POST with valid CSRF token → success
   - Test GET requests work without CSRF token

3. Create `apps/backend/tests/test_security_cookies.py`:
   - Test session cookie has `httponly` flag
   - Test session cookie has `samesite=strict`
   - Test session cookie has `secure` flag in production mode

**Acceptance Criteria:**
- 10+ security tests added
- All tests passing
- Tests run as part of `pytest` suite
- Tests cover CSP, CSRF, and cookie security

---

## Implementation Notes

- **Stack:** Python/FastAPI backend, Next.js 15 frontend
- **Package Manager:** Backend uses `uv`, frontend uses `pnpm`
- **Test Framework:** `pytest` (backend), `vitest` (frontend)
- **Base Branch:** `dev`
- **All changes should be minimal and focused — do not refactor unrelated code**
