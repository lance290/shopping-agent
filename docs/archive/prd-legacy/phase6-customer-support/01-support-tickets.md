# PRD 01: Support Tickets & Issue Resolution

**Phase:** 6 — Customer Support & Trust Infrastructure  
**Priority:** P0  
**Status:** Planning  
**Parent:** [Phase 6 Parent](./parent.md)

---

## Problem Statement

When users encounter problems — a broken checkout, a seller who doesn't respond, a confusing search result — they have **no way to get help**. The bug-report modal creates GitHub Issues for engineers, not support staff. There is no ticket system, no SLA tracking, no assignment, and no resolution workflow.

Without structured issue resolution:
- User problems go undetected and unresolved
- There is no data on what's breaking the user experience
- The team cannot prioritize fixes based on user pain
- Payment processors (Stripe) require documented support processes

---

## Solution Overview

Build a **support ticket system** that enables:

1. **Ticket creation** — Users submit structured requests (from help center contact form, in-app, or email)
2. **Ticket management** — Admin dashboard to view, assign, prioritize, and resolve tickets
3. **Status tracking** — Users can see their ticket status and receive updates
4. **SLA enforcement** — Automatic escalation if tickets aren't addressed within time limits
5. **Analytics** — Ticket volume, resolution time, category trends

---

## Scope

### In Scope
- `SupportTicket` model with full lifecycle (open → in_progress → waiting_on_user → resolved → closed)
- User-facing: submit ticket, view my tickets, reply to ticket
- Admin-facing: ticket queue, assignment, internal notes, resolution
- Email notifications: ticket created, status changed, reply received
- Basic SLA: auto-escalate if no response within 24 hours
- Ticket categories aligned with help center categories
- File attachments (screenshots, documents)

### Out of Scope
- Third-party helpdesk integration (Zendesk, Intercom) — build native first
- AI-powered ticket routing or auto-response
- Phone or live chat support channels
- Public ticket visibility (all tickets are private between user and support)

---

## User Stories

**US-01:** As a buyer, I want to submit a support ticket when I have a problem so that someone can help me resolve it.

**US-02:** As a seller, I want to check the status of my support request and reply with additional information.

**US-03:** As an admin, I want to see all open tickets sorted by priority and age so I can address the most urgent ones first.

**US-04:** As an admin, I want to assign tickets to team members and add internal notes so we can collaborate on resolution.

**US-05:** As a user, I want to receive email updates when my ticket status changes so I know when to check back.

---

## Business Requirements

### Authentication & Authorization
- **Ticket creation:** Authenticated users only (need user_id for tracking)
- **View own tickets:** Authenticated, own tickets only
- **Admin queue:** `require_admin` dependency
- **Reply to ticket:** Authenticated — user can reply to own tickets; admin can reply to any

### Data Requirements

**SupportTicket model:**
```
id, ticket_number (human-readable, e.g. "SUP-00142")
user_id (FK user), user_email
category: getting_started | buying | selling | payments | account | dispute | bug | other
priority: low | medium | high | urgent
status: open | in_progress | waiting_on_user | resolved | closed
subject, description (text)

# Assignment
assigned_to (FK user, nullable) — admin user handling this
escalated: bool (default false)
escalated_at: datetime (nullable)

# Resolution
resolution_notes (text, nullable)
resolved_at: datetime (nullable)
closed_at: datetime (nullable)

# Context links (optional — tie to specific entities)
row_id (FK row, nullable)
bid_id (FK bid, nullable)
purchase_event_id (FK purchase_event, nullable)
merchant_id (FK merchant, nullable)

# Attachments
attachment_urls: JSON array of S3/storage URLs

created_at, updated_at
```

**TicketMessage model:**
```
id, ticket_id (FK support_ticket)
sender_id (FK user) — user or admin
sender_role: user | admin
body (text)
is_internal: bool (default false) — internal notes visible only to admins
attachment_urls: JSON array
created_at
```

### SLA Rules

| Priority | First Response | Resolution Target |
|----------|---------------|-------------------|
| Urgent | 2 hours | 8 hours |
| High | 4 hours | 24 hours |
| Medium | 24 hours | 72 hours |
| Low | 48 hours | 1 week |

- Auto-escalate if first response SLA breached
- Email alert to admin team on escalation

### Performance
- Ticket creation < 500ms
- Ticket list (user) < 300ms
- Admin queue with filters < 500ms

---

## Technical Design

### Backend

**New file:** `routes/support.py`

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /support/tickets` | User | Create a new ticket |
| `GET /support/tickets` | User | List my tickets (paginated) |
| `GET /support/tickets/{id}` | User/Admin | Get ticket detail + messages |
| `POST /support/tickets/{id}/messages` | User/Admin | Reply to ticket |
| `PATCH /support/tickets/{id}` | Admin | Update status, priority, assignment |
| `GET /admin/support/tickets` | Admin | Full ticket queue with filters |
| `GET /admin/support/stats` | Admin | Ticket volume, avg resolution time, SLA compliance |

**New file:** `services/support_sla.py`
- Check for SLA breaches (run via cron or admin trigger)
- Auto-escalate overdue tickets
- Send notification emails

### Frontend

| Page | Description |
|------|-------------|
| `/help/contact` | Ticket submission form (from PRD 00, routes here) |
| `/help/tickets` | User's ticket list with status badges |
| `/help/tickets/[id]` | Ticket detail: messages thread, reply form |
| `/admin/support` | Admin ticket queue: filters by status, priority, category, assignee |
| `/admin/support/[id]` | Admin ticket detail: reply, internal notes, status controls, assignment |

### Ticket Number Generation

Sequential human-readable IDs: `SUP-00001`, `SUP-00002`, etc. Generated server-side from a database sequence.

### Email Notifications

| Event | Recipient | Template |
|-------|-----------|----------|
| Ticket created | User + admin team | Confirmation with ticket number |
| Admin reply | User | "Your support request has been updated" |
| User reply | Assigned admin | "New reply on SUP-XXXXX" |
| Status change | User | "Your ticket status changed to [status]" |
| SLA breach | Admin team | "URGENT: Ticket SUP-XXXXX has breached SLA" |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| First response time (median) | < 12 hours |
| Resolution time (median) | < 48 hours |
| SLA compliance rate | > 90% |
| User satisfaction (post-resolution survey) | > 4/5 |
| Tickets per 100 active users (lower = better self-service) | < 5 |

---

## Acceptance Criteria

- [ ] Authenticated user can create a support ticket with subject, description, category, and optional attachments
- [ ] User can view their own tickets and their current status
- [ ] User can reply to their ticket thread
- [ ] Admin can view all tickets with filters (status, priority, category, assignee)
- [ ] Admin can assign tickets, change priority/status, and add internal notes
- [ ] Email sent to user on ticket creation and status changes
- [ ] Email sent to admin team on new ticket and SLA breach
- [ ] Tickets auto-escalate when first response SLA is breached
- [ ] Admin stats endpoint returns volume, avg resolution time, SLA compliance
- [ ] Ticket detail page shows full message thread with timestamps

---

## Dependencies
- **PRD 00 (Help Center):** Contact form routes to this system
- **PRD 02 (Disputes):** Dispute tickets are a specialized ticket type
- **Email service:** `services/email.py` already exists
- **Notification model:** Phase 4 PRD 04 — in-app notifications for ticket updates

## Risks
- **Volume spike** — Early days may have zero tickets; launch marketing may spike → start with email fallback
- **No dedicated support staff** — Initially handled by founders/engineers → keep admin UI simple
- **Attachment storage** — Need S3 or equivalent for file uploads → can defer attachments to v2
