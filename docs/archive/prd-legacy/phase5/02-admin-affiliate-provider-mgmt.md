# PRD: Admin Affiliate & Provider Management

**Status:** Not built  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P2  
**Origin:** `PRD-buyanything.md` Section 12 ("Admin Strategy")

---

## Problem Statement

The original PRD requires: *"Manage provider keys/config. Manage domain → affiliate handler rules. Inspect clickout logs and revenue attribution."*

Affiliate handlers are configured via environment variables and hardcoded domain mappings in `affiliate.py`. There is no UI for an operator to:
- See which handlers are active/configured
- Add or modify domain → handler mappings
- Toggle handlers on/off without a deploy
- View per-handler clickout performance
- Manage search provider API keys or enable/disable providers

**Current state:**
- `LinkResolver.list_handlers()` exists but isn't exposed via any admin endpoint or UI.
- Provider configuration is hardcoded in `SourcingRepository.__init__()` based on env vars.
- Admin dashboard shows clickout counts but not per-handler breakdowns.

---

## Requirements

### R1: Admin Affiliate Dashboard (P1)

View all affiliate handlers and their configuration status.

**Acceptance criteria:**
- [ ] `GET /admin/affiliate/handlers` endpoint returns handler list with status
- [ ] Admin UI page at `/admin/affiliate` showing: handler name, domains, configured (yes/no), clickout count, estimated revenue
- [ ] Each handler shows whether its env var is set (without exposing the value)

### R2: Domain → Handler Rule Management (P2)

Allow admin to add custom domain → handler mappings without code changes.

**Acceptance criteria:**
- [ ] `AffiliateRule` model: `domain`, `handler_name`, `priority`, `active`, `created_at`
- [ ] `POST /admin/affiliate/rules` — Create rule
- [ ] `PATCH /admin/affiliate/rules/{id}` — Update rule
- [ ] `DELETE /admin/affiliate/rules/{id}` — Delete rule
- [ ] `LinkResolver` checks DB rules before hardcoded domain map
- [ ] Admin UI for CRUD on rules

### R3: Provider Configuration Dashboard (P2)

View and manage search provider status.

**Acceptance criteria:**
- [ ] `GET /admin/providers` endpoint returns provider list with: name, configured (yes/no), last search time, result count (7d), error rate
- [ ] Admin UI page at `/admin/providers`
- [ ] Shows which providers are active vs disabled vs missing API keys

### R4: Clickout Log Inspector (P2)

View recent clickout events with filtering.

**Acceptance criteria:**
- [ ] `GET /admin/clickouts` endpoint with filters: `handler_name`, `merchant_domain`, `date_range`, `user_id`
- [ ] Paginated results with: timestamp, user, merchant, handler, affiliate tag, row link
- [ ] Admin UI table at `/admin/clickouts`

---

## Technical Implementation

### Backend

**New models:**
- `AffiliateRule(domain, handler_name, priority, active, created_at)`

**New/modified files:**
- `apps/backend/routes/admin.py` — Add affiliate, provider, clickout endpoints
- `apps/backend/affiliate.py` — `LinkResolver` checks `AffiliateRule` table before hardcoded map

### Frontend
- `apps/frontend/app/admin/affiliate/page.tsx` — Handler + rules management
- `apps/frontend/app/admin/providers/page.tsx` — Provider status
- `apps/frontend/app/admin/clickouts/page.tsx` — Clickout log viewer

---

## Dependencies

- Phase 4 PRD 00 (revenue) — affiliate tags must be configured first
- Phase 4 PRD 09 (analytics) — clickout metrics feed into this dashboard

---

## Effort Estimate

- **R1:** Small (1 day — endpoint + basic UI)
- **R2:** Medium (1-2 days — model + CRUD + resolver integration)
- **R3:** Small (half-day — read-only dashboard)
- **R4:** Medium (1 day — filtered log viewer)
