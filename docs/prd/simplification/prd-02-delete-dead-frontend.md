# PRD-02: Delete Dead Frontend Code

## Business Outcome
- **Measurable impact:** Remove ~2,500 LOC of dead frontend code — proxy routes for deleted backend endpoints, the unused `stores/` directory (partially), and stale root-level markdown reports. Reduces confusion about which code is canonical and which is vestigial.
- **Success criteria:** All listed files/directories deleted; frontend builds cleanly (`next build`); all existing frontend tests pass; no UI regression.
- **Target users:** Developers (cleaner codebase, less ambiguity about what's real).

## Scope
- **In-scope:**
  - Delete frontend API proxy routes whose backend endpoints were removed in PRD-01
  - Delete frontend API proxy routes for features that have no UI
  - Delete dead files from `app/stores/` directory (preserving `detailPanelStore.ts` which IS imported)
  - Delete stale root-level AI-generated markdown reports
  - Remove any dead imports caused by these deletions
- **Out-of-scope:**
  - Modifying components or the main store (`store.ts`)
  - Changing routing or page structure
  - Backend changes (covered by PRD-01)
  - Simplifying `store.ts` (covered by PRD-05)

## Current State (Evidence)

### Dormant Proxy Route Candidates (second-pass corrected)

These routes currently have no verified frontend callers, but not all corresponding backend routes are deleted in PRD-01:

| Frontend Proxy Route | Backend Route | Second-pass status |
|---------------------|---------------|--------------------|
| `app/api/signals/route.ts` | `routes/signals.py` | Candidate for deletion (aligns with PRD-01 candidate backend delete) |
| `app/api/signals/preferences/route.ts` | `routes/signals.py` | Candidate for deletion (aligns with PRD-01 candidate backend delete) |
| `app/api/stripe-connect/earnings/route.ts` | `routes/stripe_connect.py` | Candidate for deletion only if merchant/seller flow confirms unused |
| `app/api/notifications/route.ts` | `routes/notifications.py` | Candidate for deletion only if no UI/tests/internal callers |
| `app/api/notifications/count/route.ts` | `routes/notifications.py` | Candidate for deletion only if no UI/tests/internal callers |

### Dead Proxy Routes for Features With No UI

These proxy routes exist but no frontend component ever calls them:

| Frontend Proxy Route | Evidence of Death |
|---------------------|-------------------|
| `app/api/seller/bookmarks/route.ts` | No confirmed frontend caller in current UI; verify before deletion |
| `app/api/checkout/batch/route.ts` | No batch checkout UI exists |
| `app/api/merchants/connect/onboard/route.ts` | No Stripe Connect onboarding UI |
| `app/api/merchants/connect/status/route.ts` | No Stripe Connect status UI |

### Dead `stores/` Directory Files (5 of 7 files)

| File | LOC | Status |
|------|-----|--------|
| `stores/detailPanelStore.ts` | 121 | **KEEP** — imported by `OfferTile.tsx` and `TileDetailPanel.tsx` |
| `stores/index.ts` | 137 | **DELETE** — unified store wrapper, not imported by any component |
| `stores/rows.ts` | 202 | **DELETE** — row state logic, not imported by any component |
| `stores/search.ts` | 124 | **DELETE** — search state logic, not imported by any component |
| `stores/types.ts` | 111 | **DELETE** — type definitions, check if `detailPanelStore.ts` imports from it |
| `stores/ui.ts` | 26 | **DELETE** — UI state, not imported by any component |
| `stores/utils.ts` | 118 | **DELETE** — utility functions, check if `detailPanelStore.ts` imports from it |

**Action:** Before deleting `types.ts` and `utils.ts`, verify that `detailPanelStore.ts` doesn't import from them. If it does, either inline the needed types/utils into `detailPanelStore.ts` or keep the dependency.

### Stale Root-Level Markdown Reports

| File | Purpose | Evidence of Staleness |
|------|---------|----------------------|
| `ARCHITECTURE_ANALYSIS.md` | AI-generated analysis | Stale — superseded by `SIMPLIFICATION_PLAN.md` |
| `CODE_QUALITY_AUDIT.md` | AI-generated audit | Stale — one-time report, never updated |
| `CODE_REVIEW_HIGHLIGHTS.md` | AI-generated review | Stale — one-time report |
| `CODE_REVIEW_REPORT.md` | AI-generated review | Stale — one-time report |
| `CODE_REVIEW_SUMMARY.md` | AI-generated review | Stale — one-time report |
| `DEAD_CODE_REMOVAL_ANALYSIS.md` | AI-generated analysis | Stale — superseded by this PRD |
| `SECURITY_AUDIT_REPORT.md` | AI-generated audit | Stale — one-time report |
| `SECURITY_ACTION_PLAN.md` | AI-generated plan | Stale — never executed |
| `SECRETS_MANAGEMENT.md` | AI-generated doc | Stale — one-time report |

**Keep:** `README.md`, `DEPLOYMENT.md`, `TROUBLESHOOTING.md`, `CLAUDE.md`, `SIMPLIFICATION_PLAN.md`

## User Flow
No user flow change. This effort only removes code that is never reached by any UI.

## Business Requirements

### Authentication & Authorization
- No auth changes

### Monitoring & Visibility
- Run `next build` to verify no broken imports
- Run frontend tests

### Performance Expectations
- Marginal build time improvement (fewer files to compile)
- No runtime change

### Data Requirements
- No data changes

### UX & Accessibility
- No UI changes

### Privacy, Security & Compliance
- Removing dead proxy endpoints reduces attack surface

## Deletion Manifest

### Step 1: Delete verified-unused proxy route directories

```
VERIFY FIRST (grep + test callers):
- apps/frontend/app/api/signals/
- apps/frontend/app/api/stripe-connect/
- apps/frontend/app/api/notifications/
- apps/frontend/app/api/seller/bookmarks/
- apps/frontend/app/api/checkout/batch/
- apps/frontend/app/api/merchants/connect/

DELETE only the routes confirmed to have zero callers and no active backend dependency.
```

### Step 2: Delete dead `stores/` files

```
VERIFY: grep -rn "from.*stores/" apps/frontend/app/ (find all imports)
  - Expected: only OfferTile.tsx and TileDetailPanel.tsx importing detailPanelStore

DELETE: apps/frontend/app/stores/index.ts     (137 LOC)
DELETE: apps/frontend/app/stores/rows.ts      (202 LOC)
DELETE: apps/frontend/app/stores/search.ts    (124 LOC)
DELETE: apps/frontend/app/stores/ui.ts        (26 LOC)

VERIFY: detailPanelStore.ts imports — if it imports from types.ts or utils.ts, 
        inline those dependencies before deleting

DELETE: apps/frontend/app/stores/types.ts     (111 LOC) — if safe
DELETE: apps/frontend/app/stores/utils.ts     (118 LOC) — if safe
```

### Step 3: Delete stale root-level markdown reports

```
DELETE: ARCHITECTURE_ANALYSIS.md
DELETE: CODE_QUALITY_AUDIT.md
DELETE: CODE_REVIEW_HIGHLIGHTS.md
DELETE: CODE_REVIEW_REPORT.md
DELETE: CODE_REVIEW_SUMMARY.md
DELETE: DEAD_CODE_REMOVAL_ANALYSIS.md
DELETE: SECURITY_AUDIT_REPORT.md
DELETE: SECURITY_ACTION_PLAN.md
DELETE: SECRETS_MANAGEMENT.md
```

### Step 4: Verify

```
cd apps/frontend && npx next build   # must succeed
cd apps/frontend && npm test          # must pass
```

## Dependencies
- **Upstream:** None required. Can run in parallel with PRD-01 as long as each proxy deletion is gated by verified caller analysis.
- **Downstream:** PRD-05 (Simplify Frontend State) — benefits from having the dead `stores/` files gone, reducing confusion about which store is canonical.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| A "dead" proxy route is actually called by a component we missed | High | `grep -rn` for every route path in all `.tsx`/`.ts` files before deletion |
| `detailPanelStore.ts` imports from a file we're deleting | Medium | Verify imports before deleting `types.ts` and `utils.ts`; inline if needed |
| Root-level MD deletion confuses team members who reference them | Low | These are stale AI reports; the analysis is captured in `SIMPLIFICATION_PLAN.md` and this PRD set |
| `next build` fails after deletion | Medium | Run build after each step, not just at the end |

## Acceptance Criteria (Business Validation)
- [ ] Candidate proxy routes were audited; only verified-unused routes were deleted
- [ ] 5-6 dead `stores/` files deleted (index, rows, search, ui, and conditionally types + utils)
- [ ] `detailPanelStore.ts` still works (imported by `OfferTile.tsx` and `TileDetailPanel.tsx`)
- [ ] 9 stale root-level MD files deleted
- [ ] `next build` succeeds with zero errors
- [ ] Frontend tests pass
- [ ] Manual smoke test: login → chat → tiles render → like → click offer

## Traceability
- **Parent PRD:** `docs/prd/simplification/parent.md`
- **Analysis:** `SIMPLIFICATION_PLAN.md` — Problem 4: Dead Feature Sprawl, Problem 5: Two Competing State Stores

---
**Note:** Technical implementation decisions are made during /plan and /task.
