# PRD: Revenue & Monetization Layer

**Status:** Not built — P0 priority  
**Created:** 2026-02-06  
**Last Updated:** 2026-02-06  
**Priority:** P0 — Must be addressed before any other Phase 4 work

---

## Problem Statement

BuyAnything.ai has a complete procurement pipeline (search → tile → select → checkout) but **captures zero revenue from any transaction**. Three revenue mechanisms are coded but none are active:

1. **Affiliate links** — Handlers exist for Amazon, eBay, Skimlinks but all env vars are empty.
2. **Stripe Checkout** — Creates payment sessions but with no platform cut (no Stripe Connect, no `application_fee_amount`).
3. **B2B transaction fees** — Referenced in PRDs but zero implementation.

This PRD defines the monetization layer that must be in place for the platform to generate revenue.

---

## Revenue Streams

### Stream 1: Affiliate Commissions (B2C — Immediate)

**How it works:** When a buyer clicks out to Amazon/eBay/etc., the URL is rewritten to include an affiliate tag. When the buyer purchases, BuyAnything.ai earns a commission (typically 2-10%).

**Current state:**
- `affiliate.py` has `AmazonAssociatesHandler`, `EbayPartnerHandler`, `SkimlinksHandler` — all coded and working.
- `routes/clickout.py` logs every clickout and applies affiliate transforms.
- `ClickoutEvent` model persists every click for attribution.

**What's needed:**
- [ ] Sign up for Amazon Associates, eBay Partner Network, Skimlinks accounts
- [ ] Set env vars: `AMAZON_AFFILIATE_TAG`, `EBAY_CAMPAIGN_ID`, `EBAY_ROTATION_ID`, `SKIMLINKS_PUBLISHER_ID`
- [ ] Verify affiliate links are appended correctly (test with real clickout)
- [ ] Add commission tracking: extend `PurchaseEvent` with `commission_rate` and `estimated_commission` fields
- [ ] Build simple revenue dashboard in admin panel (total clicks, estimated commissions by merchant)

**Effort:** Small (mostly config + minor model changes)  
**Revenue timeline:** Immediate once tags are configured

---

### Stream 2: Stripe Connect Marketplace Fee (B2C/B2B — Medium-term)

**How it works:** Sellers onboard via Stripe Connect. When a buyer pays through Stripe Checkout, BuyAnything.ai takes a percentage via `application_fee_amount` on the checkout session.

**Current state:**
- `routes/checkout.py` creates Stripe Checkout sessions but with no connected account and no application fee.
- `Merchant` model exists with auth linkage but no Stripe Connect account ID.

**What's needed:**
- [ ] Enable Stripe Connect on the Stripe account (choose platform type: Standard or Express)
- [ ] Add `stripe_account_id` field to `Merchant` model
- [ ] Build Stripe Connect onboarding flow:
  - Seller clicks "Connect payment account" on seller dashboard
  - Redirect to Stripe-hosted onboarding
  - Webhook captures `account.updated` event to store `stripe_account_id`
- [ ] Update `routes/checkout.py` to include:
  - `stripe_account` parameter (connected account)
  - `application_fee_amount` (platform fee in cents)
- [ ] Add `platform_fee_amount` and `commission_rate` to `PurchaseEvent` model
- [ ] Add payout visibility for sellers (earnings, pending payouts)
- [ ] Add revenue reporting for admin (total platform fees, by merchant, by period)

**Effort:** Medium (Stripe Connect setup + onboarding flow + checkout changes)  
**Revenue timeline:** Once first seller completes Stripe Connect onboarding

---

### Stream 3: B2B Transaction Fees (B2B — Future)

**How it works:** For B2B deals closed via DocuSign/contract, BuyAnything.ai charges a transaction fee (flat or percentage) on the contract value.

**Current state:**
- `Contract` model exists but DocuSign integration is scaffold-only.

**What's needed:**
- [ ] Define fee structure (% of contract value, flat fee, or tiered)
- [ ] Implement invoicing for B2B transaction fees
- [ ] Integrate with DocuSign (prerequisite: PRD 05 closing layer)
- [ ] Add `transaction_fee` to `Contract` model

**Effort:** Large (depends on DocuSign integration)  
**Revenue timeline:** After DocuSign integration is complete

---

### Stream 4: Premium Seller Features (Future)

**How it works:** Sellers pay for priority placement, enhanced visibility, or advanced analytics.

**Current state:** Nothing built.

**What's needed:**
- [ ] Define premium tier features
- [ ] Implement subscription billing (Stripe Subscriptions)
- [ ] Build feature gating

**Effort:** Large  
**Revenue timeline:** After marketplace has meaningful seller volume

---

## Data Model Changes

