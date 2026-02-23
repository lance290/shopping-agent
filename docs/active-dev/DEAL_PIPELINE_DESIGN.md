# Deal Pipeline Design — Select, Contracts & Commissions

**Status:** Design doc — not yet implemented  
**Author:** Cascade  
**Date:** 2026-02-20  

---

## 1. Problem Statement

Today, "Select" on an offer tile sets `bid.is_selected = true` and `row.status = "closed"` — but nothing actually *happens*. The user can still contact other vendors, the vendor doesn't know they were selected, and there's no mechanism for contracts, payment, or commission.

We need a deal pipeline that takes a row from "vendor contacted" through to "deal closed" with clear status tracking at every step.

---

## 2. Current State (What Exists)

### Models already in the DB
| Model | Table | What it does today |
|---|---|---|
| `Bid` | `bid` | `is_selected`, `closing_status` (never used) |
| `Row` | `row` | `status` flips to `"closed"` on select |
| `OutreachEvent` | `outreach_event` | Tracks sent emails, with `status`, `sent_at`, `opened_at`, `clicked_at`, `quote_submitted_at` |
| `SellerQuote` | `seller_quote` | Vendor-submitted quotes via magic link; `status`: pending/submitted/accepted/rejected |
| `DealHandoff` | `deal_handoff` | Tracks email introductions; `status`: introduced/closed/cancelled — **never used** |
| `Contract` | `contract` | DocuSign envelope tracking; `status`: draft→sent→viewed→signed→completed — **never used** |
| `Vendor` | `vendor` | Has `stripe_account_id`, `default_commission_rate` (0.05), `stripe_onboarding_complete` — **never used** |

### Frontend
- `OfferTile` "Select" button → `selectOfferForRow()` → `PATCH /rows/{id}` with `selected_bid_id`
- Row status changes to "closed", bid gets `is_selected = true`
- "Contacted" / "Quote Received" badges now show on tiles (just shipped)

### Key insight
Most of the *models* already exist — we just need to wire up the *flows*.

---

## 3. Proposed Deal Stages

```
Row statuses (linear, one active at a time):

  new → sourcing → comparing → selected → contracted → completed
                                  │
                                  └→ cancelled (at any point after select)
```

### Per-offer (Bid) lifecycle
```
  (no status) → contacted → quoted → selected → deal_pending → deal_closed
                                                     │
                                                     └→ deal_cancelled
```

Mapped to `bid.closing_status`:
| Stage | `closing_status` | What happened |
|---|---|---|
| Not contacted | `null` | Marketplace result or vendor tile, no outreach |
| Contacted | `"contacted"` | Email sent (OutreachEvent exists with sent_at) |
| Quoted | `"quoted"` | SellerQuote submitted |
| Selected | `"selected"` | User clicked Select — **this is the freeze point** |
| Deal Pending | `"pending"` | Contract sent or payment initiated |
| Deal Closed | `"closed"` | Contract signed or payment confirmed |
| Cancelled | `"cancelled"` | User or vendor backed out |

---

## 4. What "Select" Should Lock Down

When the user clicks **Select** on an offer:

### Immediate (Phase 1 — build first)
1. **Freeze the row** — disable "Request Quote" buttons on all other vendor tiles for this row
2. **Mark the bid** — `bid.is_selected = true`, `bid.closing_status = "selected"`
3. **Mark the row** — `row.status = "selected"` (not "closed" — that implies done)
4. **Notify the vendor** — send a "You've been selected" email to the vendor with next steps
5. **Create a DealHandoff** record linking buyer, vendor, row, and quote
6. **UI change** — selected tile gets a prominent "Selected" treatment; other tiles become muted/collapsed

### Deferred (Phase 2)
7. **Allow undo** — within a grace period (e.g., 1 hour), user can un-select and pick someone else
8. **Disable further outreach** — prevent new emails to other vendors for this row (soft block — show "Deal in progress" instead of "Request Quote")

### Open question for Lance
> Should "Select" on a *marketplace* offer (Amazon, etc.) behave differently from "Select" on a vendor quote? Marketplace offers don't have a vendor email to notify — it's purely a user-side bookmark. We could treat marketplace Select as "I bought this" (confirmation) vs. vendor Select as "I'm choosing this vendor" (triggers a deal flow).

---

## 5. Response Tracking

