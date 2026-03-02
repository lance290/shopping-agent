# PRD: Entitlement Tiers & Usage Limits

**Status:** Not built  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P2  
**Origin:** `Competitive_Analysis_PartFinder.md` — "free: 10 vendors/row, premium: 50"

---

## Problem Statement

The competitive analysis against PartFinder identified entitlement tiers as a key monetization and retention lever. PartFinder offers Free/Pro/Enterprise tiers. BuyAnything.ai currently has no usage limits, no pricing tiers, and no feature gating for buyers or sellers.

Without tiers:
- No path to buyer-side revenue (all usage is free and unlimited)
- No upsell mechanism for power users
- No way to manage platform costs (LLM calls, search API calls)
- Competitive positioning lacks a clear pricing story for investors

**Current state:** All users have identical, unlimited access to all features.

---

## Requirements

### R1: Tier Definition (P1)

Define buyer and seller tiers with feature limits.

**Proposed tiers (buyer-side):**

| Feature | Free | Pro ($TBD/mo) |
|---------|------|----------------|
| Active rows | 5 | Unlimited |
| Vendors per outreach | 3 | 20 |
| Search providers | 2 | All |
| Share links | 3/month | Unlimited |
| Choice-factor depth | Basic (3 factors) | Full |
| Priority support | — | Yes |

**Proposed tiers (seller-side):**

| Feature | Free | Premium ($TBD/mo) |
|---------|------|--------------------|
| RFP notifications | 5/month | Unlimited |
| Quote submissions | 5/month | Unlimited |
| Priority placement | — | Yes |
| Analytics dashboard | Basic | Advanced |

**Acceptance criteria:**
- [ ] Tier definitions stored in config (not hardcoded)
- [ ] Each limit enforceable at the API level
- [ ] Tier can be changed per user by admin

### R2: Usage Tracking (P1)

Track usage against tier limits.

**Acceptance criteria:**
- [ ] `UserUsage` model tracks: active_rows_count, outreach_count_month, shares_count_month, quotes_count_month
- [ ] Counters reset monthly
- [ ] Usage checked before creating rows, outreach, shares, quotes

### R3: Limit Enforcement (P1)

Return clear errors when limits are exceeded.

**Acceptance criteria:**
- [ ] API returns 403 with `{"detail": "Row limit reached. Upgrade to Pro for unlimited rows.", "upgrade_url": "/pricing"}`
- [ ] Frontend shows upgrade prompt (not just an error)
- [ ] Admin can override limits per user

### R4: Subscription Billing (P2)

Integrate Stripe Subscriptions for paid tiers.

**Acceptance criteria:**
- [ ] `User.subscription_tier` field (free, pro, premium)
- [ ] `User.stripe_customer_id` for billing
- [ ] Pricing page at `/pricing`
- [ ] Stripe Checkout for subscription signup
- [ ] Webhook handles `customer.subscription.updated` and `customer.subscription.deleted`

### R5: Feature Gating UI (P2)

Show users what they're missing and how to upgrade.

**Acceptance criteria:**
- [ ] Locked features show a lock icon + "Pro feature" tooltip
- [ ] Usage meter in user settings (e.g., "3/5 rows used this month")
- [ ] Upgrade CTA in appropriate places (row creation, outreach trigger, share creation)

---

## Technical Implementation

### Backend

**New models:**
- `UserUsage(user_id, active_rows, outreach_this_month, shares_this_month, quotes_this_month, period_start)`

**Modified models:**
- `User` — Add `subscription_tier`, `stripe_customer_id`

**New files:**
- `apps/backend/services/entitlements.py` — Tier definitions + limit checking
- `apps/backend/routes/billing.py` — Subscription management endpoints

### Frontend
- `apps/frontend/app/pricing/page.tsx` — Pricing page
- `apps/frontend/app/components/UpgradePrompt.tsx` — Reusable upgrade CTA
- `apps/frontend/app/settings/page.tsx` — Usage meter

---

## Dependencies

- Phase 4 PRD 00 (revenue) — Stripe account must be configured
- Phase 5 PRD 04 (lead fees) — Seller tier limits feed into merchant monetization

---

## Effort Estimate

- **R1-R2:** Medium (1-2 days — tier config + usage tracking)
- **R3:** Small (half-day — enforcement middleware)
- **R4:** Medium (1-2 days — Stripe Subscriptions integration)
- **R5:** Medium (1 day — frontend gating UI)
