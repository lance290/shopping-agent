# PRD: Notification System

**Status:** Not built — cross-cutting dependency  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P1  
**Origin:** GAP-ANALYSIS.md ("No notification system at all"), PRD 04 critical dependency, PRD 12 R2 assumption

---

## Problem Statement

Multiple Phase 4 PRDs assume a notification system exists, but none define or own one. Without notifications, the two-sided marketplace loop is broken:

- **Sellers** don't know when a matching RFP appears (PRD 04 gap)
- **Buyers** don't know when a seller quote arrives (PRD 04 gap)
- **Buyers** aren't notified when vendor outreach expires (PRD 12 R2)
- **Viral flywheel** can't prompt sellers to become buyers (PRD 06 gap)

**Current state:** Zero notification infrastructure. No in-app badges, no email digests, no push notifications.

---

## Requirements

### R1: Notification Model (P0)

Store notifications for any user.

```python
class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    type: str  # "quote_received", "outreach_expired", "rfp_match", "deal_closed", etc.
    title: str
    body: str
    link: Optional[str] = None  # Deep link (e.g., "/rows/42")
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Acceptance criteria:**
- [ ] `Notification` model created with Alembic migration
- [ ] Supports any notification type via `type` string
- [ ] `link` field enables deep-linking to relevant page
- [ ] `read` flag for dismissal

### R2: Backend Notification API (P0)

Endpoints for reading and managing notifications.

**Endpoints:**
- `GET /notifications` — List notifications for current user (paginated, newest first)
- `PATCH /notifications/{id}/read` — Mark as read
- `POST /notifications/read-all` — Mark all as read
- `GET /notifications/unread-count` — Return count of unread notifications

**Acceptance criteria:**
- [ ] All endpoints require auth
- [ ] Paginated with `limit`/`offset`
- [ ] Unread count endpoint returns integer (for badge)

### R3: Notification Triggers (P1)

Hook into existing flows to create notifications.

| Trigger | Recipient | Type | When |
|---------|-----------|------|------|
| Seller quote submitted | Buyer (row owner) | `quote_received` | `SellerQuote` created |
| Outreach expired | Buyer (row owner) | `outreach_expired` | Outreach timeout (PRD 12 R1) |
| RFP matches merchant category | Seller (merchant) | `rfp_match` | Row created with matching category |
| Deal closed | Both parties | `deal_closed` | `DealHandoff.status` → "closed" |
| Bid selected | Seller | `bid_selected` | `Bid.is_selected` set to true |

**Acceptance criteria:**
- [ ] Each trigger creates a `Notification` row
- [ ] Triggers are in service layer (not inline in routes)
- [ ] New triggers can be added without modifying notification infrastructure

### R4: Frontend Notification Bell (P1)

In-app notification UI.

**Implementation:**
- Notification bell icon in the app header (next to user menu)
- Badge showing unread count
- Dropdown showing recent notifications
- Click notification → navigate to `link`
- "Mark all read" button

**Acceptance criteria:**
- [ ] Bell icon visible on all authenticated pages
- [ ] Unread count badge (red dot or number)
- [ ] Clicking a notification marks it read and navigates
- [ ] Polls `/notifications/unread-count` every 30s (or uses SSE)

### R5: Email Notification Digest (P2)

Daily email summary of unread notifications.

**Acceptance criteria:**
- [ ] Users can opt in/out of email notifications (default: on)
- [ ] Daily digest sent at 9am user's timezone (or UTC)
- [ ] Only sent if there are unread notifications
- [ ] Uses existing email service (Resend/SendGrid)
- [ ] Unsubscribe link in footer

---

## Technical Implementation

### Backend

**New files:**
- `apps/backend/models.py` — Add `Notification` model
- `apps/backend/routes/notifications.py` — CRUD endpoints
- `apps/backend/services/notify.py` — `send_notification(user_id, type, title, body, link)` helper

**Modified files:**
- `apps/backend/routes/quotes.py` — Trigger `quote_received` on quote submission
- `apps/backend/routes/rows.py` — Trigger `rfp_match` on row creation (match against merchant categories)
- `apps/backend/main.py` — Register notifications router

### Frontend

**New files:**
- `apps/frontend/app/components/NotificationBell.tsx` — Bell + dropdown
- `apps/frontend/app/api/notifications/route.ts` — Proxy route

**Modified files:**
- `apps/frontend/app/components/Board.tsx` — Add `NotificationBell` to header

---

## Dependencies

- Phase 4 PRD 04 (seller tiles) — notification triggers for quote/RFP matching
- Phase 4 PRD 12 (vendor unresponsiveness) — notification trigger for outreach expiry

---

## Effort Estimate

- **R1-R2:** Small (1 day — model + CRUD endpoints)
- **R3:** Medium (1-2 days — hook into existing flows)
- **R4:** Medium (1 day — frontend bell + dropdown)
- **R5:** Small (half-day — email digest job)
