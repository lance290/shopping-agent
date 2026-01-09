# Plan - feature-email-auth

<!-- PLAN_APPROVAL: approved by Lance at 2026-01-09T07:01:05Z -->

## Summary
Add passwordless email authentication using 6-digit verification codes sent via Resend. The app’s home route (`/`) becomes protected: unauthenticated users are redirected to `/login`. Users can log out and log back in at will.

## Requirements (Confirmed)
- **Login method**: Email + 6-digit verification code
- **Code lifecycle**:
  - New code invalidates old code for that email
  - **No time-based expiration**
  - **Attempt limit**: 5 failed attempts, then **45-minute cooldown**
- **Email provider**: Resend
  - Env: `RESEND_API_KEY` and `FROM_EMAIL="Agent Shopper <shopper@info.xcor-cto.com>"`
  - Simple email template
  - Any email domain allowed
- **Route protection**:
  - Only `/` is protected for now
  - If logged out: redirect to `/login`
  - If logged in and visit `/login`: redirect to `/`

## Current Architecture (Observed)
- **Frontend**: Next.js App Router (`apps/frontend/app`), home is a client component (`app/page.tsx`)
- **BFF**: Fastify (`apps/bff/src/index.ts`) proxying `/api/*` to backend
- **Backend**: FastAPI + SQLModel (`apps/backend/main.py`, `models.py`) with Postgres in dev (`docker-compose.dev.yml`)
- No existing auth/session implementation.

## Proposed Approach (MVP + Best Practices)
Implement auth state as a **server-validated session token stored in an HTTP-only cookie**, with verification-code issuance and state tracked in the **backend database**.

### Why this approach
- Avoids “in-memory OTP” issues in multi-instance deployments
- Keeps secrets and email sending on the server side
- Keeps frontend simple (cookie + redirects)

## Data Model (Backend)
Add SQLModel tables to `apps/backend/models.py`:
- **AuthLoginCode**
  - `id`
  - `email` (indexed)
  - `code_hash` (hash of 6-digit code)
  - `is_active` (only one active per email)
  - `attempt_count` (int)
  - `locked_until` (datetime | null) — for 45-min cooldown
  - `created_at`
- **AuthSession**
  - `id`
  - `email` (indexed)
  - `session_token_hash` (hash of opaque token)
  - `created_at`
  - `revoked_at` (datetime | null)

Notes:
- Since codes have no time-based expiration, the key security controls are:
  - newest invalidates old
  - attempt limit + cooldown
  - opaque session tokens stored hashed

## Backend API (FastAPI)
Add endpoints in `apps/backend/main.py`:
- `POST /auth/start`
  - Body: `{ "email": string }`
  - Behavior:
    - If `locked_until > now`: return `429` with `locked_until`
    - Invalidate any previous active code(s) for email
    - Generate new 6-digit code
    - Store hash + reset attempts
    - Send via Resend
  - Response: `{ "status": "sent" }` (and optionally `locked_until` when locked)

- `POST /auth/verify`
  - Body: `{ "email": string, "code": string }`
  - Behavior:
    - If locked: `429`
    - If code mismatch: increment attempts; if attempts reach 5 set `locked_until = now + 45m`, deactivate code
    - If match: deactivate code, create session token, store token hash
  - Response: `{ "status": "ok", "sessionToken": string }`

- `POST /auth/logout`
  - Header: `Authorization: Bearer <sessionToken>`
  - Behavior: mark session revoked
  - Response: `{ "status": "ok" }`

- `GET /auth/me`
  - Header: `Authorization: Bearer <sessionToken>`
  - Response: `{ "authenticated": true, "email": string }` or `401`

## Resend Integration
Implement in backend using existing `httpx` dependency:
- Call Resend REST API `POST https://api.resend.com/emails`
- Use:
  - `RESEND_API_KEY`
  - `FROM_EMAIL`
- Email content (simple):
  - Subject: `Your verification code`
  - Body: `Your verification code is: 123456`

