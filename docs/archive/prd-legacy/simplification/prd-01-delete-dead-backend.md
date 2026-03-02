# PRD-01: Delete Dead Backend Code

## Business Outcome
- **Measurable impact:** Remove only **verified-dead** backend code and avoid regressions from deleting currently wired runtime paths. This pass targets clearly unused modules first, then defers active-but-low-value code to later PRDs with explicit replacement plans.
- **Success criteria:** Verified-dead files deleted; `main.py` router registrations updated only for routes intentionally removed; no runtime behavior regressions in seller/auth/checkout/admin flows; tests pass.
- **Target users:** Developers (cleaner codebase, fewer misleading code paths).

## Scope
- **In-scope:**
  - Delete dead route files and unregister them from `main.py`
  - Delete dead service files
  - Remove dead model columns (Alembic migration)
  - Delete tests that exclusively test deleted code
  - Update any remaining import sites
- **Out-of-scope:**
  - Deleting entire models/tables (that's PRD-03 for vendor unification)
  - Modifying frontend code (that's PRD-02)
  - Changing any actively used logic

## Current State (Evidence)

### Dead/Dormant Route Candidates (second-pass corrected)

| File | LOC | Status after second-pass verification |
|------|-----|--------------------------------------|
| `routes/contracts.py` | 184 | Candidate for deletion (no confirmed active UI/automation call path) |
| `routes/signals.py` | 190 | Candidate for deletion (no confirmed frontend usage) |
| `routes/stripe_connect.py` | 218 | Candidate for deletion, but overlaps with `routes/merchants.py` Connect endpoints |
| `routes/notifications.py` | 147 | **Do not delete in PRD-01** — route module exports `create_notification`, imported by `routes/auth.py` and `routes/seller.py` |
| `routes/webhooks.py` | 101 | **Do not delete in PRD-01** — router is registered in `main.py` |

**Registered in `main.py`:**
```python
# main.py:42
from routes.contracts import router as contracts_router
# main.py:45
from routes.notifications import router as notifications_router
# main.py:46
from routes.stripe_connect import router as stripe_connect_router
# main.py:47
from routes.signals import router as signals_router
# main.py:150
app.include_router(contracts_router)
# main.py:153
app.include_router(notifications_router)
# main.py:154
app.include_router(stripe_connect_router)
# main.py:155
app.include_router(signals_router)
```

`webhooks.py` — verify if registered in `main.py`; if not, it's already unreachable.

### Dead Service Files (second-pass corrected)

| File | LOC | Status after second-pass verification |
|------|-----|--------------------------------------|
| `services/reputation.py` | 179 | Verified dead at runtime (tests only) |
| `services/vendor_discovery.py` | 217 | Verified dead at runtime (tests only) |
| `services/wattdata_mock.py` | 25 | Verified dead |
| `services/fraud.py` | 70 | **Active** — imported by `routes/clickout.py`, contributes to `ClickoutEvent.is_suspicious` and admin metrics |
| `services/outreach_monitor.py` | 150 | **Active** — used by `/admin/outreach/check-expired` |

### Model Column Cleanup (second-pass corrected)

**Columns previously marked dead but currently active in backend logic (defer):**
- Bid scoring columns (`combined_score`, `relevance_score`, `price_score`, `quality_score`, `diversity_bonus`, `source_tier`) are written by `sourcing/service.py` and used by ranking/fallback logic.
- `ClickoutEvent.is_suspicious` is computed in `routes/clickout.py` and used by admin metrics.
- ShareLink metric fields are used by `/admin/growth` and `/api/shares/{token}/metrics`.

**User model — 1 dead column:**
- `trust_level: str` (default "standard", never read or modified by any route)

**Safe low-risk candidate in this PRD:**
- `User.trust_level` (appears unused outside tests/migration artifacts)

**Merchant model — dead columns (model itself is dead but deletion is PRD-03):**
- `verification_level`, `reputation_score`, `stripe_account_id`, `stripe_onboarding_complete` — defer to PRD-03

### Root-Level Dead Files

| File | LOC | Evidence |
|------|-----|----------|
| `sourcing.py` | 778 | Complete duplicate of `sourcing/repository.py`. Imported by 3 files that can be pointed to `sourcing/` instead. **Deletion deferred to PRD-06** (sourcing consolidation). |

## User Flow
No user flow change. This effort only removes code that is never reached.

## Business Requirements

### Authentication & Authorization
- No auth changes

### Monitoring & Visibility
- After deletion, verify `main.py` starts without import errors
- Run full test suite

### Performance Expectations
- Marginal improvement in startup time (fewer router registrations)
- No runtime performance change (dead code was never executed)

### Data Requirements
- **Alembic migration required** to drop dead columns from `bid`, `user`, `clickout_event`, `share_link` tables
- Migration must have `downgrade()` that re-adds the columns (reversible)
- Column drops are non-destructive — all are `Optional` with defaults

### UX & Accessibility
- No UI changes

### Privacy, Security & Compliance
- Removing dead endpoints reduces attack surface

## Deletion Manifest

### Step 1: Delete route files + unregister from `main.py` (revised)

```
DELETE: apps/backend/routes/contracts.py      (184 LOC)
DELETE: apps/backend/routes/signals.py        (190 LOC)

DEFER (do not delete in PRD-01):
- apps/backend/routes/stripe_connect.py
- apps/backend/routes/notifications.py
- apps/backend/routes/webhooks.py

EDIT: apps/backend/main.py
  - Remove import/include lines for contracts_router and signals_router only
  - Leave notifications_router, stripe_connect_router, webhooks_router intact in PRD-01
```

### Step 2: Delete service files (revised)

```
DELETE: apps/backend/services/reputation.py       (179 LOC)
DELETE: apps/backend/services/vendor_discovery.py (217 LOC)
DELETE: apps/backend/services/wattdata_mock.py    (25 LOC)

DEFER (active runtime usage):
- apps/backend/services/fraud.py
- apps/backend/services/outreach_monitor.py
```

### Step 3: Remove callsites for deleted services (revised)

```
EDIT: remove import sites that reference deleted files only:
  - any remaining imports of services.reputation
  - any remaining imports of services.vendor_discovery
  - any remaining imports of services.wattdata_mock
```

### Step 4: Optional low-risk model column cleanup

```
EDIT: apps/backend/models/auth.py
  - Remove: trust_level from User (only if grep confirms no runtime use)

CREATE: apps/backend/alembic/versions/xxxx_drop_user_trust_level.py (optional)
  - drop only verified-unused columns in this PRD
  - defer scoring/clickout/share metric column removals to later PRDs
```

### Step 5: Delete dead tests

```
EDIT: apps/backend/tests/test_phase4_endpoints.py
  - Remove tests that import from services.reputation
  - Keep fraud tests (service is still active)

EDIT: apps/backend/tests/test_phase3_endpoints.py
  - Remove tests that import from services.vendor_discovery
```

## Dependencies
- **Upstream:** None (can run in parallel with PRD-00 and PRD-02)
- **Downstream:** PRD-03 (Vendor Model) removes entire models/tables; this PRD only removes columns

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Deleted route was silently used by a background job | High | `grep -rn` for every route path and function name before deletion |
| Alembic migration fails on Railway (column doesn't exist) | Medium | Use `op.drop_column()` with `if_exists` guard or inspect before drop |
| Test file imports from deleted module | Medium | Run `pytest` after each deletion step to catch immediately |
| Admin endpoint for outreach monitor was occasionally used | Low | Check Railway logs for hits on `/admin/outreach/check-expired` in last 30 days |

## Acceptance Criteria (Business Validation)
- [ ] 2 route files deleted: `contracts.py`, `signals.py`
- [ ] 3 service files deleted: `reputation.py`, `vendor_discovery.py`, `wattdata_mock.py`
- [ ] `main.py` has no imports or `include_router` calls for deleted routes
- [ ] `notifications.py`, `webhooks.py`, `stripe_connect.py`, `fraud.py`, `outreach_monitor.py` remain intact in PRD-01
- [ ] Optional low-risk migration (e.g., `User.trust_level`) applies cleanly if executed
- [ ] `python -c "from main import app"` succeeds (no import errors)
- [ ] All remaining tests pass
- [ ] Backend starts and `/health` returns 200

## Traceability
- **Parent PRD:** `docs/prd/simplification/parent.md`
- **Analysis:** `SIMPLIFICATION_PLAN.md` — Phase 1: Delete Dead Code, Problem 4: Dead Feature Sprawl

---
**Note:** Technical implementation decisions are made during /plan and /task.
