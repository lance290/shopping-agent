# PRD: Codebase Hardening

**Author:** Codebase Audit (2026-02-05)
**Priority:** P0–P2 by section
**Scope:** Backend, BFF, Frontend, Infrastructure

---

## Executive Summary

A full-stack audit of the Shopping Agent codebase identified **4 critical**, **6 high**, and **8 medium** findings across security, reliability, architecture, and operational hygiene. The critical findings involve open SSRF vectors, production SSL bypass, unprotected webhook endpoints, and duplicated auth logic. Most issues are fixable with surgical edits (1–20 lines each).

---

## Severity Legend

| Tag | Meaning | SLA |
|-----|---------|-----|
| 🔴 P0 | Exploitable in production, data loss risk, or security breach | Fix immediately |
| 🟠 P1 | Reliability risk, tech debt that compounds, or architectural flaw | Fix this sprint |
| 🟡 P2 | Code quality, maintainability, or minor operational risk | Fix next sprint |

---

## 🔴 P0 — Critical (Fix Immediately)

### P0-1: Open SSRF via Frontend Catch-All Proxy

**File:** `apps/frontend/app/api/proxy/[...path]/route.ts`
**Lines:** 7–9, 64–66

The catch-all proxy route forwards *any* path to `NEXT_PUBLIC_BACKEND_URL` without validation. An attacker can craft requests like `/api/proxy/../../internal-service/admin` or inject arbitrary hosts if the env var is manipulated. The backend URL is also sourced from a `NEXT_PUBLIC_` variable, meaning it's exposed to the browser bundle.

**Fix:**
- Allowlist valid proxy paths (e.g., `auth/start`, `auth/verify`, `auth/me`, `auth/logout`).
- Rename `NEXT_PUBLIC_BACKEND_URL` to a server-only env var (drop the `NEXT_PUBLIC_` prefix).
- Validate that the resolved path stays within the expected backend domain.

**Impact:** SSRF, potential internal network scanning, credential theft via auth header forwarding to arbitrary hosts.

---

### P0-2: Production SSL Verification Disabled

**File:** `apps/backend/database.py` lines 23–28
**Also:** `apps/backend/scripts/migrate_triage_columns.py` lines 18–23, `apps/backend/scripts/verify_triage_models.py` lines 20–25

```python
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

This completely disables TLS certificate validation for the production database connection. Any MITM can intercept database traffic, including credentials and query data.

**Fix:**
- Use Railway's internal networking (private URLs don't need SSL).
- OR use `ssl.CERT_REQUIRED` with Railway's CA certificate.
- At minimum, set `ssl_context.check_hostname = True` and `ssl_context.verify_mode = ssl.CERT_REQUIRED`.

**Impact:** Database credentials and data exposed to MITM attacks in production.

---

### P0-3: Webhook Signature Verification Bypassed in Production

**File:** `apps/backend/routes/webhooks.py` lines 44–46

```python
if WEBHOOK_SECRET != "dev-webhook-secret":
    if not verify_webhook_signature(payload_bytes, x_hub_signature_256 or ""):
```

If `WEBHOOK_SECRET` env var is not set, it defaults to `"dev-webhook-secret"`, which **skips signature verification entirely**. An attacker can forge GitHub webhook payloads to manipulate bug report statuses.

**Fix:**
- Require `WEBHOOK_SECRET` to be set in production (fail startup if missing when `RAILWAY_ENVIRONMENT` is set).
- Always verify signatures; only skip in explicit test mode (`E2E_TEST_MODE`).

**Impact:** Arbitrary bug status manipulation, potential denial of service via crafted payloads.

---

### P0-4: Triplicated `require_admin` / `get_current_session` Definitions

**Files:**
- `apps/backend/dependencies.py` lines 16–81 (canonical)
- `apps/backend/routes/bugs.py` lines 213–235 (duplicate)
- `apps/backend/routes/admin.py` lines 28–50 (duplicate)
- `apps/backend/routes/auth.py` lines 232–249 (duplicate `get_current_session`)

Three separate `require_admin` implementations and two `get_current_session` implementations exist. If one is patched for a security fix (e.g., session expiry), the others remain vulnerable.

**Fix:**
- Delete duplicates from `routes/bugs.py`, `routes/admin.py`, and `routes/auth.py`.
- Import exclusively from `dependencies.py`.
- All routes already import from `database`, so the dependency path is clean.

**Impact:** Security patches applied inconsistently; one unpatched copy = bypass.

---

## 🟠 P1 — High (Fix This Sprint)

### P1-1: Backend CORS Allows Only localhost

**File:** `apps/backend/main.py` lines 50–59

```python
allow_origins=[
    "http://localhost:3003",
    "http://127.0.0.1:3003",
],
```

Production frontend URLs (`https://frontend-dev-aca4.up.railway.app`) are not included. This means either:
- CORS is silently broken in production (requests fail), or
- Something else is handling CORS (BFF proxy), hiding the misconfiguration.

