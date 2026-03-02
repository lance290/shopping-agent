# Implementation Plan: PRD 01 — Support Tickets & Issue Resolution

**Status:** Draft — awaiting approval  
**Priority:** P0 (build after PRD 00 + 04, or in parallel)  
**Estimated effort:** 2 days  
**Depends on:** PRD 00 (contact form routes to this), email service (exists)

---

## Goal

When a user has a problem, give them a way to file a ticket, track its status, and get a response. Give admins a queue to manage, assign, and resolve tickets with SLA tracking.

---

## Current State

- **Zero ticket infrastructure.** Bug reports go to GitHub Issues via `ReportBugModal`.
- No `SupportTicket` model, no admin support queue, no user-facing ticket list.
- Email service exists (`services/email.py`) and can send transactional emails.
- `Notification` model exists and can push in-app notifications.
- `AuditLog` exists for tracking admin actions.

---

## Build Order

### Phase A: Backend Models + Migration (30 min)

**File: `apps/backend/models.py`** — add two models:

```python
class SupportTicket(SQLModel, table=True):
    __tablename__ = "support_ticket"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_number: str = Field(unique=True, index=True)  # "SUP-00001"
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    user_email: str
    
    category: str = Field(index=True)  # getting_started, buying, selling, payments, account, dispute, bug, other
    priority: str = "medium"  # low, medium, high, urgent
    status: str = "open"  # open, in_progress, waiting_on_user, resolved, closed
    
    subject: str
    description: str
    
    # Assignment
    assigned_to: Optional[int] = Field(default=None, foreign_key="user.id")
    escalated: bool = False
    escalated_at: Optional[datetime] = None
    
    # Resolution
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Context links (optional — tie to specific entities)
    row_id: Optional[int] = Field(default=None, foreign_key="row.id")
    merchant_id: Optional[int] = Field(default=None, foreign_key="merchant.id")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TicketMessage(SQLModel, table=True):
    __tablename__ = "ticket_message"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="support_ticket.id", index=True)
    sender_id: int = Field(foreign_key="user.id")
    sender_role: str  # "user" or "admin"
    body: str
    is_internal: bool = False  # Internal notes only visible to admins
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

Ticket number generation: sequence-based via SQL `nextval` or Python counter from max existing ID.

**Migration:** Create `support_ticket` and `ticket_message` tables.

---

### Phase B: Backend Routes (2-3 hours)

**New file: `apps/backend/routes/support.py`**

#### User-facing endpoints:

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /support/tickets` | User (or anonymous via email) | Create ticket. Body: `{ subject, description, category, user_email }` |
| `GET /support/tickets` | User | List my tickets (by `user_id`), paginated |
| `GET /support/tickets/{id}` | User (own) or Admin | Ticket detail + messages |
| `POST /support/tickets/{id}/messages` | User (own) or Admin | Reply to ticket |

#### Admin endpoints:

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /admin/support/tickets` | Admin | Full queue. Filters: `?status=`, `?priority=`, `?category=`, `?assigned_to=` |
| `PATCH /admin/support/tickets/{id}` | Admin | Update status, priority, assignment. Body: `{ status?, priority?, assigned_to? }` |
| `POST /admin/support/tickets/{id}/messages` | Admin | Reply (user-visible) or internal note (`is_internal: true`) |
| `GET /admin/support/stats` | Admin | Volume, avg resolution time, SLA compliance |

#### Ticket creation logic:
1. Generate `ticket_number` = `"SUP-" + str(max_id + 1).zfill(5)`
2. If user is authenticated, link `user_id`
3. Send confirmation email to `user_email`
4. Send notification email to admin
5. Create in-app notification for admin users

#### Status transition rules:
- `open` → `in_progress` (admin assigns/starts working)
- `open` or `in_progress` → `waiting_on_user` (admin asked for info)
- `waiting_on_user` → `in_progress` (user replied)
- `in_progress` → `resolved` (admin resolves)
- `resolved` → `closed` (auto after 7 days or user confirms)
- Any → `escalated` (SLA breach or manual escalation)

**Register in `main.py`.**

---

### Phase C: Contact Form Integration (15 min)

**File: `apps/backend/routes/help.py`** — update `POST /help/contact`:

Change from "send email to admin" to "create SupportTicket + send email":
```python
@router.post("/help/contact")
async def submit_contact_form(body: ContactForm, ...):
    # Create support ticket
    ticket = SupportTicket(
        ticket_number=await generate_ticket_number(session),
        user_id=auth_session.user_id if auth_session else None,
        user_email=body.email,
        category=body.category,
        subject=f"Contact form: {body.category}",
        description=body.description,
    )
    session.add(ticket)
    await session.commit()
    
    # Send confirmation email
    await send_ticket_confirmation_email(body.email, ticket.ticket_number)
    
    return {"ticket_number": ticket.ticket_number, "message": "We've received your message."}
