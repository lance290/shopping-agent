# PRD: Seller Dashboard

**Phase:** 3 — Closing the Loop  
**Priority:** P1  
**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Parent:** [Phase 3 Parent](./parent.md)

---

## 1. Problem Statement

The Phase 2 parent PRD describes a **"Seller-Side Tile Workspace"** where sellers can view buyer RFPs as tiles and bid on them. Today:

- Sellers can only interact via **magic link** (quote form sent by email).
- There is **no seller-facing UI** — no dashboard, no inbox, no quote management.
- Registered merchants (`/merchants/register`) have a profile but nowhere to use it.
- Sellers cannot proactively discover buyer needs that match their offerings.

Without a seller dashboard, the marketplace is **one-sided**: buyers can find sellers, but sellers are passive recipients of outreach emails.

---

## 2. Solution Overview

Build a **Seller Dashboard** at `/seller` that gives registered merchants:

1. **RFP Inbox** — Buyer requests matching the seller's categories, displayed as tiles (mirroring the buyer's Netflix-style UX).
2. **My Quotes** — Status tracker for submitted, pending, accepted, and rejected quotes.
3. **Profile Management** — Edit business info, categories, service areas.
4. **Notifications** — Email/in-app alerts when new matching RFPs arrive.

The seller experience should feel like **the buyer board, but flipped** — instead of "things I want to buy," it shows "things I can sell."

---

## 3. Scope

### In Scope
- `/seller` route with dashboard layout
- RFP Inbox: list of buyer Rows matching seller's categories
- Quote management: view/edit submitted quotes, see status
- Profile settings: edit Merchant record
- Basic notification preferences
- Auth: sellers log in with existing email auth; merchants are linked to User accounts

### Out of Scope
- Real-time chat between buyer and seller (Phase 4)
- Seller analytics / performance metrics (Phase 4)
- Bid/counter-offer negotiation flow (Phase 4)
- Seller-initiated outreach to buyers (Phase 4)
- Payment/payout management via Stripe Connect (Phase 4)

---

## 4. User Stories

**US-01:** As a registered merchant, I want to see a dashboard of buyer RFPs that match my categories so I can proactively submit quotes.

**US-02:** As a seller, I want to click on a buyer RFP tile and see the full request details (choice factors, budget, description) so I can decide whether to quote.

**US-03:** As a seller, I want to submit a quote directly from the dashboard (same form as magic link, but without needing the email) so I can respond quickly.

**US-04:** As a seller, I want to see the status of all my submitted quotes (pending, accepted, rejected) so I can manage my pipeline.

**US-05:** As a seller, I want to edit my business profile (categories, contact info, service areas) so my RFP matches stay relevant.

**US-06:** As a seller, I want to receive an email when a new RFP matching my categories is posted so I don't miss opportunities.

---

## 5. Acceptance Criteria

| ID | Criteria |
|----|----------|
| AC-01 | Authenticated merchants can access `/seller` and see their dashboard. |
| AC-02 | RFP Inbox shows Rows where `service_category` or search query matches the merchant's registered categories. |
| AC-03 | Clicking an RFP tile opens a detail view with the Row's title, choice factors, budget, and a "Submit Quote" button. |
| AC-04 | "Submit Quote" opens the same quote form used in `/quote/[token]` but pre-authenticated (no magic link needed). |
| AC-05 | My Quotes tab shows all `SellerQuote` records for this merchant, grouped by status. |
| AC-06 | Profile tab allows editing all `Merchant` fields and saves changes. |
| AC-07 | Non-merchant users visiting `/seller` see a prompt to register via `/merchants/register`. |
| AC-08 | When WattData ICP matching is available (PRD-02), the inbox additionally shows WattData-sourced matches. |

---

## 6. Technical Design

### 6.1 Backend: New Endpoints

**GET /api/seller/inbox**
- Auth required (must be linked to a Merchant record).
- Returns Rows matching the merchant's categories.
- Matching logic: `Row.service_category IN merchant.categories` OR full-text search on `Row.title` against merchant categories.
- Pagination: `?page=1&per_page=20`
- When WattData adapter supports `find_buyers()`, merge those results.

