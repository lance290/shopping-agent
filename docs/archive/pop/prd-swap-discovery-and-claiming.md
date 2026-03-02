# PRD: Swap Discovery and Claiming Experience

## Business Outcome
- Measurable impact: Increase claimable savings opportunities per active household list.
- Success criteria: Households can discover and claim relevant savings offers during list planning.
- Target users: Budget-conscious shoppers selecting offers before checkout.

## Scope
- In-scope: Offer discovery for list items, ranked presentation, claim lifecycle management, claim expiration rules.
- Out-of-scope: Receipt validation and wallet payout settlement.

## User Flow
1. A list item is present in a household list.
2. Bob surfaces available swaps/offers tied to that item or category.
3. User reviews offers and claims one or more eligible options.
4. Claim status becomes visible for later redemption.

## Business Requirements

### Authentication & Authorization
- Only authenticated household members can claim or cancel claims.
- Claims are tied to the actor and household context.
- Unauthorized claim attempts must be denied and logged.

### Monitoring & Visibility
- Track offer impression rate, claim conversion rate, and claim expiration rate.
- Track category-level offer coverage gaps.
- Surface no-offer scenarios for supply-side follow-up.

### Billing & Entitlements
- Claiming behavior must support future monetization/entitlement controls by plan tier.
- Offer sponsorship rules must be transparent and auditable.
- Usage limits (if any) must be enforceable and explainable to users.

### Data Requirements
- Persist offer metadata shown to users at claim time.
- Persist claim timestamps, status transitions, and expiration windows.
- Retain attribution context needed for downstream revenue/reward calculations.

### Performance Expectations
- Baseline time from item availability to offer visibility must be measured.
- Claim confirmation feedback must be immediate enough for in-session user confidence.
- Coverage and latency targets are defined after pilot baseline collection.

### UX & Accessibility
- Offer cards must communicate value, eligibility, and expiration clearly.
- Claim actions must be one-step and reversible when policy allows.
- Offer interactions must be keyboard and screen-reader accessible on web views.

### Privacy, Security & Compliance
- Offer personalization must avoid exposing private household data to brands.
- Claim activity must be retained for dispute handling and audit.
- Policy disclosures (eligibility, expiration, sponsor context) must be visible.

## Dependencies
- Upstream: `prd-onboarding-and-intake.md`, `prd-shared-list-collaboration.md`.
- Downstream: `prd-receipt-redemption-and-wallet.md`, `prd-brand-portal-and-demand-response.md`.

## Risks & Mitigations
- Low offer coverage could reduce perceived value.
  Mitigation: Add demand signals and supply-side escalation path.
- Ambiguous ranking logic may erode trust.
  Mitigation: Define transparent ranking and sponsorship disclosures.

## Acceptance Criteria (Business Validation)
- [ ] Baseline offer coverage and claim conversion are measured in first 2 weeks (source: pilot telemetry; Baseline TBD: measure in first 2 weeks).
- [ ] A household member can claim and cancel (when eligible) an offer from list context (binary test).
- [ ] Claim expirations are enforced and visibly communicated to users (binary test).
- [ ] Policy-approved quantitative claim-conversion target is documented after baseline collection (binary governance gate).

## Traceability
- Parent PRD: `docs/PRD/need sourcing_ Bob@buy-anything.com.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---

**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
