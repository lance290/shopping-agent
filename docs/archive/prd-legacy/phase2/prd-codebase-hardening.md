# PRD: Codebase Hardening

**Status:** Draft
**Author:** Cascade + Lance
**Created:** 2026-02-05
**Last Updated:** 2026-02-05
**Priority:** P0–P2 by section
**Scope:** Backend, BFF, Frontend, Infrastructure

---

## 1. Executive Summary

### 1.1 Context

A full-stack audit of the Shopping Agent codebase (backend, BFF, frontend, CI/CD, Docker) identified **4 critical**, **6 high**, and **8 medium** findings across security, reliability, architecture, and operational hygiene.

The codebase has strong foundations — hashed session tokens, audit logging with redaction, multi-stage Docker images with non-root users, retry logic on external calls, and a clean storage abstraction. However, several security holes opened during rapid feature development that need to be closed before scaling beyond the current user base.

### 1.2 North Star

> **"Every request is authenticated, every boundary is validated, every failure is visible."**

### 1.3 Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| SSRF attack surface | Open (catch-all proxy) | Zero (allowlisted paths only) | Code review |
| Webhook forgery resistance | Bypassed (default secret) | Always verified | Integration test |
| Auth implementation copies | 3 (divergent) | 1 (canonical) | `grep -r "require_admin"` count |
| Silent error swallowing | ~12 bare `except:` blocks | 0 | Linter rule |
| CI pipeline passing | Never (wrong package manager) | Green on every push | GitHub Actions |
| Session cookie security | `httpOnly: false` | `httpOnly: true, secure: true` | Browser dev tools |

---

## 2. What's At Risk

### 2.1 Attack Scenarios (Why This Matters)

| Scenario | Finding | Impact |
|----------|---------|--------|
| Attacker sends crafted request to `/api/proxy/internal-admin/users` | P0-1 (SSRF) | Access to internal backend endpoints, credential leak via forwarded auth headers |
| Attacker intercepts Railway DB traffic | P0-2 (SSL disabled) | Full database read/write, credential theft |
| Attacker POSTs forged GitHub webhook to `/api/webhooks/github` | P0-3 (No signature check) | Arbitrary bug status changes, potential code execution via crafted PR URLs |
| Security fix applied to `dependencies.py` but not `routes/admin.py` copy | P0-4 (Duplicated auth) | Admin bypass via unpatched code path |
| XSS via Skimlinks or any injected script | P1-3 (Non-HttpOnly cookie) | Session token theft from cookie + localStorage |

### 2.2 Operational Scenarios

| Scenario | Finding | Impact |
|----------|---------|--------|
| `python reset_prod_db.py` run with prod `DATABASE_URL` set | P1-5 | Total production data loss, no recovery |
| Deploy fails; logs show interleaved `print()` from 4 workers | P2-4 | Undebuggable production incidents |
| CI "passes" but never actually ran tests | P2-1 | False confidence; bugs ship to production |
| Alembic migration + inline `ALTER TABLE` conflict | P2-3 | Schema drift between environments |

---

## 3. Detailed Findings & Specifications

### 3.1 🔴 P0 — Critical (Fix Immediately)

---

#### P0-1: Open SSRF via Frontend Catch-All Proxy

**File:** `apps/frontend/app/api/proxy/[...path]/route.ts`

**Current behavior:**
The catch-all Next.js API route forwards ANY path to `NEXT_PUBLIC_BACKEND_URL` without validation. It also forwards the `Authorization` header to whatever destination it resolves to.

```typescript
// Current — vulnerable
const path = (await params).path.join('/');
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
const url = `${backendUrl}/${path}`;
```

**Problems:**
1. Path traversal: `/api/proxy/../../internal-service/admin` could resolve to unintended hosts.
2. `NEXT_PUBLIC_` prefix exposes the backend URL to the browser bundle.
3. Auth header forwarded to any resolved destination.

**Required changes:**
1. Replace catch-all with an explicit allowlist of proxy-able paths:
   ```typescript
   const ALLOWED_PATHS = new Set([
     'auth/start',
     'auth/verify',
     'auth/me',
     'auth/logout',
   ]);
   ```
2. Rename `NEXT_PUBLIC_BACKEND_URL` → `BACKEND_URL` (server-only).
3. Reject any path not in the allowlist with 404.
4. Sanitize path segments (no `..`, no double slashes).

**Acceptance criteria:**
- [ ] `/api/proxy/auth/verify` works as before.
- [ ] `/api/proxy/../../anything` returns 404.
- [ ] `/api/proxy/rows` returns 404 (rows go through dedicated route files).
- [ ] `NEXT_PUBLIC_BACKEND_URL` no longer appears in browser bundle.