**GET /api/seller/quotes**
- Auth required.
- Returns all `SellerQuote` records where `seller_email` matches the merchant's email.
- Includes related Row data (title, status, choice_factors).

**POST /api/seller/quotes**
- Auth required.
- Same logic as existing quote submission, but authenticated (no magic link token needed).
- Creates `SellerQuote` + converts to `Bid`.

**GET /api/seller/profile**
- Returns the current merchant's `Merchant` record.

**PATCH /api/seller/profile**
- Updates the merchant's profile fields.

### 6.2 Frontend: New Pages

**`/seller/page.tsx`** — Dashboard shell with tabs:
- **Inbox** — Grid/list of matching RFP cards
- **My Quotes** — Table/cards of submitted quotes with status badges
- **Profile** — Edit form for merchant details

**`/seller/rfp/[rowId]/page.tsx`** — RFP detail view:
- Shows Row title, choice factors, budget, description
- "Submit Quote" button opens inline quote form
- Shows other sellers' quote count (anonymized)

### 6.3 RFP Matching Logic

Phase 1 (simple):
```sql
SELECT r.* FROM row r
WHERE r.is_service = true
  AND r.service_category = ANY(merchant.categories)
  AND r.status IN ('sourcing', 'inviting', 'bids_arriving')
ORDER BY r.created_at DESC
```

Phase 2 (with WattData):
```python
adapter = get_vendor_adapter()
wattdata_matches = await adapter.find_buyers(seller_profile)
db_matches = await get_matching_rows(merchant.categories)
return merge_and_dedupe(db_matches, wattdata_matches)
```

### 6.4 Auth Integration

- Sellers use the same email auth as buyers.
- The `/seller` route checks if the authenticated user has a linked `Merchant` record (`merchant.user_id = user.id`).
- If not, redirect to `/merchants/register`.

---

## 7. UX Design Notes

- The seller dashboard should share the same **design language** as the buyer board (warm-light background, card components, blurple accents).
- RFP tiles in the inbox should resemble `RequestTile` from the buyer side, showing:
  - Request title
  - Category badge
  - Budget range (if provided)
  - Number of choice factors
  - "Quote" CTA button
- My Quotes should use status badges consistent with `DealStatus.tsx`.

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Seller registration → first quote submission | >20% conversion |
| Average time from RFP post to first seller quote | <24 hours |
| Seller return rate (visits dashboard again within 7 days) | >40% |
| Quotes submitted via dashboard vs. magic link | Dashboard > 50% after launch |

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Low seller adoption — no sellers register | Seed with existing outreach vendors; direct merchant registration outreach |
| RFP matching too broad (noisy inbox) | Allow sellers to set category preferences; add relevance scoring |
| Sellers spam low-quality quotes | Add quote quality signals; let buyers rate seller responsiveness |
| Auth confusion (buyer vs seller login) | Same login, role-based routing; clear "Switch to Seller" / "Switch to Buyer" nav |

---

## 10. Dependencies

- **Auth system** (done) — sellers use existing email auth
- **Merchant model** (done) — registration, categories, service areas
- **SellerQuote model** (done) — quote intake, status tracking
- **WattData MCP** (PRD-02) — enhances inbox matching when available

---

## 11. Implementation Checklist

- [ ] Create `routes/seller.py` with inbox, quotes, profile endpoints
- [ ] Add RFP matching query logic
- [ ] Create `/seller/page.tsx` dashboard shell with tabs
- [ ] Create RFP Inbox component with request cards
- [ ] Create My Quotes component with status tracking
- [ ] Create Profile edit form
- [ ] Create `/seller/rfp/[rowId]/page.tsx` detail view
- [ ] Add "Submit Quote" flow (authenticated, no magic link)
- [ ] Add frontend API proxy routes
- [ ] Add email notification for new matching RFPs (optional for v1)
- [ ] Write tests for seller endpoints
- [ ] Write tests for RFP matching logic
