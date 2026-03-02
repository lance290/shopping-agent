# Parent PRD: Codebase Simplification

**Generated:** February 14, 2026
**Status:** Ready for Effort Generation
**Branch:** dev

---

## Problem Statement

### What problems are we solving?

The codebase has **~50,000 lines of application code** serving what is fundamentally a **3-entity app** (User, Row, Bid). Six phases of PRD-driven development have accumulated:

- **24 database tables** (only ~8 serve the core flow)
- **25 backend route files** (only ~8 serve the actual UI)
- **44 frontend API proxy routes** (pure pass-through boilerplate)
- **3 separate vendor/seller models** with overlapping fields and no FK linking them
- **~10,000 lines of dead code** across backend services, routes, and frontend proxies
- **2 competing Zustand stores** (only one is used)
- **15+ JSON-in-string model fields** with no schema validation

### Who is affected?

- **Developers** — every simple change touches 4+ files across 3+ layers; recurring bugs re-emerge after being "fixed"
- **Users** — bugs caused by indirection (wrong data on wrong row, likes not persisting, clickouts breaking)
- **Product velocity** — planning/tracking artifacts (98 PRDs, 454 CFOI files) vastly outnumber shipped features

### Why now?

The same 5 bug classes keep recurring despite repeated fixes:

1. **Port/URL mismatch** — 44 proxy files define `BACKEND_URL` in 4 different ways across 25 files
2. **Wrong data on wrong row** — race conditions in 599-line monolithic store
3. **Likes not persisting** — `getOfferStableKey()` has 4 fallback strategies because identity is unstable
4. **Project assignment dropping** — proxy layer loses context
5. **Data wipes** — fragile migrations for dead features

The root cause is structural. Patching individual bugs doesn't fix the architecture that generates them.

---

## Solution Overview

Systematically reduce the codebase from ~50,000 LOC to ~24,000 LOC while preserving 100% of user-facing functionality. This is achieved through 7 child efforts:

| # | Effort | Est. | Risk |
|---|--------|------|------|
| 00 | Unify the Proxy Layer | 1 day | Low |
| 01 | Delete Dead Backend Code | 1 day | Low |
| 02 | Delete Dead Frontend Code | 0.5 day | Low |
| 03 | Unify the Vendor Model | 2 days | Medium |
| 04 | Fix JSON-in-String Data Model | 2 days | Medium |
| 05 | Simplify Frontend State | 1 day | Medium |
| 06 | Consolidate Sourcing System | 1.5 days | Low-Medium |

**Total: ~9 days of focused work.**

### Success Criteria

- [ ] Backend LOC reduced from ~31,000 to ~15,000
- [ ] Frontend LOC reduced from ~19,000 to ~12,000
- [ ] Frontend proxy route files reduced from 44 to ≤10 (or 0 with rewrites)
- [ ] Database tables reduced from 24 to ≤14
- [ ] `BACKEND_URL` defined in exactly 1 place
- [ ] `getAuthHeader()` defined in exactly 1 place
- [ ] Zero dead backend services (currently 4 never-imported files)
- [ ] Single vendor entity (currently 3 overlapping models)
- [ ] Single Zustand store (currently 2 competing implementations)
- [ ] All existing tests continue to pass after each effort
- [ ] No user-facing functionality removed

---

## Current State Inventory

### Database Tables (24 total)

**Core (8 — keep):**
`User`, `AuthSession`, `AuthLoginCode`, `Row`, `Project`, `Bid`, `Seller`→`Vendor`, `Comment`

**Active but need cleanup (4):**
`ShareLink` (remove 5 dead metric columns), `ClickoutEvent` (remove `is_suspicious`), `VendorProfile` (merge into Vendor), `SellerQuote`

**Dead / write-only (4 — delete or archive):**
`AuditLog` (write-only, never read), `Contract`, `DealHandoff`, `UserSignal`

**Borderline (8 — evaluate):**
`BugReport` (used by bug reporting + webhook status transitions), `Merchant` (active seller registration/profile flow), `Notification` (backend helper used by auth/seller flows), `OutreachEvent` (used by outreach flow), `PurchaseEvent` (checkout webhook + admin metrics), `RequestSpec` (1:1 with Row, candidate for inlining), `SellerBookmark` (seller route support; no confirmed UI), `UserPreference`

### Backend Route Files (25 total)

**Core (12 — keep):**
`auth.py`, `rows.py`, `rows_search.py`, `bids.py`, `chat.py`, `likes.py`, `comments.py`, `clickout.py`, `shares.py`, `outreach.py`, `quotes.py`, `projects.py`

**Admin (2 — keep):**
`admin.py`, `bugs.py`

**Dead/Dormant candidates (3 — verify before delete):**
`contracts.py` (184 LOC), `signals.py` (190 LOC), `stripe_connect.py` (218 LOC)

**Keep (confirmed active):**
`notifications.py` (helper used by auth/seller flows), `webhooks.py` (GitHub/Railway webhook endpoints are registered in `main.py`)

**Redundant / consolidate (2):**
`search_enriched.py` (135 LOC — merge into rows_search), `rate_limit.py` (31 LOC — inline into middleware)

`merchants.py` and `seller.py` are currently active via `/merchants/register` and `/seller/*` frontend flows and must be treated as migration targets, not dead code.

### Backend Services (11 total)

**Core (5 — keep):**
`llm.py`, `email.py`, `vendors.py`, `intent.py`, `notify.py`

