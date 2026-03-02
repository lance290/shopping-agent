# PRD: Lead Fees & Merchant Monetization

**Status:** Not built  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P2  
**Origin:** `Competitive_Analysis_PartFinder.md` — "Lead fees (charge merchant per RFP notification), success fees (% of closed deals), premium tier (priority placement)"

---

## Problem Statement

The competitive analysis identifies three merchant-side revenue streams beyond affiliate commissions and Stripe Connect fees. None are defined in Phase 4 PRDs:

1. **Lead fees** — Charge merchants per RFP notification received
2. **Success fees** — Percentage of closed deals (beyond Stripe Connect platform fee)
3. **Premium placement** — Merchants pay for priority positioning in search results

PRD 00 covers affiliate + Stripe Connect but these are **buyer-initiated** revenue. Lead fees and success fees are **seller-initiated** revenue — a fundamentally different model that creates recurring merchant value.

**Current state:** Merchants register for free, receive outreach for free, and face no platform fees on quotes.

---

## Requirements

### R1: Lead Fee Model (P2)

Charge merchants when they receive an RFP notification matching their category.

**Model options:**
- **Per-lead:** $X per RFP notification (e.g., $2-10 depending on category)
- **Credit-based:** Merchant buys a credit pack (e.g., 50 leads for $100)
- **Subscription:** Included in premium tier (see PRD 03 entitlements)

**Acceptance criteria:**
- [ ] `MerchantLedger` model tracks lead credits/charges per merchant
- [ ] RFP notification only sent to merchants with available credits (or on subscription)
- [ ] Merchant dashboard shows credit balance and lead history
- [ ] Admin can grant free credits (e.g., onboarding bonus)

### R2: Success Fee Model (P2)

Take a percentage when a merchant's quote results in a closed deal.

**Model:**
- Default: 5% of deal value (configurable per category)
- Charged via Stripe Connect `application_fee_amount` (already in PRD 00)
- Or invoiced monthly for deals closed via email handoff (non-Stripe)

**Acceptance criteria:**
- [ ] Success fee tracked on `DealHandoff` and `PurchaseEvent`
- [ ] Merchant dashboard shows fees charged and net earnings
- [ ] Fee rate configurable per merchant and per category

### R3: Premium Placement (P3)

Merchants pay for priority positioning when their bids appear in buyer rows.

**Model:**
- Premium merchants' bids get a score boost (e.g., +15% on `combined_score`)
- Premium badge on their tiles ("Featured Seller")
- Priority in RFP matching (appear before free-tier merchants)

**Acceptance criteria:**
- [ ] `Merchant.is_premium` flag
- [ ] Score boost applied in ranking (PRD 11 integration)
- [ ] "Featured" badge on premium merchant tiles
- [ ] Premium status included in entitlement tier (PRD 03)

---

## Technical Implementation

### Backend

**New models:**
- `MerchantLedger(merchant_id, type, amount, description, created_at)` — Credit/debit ledger

**Modified models:**
- `Merchant` — Add `lead_credits`, `is_premium`, `success_fee_rate`
- `DealHandoff` — Add `success_fee_amount`

**New files:**
- `apps/backend/services/merchant_billing.py` — Lead credit management, success fee calculation

### Frontend
- Merchant dashboard: credit balance, lead history, earnings
- Premium badge component on tiles

---

## Dependencies

- Phase 4 PRD 00 (revenue) — Stripe Connect for success fee collection
- Phase 4 PRD 04 (seller tiles) — Quote intake must exist
- Phase 5 PRD 00 (notifications) — RFP notifications are the "leads" being charged for
- Phase 5 PRD 03 (entitlements) — Premium tier definitions

---

## Effort Estimate

- **R1:** Medium (2 days — ledger model + credit system + dashboard)
- **R2:** Small (1 day — fee tracking on existing deal flow)
- **R3:** Small (half-day — flag + score boost + badge)