## BFF (Fastify) Routing
Add proxy routes in `apps/bff/src/index.ts`:
- `POST /api/auth/start` → backend `POST /auth/start`
- `POST /api/auth/verify` → backend `POST /auth/verify`
- `POST /api/auth/logout` → backend `POST /auth/logout` (forward `Authorization`)
- `GET /api/auth/me` → backend `GET /auth/me` (forward `Authorization`)

## Frontend (Next.js) UX + Route Protection
### Pages
- Add `app/login/page.tsx`:
  - Step 1: email input + “Send code”
  - Step 2: code input + “Verify”
  - Show cooldown message when `429` with `locked_until`

### Session cookie
- Use Next route handlers to set/clear cookie (avoids exposing token to client JS):
  - `POST /api/auth/start` → calls BFF `POST /api/auth/start`
  - `POST /api/auth/verify` → calls BFF `POST /api/auth/verify`, sets `sa_session` HTTP-only cookie
  - `POST /api/auth/logout` → calls BFF `POST /api/auth/logout`, clears cookie
  - `GET /api/auth/me` → calls BFF `GET /api/auth/me` using cookie-derived token

Cookie settings:
- `httpOnly: true`
- `secure: true` in production
- `sameSite: 'lax'`
- `path: '/'`

### Route guarding
Because `app/page.tsx` is a client component today, implement protection via **Next Middleware**:
- Add `apps/frontend/middleware.ts`
- For `/`:
  - If `sa_session` missing: redirect to `/login`
- For `/login`:
  - If `sa_session` present: redirect to `/`

(Optionally) “defense in depth”:
- Home page can also call `/api/auth/me` on mount; if `401`, redirect to `/login`.

## Verification Plan (aligned to DoD)
### Thresholds
- **auth_home_protected**:
  - Visiting `/` without session redirects to `/login`
- **auth_email_code_login_success**:
  - `POST /api/auth/start` succeeds, `POST /api/auth/verify` sets cookie, user lands on `/`
- **auth_logout_relogin**:
  - Logout clears cookie, `/` redirects to `/login`, then login works again

### Signals
- **e2e_auth_login_logout**:
  - Add Playwright test for send-code → verify → logout
- **unit_auth_backend_verification**:
  - Add backend unit tests for:
    - invalidation of old codes
    - attempt count increment
    - lockout after 5
    - unlock behavior after 45 minutes
    - session creation and revocation

## Testing & Tooling Notes
- `apps/frontend/playwright.config.ts` is currently hardcoded to the production URL.
  - Update plan includes making `baseURL` configurable via env (e.g. `PLAYWRIGHT_BASE_URL`) so local/CI can run deterministically.

## Risks / Non-goals
- **No time-based OTP expiration** increases abuse risk.
  - Mitigations included: attempt limit + cooldown + invalidate old codes
- Backend and BFF APIs remain unauthenticated for data endpoints (rows/search/chat).
  - This plan focuses on “home page gated” MVP; expanding API protection can be a follow-on effort.

## Assumptions
- Postgres is available in dev via `docker-compose.dev.yml` and in deployment via existing backend configuration.
- Adding SQLModel models is acceptable (tables are created on startup via `init_db()`).
- No dedicated user table is required for MVP; email string is the user identity.

## Milestones
1. **Backend auth primitives**
   - Add models for login codes + sessions
   - Implement `/auth/start`, `/auth/verify`, `/auth/me`, `/auth/logout`
   - Implement Resend email sending

2. **BFF proxy endpoints**
   - Add `/api/auth/*` proxy routes

3. **Frontend auth UX**
   - Add `/login` page
   - Add Next API route handlers for auth
   - Add middleware protection for `/` and `/login`

4. **Tests**
   - Backend unit tests for auth logic
   - Playwright E2E for login/logout

## Manual QA Checklist
- Open `/` in an incognito window → redirected to `/login`
- Request code, verify code → lands on `/`
- Enter wrong code 5 times → locked for 45 minutes
- Logout → redirected to `/login`
- Login again → lands on `/`