**Dead candidates (3 — delete):**
`reputation.py` (179 LOC — no runtime imports), `vendor_discovery.py` (217 LOC — no runtime imports), `wattdata_mock.py` (25 LOC — unused)

**Active (do not delete in PRD-01):**
`fraud.py` (used by clickout route and admin metrics), `outreach_monitor.py` (used by admin outreach endpoint)

### Frontend API Proxy Routes (44 total)

**`BACKEND_URL` is defined 4 different ways across 25 files:**

| Pattern | Files Using |
|---------|-------------|
| `process.env.NEXT_PUBLIC_API_URL \|\| 'http://localhost:8000'` | 8 routes (admin/*, checkout/*, bids/social/batch) |
| `normalizeBaseUrl(process.env.NEXT_PUBLIC_BACKEND_URL \|\| process.env.BACKEND_URL \|\| 'http://127.0.0.1:8000')` | 3 routes (bids/[id], chat, likes) |
| `process.env.BACKEND_URL \|\| process.env.BFF_URL \|\| 'http://localhost:8000'` | auth/constants.ts (shared by auth routes) |
| `import { BACKEND_URL } from '../../utils/bff'` | 14 routes (bugs, clickout, comments, rows, etc.) |

**`getAuthHeader()` is copy-pasted in 9 route files** instead of being shared.

### Frontend State (2 competing stores)

| Store | LOC | Imports | Status |
|-------|-----|---------|--------|
| `app/store.ts` | 599 | 19 component files | **Active — canonical** |
| `app/stores/` directory | 839 (7 files) | 2 component files (`OfferTile.tsx`, `TileDetailPanel.tsx`) | **Mostly dead** |

The `stores/` directory has `detailPanelStore.ts` which IS imported by 2 components. The rest (`index.ts`, `rows.ts`, `search.ts`, `types.ts`, `ui.ts`, `utils.ts`) are dead.

### Sourcing Code Clarification (Second-Pass)

There are duplicate symbol definitions between `apps/backend/sourcing.py` (root, 778 LOC) and `apps/backend/sourcing/repository.py`.

However, `from sourcing import ...` currently resolves to the **package** `apps/backend/sourcing/__init__.py` (not the root `sourcing.py` module), because the package directory takes precedence in import resolution.

Implication:
- The root `apps/backend/sourcing.py` is likely a **shadow/dead module**.
- Deleting it is still desirable, but the deletion should be treated as dead-code cleanup, not a live import migration of `main.py`/`routes/*`.

---

## Child PRDs

### PRD-00: Unify the Proxy Layer

See: `docs/prd/simplification/prd-00-unify-proxy-layer.md`

### PRD-01: Delete Dead Backend Code

See: `docs/prd/simplification/prd-01-delete-dead-backend.md`

### PRD-02: Delete Dead Frontend Code

See: `docs/prd/simplification/prd-02-delete-dead-frontend.md`

### PRD-03: Unify the Vendor Model

See: `docs/prd/simplification/prd-03-unify-vendor-model.md`

### PRD-04: Fix JSON-in-String Data Model

See: `docs/prd/simplification/prd-04-fix-data-model.md`

### PRD-05: Simplify Frontend State

See: `docs/prd/simplification/prd-05-simplify-frontend-state.md`

### PRD-06: Consolidate Sourcing System

See: `docs/prd/simplification/prd-06-consolidate-sourcing.md`

---

## Execution Order & Dependencies

```
PRD-00 (proxy layer) ──┐
                       ├──→ PRD-05 (frontend state)
PRD-01 (dead backend) ─┤
                       ├──→ PRD-03 (vendor model) ──→ PRD-04 (data model)
PRD-02 (dead frontend)─┘
                         PRD-06 (sourcing) — independent, can run in parallel
```

**Recommended sequence:**
1. PRD-00 + PRD-01 + PRD-02 (parallel, low risk, immediate impact)
2. PRD-06 (independent, low-medium risk)
3. PRD-03 (medium risk, requires migration)
4. PRD-04 (medium risk, requires migration, builds on PRD-03)
5. PRD-05 (medium risk, benefits from cleaner data flow from PRD-04)

---

## Constraints

- **No user-facing functionality removed** — every feature a real user currently uses must continue working
- **All existing tests must pass** after each effort (309 tests as of last run)
- **Railway deployment must remain functional** — backend on port 8080, frontend connects via `BACKEND_URL` env var
- **Database migrations must be reversible** — use Alembic with proper upgrade/downgrade
- **One effort at a time** — each effort is independently deployable and testable

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking import chains when deleting files | High | Medium | grep all import sites before deletion; run full test suite after each file removed |
| Migration data loss (vendor merge) | High | Low | Write migration with explicit data mapping; test on local DB copy first |
| Proxy layer change breaks Railway deploy | High | Medium | Test both `BACKEND_URL` env var paths; verify Railway env vars are set correctly |
| Removing "dead" code that's actually used by a deployed cron/worker | Medium | Low | Audit Railway services list; check for scheduled tasks |
| Frontend store simplification causes UI regression | Medium | Medium | Manual smoke test: login → create row → see offers → like → click out |

## Traceability

- **Analysis document:** `SIMPLIFICATION_PLAN.md` (root)
- **Product North Star:** `.cfoi/branches/main/product-north-star.md`
- **Prior phases:** `docs/prd/phase2/`, `docs/prd/marketplace-pivot/`

---
**Note:** Technical implementation decisions are made during /plan and /task phases, not in this PRD.
