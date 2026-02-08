# PRD-04: Frontend Proxy Collapse & Store Refactor

**Priority:** P1 — cleanup, reduces maintenance burden  
**Effort:** 1-1.5 days  
**Dependencies:** PRD-02 (Kill BFF — determines final backend URL pattern)  
**Net effect:** Delete ~40 proxy route files (~1,600 lines), split 757-line store into 3 focused stores

---

## Problem

### 44 frontend API proxy routes that just forward headers

The `apps/frontend/app/api/` directory contains 44 route files. Nearly all of them follow this pattern:

```typescript
export async function POST(req: Request) {
  const body = await req.json();
  const res = await fetch(`${BACKEND_URL}/some-endpoint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: req.headers.get('authorization') },
    body: JSON.stringify(body),
  });
  return Response.json(await res.json(), { status: res.status });
}
```

This adds:
- **Latency:** Every request takes an extra network hop through Next.js
- **Maintenance:** Every new backend endpoint needs a matching proxy file
- **Debugging pain:** Errors can originate in the proxy layer, obscuring the real cause
- **44 files** to keep in sync with backend routes

### 757-line monolith store

`store.ts` manages everything: rows, search results, projects, social data, UI state, sort modes, sidebar, modals, pending deletes, card click queries. This makes it hard to:
- Find where state lives
- Understand what triggers what
- Test slices in isolation

---

## Part A: Replace 44 Proxy Routes with 1 Catch-All

### Strategy

Replace all individual proxy files with a single catch-all route that forwards any `/api/*` request to the backend. Next.js supports this via `app/api/[...path]/route.ts`.

**This file already exists:** `app/api/proxy/[...path]/route.ts` (124 lines). It's a generic proxy. The problem is that the individual route files take precedence over the catch-all due to Next.js routing specifics.

### Plan

1. **Delete all individual proxy files** that are pure pass-through (no transformation logic)
2. **Keep files that add real logic** (listed below)
3. **Move the catch-all** from `app/api/proxy/[...path]/route.ts` to `app/api/[...path]/route.ts` so it catches everything

### Files to DELETE (pure proxies, ~35 files)

These files add zero logic — they just forward request/response:

```
app/api/admin/growth/route.ts          (20 lines)
app/api/admin/metrics/route.ts         (21 lines)
app/api/admin/revenue/route.ts         (19 lines)
app/api/admin/stats/route.ts           (19 lines)
app/api/auth/logout/route.ts           (35 lines)
app/api/auth/me/route.ts               (23 lines)
app/api/auth/start/route.ts            (20 lines)
app/api/auth/verify/route.ts           (34 lines)
app/api/bids/[id]/route.ts             (59 lines)
app/api/bids/social/batch/route.ts     (28 lines)  ← also deleted in PRD-03
app/api/bugs/[id]/route.ts             (74 lines)
app/api/check-service/route.ts         (30 lines)
app/api/checkout/route.ts              (33 lines)
app/api/checkout/batch/route.ts        (25 lines)
app/api/clickout/route.ts              (56 lines)
app/api/comments/route.ts              (94 lines)
app/api/health/route.ts                (11 lines)
app/api/likes/route.ts                 (117 lines) ← also deleted in PRD-03
app/api/likes/counts/route.ts          (61 lines)  ← also deleted in PRD-03
app/api/merchants/register/route.ts    (44 lines)
app/api/notifications/route.ts         (22 lines)  ← also deleted in PRD-01
app/api/notifications/count/route.ts   (20 lines)  ← also deleted in PRD-01
app/api/outreach/[rowId]/route.ts      (67 lines)
app/api/projects/route.ts              (109 lines)
app/api/quotes/[quoteId]/select/route.ts (41 lines)
app/api/quotes/form/[token]/route.ts   (33 lines)
app/api/quotes/submit/[token]/route.ts (35 lines)
app/api/rows/route.ts                  (149 lines)
app/api/search/route.ts                (52 lines)
app/api/seller/bookmarks/route.ts      (68 lines)
app/api/seller/inbox/route.ts          (25 lines)
app/api/seller/profile/route.ts        (41 lines)
app/api/seller/quotes/route.ts         (41 lines)
app/api/shares/route.ts                (35 lines)
app/api/shares/[token]/route.ts        (21 lines)
app/api/signals/route.ts               (25 lines)
app/api/signals/preferences/route.ts   (19 lines)  ← also deleted in PRD-01
app/api/stripe-connect/earnings/route.ts (19 lines) ← also deleted in PRD-01
app/api/vendors/[category]/route.ts    (33 lines)
app/api/merchants/connect/onboard/route.ts (20 lines) ← also deleted in PRD-01
app/api/merchants/connect/status/route.ts  (19 lines) ← also deleted in PRD-01
```

### Files to KEEP (add real logic)

| File | Lines | Why Keep |
|---|---|---|
| `app/api/chat/route.ts` | 55 | SSE streaming requires special handling (ReadableStream pipe) |
| `app/api/bugs/route.ts` | 70 | Multipart form data handling for file uploads |

### Catch-All Proxy

Move and simplify `app/api/proxy/[...path]/route.ts` → `app/api/[...path]/route.ts`:

```typescript
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

async function proxyRequest(req: Request, path: string) {
  const url = `${BACKEND_URL}/${path}`;
  const headers: Record<string, string> = { };
  
  // Forward auth header
  const auth = req.headers.get('authorization');
  if (auth) headers['Authorization'] = auth;
  
  // Forward content-type
  const ct = req.headers.get('content-type');
  if (ct) headers['Content-Type'] = ct;

  const res = await fetch(url, {
    method: req.method,
    headers,
    body: ['GET', 'HEAD'].includes(req.method) ? undefined : await req.text(),
  });

  return new Response(res.body, {
    status: res.status,
    headers: { 'Content-Type': res.headers.get('content-type') || 'application/json' },
  });
}

export async function GET(req: Request, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path.join('/'));
}
export async function POST(req: Request, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path.join('/'));
}
export async function PATCH(req: Request, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path.join('/'));
}
export async function DELETE(req: Request, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path.join('/'));
}
export async function PUT(req: Request, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path.join('/'));
}
```

~40 lines replaces ~1,600.

### Frontend Fetch Calls

Currently the frontend calls `/api/rows`, `/api/likes`, etc. which hit the proxy files. After deletion, these same URLs will hit the catch-all proxy, which forwards to the backend at the same path. **No frontend fetch call changes needed** as long as the catch-all preserves the path mapping.

The only thing to verify: the backend endpoints match the paths the frontend expects. Quick audit:

| Frontend calls | Backend serves | Match? |
|---|---|---|
| `/api/rows` | `/rows` | ✅ (catch-all strips `/api/` prefix... or keeps it — need to decide) |

**Decision:** The catch-all should strip the `/api/` prefix when forwarding. Most backend routes don't have an `/api/` prefix (e.g., backend serves `/rows`, not `/api/rows`). Exception: `shares.py` uses `/api/shares` — this needs to be normalized.

Normalize `routes/shares.py` to use `/shares` instead of `/api/shares` (4 decorator changes).

---

## Part B: Split the Store

### Current: 1 file, 757 lines

`store.ts` has one giant `useAppStore` with:

- Row state + CRUD actions (~200 lines)
- Search results + provider statuses + sorting (~150 lines)
- Social data: likes, comments (~100 lines) — reduced by PRD-03
- Project state (~50 lines)
- UI state: sidebar, modals, pending deletes (~80 lines)
- Helper functions: `mapBidToOffer`, `getOfferStableKey` (~50 lines)
- Interfaces: `Offer`, `Row`, `Project`, `Bid`, `BidSocialData`, etc. (~130 lines)

### Target: 3 files

| File | Responsibility | ~Lines |
|---|---|---|
| `stores/core.ts` | Rows, projects, bids, CRUD actions, interfaces | ~250 |
| `stores/search.ts` | `rowResults`, `providerStatuses`, sort modes, `mapBidToOffer` | ~150 |
| `stores/ui.ts` | Sidebar, active row/project, modals, pending deletes | ~80 |

### How Stores Communicate

Use Zustand's `useStore` with selectors. Each store is independent. Components pick from whichever store they need:

```typescript
const rows = useCoreStore(s => s.rows);
const results = useSearchStore(s => s.rowResults[rowId]);
const sidebarOpen = useUIStore(s => s.sidebarOpen);
```

Cross-store calls (e.g., search needs row ID) pass the value as a parameter rather than importing another store directly.

### Migration Strategy

1. Create `stores/` directory
2. Move interfaces to `stores/types.ts`
3. Extract UI state → `stores/ui.ts`
4. Extract search state → `stores/search.ts`
5. Core row/project state stays → `stores/core.ts`
6. Update all component imports from `../store` to `../stores/core` (etc.)
7. Delete old `store.ts`

---

## Verification

### Part A
1. `find apps/frontend/app/api -name 'route.ts' | wc -l` → should be ~3 (catch-all + chat + bugs)
2. Core flow works: create row, search, see results
3. Auth works: login, logout, session persistence
4. Shares work: create share link, open in incognito
5. Comments work: add/delete comment on a tile
6. `npx next build` — clean build

### Part B
1. `wc -l apps/frontend/app/stores/*.ts` — each file < 300 lines
2. No file named `store.ts` exists in `app/`
3. All components render without errors
4. State persists across navigation (sidebar open, active row, etc.)
5. Search results populate correctly per row

---

## Risks

| Risk | Mitigation |
|---|---|
| Catch-all proxy misroutes a path | Test every major flow. The paths are deterministic. |
| Some proxy files add subtle logic (auth transform, error mapping) | I audited them — only `bugs/route.ts` (multipart) and `chat/route.ts` (SSE) have real logic. Double-check `auth/verify/route.ts` before deleting. |
| Store split breaks component reactivity | Use Zustand selectors. Each store is a standalone `create()`. Components subscribe to exactly what they need. |
| Query string forwarding | Catch-all must forward `req.url` search params. Use `new URL(req.url).search` to append. |