### Already working
- **Quote submission** — vendor clicks magic link → submits quote → `SellerQuote.status = "submitted"` → shows as "Quote Received" badge on tile

### Needs work

#### 5a. Inbound email reply detection
When a vendor replies to our outreach email, we currently have no way to know.

**Options (pick one):**

| Option | Effort | Reliability | Cost |
|---|---|---|---|
| **A) Resend inbound webhook** | Low | High | Free (Resend supports it) |
| **B) Dedicated reply-to domain** | Medium | High | ~$5/mo for domain + MX |
| **C) User self-reports** | Trivial | Low | Free |

**Recommendation:** Start with **C** (add a "Mark as Replied" button on contacted tiles) and build **A** when volume justifies it.

For Option A: Resend can forward inbound emails to a webhook. We'd use a reply-to like `row-{id}-{vendor_hash}@replies.buyanything.ai`, parse the inbound webhook, and update `OutreachEvent.status = "responded"`.

#### 5b. Email open/click tracking
Resend supports open/click webhooks. We already have `OutreachEvent.opened_at` and `clicked_at` columns — just need to wire up the Resend webhook.

**Recommendation:** Wire this up alongside the deal pipeline. Low effort, nice-to-have for the "activity" view.

---

## 6. Contract Generation & E-Signature

### When is a contract needed?
- **Marketplace purchases** (Amazon, etc.): No contract needed — user buys directly
- **Vendor quotes < $500**: Probably overkill — email confirmation is sufficient
- **Vendor quotes ≥ $500**: Contract recommended
- **Enterprise/custom services**: Contract required

### Contract flow
```
Select → Generate contract (from template) → Review → Send for signature → Signed → Deal closed
```

### Implementation options

| Option | Effort | Cost | UX |
|---|---|---|---|
| **A) DocuSign API** | High (2-3 days) | ~$25/mo for 100 envelopes | Gold standard |
| **B) PandaDoc API** | High (2-3 days) | ~$35/mo | Good templates |
| **C) PDF + email confirm** | Low (1 day) | Free | MVP-sufficient |
| **D) In-app acceptance** | Medium (1-2 days) | Free | Fast but less legal weight |

**Recommendation:** Start with **D** (in-app acceptance with audit trail) — vendor and buyer both click "Accept" on a deal summary page. Store the acceptance timestamps and IP addresses for a lightweight audit trail. Graduate to DocuSign when deal values warrant it.

### Contract template data (already available)
- Row title (what they're buying)
- Buyer name + email + company (from User model — just added)
- Vendor name + email + company (from SellerQuote or OutreachEvent)
- Quote price + currency (from SellerQuote)
- Quote details/description (from SellerQuote)

### The `Contract` model already exists
Just needs to be wired up. For the in-app acceptance flow, we'd use `status = "draft" → "sent" → "signed" → "completed"` and skip the DocuSign fields until Phase 2.

---

## 7. Commission Structure

### Current state
- `Vendor.default_commission_rate = 0.05` (5%) — exists but never used
- `Vendor.stripe_account_id` — exists but never used
- No `Commission` or `Payment` model yet

### Proposed commission model

```
Commission
  id
  deal_handoff_id  → DealHandoff
  row_id           → Row
  bid_id           → Bid
  vendor_id        → Vendor
  buyer_user_id    → User
  
  deal_value       float     — total deal value
  commission_rate  float     — rate at time of deal (snapshot from vendor)
  commission_amount float    — deal_value × commission_rate
  currency         str
  
  status           str       — "pending", "invoiced", "paid", "waived"
  
  stripe_payment_intent_id   — for collecting from vendor
  stripe_transfer_id         — if using Stripe Connect
  
  invoiced_at      datetime
  paid_at          datetime
  created_at       datetime
```

### Collection options

| Option | How it works | When to use |
|---|---|---|
| **A) Stripe Connect** | Buyer pays BuyAnything, BA takes cut, transfers rest to vendor | Full marketplace checkout |
| **B) Invoice vendor** | Deal happens off-platform; BA invoices vendor for commission | Current flow (vendor deals directly with buyer) |
| **C) Honor system** | Track commission owed, collect manually/quarterly | MVP for trusted vendors |

