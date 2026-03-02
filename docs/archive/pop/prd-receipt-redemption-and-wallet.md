# PRD: Receipt Redemption and Wallet Credit Loop

## Business Outcome
- Measurable impact: Convert claimed offers into verified user savings and wallet credits.
- Success criteria: Users complete redemption loop with transparent credit outcomes.
- Target users: Shoppers who claim offers and submit purchase proof.

## Scope
- In-scope: Receipt submission, validation outcome communication, claim redemption state transitions, wallet credit posting, payout request policy.
- Out-of-scope: Advanced fraud adjudication tooling and non-core payout rails.

## User Flow
1. User submits receipt after shopping.
2. System validates submitted proof against claimed offers.
3. Eligible claims are marked redeemed and wallet balance updates.
4. User sees redemption summary and available balance.
5. User can request payout when policy thresholds are met.

## Business Requirements

### Authentication & Authorization
- Only authenticated users can submit receipts and request payouts.
- Users can view only their own redemption and wallet history.
- Administrative exception access must be audited and policy-bound.

### Monitoring & Visibility
- Track submission-to-resolution time, match rate, and failure reasons.
- Track credited value, payout requests, payout completion, and reversals.
- Monitor duplicate/fraud indicators and manual-review volumes.

### Billing & Entitlements
- Wallet credits follow documented economic rules from approved offers.
- Minimum payout threshold policy must be explicit and user-visible.
- Entitlement controls must support staged rollout of payout features.

### Data Requirements
- Persist receipt submission record, validation outcome, and redemption linkage.
- Persist immutable wallet transaction history suitable for reconciliation.
- Retain dispute and adjustment context for support/compliance.

### Performance Expectations
- Baseline receipt resolution time must be measured in pilot window.
- Users must receive explicit status updates for pending, succeeded, and failed outcomes.
- Service-level targets are finalized after baseline telemetry.

### UX & Accessibility
- Receipt submission path must be usable from mobile-first contexts.
- Wallet balance and transaction history must be understandable and auditable by users.
- Error states must explain next action (retry, dispute, support).

### Privacy, Security & Compliance
- Financial and receipt data must be handled as sensitive user information.
- Retention and deletion policies must align to legal/compliance obligations.
- Ledger changes must be traceable with non-repudiable audit history.

## Dependencies
- Upstream: `prd-swap-discovery-and-claiming.md`.
- Downstream: `prd-referrals-growth-economics.md`.

## Risks & Mitigations
- False negatives in receipt matching may frustrate users.
  Mitigation: Provide dispute path with clear turnaround expectations.
- Financial reconciliation errors could create trust/compliance risk.
  Mitigation: Enforce immutable transaction records and daily reconciliation controls.

## Acceptance Criteria (Business Validation)
- [ ] Baseline redemption match rate and processing time are measured in first 2 weeks (source: pilot telemetry; Baseline TBD: measure in first 2 weeks).
- [ ] User receives a clear success/failure outcome for each submitted receipt (binary test).
- [ ] Wallet history shows a complete chronological record of credits/debits for sampled users (binary test).
- [ ] Minimum payout threshold policy is documented and visible to users before payout submission (binary test; source requirement references $5.00 default assumption).

## Traceability
- Parent PRD: `docs/PRD/need sourcing_ Bob@buy-anything.com.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---

**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
