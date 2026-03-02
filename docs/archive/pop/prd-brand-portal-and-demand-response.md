# PRD: Brand Portal and Demand Response

## Business Outcome
- Measurable impact: Increase active brand participation and offer supply where user demand exists.
- Success criteria: Brands can onboard, publish offers, and respond to demand signals with measurable redemption impact.
- Target users: Brand admins managing category offer strategy.

## Scope
- In-scope: Brand onboarding/verification, offer publishing controls, demand alerts, basic brand performance visibility.
- Out-of-scope: Full enterprise media-buy tooling and complex campaign automation.

## User Flow
1. Brand admin signs up and verifies account ownership.
2. Brand configures eligible offer rules for categories/products.
3. Demand signals notify brands where offer gaps exist.
4. Brand publishes or updates offers and monitors redemption outcomes.

## Business Requirements

### Authentication & Authorization
- Brand admins must verify identity before publishing offers.
- Brand users may access only their own brand assets and analytics.
- Sensitive brand controls require role-based authorization.

### Monitoring & Visibility
- Track brand onboarding completion and time-to-first-offer.
- Track offer activation, spend, redemption volume, and conversion.
- Track demand-alert open/action rates to measure responsiveness.

### Billing & Entitlements
- Offer economics must support bid value, user benefit, and platform margin accounting.
- Brand usage tiers and limits must be enforceable.
- Invoice/reconciliation-ready event logs must be available.

### Data Requirements
- Persist brand profiles, verification status, offer rules, and lifecycle history.
- Persist demand-alert events and brand response actions.
- Persist offer-level performance metrics with period rollups.

### Performance Expectations
- Baseline brand portal activation and publish latency is measured during pilot.
- Demand alerts must be delivered with enough timeliness to influence active shopping windows.
- SLA targets are finalized after baseline measurement.

### UX & Accessibility
- Brand workflows must prioritize quick publish/update cycles for offers.
- Dashboard views must clearly show status, performance, and next action.
- Portal must support standard accessibility and modern browser compatibility.

### Privacy, Security & Compliance
- Brand insights must use aggregate household demand; no direct household identity disclosure.
- Brand action logs require auditability for compliance and dispute handling.
- Offer disclosures must meet advertising and consumer protection requirements.

## Dependencies
- Upstream: `prd-swap-discovery-and-claiming.md`.
- Downstream: `prd-referrals-growth-economics.md`.

## Risks & Mitigations
- Slow brand response may reduce household value perception.
  Mitigation: Support standing offer rules and scheduled outreach cadence.
- Misconfigured offers may create failed claims.
  Mitigation: Add validation rules and pre-publication checks.

## Acceptance Criteria (Business Validation)
- [ ] Baseline brand onboarding completion and time-to-first-offer are measured in first 2 weeks (source: pilot telemetry; Baseline TBD: measure in first 2 weeks).
- [ ] Verified brand admin can publish, pause, and expire offers from portal workflow (binary test).
- [ ] Demand alerts are generated for uncovered categories and delivery is logged (binary test).
- [ ] Brand dashboard exposes offer-level redemption and spend summary for sampled period (binary test).

## Traceability
- Parent PRD: `docs/PRD/need sourcing_ Bob@buy-anything.com.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---

**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
