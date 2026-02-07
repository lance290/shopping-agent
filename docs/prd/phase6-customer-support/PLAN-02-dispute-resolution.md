# Implementation Plan: PRD 02 — Dispute Resolution & Refunds

**Status:** Draft — awaiting approval  
**Priority:** P1 (build after PRD 01 — disputes are specialized tickets)  
**Estimated effort:** 2-3 days  
**Depends on:** PRD 01 (Support Tickets), Stripe integration (exists)

---

## Goal

When a buyer or seller has a problem with a transaction, give them a structured way to file a dispute, submit evidence, and get a resolution. Enable admins to mediate and trigger Stripe refunds.

---

## Current State

- `PurchaseEvent.status` includes `"refunded"` as a valid value, but **nothing ever sets it**
- No `Dispute` model, no evidence model, no refund endpoint
- Phase 4 PRD 05 (Closing Layer) explicitly put dispute resolution **out of scope**: *"Escrow, chargeback arbitration, dispute resolution workflows"*
- Stripe SDK is installed and configured (used for Stripe Connect)
- Stripe's own `Refund` API is available via the SDK

---

## Build Order

### Phase A: Backend Models + Migration (30 min)

**File: `apps/backend/models.py`** — add two models:

```python
class Dispute(SQLModel, table=True):
    __tablename__ = "dispute"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    dispute_number: str = Field(unique=True, index=True)  # "DSP-00001"
    
    # Parties
    filed_by_user_id: int = Field(foreign_key="user.id", index=True)
    against_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    against_merchant_id: Optional[int] = Field(default=None, foreign_key="merchant.id")
    
    # Transaction context
    purchase_event_id: Optional[int] = Field(default=None, foreign_key="purchase_event.id")
    row_id: Optional[int] = Field(default=None, foreign_key="row.id")
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id")
    
    # Dispute details
    dispute_type: str  # item_not_received, item_not_as_described, defective_item, service_not_performed, service_quality, unauthorized_charge, fraudulent_buyer
    status: str = "opened"  # opened, evidence, in_review, resolved_buyer_favor, resolved_seller_favor, resolved_mutual, escalated, expired, closed
    priority: str = "medium"  # low, medium, high, urgent
    
    description: str
    desired_outcome: Optional[str] = None
    
    # Resolution
    resolution_type: Optional[str] = None  # refund_full, refund_partial, replacement, dismissed, warning, suspension
    resolution_notes: Optional[str] = None
    resolved_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    refund_amount: Optional[float] = None
    refund_stripe_id: Optional[str] = None
    
    # Linked support ticket (for communication thread)
    support_ticket_id: Optional[int] = Field(default=None, foreign_key="support_ticket.id")
    
    # Timing
    evidence_deadline: Optional[datetime] = None  # 7 days from opening
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DisputeEvidence(SQLModel, table=True):
    __tablename__ = "dispute_evidence"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    dispute_id: int = Field(foreign_key="dispute.id", index=True)
    submitted_by_user_id: int = Field(foreign_key="user.id")
    
    evidence_type: str  # text, screenshot, receipt, tracking, communication, other
    description: str
    attachment_url: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Migration:** Create `dispute` and `dispute_evidence` tables.

---

### Phase B: Refund Service (1 hour)

**New file: `apps/backend/services/refund.py`**

```python
async def process_refund(
    session: AsyncSession,
    purchase_event_id: int,
    amount: Optional[float] = None,  # None = full refund
    reason: str = "requested_by_customer",
) -> dict:
    """
    Process a Stripe refund for a purchase.
    Updates PurchaseEvent.status to "refunded".
    Returns refund details or raises on failure.
    """
```

Logic:
1. Look up `PurchaseEvent` by ID
2. Get the Stripe `payment_intent` or `session_id` from the purchase
3. Call `stripe.Refund.create(payment_intent=..., amount=amount_in_cents)`
4. Update `PurchaseEvent.status` = `"refunded"`
5. Return refund ID and status
6. If no Stripe session (affiliate purchase), return error explaining platform can't refund

**Key constraint:** Stripe refunds must be within 180 days of original charge.

---

### Phase C: Backend Routes (2 hours)

**New file: `apps/backend/routes/disputes.py`**

#### User-facing:

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /disputes` | User | File a dispute. Body: `{ purchase_event_id?, row_id?, dispute_type, description, desired_outcome? }` |
| `GET /disputes` | User | List my disputes (filed by me or against me) |
| `GET /disputes/{id}` | User (party) or Admin | Dispute detail + evidence |
| `POST /disputes/{id}/evidence` | User (party) | Submit evidence. Body: `{ evidence_type, description, attachment_url? }` |

