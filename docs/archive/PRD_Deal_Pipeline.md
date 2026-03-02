# PRD: Deal Pipeline — Select, Acceptance & Commission Readiness

**Status:** Active  
**Date:** 2026-02-22  
**Priority:** P1 — required for bespoke vendor monetization  
**Depends on:** Existing outreach + quote flows (already working)  
**Decisions made:** Lance, Feb 22 2026

---

## 1. Context

BuyAnything connects buyers with ~3,000 bespoke vendors (jet charters, caterers, jewelers, etc.). For marketplace products (Amazon, eBay), we earn affiliate commissions automatically. For bespoke vendors, **we currently have no mechanism to capture value from the deals we facilitate**.

The outreach flow works: buyer searches → vendor tiles appear → buyer clicks "Request Quote" → email sent → vendor submits quote via magic link → quote appears as a tile. But after the buyer clicks "Select", nothing meaningful happens — the row just flips to "closed" and the bid gets `is_selected = true`. No vendor notification, no deal tracking, no acceptance confirmation, no commission trail.

### What exists today (code-verified)

| Component | Status | Location |
|---|---|---|
| `DealHandoff` model | Exists, partially wired | `models/marketplace.py:101` |
| `Contract` model | Exists, never wired | `models/marketplace.py:135` |
| `SellerQuote` model | Working | `models/marketplace.py:20` |
| `OutreachEvent` model | Working | `models/marketplace.py:62` |
| `Vendor.default_commission_rate` | Field exists (0.05), never used | `models/bids.py:47` |
| `Vendor.stripe_account_id` | Field exists, never used | `models/bids.py:45` |
| `Bid.closing_status` | Field exists, never set meaningfully | `models/bids.py:105` |
| `Bid.is_selected` | Working — set on PATCH /rows/{id} | `routes/rows.py:322` |
| Quote select → DealHandoff | Working for quote path only | `routes/quotes.py:258` |
| Handoff emails (buyer + seller) | Working | `services/email.py` |
| Close handoff endpoint | Exists | `routes/quotes.py:329` |
| `Commission` model | **Does not exist** | — |
| Deal acceptance page | **Does not exist** | — |
| Vendor "you've been selected" email | **Does not exist** (handoff emails exist but only for quote path) | — |
| Row freeze on select | **Partial** — status goes to "closed" but UI doesn't mute other tiles | — |

### Decisions (Lance, Feb 22)

| Question | Decision |
|---|---|
| When does commission trigger? | **On Deal Acceptance** — both buyer and vendor confirm |
| Deal falls through after acceptance? | **Case by case** — admin manually waives/disputes |
| How to collect from bespoke vendors? | **Deferred** — build the pipeline, decide monetization model later |
| Marketplace vs vendor commission? | Separate systems — affiliate networks handle marketplace; we handle vendor |

---

## 2. Scope

### In scope (Phases 1–3)
- Phase 1: Select Freeze + Vendor Notification
- Phase 2: Manual Response Tracking
- Phase 3: Deal Acceptance Page (magic link for vendor, mutual confirmation)

### Out of scope (Phase 4 — deferred)
- `Commission` model and auto-invoicing
- Stripe Invoice generation
- Reputation penalties for non-paying vendors
- DocuSign / e-signature integration

---

## 3. Phase 1: Select Freeze + Vendor Notification

**Goal:** When a buyer selects a bid, freeze the row, notify the vendor, and create a proper deal record.

### 3.1 Backend changes

**File: `routes/rows.py`** — Update the PATCH /rows/{id} select logic (~line 315-326)

Currently:
- Sets `bid.is_selected = true` for the chosen bid
- Sets `row.status = "closed"`

Change to:
- Set `bid.is_selected = true`, `bid.closing_status = "selected"`
- Set `row.status = "selected"` (not "closed" — closed means deal is done)
- Create a `DealHandoff` record linking buyer, vendor, row, bid
- If the bid has a `vendor_id`, look up vendor email and send "You've been selected" notification
- If the bid came from a `SellerQuote`, also update `SellerQuote.status = "accepted"`

