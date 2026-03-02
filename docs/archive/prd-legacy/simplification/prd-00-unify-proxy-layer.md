# PRD-00: Unify the Proxy Layer

## Business Outcome
- **Measurable impact:** Eliminate the #1 recurring bug class — port/URL mismatches caused by 44 hand-written proxy routes defining `BACKEND_URL` in 4 different ways across 25 files.
- **Success criteria:** `BACKEND_URL` defined in exactly 1 place; `getAuthHeader()` defined in exactly 1 place; all 44 proxy routes use the shared implementation; zero behavior change for end users.
- **Target users:** Developers (reduced bug surface); indirectly all users (fewer URL-related outages).

## Scope
- **In-scope:**
  - Create a single `apps/frontend/app/utils/api-proxy.ts` module that exports:
    - `BACKEND_URL` (single source of truth, reads from env vars with correct fallback chain)
    - `getAuthHeader(request: NextRequest): string | null` (reads from `Authorization` header or `sa_session` cookie)
    - `proxyGet(request, backendPath): Promise<NextResponse>`
    - `proxyPost(request, backendPath): Promise<NextResponse>`
    - `proxyPatch(request, backendPath): Promise<NextResponse>`
    - `proxyDelete(request, backendPath): Promise<NextResponse>`
  - Rewrite all active `route.ts` proxy files to use the shared helpers
  - Delete all local `BACKEND_URL` definitions and local `getAuthHeader()` copies
  - Consolidate `apps/frontend/app/api/auth/constants.ts` and `apps/frontend/app/utils/bff.ts` into one canonical source for backend URL + cookie name constants (delete only after all imports migrate)
  - Preserve auth cookie behavior in both `api/auth/*` routes and `api/proxy/[...path]/route.ts`
- **Out-of-scope:**
  - Replacing proxy routes with Next.js `rewrites` (evaluated but deferred — rewrites run at build-time, we need runtime env vars on Railway)
  - Changing backend routes or paths
  - Modifying frontend client-side code (components, store)

## Current State (Evidence)

### `BACKEND_URL` — 4 competing definitions across 25 files

| # | Pattern | Used By |
|---|---------|---------|
| 1 | `process.env.NEXT_PUBLIC_API_URL \|\| 'http://localhost:8000'` | `admin/growth`, `admin/metrics`, `admin/revenue`, `admin/stats`, `bids/social/batch`, `checkout/batch`, `checkout`, `seller/bookmarks` |
| 2 | `normalizeBaseUrl(process.env.NEXT_PUBLIC_BACKEND_URL \|\| process.env.BACKEND_URL \|\| 'http://127.0.0.1:8000')` | `bids/[id]`, `chat`, `likes` |
| 3 | `process.env.BACKEND_URL \|\| process.env.BFF_URL \|\| 'http://localhost:8000'` | `auth/constants.ts` → used by `auth/*` routes |
| 4 | `import { BACKEND_URL } from '../../utils/bff'` → which reads `process.env.NEXT_PUBLIC_BACKEND_URL \|\| process.env.BACKEND_URL \|\| 'http://127.0.0.1:8000'` | `bugs/*`, `clickout`, `comments`, `merchants/*`, `outreach/*`, `projects`, `quotes/*`, `rows`, `rows/[rowId]/vendors`, `search`, `shares/*` |

**Railway has:** `BACKEND_URL=http://backend.railway.internal:8080` set on the frontend service.

Use a single normalized fallback chain that remains backward-compatible with deployed environments: `BACKEND_URL`, `NEXT_PUBLIC_BACKEND_URL`, legacy `BFF_URL`, and only then localhost fallback.

### `getAuthHeader()` — copy-pasted in 9 files

Files that define their own `getAuthHeader()`:
- `bids/[id]/route.ts`
- `bugs/[id]/route.ts`
- `bugs/route.ts`
- `clickout/route.ts`
- `comments/route.ts`
- `likes/route.ts`
- `projects/route.ts`
- `rows/route.ts`
- `shares/route.ts`

All 9 implementations are identical: check `Authorization` header first, fall back to `sa_session` cookie, return `Bearer <token>` or `null`.

### Special auth proxy handling

`proxy/[...path]/route.ts` handles `auth/start`, `auth/verify`, `auth/me`, `auth/logout` with an allowlist and cookie set/clear behavior.

Additionally, dedicated `api/auth/*` routes also implement auth forwarding and cookie handling today. Second-pass correction: do **not** assume `proxy/[...path]` is the only auth cookie path. Consolidation work must account for both route families.

## User Flow
1. Frontend component calls `/api/<path>` (no change)
2. Next.js API route handler receives request
3. Handler calls `proxyGet(request, '/backend-path')` or `proxyPost(request, '/backend-path')`
4. `api-proxy.ts` reads `BACKEND_URL`, extracts auth header, forwards request, returns response
5. No behavior change visible to end user

