# PRD: Unified Closing Layer (Stripe + DocuSign)

**Status:** Scaffold only — critical monetization gap  
**Last Updated:** 2026-02-06 (gap analysis pass)

## Implementation Status (as of 2026-02-06)

| Feature | Status | Current Code |
|---------|--------|-------------|
| Stripe Checkout (single bid, retail) | ✅ Done | `routes/checkout.py` — creates session, redirects buyer |
| Stripe webhook handling | ✅ Done | `POST /api/webhooks/stripe` — records PurchaseEvent |
| PurchaseEvent tracking | ✅ Done | Model with amount, currency, payment_method, status |
| Bid.is_selected flag | ✅ Done | Buyer can select/lock a tile |
| Affiliate clickout tracking | ✅ Done | `routes/clickout.py` + `affiliate.py` (handlers coded) |
| **Platform revenue capture** | **🚨 NOT DONE** | **No Stripe Connect, no application_fee, no commission** |
| Affiliate tags configured | ❌ Not done | `AMAZON_AFFILIATE_TAG=`, `EBAY_CAMPAIGN_ID=`, `SKIMLINKS_PUBLISHER_ID=` all empty |
| Multi-vendor checkout | ❌ Not built | Can only buy one bid at a time |
| Closing status per tile | ❌ Not built | No `closing_status` field — buyer can't see pending/completed state |
| DocuSign integration | ❌ Scaffold only | `Contract` model has columns but zero API integration |
| C2C closing flow | ❌ Not built | Not addressed anywhere |

### 🚨 CRITICAL: Revenue Gap

**The platform currently captures zero revenue from transactions.**

- **Stripe Checkout** creates sessions but money goes to the merchant, not BuyAnything.ai. There's no `application_fee_amount`, no Stripe Connect onboarding for sellers, no platform cut.
- **Affiliate links** are coded (Amazon Associates, eBay Partner, Skimlinks) but all env vars are empty — every clickout goes through without a tag.
- **PurchaseEvent** tracks amounts but has no `platform_fee`, `commission_amount`, or `commission_rate` fields.

**This PRD must address how BuyAnything.ai gets paid before building multi-vendor checkout or DocuSign.**

### Revenue model options to specify:
1. **Affiliate commissions (B2C):** Configure affiliate tags — immediate revenue, no code changes needed.
2. **Stripe Connect (marketplace fee):** Sellers onboard via Stripe Connect; `application_fee_amount` on each checkout session gives you a percentage. Requires Stripe Connect setup + seller onboarding flow.
3. **Transaction fees (B2B):** Flat fee or percentage on B2B contract value. Requires invoicing/billing infrastructure.
4. **Subscription/premium tiers:** Charge sellers for visibility or priority placement. Future.

## Business Outcome
- Measurable impact: Increase “intent-to-close” completion by allowing retail payment and B2B contract execution to occur in a single consistent flow.
- Target users:
  - Buyers selecting a final tile
  - Sellers closing a deal (especially B2B)

## Scope
- In-scope:
  - Retail closing flow via a checkout experience
  - B2B closing flow where a “contract required” selection triggers a DocuSign signing workflow
  - C2C closing supported only when it fits the same checkout pattern (non-escrow), with clear buyer/seller acknowledgement
  - Multi-vendor project: support closing more than one selected tile in a project
  - Status visibility: buyer can see whether a selected tile is pending payment/contract/completed
- Out-of-scope:
  - Proprietary fulfillment/logistics
  - Full invoicing/ERP replacement
  - Escrow, chargeback arbitration, dispute resolution workflows, and marketplace trust/safety tooling beyond basic audit logs

## User Flow
1. Buyer selects/locks a tile.
2. System identifies whether the selection is retail checkout or contract-required.
3. Retail: buyer completes payment.
4. B2B: system initiates contract signing for both parties.
5. System marks the selection as closed and updates the project view.

## Business Requirements

### Authentication & Authorization
- Only the buyer (and authorized collaborators) can initiate closing.
- Only the buyer and the relevant seller can access contract documents.

### Monitoring & Visibility
- Track:
  - Intent-to-close conversion rate
  - Payment success rate
  - Contract completion rate
  - Time to close (payment/contract)

### Billing & Entitlements
- Retail: supports affiliate model and/or direct transaction processing per business policy.
- B2B: supports transaction fees per business policy.

### Data Requirements
- Persist:
  - Closing state per selected tile
  - Payment/contract references (identifiers and status)
  - Audit logs for signing and payment events

### Performance Expectations
- Closing flow should be reliable and provide clear recovery paths.

### UX & Accessibility
- Buyer-facing closing UX must be consistent across retail and B2B.
- Status must be visible in the project/row UI.

### Privacy, Security & Compliance
- Payment and contract flows must meet provider security expectations.
- Audit trails must exist for compliance and dispute resolution.

## Dependencies
- Upstream:
  - Buyer workspace + tile provenance
  - Seller quote intake (for B2B)
- Downstream:
  - Growth/analytics and optimization

## Risks & Mitigations
- Contract/payment failures create trust issues → clear status + retries + support escalation.

## Acceptance Criteria (Business Validation)
- [ ] Buyer can complete a retail close for a selected tile (binary).
- [ ] Buyer can trigger a contract-required close and both parties can complete signing (binary).
- [ ] Project view reflects closing status per selected tile (binary).

## Traceability
- Parent PRD: `docs/prd/marketplace-pivot/parent.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---
**Note:** Technical implementation decisions are made during /plan and /task.
