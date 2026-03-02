# PRD 02: Dispute Resolution & Refunds

**Phase:** 6 — Customer Support & Trust Infrastructure  
**Priority:** P1  
**Status:** Planning  
**Parent:** [Phase 6 Parent](./parent.md)

---

## Problem Statement

The platform facilitates real money transactions through three channels — affiliate clickouts, Stripe checkout, and seller quotes/contracts — but has **zero dispute resolution infrastructure**. The `PurchaseEvent.status` field includes `"refunded"` as a value, but nothing ever sets it. The Closing Layer PRD (Phase 4 PRD 05) explicitly put dispute resolution **out of scope**.

When a transaction goes wrong:
- **Buyer purchased via affiliate link** → Item never arrived, wrong item, or defective — buyer has no recourse through the platform
- **Buyer paid via Stripe checkout** → Seller didn't deliver, or item doesn't match — no refund flow
- **Seller quote accepted via contract** → Buyer disputes quality of work — no arbitration
- **Seller suspended unfairly** → No appeal process

Without dispute handling:
- Stripe may suspend the platform account (they require documented dispute processes)
- Buyers lose trust and stop transacting
- Sellers have no protection against bad-faith buyers
- The platform has no data on transaction quality

---

## Solution Overview

Build a **dispute resolution system** that handles:

1. **Dispute filing** — Buyer or seller can open a dispute against a transaction
2. **Evidence collection** — Both parties can submit evidence (screenshots, messages, tracking info)
3. **Resolution workflow** — Admin review → mediation → decision → enforcement
4. **Refund processing** — Automated refund via Stripe when resolution requires it
5. **Escalation** — Unresolved disputes escalate with increasing urgency
6. **Affiliate disputes** — Special handling for purchases made through affiliate links (platform has limited control)

---

## Scope

### In Scope
- `Dispute` model with full lifecycle
- Buyer-initiated disputes (wrong item, not delivered, not as described, unauthorized charge)
- Seller-initiated disputes (fraudulent buyer, unjustified chargeback)
- Evidence submission from both parties
- Admin mediation dashboard
- Refund processing via Stripe API (for Stripe checkout purchases)
- Dispute outcome recording and enforcement (e.g., merchant suspension)
- Dispute-related email notifications
- Integration with support tickets (PRD 01) — disputes are a specialized ticket type

### Out of Scope
- Escrow (holding funds during disputes) — requires significant Stripe Connect changes
- Automated AI-powered dispute resolution
- Legal arbitration or external mediation services
- Chargeback management with card networks (handled by Stripe directly)
- Seller payout clawback (requires Stripe Connect destination charges)

---

## User Stories

**US-01:** As a buyer, I want to open a dispute when a purchase doesn't meet expectations, so I can get a refund or replacement.

**US-02:** As a seller, I want to respond to a buyer's dispute with evidence, so I can defend against unjustified claims.

**US-03:** As an admin, I want to review disputes with evidence from both sides, so I can make a fair decision.

**US-04:** As a buyer, I want to receive a refund when my dispute is resolved in my favor.

**US-05:** As a seller, I want to dispute a fraudulent buyer who received the product but claims otherwise.

**US-06:** As a user, I want to track the status of my dispute and see the timeline of events.

---

## Business Requirements

### Authentication & Authorization
- **File dispute:** Authenticated user who is a party to the transaction
- **Respond to dispute:** Authenticated counter-party
- **Mediate/resolve:** Admin only
- **View dispute:** Only involved parties + admins

### Dispute Types

| Type | Filed By | Description |
|------|----------|-------------|
| `item_not_received` | Buyer | Paid but nothing arrived |
| `item_not_as_described` | Buyer | Received item doesn't match listing |
| `defective_item` | Buyer | Item is broken or non-functional |
| `unauthorized_charge` | Buyer | Didn't authorize this transaction |
| `service_not_performed` | Buyer | Seller quote accepted but work not done |
| `service_quality` | Buyer | Work done but quality unacceptable |
| `fraudulent_buyer` | Seller | Buyer received goods but filed false dispute |
| `unjustified_return` | Seller | Buyer returning without valid reason |

### Dispute Lifecycle

```
                    ┌─────────────┐
                    │   opened    │  ← Buyer/seller files dispute
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  evidence   │  ← Both parties submit evidence (7-day window)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  in_review  │  ← Admin reviews evidence
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───┐ ┌──────▼──────┐
       │ resolved_   │ │ resolved_ │ │  escalated  │
       │ buyer_favor │ │ seller_favor│ │             │
       └──────┬──────┘ └──┬───┘ └──────┬──────┘
              │            │            │
              │    ┌───────▼───────┐    │
              └───►│    closed     │◄───┘
                   └───────────────┘
```

### Resolution Outcomes

| Outcome | Action |
|---------|--------|
| `resolved_buyer_favor` | Full or partial refund issued; seller warned or suspended |
| `resolved_seller_favor` | Dispute dismissed; buyer warned if pattern of abuse |
| `resolved_mutual` | Partial refund agreed by both parties |
| `escalated` | Requires senior review or external mediation |
| `expired` | Evidence window closed, auto-resolved per policy |

### Refund Rules

| Purchase Channel | Refund Method |
|-----------------|---------------|
| Stripe Checkout | Stripe API refund (full or partial) |
| Affiliate clickout | Platform cannot refund — guide buyer to retailer's return policy |
| Seller quote (contract) | Manual refund via Stripe Connect or offline |