**Test:**
```bash
curl -X POST http://localhost:3003/api/proxy/../../etc/passwd
# Expected: 404
curl -X POST http://localhost:3003/api/proxy/auth/verify -d '{"phone":"+16503398297","code":"123456"}'
# Expected: normal auth flow
```

---

#### P0-2: Production SSL Verification Disabled

**File:** `apps/backend/database.py` lines 23–28
**Also:** `apps/backend/scripts/migrate_triage_columns.py`, `apps/backend/scripts/verify_triage_models.py`

**Current behavior:**
```python
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

**Required changes:**
```python
# Option A: Use Railway private networking (no SSL needed)
connect_args = {}
if os.getenv("RAILWAY_ENVIRONMENT"):
    db_url = os.getenv("DATABASE_PRIVATE_URL") or DATABASE_URL
    # Railway private URLs don't need SSL
    # Only add SSL if using public URL
    if "railway.internal" not in db_url:
        ssl_context = ssl.create_default_context()
        # Don't disable verification
        connect_args["ssl"] = ssl_context

# Option B: If SSL is required, verify properly
ssl_context = ssl.create_default_context()
# Do NOT set check_hostname = False
# Do NOT set verify_mode = CERT_NONE
connect_args["ssl"] = ssl_context
```

**Acceptance criteria:**
- [ ] Production DB connection works via Railway private networking without SSL.
- [ ] OR production DB connection uses SSL with certificate verification enabled.
- [ ] Same fix applied to all 3 files that contain the pattern.
- [ ] Local development still works (no SSL needed for localhost).

---

#### P0-3: Webhook Signature Verification Bypassed in Production

**File:** `apps/backend/routes/webhooks.py` lines 16, 44–46

**Current behavior:**
```python
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret")
# ...
if WEBHOOK_SECRET != "dev-webhook-secret":
    if not verify_webhook_signature(...):
```

If the env var is unset, the default `"dev-webhook-secret"` causes the `!=` check to be `False`, skipping verification entirely.

**Required changes:**
```python
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

@router.post("/api/webhooks/github")
async def github_webhook(request: Request, ...):
    payload_bytes = await request.body()

    # Always verify in production
    is_test_mode = os.getenv("E2E_TEST_MODE") == "1"
    if not is_test_mode:
        if not WEBHOOK_SECRET:
            raise HTTPException(status_code=503, detail="Webhook not configured")
        if not verify_webhook_signature(payload_bytes, x_hub_signature_256 or ""):
            raise HTTPException(status_code=401, detail="Invalid signature")
```

**Acceptance criteria:**
- [ ] Production: webhook without valid signature → 401.
- [ ] Production: missing `WEBHOOK_SECRET` env var → 503 (not silent bypass).
- [ ] E2E test mode: signature check skipped (existing behavior).
- [ ] Same pattern applied to Railway webhook endpoint.

---

#### P0-4: Triplicated `require_admin` / `get_current_session`

**Files with duplicates:**
- `apps/backend/dependencies.py` — **canonical** (keep this one)
- `apps/backend/routes/bugs.py` lines 213–235 — **delete**
- `apps/backend/routes/admin.py` lines 28–50 — **delete**
- `apps/backend/routes/auth.py` lines 232–249 — **delete** `get_current_session` (keep the one that other routes import, or consolidate)

**Required changes:**
1. Delete `require_admin` from `routes/bugs.py` and `routes/admin.py`.
2. Move the canonical `get_current_session` to `dependencies.py` if not already there.
3. Update all imports:
   ```python
   from dependencies import get_current_session, require_auth, require_admin
   ```
4. Remove inline `from routes.auth import get_current_session` calls scattered in route files.

**Acceptance criteria:**
- [ ] `grep -rn "def require_admin" apps/backend/` returns exactly 1 result (in `dependencies.py`).
- [ ] `grep -rn "def get_current_session" apps/backend/` returns exactly 1 result.
- [ ] All existing tests pass.
- [ ] Admin endpoints still require admin role.

---

### 3.2 🟠 P1 — High (Fix This Sprint)

---

#### P1-1: Backend CORS Allows Only localhost

**File:** `apps/backend/main.py` lines 50–59

**Required changes:**
```python
CORS_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3003,http://127.0.0.1:3003")
origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Set in Railway: `CORS_ALLOWED_ORIGINS=https://frontend-dev-aca4.up.railway.app`

