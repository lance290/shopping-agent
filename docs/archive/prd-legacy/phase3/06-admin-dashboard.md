# PRD: Admin Dashboard

**Phase:** 3 — Closing the Loop  
**Priority:** P2  
**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Parent:** [Phase 3 Parent](./parent.md)

---

## 1. Problem Statement

Backend admin routes exist (`routes/admin.py`) but there is **no frontend admin UI**. Operators have no visibility into:

- System health and usage metrics
- User activity and registration trends
- Outreach performance (emails sent, opened, quoted)
- Clickout and affiliate revenue tracking
- Merchant registry management
- Bug report triage

Today, all operational insight requires direct database queries or API calls via curl. This is unsustainable as the platform scales.

---

## 2. Solution Overview

Build an **Admin Dashboard** at `/admin` accessible only to users with `is_admin=true`. The dashboard provides:

1. **Overview** — Key metrics at a glance (users, rows, bids, clickouts, purchases).
2. **Users** — User list with search, registration source, activity summary.
3. **Marketplace Activity** — Rows, bids, outreach events, quotes, deals.
4. **Monetization** — Clickout events, affiliate handler breakdown, purchase events, GMV.
5. **Merchants** — Registry management (approve, suspend, view profiles).
6. **Bug Reports** — Triage queue with status management.

---

## 3. Scope

### In Scope
- `/admin` route with role-based access control (is_admin check)
- Overview dashboard with summary cards
- User management table
- Marketplace activity views (rows, outreach, quotes)
- Clickout/revenue analytics
- Merchant management (approve/suspend)
- Bug report triage

### Out of Scope
- Real-time dashboards / WebSocket updates (Phase 4)
- A/B test management (Phase 4)
- Financial reporting / CSV export (Phase 4)
- Custom admin roles / RBAC beyond is_admin (Phase 4)

---

## 4. User Stories

**US-01:** As an admin, I want to see a summary dashboard so I can understand platform health at a glance.

**US-02:** As an admin, I want to view all registered users and their activity so I can identify power users and issues.

**US-03:** As an admin, I want to see outreach metrics (sent, opened, quoted) so I can measure seller engagement.

**US-04:** As an admin, I want to see clickout volume and affiliate handler distribution so I can optimize monetization.

**US-05:** As an admin, I want to approve or suspend merchant registrations so I can maintain marketplace quality.

**US-06:** As an admin, I want to triage bug reports so I can prioritize fixes.

---

## 5. Acceptance Criteria

| ID | Criteria |
|----|----------|
| AC-01 | Only users with `is_admin=true` can access `/admin`. Non-admins see a 403 or redirect. |
| AC-02 | Overview page shows: total users, total rows, total bids, total clickouts, total purchases, total GMV. |
| AC-03 | Users page shows a paginated table of all users with email, created_at, row count, last activity. |
| AC-04 | Marketplace page shows outreach events grouped by status (sent/opened/clicked/quoted). |
| AC-05 | Monetization page shows clickout events grouped by handler_name with counts. |
| AC-06 | Merchants page lists all merchants with status badges and approve/suspend actions. |
| AC-07 | Bug reports page shows reports sorted by severity with status management. |

---

## 6. Technical Design

### 6.1 Backend: Admin Endpoints

Extend existing `routes/admin.py`:

**GET /admin/stats**
```json
{
  "users": { "total": 150, "last_7_days": 23 },
  "rows": { "total": 420, "active": 380 },
  "bids": { "total": 3200 },
  "clickouts": { "total": 890, "last_7_days": 120 },
  "purchases": { "total": 15, "gmv": 4500.00 },
  "merchants": { "total": 8, "pending": 3 },
  "outreach": { "sent": 200, "opened": 80, "quoted": 12 },
  "bugs": { "total": 25, "open": 8 }
}
```

**GET /admin/users?page=1&per_page=50&search=email**

**GET /admin/clickouts?page=1&per_page=50&handler=amazon**

**GET /admin/outreach?page=1&per_page=50&status=sent**

**PATCH /admin/merchants/{id}** — Update merchant status (approve/suspend).

**PATCH /admin/bugs/{id}** — Update bug report status.

### 6.2 Frontend: Admin Pages

**`/admin/page.tsx`** — Dashboard shell with sidebar navigation:
- Overview (default)
- Users
- Marketplace
- Monetization
- Merchants
- Bug Reports

Each section is a tab or sub-page with a data table and summary cards.

### 6.3 Auth Guard

```typescript
// middleware or page-level check
const user = await getCurrentUser();
if (!user?.is_admin) {
  redirect('/');
}
```

### 6.4 UI Components

Reuse existing design system:
- `Card` for metric summaries
- Tables with pagination for list views
- Status badges (consistent with existing `DealStatus.tsx` patterns)
- Simple bar/count visualizations (no charting library needed for v1)

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Admin can answer "how many users signed up this week?" | Without SQL queries |
| Admin can approve a merchant | In <3 clicks |
| Admin can triage a bug report | In <3 clicks |
| Page load time for admin dashboard | <2 seconds |

---

## 8. Implementation Checklist

- [ ] Extend `routes/admin.py` with stats, users, clickouts, outreach, merchant management endpoints
- [ ] Create `/admin/page.tsx` dashboard shell
- [ ] Create Overview section with summary cards
- [ ] Create Users table with search and pagination
- [ ] Create Marketplace activity view
- [ ] Create Monetization / clickout analytics view
- [ ] Create Merchants management view with approve/suspend
- [ ] Create Bug Reports triage view
- [ ] Add admin auth guard (is_admin check)
- [ ] Add frontend API proxy routes for admin endpoints
- [ ] Write tests for admin endpoints