```

---

### Phase D: Email Notifications (30 min)

**File: `apps/backend/services/email.py`** — add functions:

| Function | Trigger | Content |
|----------|---------|---------|
| `send_ticket_confirmation_email()` | Ticket created | "Your support request SUP-XXXXX has been received" |
| `send_ticket_reply_email()` | Admin replies | "Your support request has been updated" |
| `send_ticket_escalation_email()` | SLA breach | "URGENT: Ticket SUP-XXXXX needs attention" (to admin) |

---

### Phase E: SLA Checker (30 min)

**New file: `apps/backend/services/support_sla.py`**

Simple function (callable via admin endpoint or future cron):

```python
async def check_sla_breaches(session: AsyncSession):
    """Find tickets that have breached their SLA and escalate them."""
    now = datetime.utcnow()
    
    # First response SLA: 24 hours for medium priority
    sla_rules = {
        "urgent": timedelta(hours=2),
        "high": timedelta(hours=4),
        "medium": timedelta(hours=24),
        "low": timedelta(hours=48),
    }
    
    open_tickets = await session.exec(
        select(SupportTicket).where(
            SupportTicket.status == "open",
            SupportTicket.escalated == False,
        )
    )
    
    escalated = []
    for ticket in open_tickets.all():
        sla_window = sla_rules.get(ticket.priority, timedelta(hours=24))
        if now - ticket.created_at > sla_window:
            ticket.escalated = True
            ticket.escalated_at = now
            session.add(ticket)
            escalated.append(ticket.ticket_number)
    
    await session.commit()
    return escalated
```

Add admin endpoint: `POST /admin/support/check-sla` — triggers the check and returns escalated tickets.

---

### Phase F: Frontend — User Ticket Pages (1-2 hours)

**New file: `apps/frontend/app/help/tickets/page.tsx`**
- "My Support Requests" — list of user's tickets with status badges
- Each row: ticket number, subject, status, last updated
- Click → ticket detail

**New file: `apps/frontend/app/help/tickets/[id]/page.tsx`**
- Ticket detail: subject, description, status badge
- Message thread (chat-style, chronological)
- Reply form at bottom
- Status timeline on the side (or top for mobile)

**Update: `apps/frontend/app/help/contact/page.tsx`**
- After successful submission, show ticket number and link to `/help/tickets/{id}`

---

### Phase G: Frontend — Admin Support Queue (1 hour)

**New file: `apps/frontend/app/admin/support/page.tsx`**
- Table: ticket #, subject, user email, category, priority, status, assigned to, age
- Filters: status dropdown, priority dropdown, category dropdown
- Click row → ticket detail

**New file: `apps/frontend/app/admin/support/[id]/page.tsx`**
- Full ticket detail with message thread
- Admin controls: status dropdown, priority dropdown, assign dropdown
- Reply form (with "internal note" checkbox)
- Resolution form (appears when marking as resolved)

---

### Phase H: Frontend Proxy Routes (15 min)

| Route file | Method | Proxies to |
|-----------|--------|-----------|
| `app/api/support/tickets/route.ts` | GET, POST | `/support/tickets` |
| `app/api/support/tickets/[id]/route.ts` | GET, PATCH | `/support/tickets/{id}` |
| `app/api/support/tickets/[id]/messages/route.ts` | GET, POST | `/support/tickets/{id}/messages` |
| `app/api/admin/support/tickets/route.ts` | GET | `/admin/support/tickets` |
| `app/api/admin/support/tickets/[id]/route.ts` | PATCH | `/admin/support/tickets/{id}` |
| `app/api/admin/support/stats/route.ts` | GET | `/admin/support/stats` |

---

### Phase I: Tests (1 hour)

**New file: `apps/backend/tests/test_support_tickets.py`**

| # | Test | Expected |
|---|------|----------|
| 1 | Create ticket (authenticated) | 200, ticket_number returned |
| 2 | Create ticket (anonymous with email) | 200 |
| 3 | List my tickets | 200, only my tickets |
| 4 | Get ticket detail (own) | 200, messages included |
| 5 | Get ticket detail (other user's) | 403 |
| 6 | Reply to own ticket | 200, message added |
| 7 | Admin list all tickets | 200, full list |
| 8 | Admin filter by status | 200, filtered results |
| 9 | Admin update ticket status | 200, status changed |
| 10 | Admin assign ticket | 200, assigned_to set |
| 11 | Admin internal note | 200, is_internal=true |
| 12 | User can't see internal notes | 200, internal notes excluded |
| 13 | SLA breach detection | Overdue ticket gets escalated |
| 14 | Contact form creates ticket | 200, ticket created + email sent |
| 15 | Non-admin can't access admin queue | 403 |

---

## Files Changed Summary

| File | Change Type | Lines Est. |
|------|------------|-----------|
| `apps/backend/models.py` | Add `SupportTicket` + `TicketMessage` models | +40 |
| `apps/backend/routes/support.py` | **New file** — 8 endpoints | ~300 |
| `apps/backend/routes/help.py` | Update contact form to create ticket | ~15 modified |
| `apps/backend/services/email.py` | Add 3 email functions | +80 |
| `apps/backend/services/support_sla.py` | **New file** — SLA checker | ~60 |
| `apps/backend/main.py` | Register support router | +2 |
| `apps/backend/alembic/versions/p6_support_tickets.py` | **New file** — create tables | ~30 |
| `apps/backend/tests/test_support_tickets.py` | **New file** — 15 tests | ~350 |
| `apps/frontend/app/help/tickets/page.tsx` | **New file** — ticket list | ~100 |
| `apps/frontend/app/help/tickets/[id]/page.tsx` | **New file** — ticket detail | ~150 |
| `apps/frontend/app/help/contact/page.tsx` | Update to show ticket number | ~10 modified |
| `apps/frontend/app/admin/support/page.tsx` | **New file** — admin queue | ~150 |
| `apps/frontend/app/admin/support/[id]/page.tsx` | **New file** — admin detail | ~180 |
| Frontend proxy routes (6 files) | **New files** | ~90 |

**Total:** ~1,550 lines across 18 files (14 new, 4 modified)

---

## Sequencing Note

PRD 01 naturally follows PRD 00 (Help Center):
1. Build Help Center with contact form that sends email (PRD 00)
2. Build Support Tickets — contact form now creates tickets instead (PRD 01)
3. The user never sees the transition; the contact form URL stays the same