**Recommendation:** Start with **B** — since deals happen off-platform (buyer and vendor email directly), BuyAnything invoices the vendor for the commission after the deal closes. Use Stripe Invoicing to automate this.

### Commission rates
| Tier | Rate | Criteria |
|---|---|---|
| Standard | 5% | Default for all vendors |
| Partner | 3% | Verified vendors with 10+ deals |
| Enterprise | Custom | Negotiated per-vendor |
| Marketplace | Affiliate % | Amazon Associates, Skimlinks, etc. (separate system) |

### Open questions for Lance
1. **When does commission trigger?** On "Select"? On contract sign? On buyer confirmation of delivery?
2. **What if the deal falls through?** Refund policy for commission?
3. **Do we invoice vendors now or defer?** We could track commission owed without actually collecting until we have volume.
4. **Marketplace vs. vendor commission** — affiliate commissions (Amazon, etc.) are handled by the affiliate network. Vendor commissions are our own. Keep them separate?

---

## 8. Implementation Phases

### Phase 1: Select Freeze + Notification (1 day)
- [ ] Change `row.status` to `"selected"` (not `"closed"`)
- [ ] Set `bid.closing_status = "selected"` 
- [ ] Create `DealHandoff` record on select
- [ ] Send "You've been selected" email to vendor
- [ ] Frontend: mute/collapse non-selected tiles, disable "Request Quote" on closed rows
- [ ] Frontend: add "Undo Selection" button (1-hour grace)

### Phase 2: Manual Response Tracking (0.5 day)
- [ ] Add "Mark as Replied" button on contacted tiles
- [ ] Add "Mark as Delivered" button after selection
- [ ] Track these transitions in `OutreachEvent.status`

### Phase 3: In-App Deal Acceptance (1-2 days)
- [ ] Deal summary page at `/deal/{deal_handoff_id}` (magic link for vendor)
- [ ] Buyer and vendor "Accept" buttons with timestamp + IP audit trail
- [ ] Update `DealHandoff.status` and `Contract.status`
- [ ] Email notifications at each stage

### Phase 4: Commission Tracking (1 day)
- [ ] Create `Commission` model
- [ ] Auto-create commission record when deal closes
- [ ] Admin view to see outstanding commissions
- [ ] Stripe Invoice integration (or defer to manual)

### Phase 5: Resend Webhooks (0.5 day)
- [ ] Wire up Resend open/click/inbound webhooks
- [ ] Update OutreachEvent on open/click
- [ ] Parse inbound replies → mark as "responded"

### Phase 6: DocuSign/Full Contracts (2-3 days, only if needed)
- [ ] DocuSign API integration
- [ ] Contract template system
- [ ] E-signature flow
- [ ] Webhook for signature status updates

---

## 9. Data Flow Summary

```
User searches → Results appear as tiles
   │
   ├─ Marketplace tile: User clicks out → affiliate commission (existing)
   │
   └─ Vendor tile: User clicks "Request Quote"
         │
         ├─ Email sent → tile shows "Contacted" badge
         │     │
         │     └─ Vendor submits quote → tile shows "Quote Received" badge
         │
         └─ User clicks "Select"
               │
               ├─ Row freezes (status = "selected")
               ├─ Vendor notified via email
               ├─ DealHandoff created
               │
               ├─ [Phase 3] Deal acceptance page
               │     ├─ Buyer confirms
               │     └─ Vendor confirms
               │
               ├─ [Phase 4] Commission calculated
               │     └─ Invoice sent to vendor
               │
               └─ Deal closed (status = "completed")
```

---

## 10. Files That Will Be Touched

| File | Changes |
|---|---|
| `models/marketplace.py` | Add `Commission` model; update `DealHandoff` if needed |
| `routes/rows.py` | Update select endpoint to create DealHandoff, change status logic |
| `routes/outreach.py` | Add "mark as replied" endpoint |
| `services/email.py` | Add "you've been selected" email template |
| `OfferTile.tsx` | Mute non-selected tiles, disable actions on frozen rows |
| `RowStrip.tsx` | Show deal stage indicator |
| `VendorContactModal.tsx` | Block if row is frozen |
| New: `routes/deals.py` | Deal acceptance page endpoints |
| New: `app/deal/[id]/page.tsx` | Vendor-facing deal acceptance page |

---

*This doc is a plan. Do not implement until Lance gives the go-ahead on the open questions.*
