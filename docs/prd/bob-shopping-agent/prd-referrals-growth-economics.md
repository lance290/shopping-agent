# PRD: Referrals, Attribution, and Growth Economics

## Business Outcome
- Measurable impact: Increase qualified user growth and partner-aligned incentive outcomes.
- Success criteria: Referral flows attribute signups and apply approved earnings rules transparently.
- Target users: Referrers (users/brands), referred households, growth operations.

## Scope
- In-scope: Referral link generation, attribution window, earnings policy application, referral performance visibility.
- Out-of-scope: Multi-touch attribution modeling and enterprise affiliate marketplace integrations.

## User Flow
1. User or brand retrieves a referral link/code.
2. New household joins through referral path.
3. Attribution is recorded during onboarding/signup.
4. Eligible downstream events generate referral earnings according to policy.
5. Referrer can view referral performance and earnings history.

## Business Requirements

### Authentication & Authorization
- Referral creators must be authenticated to manage referral assets.
- Referral earnings visibility is limited to referral owner and authorized operators.
- Manual adjustments require privileged approval and audit log entry.

### Monitoring & Visibility
- Track referral clicks, attributed signups, and conversion to active households.
- Track earnings accrual, payout eligibility, and disputed attributions.
- Provide cohort reporting for growth planning.

### Billing & Entitlements
- Referral share policy must be explicit and versioned (source requirement: 30% affiliate payout assumption).
- Earnings events must reconcile with redemption economics.
- Tiered partner entitlements must be supported for future phases.

### Data Requirements
- Persist referral codes, attribution records, and eligibility window metadata.
- Persist earnings ledger entries tied to auditable source events.
- Retain historical policy version applied at time of accrual.

### Performance Expectations
- Attribution must complete within active onboarding/session context.
- Baseline referral funnel conversion must be measured before scaling spend.
- Growth targets are finalized after baseline telemetry review.

### UX & Accessibility
- Referral creation and sharing should require minimal steps.
- Referrers must understand status of clicks, signups, and earnings.
- Messaging around policy and eligibility must be plain-language.

### Privacy, Security & Compliance
- Referral tracking must respect consent and applicable privacy policy requirements.
- Data sharing between brand referrers and household users must remain privacy-safe.
- Earnings history must be auditable for finance/compliance review.

## Dependencies
- Upstream: `prd-onboarding-and-intake.md`, `prd-receipt-redemption-and-wallet.md`, `prd-brand-portal-and-demand-response.md`.
- Downstream: `prd-whatsapp-and-scale-operations.md`.

## Risks & Mitigations
- Attribution disputes can erode trust.
  Mitigation: Publish clear attribution rules and keep immutable event history.
- Incentive policy changes may create retroactive confusion.
  Mitigation: Version referral policy and expose effective-date metadata.

## Acceptance Criteria (Business Validation)
- [ ] Baseline referral click-to-signup conversion is measured in first 2 weeks (source: pilot telemetry; Baseline TBD: measure in first 2 weeks).
- [ ] Authenticated user can generate and share a referral link/code (binary test).
- [ ] Attributed signup is recorded with source referral and attribution timestamp (binary test).
- [ ] Referral earnings policy is documented with explicit share rule and effective date (binary test; source requirement references 30% payout assumption).

## Traceability
- Parent PRD: `docs/PRD/need sourcing_ Bob@buy-anything.com.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---

**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