## Business Requirements

### Authentication & Authorization
- `getAuthHeader()` must preserve exact current behavior: check `Authorization` header first, then `sa_session` cookie
- Auth proxy routes (`proxy/[...path]/route.ts`) retain their own cookie-management logic — they are NOT migrated to the generic helper

### Monitoring & Visibility
- No new monitoring required — this is a pure refactor
- Log proxy errors to console as currently done

### Performance Expectations
- Zero latency change — same fetch calls, just reorganized
- No additional network hops

### Data Requirements
- No data changes — pure frontend refactor

### UX & Accessibility
- No UI changes whatsoever

### Privacy, Security & Compliance
- Auth header forwarding must remain identical
- No new env vars exposed to browser (all server-side only)

## Target Implementation

### `apps/frontend/app/utils/api-proxy.ts` (~60 LOC)

Exports:
```typescript
export const BACKEND_URL: string          // single source of truth
export function getAuthHeader(req): string | null
export async function proxyGet(req, path, options?): Promise<NextResponse>
export async function proxyPost(req, path, options?): Promise<NextResponse>
export async function proxyPatch(req, path, options?): Promise<NextResponse>
export async function proxyDelete(req, path, options?): Promise<NextResponse>
```

Each proxy route becomes ~3-8 lines:
```typescript
import { proxyGet } from '../../utils/api-proxy';
export const GET = (req: NextRequest) => proxyGet(req, '/rows');
```

Routes with custom logic (dynamic path params, query string manipulation, special headers) keep their route file but still use `BACKEND_URL` and `getAuthHeader` from the shared module.

### Routes that need custom handling (keep route file, use shared helpers)

| Route | Why Custom |
|-------|-----------|
| `proxy/[...path]/route.ts` | Cookie set/clear for auth |
| `bids/[id]/route.ts` | Dynamic `[id]` param, `include_provenance` query |
| `bugs/[id]/route.ts` | Dynamic `[id]` param, PATCH method |
| `chat/route.ts` | SSE streaming response (not JSON) |
| `quotes/form/[token]/route.ts` | Dynamic `[token]` param |
| `quotes/submit/[token]/route.ts` | Dynamic `[token]` param |
| `quotes/[quoteId]/select/route.ts` | Dynamic `[quoteId]` param |
| `shares/[token]/route.ts` | Dynamic `[token]` param |
| `rows/[rowId]/vendors/route.ts` | Dynamic `[rowId]` param |
| `outreach/[rowId]/route.ts` | Dynamic `[rowId]` param |

These ~10 routes keep their `route.ts` but import `BACKEND_URL` and `getAuthHeader` from `api-proxy.ts` instead of defining their own.

### Routes that become trivial proxies (~30 routes)

These have zero custom logic — just forward GET/POST to a fixed backend path. Each becomes ≤5 lines using `proxyGet`/`proxyPost`.

## Dependencies
- **Upstream:** None — this is the first effort
- **Downstream:** PRD-02 (Delete Dead Frontend Code) will delete some of these proxy routes entirely; having them use a shared helper first makes that safer

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unified `BACKEND_URL` breaks Railway deploy | High | Keep fallback compatibility (`BACKEND_URL` + legacy aliases); verify deployed env vars |
| SSE chat route breaks with generic proxy helper | High | Keep chat route custom; only share common URL/auth utilities |
| Auth cookie logic breaks during refactor | High | Migrate auth routes as a unit (`api/auth/*` + `api/proxy/[...path]`) and preserve cookie semantics |
| Missing edge case in a proxy route | Medium | Run full test suite; manual smoke test (login → chat → search → like → clickout) |

## Acceptance Criteria (Business Validation)
- [ ] Exactly one canonical backend URL helper module exists (`api-proxy.ts` or `utils/bff.ts`), with all proxy routes importing from it (directly or via explicit re-export)
- [ ] Exactly one canonical auth-header helper exists, with route-specific exceptions documented (e.g., chat/clickout/custom auth handling)
- [ ] All proxy routes either use shared helpers or are explicitly marked custom with justification
- [ ] `bff.ts` and `auth/constants.ts` are either removed or converted to thin compatibility re-exports; no divergent URL logic remains
- [ ] Backend health check responds: `curl http://localhost:8000/health` → 200
- [ ] Frontend health check responds: `curl http://localhost:3000/api/health` → 200
- [ ] Login flow works (phone → verify → redirect)
- [ ] Chat + search flow works (submit intent → see tiles)
- [ ] Like toggle works (click heart → persists on reload)
- [ ] Clickout works (click offer → redirects to merchant)
- [ ] All existing tests pass

## Traceability
- **Parent PRD:** `docs/prd/simplification/parent.md`
- **Analysis:** `SIMPLIFICATION_PLAN.md` — Problem 1: The Proxy Layer Tax

---
**Note:** Technical implementation decisions are made during /plan and /task.