**File: `routes/rows.py`** — Update the POST /rows/{id}/select-option endpoint (~line 420-426)

Same changes as above — this is the other path that sets `is_selected`.

**File: `models/marketplace.py`** — Update `DealHandoff`

Add fields:
- `bid_id: Optional[int]` (FK to bid) — currently only has `quote_id`
- `vendor_id: Optional[int]` (FK to vendor)
- `vendor_email: Optional[str]`
- `vendor_name: Optional[str]`
- `acceptance_token: Optional[str]` — magic link token for vendor acceptance page (Phase 3)
- `buyer_accepted_at: Optional[datetime]`
- `buyer_accepted_ip: Optional[str]`
- `vendor_accepted_at: Optional[datetime]`
- `vendor_accepted_ip: Optional[str]`

Update status enum: `"introduced"` → add `"pending_acceptance"`, `"accepted"`, `"completed"`, `"cancelled"`, `"disputed"`

**File: `services/email.py`** — Add `send_vendor_selected_email()`

New email template: "You've been selected by a buyer on BuyAnything" with:
- What the buyer is looking for (row title)
- Deal value (if quote exists)
- Link to deal acceptance page (Phase 3, placeholder for now)
- Contact info for the buyer

**File: `main.py`** — Add DealHandoff columns to startup migration block