```python
# Extend PurchaseEvent
class PurchaseEvent(SQLModel, table=True):
    # ... existing fields ...
    
    # Revenue tracking (NEW)
    platform_fee_amount: Optional[float] = None  # Amount BuyAnything.ai earns
    commission_rate: Optional[float] = None       # e.g., 0.05 for 5%
    revenue_type: str = "affiliate"               # "affiliate", "stripe_connect", "transaction_fee"
    
# Extend Merchant  
class Merchant(SQLModel, table=True):
    # ... existing fields ...
    
    # Stripe Connect (NEW)
    stripe_account_id: Optional[str] = None       # Stripe Connected Account ID
    stripe_onboarding_complete: bool = False
    default_commission_rate: float = 0.05          # 5% default platform fee
```

---

## Environment Variables

| Variable | Description | Status |
|----------|-------------|--------|
| `AMAZON_AFFILIATE_TAG` | Amazon Associates tag (e.g., `buyanything-20`) | ❌ Empty |
| `EBAY_CAMPAIGN_ID` | eBay Partner Network campaign ID | ❌ Empty |
| `EBAY_ROTATION_ID` | eBay marketplace rotation ID | ❌ Empty |
| `SKIMLINKS_PUBLISHER_ID` | Skimlinks universal affiliate publisher ID | ❌ Empty |
| `STRIPE_CONNECT_CLIENT_ID` | Stripe Connect OAuth client ID | ❌ Not set |
| `DEFAULT_PLATFORM_FEE_RATE` | Default % fee on Stripe Connect transactions | ❌ Not set |

---

## Acceptance Criteria

- [ ] At least one affiliate program is configured and clickout URLs include tags (binary).
- [ ] `PurchaseEvent` records `platform_fee_amount` for affiliate and Stripe Connect transactions (binary).
- [ ] Admin dashboard shows estimated revenue by stream (binary).
- [ ] (Stripe Connect) A seller can complete onboarding and their `stripe_account_id` is stored (binary).
- [ ] (Stripe Connect) A buyer checkout creates a session with `application_fee_amount` going to BuyAnything.ai (binary).

---

## Priority & Phasing

| Phase | What | Effort | Revenue Impact |
|-------|------|--------|---------------|
| **Now** | Configure affiliate tags (env vars only) | 1 hour | Immediate — every clickout earns |
| **Next** | Add `platform_fee_amount`/`commission_rate` to PurchaseEvent | 1 day | Tracking only |
| **Next** | Admin revenue dashboard | 2 days | Visibility |
| **Later** | Stripe Connect onboarding + marketplace fee | 1 week | Direct transaction revenue |
| **Future** | B2B transaction fees + DocuSign | 2+ weeks | B2B revenue |
| **Future** | Premium seller tiers | TBD | Subscription revenue |

---

## Business Requirements

### Authentication & Authorization
- Affiliate tag configuration is backend-only (env vars) — no user-facing auth needed.
- Stripe Connect onboarding requires seller authentication (existing `get_current_session()` dependency).
- Revenue dashboard is admin-only (existing admin auth check in `routes/admin.py`).

### Monitoring & Visibility
- Track: affiliate clickout count per provider, estimated commission per clickout, Stripe Connect `application_fee_amount` per transaction, total platform revenue by stream by period.
- Alert on: affiliate tag misconfiguration (clickout without tag), Stripe Connect webhook failures.

### Billing & Entitlements
- This PRD *defines* the billing layer for the platform.
- No user-facing billing changes needed for affiliate stream.
- Stripe Connect stream requires seller onboarding flow.

### Data Requirements
- Extend `PurchaseEvent` with `platform_fee_amount`, `commission_rate`, `revenue_type`.
- Extend `Merchant` with `stripe_account_id`, `stripe_onboarding_complete`, `default_commission_rate`.
- Persist affiliate click attribution in existing `ClickoutEvent`.

### Performance Expectations
- Affiliate URL rewriting must add < 50ms to clickout redirect.
- Stripe Connect `application_fee_amount` adds zero latency (included in existing checkout session creation).

### UX & Accessibility
- Seller dashboard: show earnings, pending payouts, onboarding status.
- Admin dashboard: show revenue by stream.
- No buyer-facing UX changes.

### Privacy, Security & Compliance
- Stripe API keys must never be exposed to frontend.
- Affiliate tags are non-sensitive but should not leak user identity.
- Stripe Connect requires seller consent for platform fee deduction (handled by Stripe-hosted onboarding).

## Dependencies

- Upstream: Stripe account (✅ exists), Merchant model with auth (✅ done)
- Downstream: PRD 05 (Unified Closing Layer) uses this for payment processing

## Traceability

- Parent PRD: `docs/prd/marketplace-pivot/parent.md`
- Gap Analysis: `docs/prd/phase4/GAP-ANALYSIS.md`