#### Admin:

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /admin/disputes` | Admin | Dispute queue. Filters: `?status=`, `?priority=`, `?type=` |
| `PATCH /admin/disputes/{id}` | Admin | Update status, priority |
| `POST /admin/disputes/{id}/resolve` | Admin | Resolve dispute. Body: `{ resolution_type, resolution_notes, refund_amount? }` |
| `GET /admin/disputes/stats` | Admin | Volume, resolution rate, avg time |

#### Dispute creation logic:
1. Generate `dispute_number` = `"DSP-" + str(max_id + 1).zfill(5)`
2. Set `evidence_deadline` = `created_at + 7 days`
3. Create linked `SupportTicket` (category: "dispute") for communication
4. Notify counter-party via email + in-app notification
5. Notify admin team

#### Resolution logic:
1. Admin selects resolution type
2. If `refund_full` or `refund_partial`: call `services/refund.py`
3. Update dispute status
4. If seller at fault + pattern: flag merchant for review
5. Notify both parties of outcome
6. Audit log everything

#### Affiliate purchase handling:
When a dispute is filed against a purchase that was an affiliate clickout:
- The system returns a message: "This purchase was made through [retailer]. We cannot process a refund directly. Here's how to contact [retailer]'s customer service."
- Log the dispute for analytics (track which affiliate sources generate complaints)
- Still create the dispute record for internal tracking

---

### Phase D: Email Notifications (30 min)

**File: `apps/backend/services/email.py`** — add:

| Function | Trigger | Recipient |
|----------|---------|-----------|
| `send_dispute_filed_email()` | Dispute created | Counter-party + admin |
| `send_dispute_evidence_request_email()` | Dispute opened | Counter-party ("you have 7 days to respond") |
| `send_dispute_resolved_email()` | Admin resolves | Both parties |
| `send_refund_confirmation_email()` | Refund processed | Buyer |

---

### Phase E: Frontend — User Dispute Pages (1-2 hours)

**New file: `apps/frontend/app/help/disputes/new/page.tsx`**
- Dispute filing form
- Step 1: Select transaction (from user's purchase history) or describe the issue
- Step 2: Select dispute type (dropdown of types)
- Step 3: Describe the problem + desired outcome
- Step 4: Upload evidence (optional)
- For affiliate purchases: show warning that platform can't refund directly

**New file: `apps/frontend/app/help/disputes/page.tsx`**
- List of user's disputes with status badges and dates

**New file: `apps/frontend/app/help/disputes/[id]/page.tsx`**
- Dispute detail: timeline, evidence from both sides, messages (via linked support ticket)
- Evidence submission form (if within 7-day window)
- Resolution outcome display

---

### Phase F: Frontend — Admin Dispute Pages (1 hour)

**New file: `apps/frontend/app/admin/disputes/page.tsx`**
- Dispute queue table: number, type, status, priority, parties, age

**New file: `apps/frontend/app/admin/disputes/[id]/page.tsx`**
- Full dispute detail: both parties' evidence side by side
- Resolution form: type dropdown, notes, refund amount (if applicable)
- "Process Refund" button triggers Stripe refund
- Linked support ticket thread for communication

---

### Phase G: Frontend Proxy Routes (15 min)

| Route file | Proxies to |
|-----------|-----------|
| `app/api/disputes/route.ts` | `GET, POST /disputes` |
| `app/api/disputes/[id]/route.ts` | `GET /disputes/{id}` |
| `app/api/disputes/[id]/evidence/route.ts` | `POST /disputes/{id}/evidence` |
| `app/api/admin/disputes/route.ts` | `GET /admin/disputes` |
| `app/api/admin/disputes/[id]/route.ts` | `PATCH /admin/disputes/{id}` |
| `app/api/admin/disputes/[id]/resolve/route.ts` | `POST /admin/disputes/{id}/resolve` |

---

### Phase H: Tests (1 hour)

**New file: `apps/backend/tests/test_disputes.py`**

| # | Test | Expected |
|---|------|----------|
| 1 | File dispute (happy path) | 200, dispute + linked ticket created |
| 2 | File dispute requires auth | 401 |
| 3 | List my disputes | 200, only my disputes |
| 4 | Submit evidence (within window) | 200, evidence attached |
| 5 | Submit evidence (after deadline) | 400, "evidence window closed" |
| 6 | Counter-party can submit evidence | 200 |
| 7 | Unrelated user can't view dispute | 403 |
| 8 | Admin resolve (refund_full) | 200, refund processed, status updated |
| 9 | Admin resolve (dismissed) | 200, no refund |
| 10 | Affiliate dispute shows limitation message | 200, message about retailer |
| 11 | Dispute creates support ticket | Linked ticket exists |
| 12 | Admin dispute stats | 200, volume/rate/time |

---

## Files Changed Summary

| File | Change Type | Lines Est. |
|------|------------|-----------|
| `apps/backend/models.py` | Add `Dispute` + `DisputeEvidence` models | +55 |
| `apps/backend/routes/disputes.py` | **New file** — 8 endpoints | ~350 |
| `apps/backend/services/refund.py` | **New file** — Stripe refund logic | ~80 |
| `apps/backend/services/email.py` | Add 4 email functions | +120 |
| `apps/backend/main.py` | Register disputes router | +2 |
| `apps/backend/alembic/versions/p6_disputes.py` | **New file** — create tables | ~35 |
| `apps/backend/tests/test_disputes.py` | **New file** — 12 tests | ~300 |
| Frontend pages (6 files) | **New files** | ~600 |
| Frontend proxy routes (6 files) | **New files** | ~90 |

**Total:** ~1,630 lines across 18 files (16 new, 2 modified)

---

## Open Questions

1. **`PurchaseEvent` → how to find Stripe payment intent?** Need to check if `stripe_session_id` on the model maps to a checkout session we can refund against. If not, we need to store the `payment_intent` ID on purchase.
2. **Partial refund amount validation:** Should we enforce that partial refund ≤ original amount? (Yes, obviously.)
3. **Dispute against non-purchase:** Can a buyer dispute a *quote* before purchasing? (Recommendation: No — disputes are post-transaction only. Pre-purchase issues use regular support tickets.)
4. **Auto-close expired disputes:** If evidence deadline passes with no counter-party response, should the dispute auto-resolve in filer's favor? (Recommendation: No auto-resolve. Admin must decide. But auto-escalate for review.)