Per the Railway migration workaround, add `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for all new DealHandoff columns.

### 3.2 Frontend changes

**File: `OfferTile.tsx`**

Currently when `isSelected`:
- Shows green "Selected" badge and border
- Hides Select/Buy Now/Request Quote buttons
- Shows static "Selected" label

Change:
- When `row.status === "selected"` AND this tile is NOT the selected one → mute the tile (opacity, disable all buttons)
- When this tile IS selected → keep current green treatment
- Disable "Request Quote" on ALL tiles when row is in "selected" status

**File: `RowStrip.tsx`**

- Show a deal stage indicator when `row.status === "selected"`: "Deal in progress — waiting for vendor confirmation"
- When `row.status === "completed"`: "Deal completed"

### 3.3 Acceptance criteria

- [ ] Clicking "Select" on a bid sets `bid.closing_status = "selected"` and `row.status = "selected"`
- [ ] A `DealHandoff` record is created with buyer, vendor, bid, and deal value
- [ ] Vendor receives a "You've been selected" email (if vendor email is available)
- [ ] Non-selected tiles are visually muted and buttons disabled
- [ ] "Request Quote" is disabled on all tiles for a selected row
- [ ] Row shows "Deal in progress" indicator

---

## 4. Phase 2: Manual Response Tracking

**Goal:** Let buyers track deal progress with simple status buttons.

### 4.1 Backend changes

**File: `routes/outreach.py`** — Add endpoints:

- `PATCH /outreach/{event_id}/mark-replied` — sets `OutreachEvent.status = "responded"`
- `PATCH /outreach/{event_id}/mark-delivered` — sets custom status on DealHandoff

**File: `routes/rows.py` or `routes/deals.py` (new)**

- `PATCH /deals/{handoff_id}/cancel` — buyer cancels the deal, unfreezes the row
- `PATCH /deals/{handoff_id}/complete` — buyer confirms delivery/completion

### 4.2 Frontend changes

**File: `OfferTile.tsx`**

- On contacted tiles (has OutreachEvent): show "Mark as Replied" button
- On selected tile: show "Mark as Delivered" / "Cancel Selection" buttons
- Status badges: "Contacted" → "Replied" → "Selected" → "Delivered"

### 4.3 Acceptance criteria

- [ ] Buyer can mark a contacted vendor as "Replied"
- [ ] Buyer can cancel a selection (row unfreezes, status reverts)
- [ ] Buyer can mark a deal as "Delivered" / complete
- [ ] Status badges update in real-time on tiles

---

## 5. Phase 3: Deal Acceptance Page

**Goal:** Both buyer and vendor explicitly confirm the deal on a shared page, creating an audit trail for future commission enforcement.

### 5.1 Backend changes

**File: `routes/deals.py` (new)**

- `GET /deals/{handoff_id}` — returns deal summary (authenticated, buyer only)
- `GET /deals/accept/{token}` — vendor-facing deal page via magic link (no auth required)
- `POST /deals/{handoff_id}/buyer-accept` — buyer confirms (authenticated)
- `POST /deals/accept/{token}` — vendor confirms via magic link

On mutual acceptance:
- Set `DealHandoff.status = "accepted"`
- Set `DealHandoff.buyer_accepted_at`, `vendor_accepted_at` with timestamps
- Record IP addresses for audit trail
- Send confirmation emails to both parties
- Update `row.status = "completed"`

**File: `services/email.py`**

- `send_deal_acceptance_link()` — email to vendor with magic link to acceptance page
- `send_deal_confirmed_email()` — email to both parties when deal is mutually accepted

### 5.2 Frontend changes

**File: `app/deal/[id]/page.tsx` (new)** — Buyer-facing deal summary

- Shows: what they're buying, vendor info, quote price, deal status
- "Confirm Deal" button (if not yet confirmed)
- Status timeline: Selected → Pending Acceptance → Accepted → Completed

**File: `app/deal/accept/[token]/page.tsx` (new)** — Vendor-facing acceptance page (public, no auth)

- Shows: buyer request summary, agreed price, BuyAnything terms
- "Accept Deal" button
- Terms text: "By accepting, you agree to BuyAnything's vendor terms including applicable referral fees."

### 5.3 Acceptance criteria

- [ ] Vendor receives magic link to acceptance page after buyer selects
- [ ] Vendor can view deal summary and click "Accept"
- [ ] Buyer can view deal summary and click "Confirm"
- [ ] Both acceptances are timestamped with IP addresses
- [ ] Both parties receive confirmation email on mutual acceptance
- [ ] Row status moves to "completed" on mutual acceptance
- [ ] Deal acceptance page works without authentication (magic link)

---

## 6. Files touched (summary)

| File | Phase | Changes |
|---|---|---|
| `models/marketplace.py` | 1 | Add fields to DealHandoff (bid_id, vendor_id, acceptance fields) |
| `routes/rows.py` | 1 | Update select logic → create DealHandoff, set closing_status, send email |
| `services/email.py` | 1, 3 | Add vendor selected email, deal acceptance emails |
| `main.py` | 1 | Startup migration for new DealHandoff columns |
| `OfferTile.tsx` | 1, 2 | Mute non-selected tiles, add status buttons |
| `RowStrip.tsx` | 1 | Deal stage indicator |
| `routes/outreach.py` | 2 | Mark-replied endpoint |
| `routes/deals.py` (new) | 2, 3 | Deal management + acceptance endpoints |
| `app/deal/[id]/page.tsx` (new) | 3 | Buyer deal summary page |
| `app/deal/accept/[token]/page.tsx` (new) | 3 | Vendor acceptance page |
| `app/api/deals/` (new) | 3 | Frontend proxy routes for deal endpoints |

---

## 7. Migration notes

All new columns use `ADD COLUMN IF NOT EXISTS` in `main.py` startup block (Railway workaround). No Alembic migration needed for Phase 1.

Phase 3 acceptance pages are public (magic link auth) — no middleware changes needed, same pattern as existing `/quote/{token}` pages.

---

## 8. Future (Phase 4 — when monetization model is decided)

- `Commission` model: tracks deal_value × commission_rate per deal
- Auto-create commission record on mutual acceptance
- Admin dashboard for outstanding commissions
- Stripe Invoice or Stripe Connect integration
- Reputation score penalties for vendors who don't pay commissions
- Vendor subscription / lead fee alternatives

---

*This PRD is approved for implementation. Phase 4 is deferred until the monetization model is decided.*