### Data Requirements

**Dispute model:**
```
id, dispute_number (e.g., "DSP-00042")
purchase_event_id (FK, nullable)
row_id (FK, nullable)
bid_id (FK, nullable)
contract_id (FK, nullable)

filed_by_user_id (FK user) — who opened the dispute
against_user_id (FK user, nullable) — the other party
against_merchant_id (FK merchant, nullable)

type: enum (see dispute types above)
status: opened | evidence | in_review | resolved_buyer_favor | resolved_seller_favor | resolved_mutual | escalated | expired | closed
priority: low | medium | high | urgent

description (text)
desired_outcome (text) — what the filer wants

# Resolution
resolution_type: refund_full | refund_partial | replacement | dismissed | warning | suspension
resolution_notes (text)
resolved_by_user_id (FK user, nullable) — admin who resolved
refund_amount (float, nullable)
refund_stripe_id (str, nullable) — Stripe refund ID

# Timing
evidence_deadline: datetime — 7 days from opening
resolved_at, closed_at, created_at, updated_at
```

**DisputeEvidence model:**
```
id, dispute_id (FK)
submitted_by_user_id (FK user)
evidence_type: text | screenshot | receipt | tracking | communication | other
description (text)
attachment_url (str, nullable)
created_at
```

### SLA

| Stage | Time Limit |
|-------|-----------|
| Evidence window | 7 days from dispute opening |
| Admin first review | 48 hours from evidence deadline |
| Resolution decision | 5 business days from first review |
| Refund processing | 24 hours from resolution |

### Performance
- Dispute creation < 500ms
- Evidence upload < 2s (file dependent)
- Admin dispute list < 500ms

---

## Technical Design

### Backend

**New file:** `routes/disputes.py`

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /disputes` | User | File a new dispute |
| `GET /disputes` | User | List my disputes (as filer or respondent) |
| `GET /disputes/{id}` | User/Admin | Dispute detail + evidence + messages |
| `POST /disputes/{id}/evidence` | User | Submit evidence (filer or respondent) |
| `POST /disputes/{id}/respond` | User | Counter-party response |
| `PATCH /disputes/{id}` | Admin | Update status, assign, resolve |
| `POST /disputes/{id}/refund` | Admin | Trigger Stripe refund |
| `GET /admin/disputes` | Admin | Full dispute queue with filters |
| `GET /admin/disputes/stats` | Admin | Volume, resolution rate, avg time |

**New file:** `services/refund.py`
- Stripe refund processing
- Refund amount validation
- PurchaseEvent status update to `"refunded"`
- Audit log entry

### Frontend

| Page | Description |
|------|-------------|
| `/help/disputes/new` | Dispute filing form (select transaction, type, describe issue) |
| `/help/disputes` | User's dispute list with status |
| `/help/disputes/[id]` | Dispute detail: timeline, evidence, messages |
| `/admin/disputes` | Admin dispute queue |
| `/admin/disputes/[id]` | Admin resolution interface: evidence review, decision form, refund trigger |

### Integration with Support Tickets

Disputes create an associated `SupportTicket` (PRD 01) with `category: dispute` so they appear in the unified admin queue. The dispute has specialized UI and workflow; the ticket provides the communication thread.

### Affiliate Dispute Handling

For purchases made via affiliate clickouts (Amazon, etc.):
- Platform **cannot issue refunds** (the transaction happened on the retailer's site)
- Dispute form shows retailer return policy link
- Platform can log the issue and flag the affiliate source for quality tracking
- If pattern of complaints against a specific affiliate source, admin can disable that source

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Dispute rate (disputes / purchases) | < 3% |
| Resolution time (median) | < 5 business days |
| Buyer satisfaction with resolution | > 3.5/5 |
| Refund processing time | < 24 hours after decision |
| Repeat dispute rate (same user) | < 10% |

---

## Acceptance Criteria

- [ ] Buyer can file a dispute against a purchase with type, description, and evidence
- [ ] Seller/counter-party is notified and can submit counter-evidence within 7-day window
- [ ] Admin can view dispute queue, review evidence from both sides, and make a resolution decision
- [ ] Resolution in buyer's favor triggers Stripe refund (for Stripe checkout purchases)
- [ ] `PurchaseEvent.status` updated to `"refunded"` on successful refund
- [ ] For affiliate purchases, dispute form shows retailer return policy and explains platform limitations
- [ ] Both parties receive email notifications at each status change
- [ ] Dispute timeline shows all events in chronological order
- [ ] Admin stats show dispute volume, resolution rate, and average time
- [ ] Resolved disputes create audit log entries

---

## Dependencies
- **PRD 01 (Support Tickets):** Disputes create associated tickets for communication
- **PRD 03 (Messaging):** Evidence and responses may use messaging thread
- **Stripe API:** Refund processing
- **Phase 4 PRD 00 (Revenue):** `PurchaseEvent` model for transaction reference

## Risks
- **Stripe refund limits** — Refunds must be within 180 days of charge; need to enforce
- **No escrow** — Platform can't hold funds during disputes; resolution happens post-payment
- **Affiliate limitations** — Platform has no control over affiliate purchases; must set expectations clearly
- **Abuse** — Serial disputants may game the system → implement buyer trust score impact (Phase 4 PRD 10)