**Fix:**
- Read allowed origins from env var `CORS_ALLOWED_ORIGINS`.
- Default to localhost for dev; require explicit production origins for Railway.

---

### P1-2: BFF CORS Set to Wildcard `*`

**File:** `apps/bff/src/index.ts` line 333

```typescript
origin: process.env.CORS_ORIGIN || '*',
```

The BFF defaults to accepting requests from any origin, including malicious sites. Combined with auth header forwarding, this enables cross-origin credential theft.

**Fix:**
- Set `CORS_ORIGIN` explicitly in all environments.
- Never default to `*` when auth headers are forwarded.

---

### P1-3: Session Cookie Not HttpOnly

**File:** `apps/frontend/app/api/proxy/[...path]/route.ts` lines 34–39

```typescript
response.cookies.set('sa_session', data.session_token, {
    httpOnly: false, // Accessible to JS
```

The session token is stored in a non-HttpOnly cookie AND localStorage. Any XSS vulnerability (including from third-party scripts like Skimlinks loaded in `layout.tsx`) can steal session tokens.

**Fix:**
- Set `httpOnly: true` on the cookie.
- Remove localStorage token storage; read from cookie on server side only.
- Add `secure: true` for production.

---

### P1-4: In-Memory Rate Limiting (Not Distributed)

**Files:**
- `apps/backend/routes/rate_limit.py` (in-memory dict)
- `apps/backend/notifications.py` lines 42–58 (separate in-memory list)

Rate limits use process-local dictionaries. With `--workers 4` in production (`start.sh` line 30), each worker has its own rate limit state. An attacker gets `4 × limit` requests. The notification rate limiter is a separate module-level list that also resets on deploy.

**Fix:**
- Use Redis or PostgreSQL advisory locks for shared rate limiting.
- Short-term: document the 4x multiplier as acceptable for current scale.

---

### P1-5: `reset_prod_db.py` Can Drop Production Database

**File:** `apps/backend/reset_prod_db.py`

This script imports the production `engine` (which reads `DATABASE_URL`) and calls `drop_all`. There's no environment guard. Running this accidentally in production destroys all data.

**Fix:**
- Add an environment guard: refuse to run if `RAILWAY_ENVIRONMENT` or `ENVIRONMENT=production` is set.
- Require an explicit `--yes-i-really-mean-it` flag.
- Better: delete this file entirely and use Alembic's `downgrade base` if needed.

---

### P1-6: Bare `except:` Swallowing Errors Silently

**Files (sampled):**
- `apps/backend/routes/bugs.py` lines 133, 164
- `apps/backend/routes/rows.py` lines 197, 391
- `apps/backend/main.py` line 206

Bare `except:` or `except Exception:` blocks silently swallow errors without logging, making debugging impossible.

**Fix:**
- Replace bare `except:` with `except Exception as e:` and log `e`.
- Use structured logging (see P2-4).

---

## 🟡 P2 — Medium (Fix Next Sprint)

### P2-1: CI Pipeline References Root `npm ci` But Repo Uses pnpm Monorepo

**File:** `.github/workflows/ci.yml`

The CI workflow runs `npm ci` at the repo root, but the actual apps use pnpm with per-app lockfiles. The CI likely never actually runs tests or builds correctly. Services like Redis and MongoDB are provisioned but not used by the actual stack.

**Fix:**
- Rewrite CI to use `pnpm` and run per-app test/build commands.
- Remove unused Redis and MongoDB service containers.
- Add backend Python test step (`uv run pytest`).

---

### P2-2: `database.py` Logs Credential Prefix

**File:** `apps/backend/database.py` line 19

```python
print(f"DEBUG: DATABASE_URL starts with: {DATABASE_URL[:15]}...")
```

While truncated, this still logs `postgresql+asy` which confirms the driver. More importantly, debug print statements should not exist in production code.

**Fix:**
- Remove the debug print or gate it behind `ENVIRONMENT != "production"`.

---

### P2-3: Startup Inline Migration Alongside Alembic