**Acceptance criteria:**
- [ ] Local dev works with default localhost origins.
- [ ] Production responds with correct `Access-Control-Allow-Origin` header.

---

#### P1-2: BFF CORS Defaults to Wildcard `*`

**File:** `apps/bff/src/index.ts` line 333

**Required changes:**
```typescript
const CORS_ORIGIN = process.env.CORS_ORIGIN;
if (!CORS_ORIGIN && process.env.NODE_ENV === 'production') {
  console.error('[BFF] CORS_ORIGIN not set in production!');
  process.exit(1);
}

fastify.register(cors, {
  origin: CORS_ORIGIN ? CORS_ORIGIN.split(',') : ['http://localhost:3003'],
});
```

**Acceptance criteria:**
- [ ] Production: BFF refuses to start without `CORS_ORIGIN`.
- [ ] Development: defaults to `localhost:3003`.

---

#### P1-3: Session Cookie Not HttpOnly

**File:** `apps/frontend/app/api/proxy/[...path]/route.ts` lines 34–39

**Required changes:**
```typescript
response.cookies.set('sa_session', data.session_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 60 * 60 * 24 * 30,
    sameSite: 'lax',
});
```

**Migration:** Frontend code that reads `sa_session` from `document.cookie` or localStorage must be updated to read the token from the Next.js API route (server-side) or pass it via headers set by the middleware.

**Acceptance criteria:**
- [ ] `document.cookie` does not contain `sa_session` in browser console.
- [ ] Auth flow still works end-to-end.
- [ ] Skimlinks script cannot access session token.

---

#### P1-4: In-Memory Rate Limiting (Not Distributed)

**Files:** `apps/backend/routes/rate_limit.py`, `apps/backend/notifications.py`

**Short-term fix (acceptable for current scale):**
- Add a comment documenting the 4x multiplier with `--workers 4`.
- Divide limits by worker count: `max_requests = RATE_LIMIT_MAX.get(limit_type, 100) // int(os.getenv("WEB_CONCURRENCY", "4"))`.

**Long-term fix (when adding Redis):**
- Use Redis `INCR` + `EXPIRE` for distributed rate limiting.

**Acceptance criteria:**
- [ ] Rate limits are documented as per-worker.
- [ ] Notification rate limiter uses same mechanism.

---

#### P1-5: `reset_prod_db.py` Has No Safety Guard

**File:** `apps/backend/reset_prod_db.py`

**Required changes:**
```python
import sys

if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production":
    print("REFUSED: Cannot reset production database.")
    print("If you really need to, use Alembic: alembic downgrade base")
    sys.exit(1)

if "--confirm" not in sys.argv:
    print("This will DROP ALL TABLES. Pass --confirm to proceed.")
    sys.exit(1)
```

**Acceptance criteria:**
- [ ] Running without `--confirm` exits with warning.
- [ ] Running with `RAILWAY_ENVIRONMENT` set exits with refusal.

---

#### P1-6: Bare `except:` Swallowing Errors

**Files (sampled):**
- `apps/backend/routes/bugs.py` lines 133, 164
- `apps/backend/routes/rows.py` lines 197, 391
- `apps/backend/main.py` line 206

**Required changes:** Replace every bare `except:` with:
```python
except Exception as e:
    print(f"[MODULE] Error context: {e}")  # Or logger.warning(...)
```

**Acceptance criteria:**
- [ ] `grep -rn "except:" apps/backend/ | grep -v "except Exception"` returns 0 results (excluding `except ExceptionType:`).
- [ ] No silent error swallowing in any route or utility module.

---

### 3.3 🟡 P2 — Medium (Fix Next Sprint)

---

#### P2-1: CI Pipeline Uses Wrong Package Manager

**File:** `.github/workflows/ci.yml`

The workflow runs `npm ci` at the repo root, but the codebase is a pnpm monorepo with per-app lockfiles. Redis and MongoDB services are provisioned but unused.

**Required changes:**
- Rewrite CI with 3 jobs: `backend-tests`, `bff-tests`, `frontend-tests`.
- Backend: `cd apps/backend && uv run pytest`.
- BFF: `cd apps/bff && pnpm install && pnpm test`.
- Frontend: `cd apps/frontend && pnpm install && pnpm test`.
- Remove unused service containers (Redis, MongoDB).

---

#### P2-2: Debug Print of Database URL

**File:** `apps/backend/database.py` line 19

**Fix:** Delete the line or gate behind `ENVIRONMENT != "production"`.

---

