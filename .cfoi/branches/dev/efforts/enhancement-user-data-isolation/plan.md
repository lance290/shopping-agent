<!-- PLAN_APPROVAL: approved by Lance at 2026-01-09T17:35:00Z -->

# Plan — enhancement-user-data-isolation

## Summary
Scope all persisted procurement requests (currently `Row`) to the authenticated user, enforcing **read + write isolation** server-side.

Key decisions from CLARIFY:
- **Isolation target (now):** `Row` only
- **Auth session design:** add `user_id` to `AuthSession` (not email lookup on each request)
- **Existing data:** acceptable to wipe/reset (no migration required for MVP)
- **Exceptions (sharing/admin):** deferred; design should not block future account-based system

## North Star Alignment
- **Goal:** Each authenticated user can only see and operate on their own rows.
- **Acceptance checkpoints:**
  - User cannot read another user’s rows (even by guessing IDs)
  - User cannot modify/delete another user’s rows

## Current State (Code Reality)
- Backend `Row` endpoints (`/rows`, `/rows/{id}`) are currently **unauthenticated** and return all rows.
- BFF `/api/rows` proxies do **not** forward `Authorization`.
- Frontend `/api/rows` route does **not** attach the `sa_session` token.
- BFF chat tooling (`apps/bff/src/llm.ts`) calls backend `/rows` directly, also **without auth**.
- Auth system exists and uses `AuthSession` with `email` and hashed `session_token`.

## Proposed Implementation

### A) Backend: Model & Auth Foundations
1. **Schema changes (SQLModel)**
   - Add `user_id` to `AuthSession`:
     - `user_id: int = Field(foreign_key="user.id", index=True)`
   - Add `user_id` to `Row`:
     - `user_id: int = Field(foreign_key="user.id", index=True)`
   - Keep `User` as the canonical identity for now; be mindful that table name `user` can be awkward long-term.

2. **Session creation**
   - In `/auth/verify`:
     - Ensure `User` exists (already implemented)
     - Create `AuthSession` with **`user_id`** set

3. **Auth helpers**
   - Add `get_current_user_or_401(...)` helper:
     - Reads `Authorization: Bearer <token>`
     - Validates `AuthSession`
     - Loads `User` by `AuthSession.user_id`
     - Returns `User` (or raises `401`)

### B) Backend: Enforce Row Ownership
1. **Require auth for all Row endpoints**
   - `POST /rows` -> requires user, sets `Row.user_id = current_user.id`
   - `GET /rows` -> returns only `Row` where `Row.user_id == current_user.id`
   - `GET /rows/{row_id}` -> fetch row filtered by `user_id`; return `404` if not found (avoid leaking existence)
   - `PATCH /rows/{row_id}` -> update only if owned; else `404`
   - `DELETE /rows/{row_id}` -> delete only if owned; else `404`

2. **Deletion behavior**
   - Deleting a row should still remove dependent `RequestSpec` and `Bid` records as today.

3. **API response strategy**
   - Prefer `404` for “not found or not owned” on row-specific endpoints to avoid data leakage.

### C) BFF: Forward Authorization for Row + Chat
1. **Row proxy** (`/api/rows`, `/api/rows/:id`)
   - Forward `Authorization` header from incoming request to backend.
   - If missing, return `401`.

2. **Chat endpoint** (`/api/chat`) + LLM tools
   - Accept `Authorization` header from frontend.
   - Pass the token into `chatHandler(messages, authorization)`.
   - In `apps/bff/src/llm.ts`, update tool calls that create rows to include the same `Authorization` header.
     - This avoids bypassing isolation.

### D) Frontend (Next): Attach Session Token Server-Side
1. **`/api/rows` route**
   - Read `sa_session` cookie (HTTP-only) server-side and attach:
     - `Authorization: Bearer <token>`
   - Forward to BFF.

2. **`/api/chat` route**
   - Same: attach `Authorization` from `sa_session` cookie to BFF `/api/chat`.

3. **No UX change**
   - The app already assumes an authenticated user for the home route; this work ensures the backend enforces it too.

### E) Data Reset (per decision C)
Since schema changes are additive and we don’t have migrations set up:
- **Local dev:** drop/recreate DB (or remove docker volume) before validating.
- **Railway:** reset the Postgres database (acceptable data loss for MVP).

## Test Plan (Measured)

### Threshold: `user_data_isolated`
- **Manual verification (local):**
  - Create user A session, create rows, confirm user B cannot list or read A’s rows.

### Signal: `e2e_user_data_isolation`
Add a Playwright spec that:
1. Creates two authenticated sessions (A and B)
2. Uses A token to create row, confirm row appears in A list
3. Uses B token to list rows, confirm A row absent
4. Attempts `GET/PATCH/DELETE` on A’s row using B token, confirm `404`

**Open question to implement in code (but included in plan):** to make this deterministic without email delivery, add a **test-only** backend endpoint (guarded) that mints a session:
- Enabled only when `E2E_TEST_MODE=1` (and explicitly disabled on Railway/prod)
- Returns a session token for a given email, also creating `User`

This avoids coupling E2E to Resend/email.

## Risks / Watchouts
- **Breaking change risk:** once `/rows` require auth, un-authenticated callers will fail. We must update:
  - Frontend `/api/rows`
  - BFF `/api/rows`
  - BFF chat tool `createRow`
- **Table name `user`:** acceptable now, but may be renamed later when building a full account system.
- **Race conditions:** session/user creation should remain safe; unique email on `User` can raise integrity errors under concurrency.

## Assumptions
- `Row` is the only persisted user-owned entity in MVP.
- Sharing/admin/teams are deferred; design should not block adding these later.
- Data reset is acceptable to ship isolation quickly.

## Deliverables
- Authenticated, user-scoped backend row endpoints
- Authorization propagated through Next API routes + BFF proxies
- Chat tool row creation respects user ownership
- E2E proof (Playwright) that cross-user access is prevented