**File:** `apps/backend/main.py` lines 230–237

```python
await conn.execute(text("""
    ALTER TABLE row ADD COLUMN IF NOT EXISTS chat_history TEXT;
"""))
```

The app runs ad-hoc `ALTER TABLE` in the startup event *and* uses Alembic migrations in `start.sh`. This creates schema drift risk where Alembic's version history doesn't know about inline migrations.

**Fix:**
- Move all schema changes into Alembic migrations.
- Remove inline `ALTER TABLE` from startup.
- Delete `scripts/migrate_triage_columns.py` (use Alembic instead).

---

### P2-4: No Structured Logging

The entire backend uses `print()` statements for logging. There's no log level control, no structured output (JSON), and no correlation IDs. In production with 4 workers, logs are interleaved and unsearchable.

**Fix:**
- Adopt Python `logging` module with JSON formatter.
- Add request correlation IDs via FastAPI middleware.
- Replace `print()` calls with `logger.info()` / `logger.warning()` / `logger.error()`.

---

### P2-5: `sourcing.py` Monolith (779 Lines) vs `sourcing/` Package

**Files:**
- `apps/backend/sourcing.py` (779 lines, monolith)
- `apps/backend/sourcing/` (package with repository.py at 45K lines)

Two parallel sourcing implementations exist. The root `sourcing.py` defines `SearchResult`, `SourcingRepository`, etc., while `sourcing/` is a refactored package. Imports are split between both.

**Fix:**
- Complete the migration to `sourcing/` package.
- Delete or reduce `sourcing.py` to a thin re-export shim.

---

### P2-6: Test Suite Drops/Recreates All Tables Per Test

**File:** `apps/backend/tests/conftest.py` lines 32–34

```python
await conn.run_sync(SQLModel.metadata.drop_all)
await conn.run_sync(SQLModel.metadata.create_all)
```

Every test function drops and recreates all tables. This is slow and prevents running tests in parallel.

**Fix:**
- Use transactional test fixtures (begin transaction, run test, rollback).
- Only create schema once per session.

---

### P2-7: Dependency Version Drift Between `requirements.txt` and `pyproject.toml`

**Files:**
- `apps/backend/requirements.txt`: `sqlmodel>=0.0.14`
- `apps/backend/pyproject.toml`: `sqlmodel==0.0.31`

The two dependency files specify different versions. Docker uses `requirements.txt`; local dev uses `pyproject.toml` via `uv`. This means production and development may run different library versions.

**Fix:**
- Use a single source of truth. Recommended: `pyproject.toml` with `uv` generating a lockfile.
- Generate `requirements.txt` from `uv export` for Docker builds.

---

### P2-8: Third-Party Script (Skimlinks) Loaded on All Pages

**File:** `apps/frontend/app/layout.tsx` lines 24–27

Skimlinks JS is loaded globally, including on auth pages, admin pages, and error pages. This third-party script can read DOM content, cookies (since `httpOnly: false`), and intercept clicks.

**Fix:**
- Load Skimlinks only on pages that display product offers (e.g., the board/row pages).
- Ensure session cookies are `httpOnly` (see P1-3) before this matters less.

---

## What's Good

The audit also found several things done well:

- **Audit logging** with redaction is solid and never throws.
- **Error boundary** in frontend catches crashes and offers bug reporting.
- **GitHub client** has retry logic with exponential backoff.
- **Docker images** are multi-stage with non-root users.
- **Storage abstraction** (disk vs bucket) is clean.
- **Safety service** for content moderation exists.
- **Webhook signature verification** logic itself is correct (HMAC-SHA256 with constant-time comparison).
- **Session tokens** use `secrets.token_urlsafe` + SHA-256 hashing — no plaintext storage.

---

## Recommended Execution Order

| Phase | Items | Effort |
|-------|-------|--------|
| **Phase 1: Security** (1–2 days) | P0-1, P0-2, P0-3, P0-4, P1-3 | ~4 hours |
| **Phase 2: Reliability** (1 day) | P1-1, P1-2, P1-4, P1-5, P1-6 | ~3 hours |
| **Phase 3: Hygiene** (2–3 days) | P2-1 through P2-8 | ~8 hours |

Total: **~15 hours of focused work** across 3 phases.

---

## Non-Goals

- Full Alembic migration rewrite (just stop adding inline migrations).
- Redis infrastructure (document the gap, don't add infra yet).
- Frontend performance optimization (not an issue at current scale).
- API versioning (premature for MVP).