#### P2-3: Inline Migrations Alongside Alembic

**File:** `apps/backend/main.py` lines 230–237

**Fix:**
- Create proper Alembic migration for `chat_history` column.
- Remove inline `ALTER TABLE` from startup event.
- Delete `scripts/migrate_triage_columns.py` — create Alembic migration instead.

---

#### P2-4: No Structured Logging

**Current:** All backend logging is `print()`.

**Fix:**
- Add `logging` config in `main.py` with JSON formatter for production.
- Add correlation ID middleware.
- Replace `print()` with `logger.info()` / `logger.error()` across all modules.
- Estimated: ~50 print statements to replace.

---

#### P2-5: Dual `sourcing.py` / `sourcing/` Package

**Fix:**
- Audit which symbols are imported from root `sourcing.py` vs `sourcing/`.
- Move all shared types to `sourcing/models.py`.
- Reduce `sourcing.py` to a re-export shim or delete entirely.

---

#### P2-6: Test Fixtures Drop/Create Schema Per Test

**File:** `apps/backend/tests/conftest.py` lines 32–34

**Fix:**
- Create schema once per test session (session-scoped fixture).
- Use transactional rollback per test function.
- Expected: 5–10x test speed improvement.

---

#### P2-7: Dependency Version Drift

**Files:** `requirements.txt` vs `pyproject.toml`

**Fix:**
- Use `uv export --format requirements-txt > requirements.txt` to generate from lockfile.
- Add CI check that `requirements.txt` matches `pyproject.toml`.

---

#### P2-8: Third-Party Script on All Pages

**File:** `apps/frontend/app/layout.tsx` lines 24–27

**Fix:**
- Move Skimlinks `<Script>` tag from root layout to a component loaded only on board/offer pages.
- Verify it doesn't break affiliate link conversion.

---

## 4. What's Good (Existing Strengths)

| Area | Details |
|------|---------|
| **Session tokens** | `secrets.token_urlsafe` + SHA-256 hashing — no plaintext storage |
| **Audit logging** | Redaction of sensitive fields, never throws, append-only |
| **Error boundary** | Frontend catches crashes, offers bug reporting |
| **GitHub client** | Retry with exponential backoff, rate-limit awareness |
| **Docker** | Multi-stage builds, non-root users, health checks |
| **Storage** | Clean abstraction (disk vs S3-compatible bucket) |
| **Safety** | Content moderation for search queries |
| **Webhook verification logic** | HMAC-SHA256 with constant-time comparison (just needs to always run) |

---

## 5. Execution Plan

| Phase | Items | Effort | Dependencies |
|-------|-------|--------|--------------|
| **Phase A: Security** | P0-1, P0-2, P0-3, P0-4, P1-3 | ~4 hrs | None |
| **Phase B: Reliability** | P1-1, P1-2, P1-4, P1-5, P1-6 | ~3 hrs | Phase A |
| **Phase C: Hygiene** | P2-1 through P2-8 | ~8 hrs | Independent |

**Total: ~15 hours of focused work.**

### Phase A Sequence (recommended order):
1. **P0-4** (auth dedup) — enables consistent patching for everything else.
2. **P0-1** (SSRF proxy) — highest external risk.
3. **P0-3** (webhook) — small change, high impact.
4. **P0-2** (SSL) — requires Railway env testing.
5. **P1-3** (cookie security) — depends on verifying frontend auth flow.

### Phase B Sequence:
1. **P1-6** (bare except) — improves debuggability for all other fixes.
2. **P1-1 + P1-2** (CORS) — can be done together.
3. **P1-5** (reset guard) — 5-minute fix.
4. **P1-4** (rate limit docs) — documentation only for now.

### Phase C: Independent items, pick order based on developer preference.

---

## 6. Non-Goals

- Full Alembic migration rewrite (just stop adding inline migrations).
- Redis infrastructure (document the gap, don't add infra yet).
- Frontend performance optimization (not an issue at current scale).
- API versioning (premature for MVP stage).
- Rewriting the BFF in a different language.
- Adding OpenAPI schema validation (nice-to-have, not urgent).

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| P1-3 (HttpOnly cookie) breaks frontend auth flow | Test auth flow end-to-end before deploying; can revert cookie change independently |
| P0-2 (SSL fix) breaks Railway DB connection | Test with Railway private URL first; have rollback ready |
| P0-4 (auth dedup) breaks a route that relied on local copy | Run full test suite after consolidation |
| P2-1 (CI rewrite) takes longer than expected | Keep old CI as fallback; phase in new jobs incrementally |
