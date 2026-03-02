# PRD L1: Revenue & Monetization Layer

**Priority:** P0 — Pre-launch
**Target:** Week 1 (Feb 10–14, 2026)
**Depends on:** Business entity incorporation (B1), Stripe account (S1)

---

## Problem

The platform currently has **zero revenue capture mechanisms active**:

- Affiliate link handlers exist (`affiliate.py`) but all env vars are empty
- Clickout tracking logs every click but appends no affiliate tags
- Stripe Checkout creates payment sessions but takes **no platform cut** — no `application_fee_amount`, no Stripe Connect
- `PurchaseEvent` model has no `platform_fee`, `commission_amount`, or `commission_rate` fields

**We are facilitating transactions and getting $0.**

---

## Solution

### R1 — Affiliate Tag Configuration (Day 1)

Set environment variables in Railway production:

```
AMAZON_AFFILIATE_TAG=buyanything-20
EBAY_CAMPAIGN_ID=<from eBay Partner Network>
SKIMLINKS_PUBLISHER_ID=<from Skimlinks dashboard>
```

Code already exists in `apps/backend/affiliate.py` to append tags. This is a config change, not a code change.

**Verification:** Click an Amazon product link → URL contains `tag=buyanything-20`.

### R2 — Stripe Connect Onboarding (Day 2–3)

Enable Stripe Connect so the platform can take fees on seller transactions.

1. Enable Connect in Stripe Dashboard
2. Choose **Standard** accounts (sellers manage their own Stripe)
3. Wire `routes/stripe_connect.py` onboarding endpoint to real Stripe API
4. On checkout, add `application_fee_amount` (calculated from commission rate)
5. Add `payment_intent_data.transfer_data.destination` for seller's connected account

### R3 — Commission Model (Day 2)

Define rates per category:

| Category | Commission | Rationale |
|----------|-----------|-----------|
| Products (affiliate) | 1–10% (varies by program) | Amazon/eBay set these |
| Services (platform-facilitated) | 8% | Market rate for service marketplaces |
| High-value (>$10K) | 5% | Volume discount for jets, major contracts |
| Lead fee (no transaction) | $5–25 per qualified lead | Sellers pay for buyer introductions |

Store in `CommissionConfig` table or environment config. Apply at checkout time.

### R4 — PurchaseEvent Enhancement (Day 3)

Add fields to `PurchaseEvent` model:

```python
platform_fee_amount = Column(Integer, nullable=True)  # cents
commission_rate = Column(Float, nullable=True)         # 0.0–1.0
affiliate_program = Column(String, nullable=True)      # "amazon", "ebay", "skimlinks"
affiliate_commission = Column(Integer, nullable=True)  # cents (estimated)
```

### R5 — Revenue Dashboard (Day 4–5)

Admin endpoint `GET /admin/revenue` returning:

- Total GMV (sum of all PurchaseEvents)
- Total platform fees collected
- Total affiliate clicks + estimated commission
- Revenue by category
- Revenue by day/week/month

---

## Acceptance Criteria

- [ ] Affiliate tags appended to all clickout URLs in production
- [ ] At least one Stripe Connect seller onboarded (test mode OK)
- [ ] `application_fee_amount` set on checkout sessions
- [ ] `PurchaseEvent` records commission data
- [ ] Admin can view revenue metrics

---

## Revenue Projections (Conservative)

| Month | GMV | Platform Fees (5–8%) | Affiliate Revenue | Total |
|-------|-----|---------------------|-------------------|-------|
| Mar 2026 | $10,000 | $600 | $200 | $800 |
| Apr 2026 | $50,000 | $3,000 | $500 | $3,500 |
| May 2026 | $150,000 | $9,000 | $1,500 | $10,500 |
