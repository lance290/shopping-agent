# PRD: Household Onboarding and Multi-Channel Intake

## Business Outcome
- Measurable impact: Increase activated households entering Bob through email/SMS and reaching an active shared list state.
- Success criteria: Activation baseline is measured, then improved in pilot cohorts.
- Target users: Household organizers starting or inviting family members.

## Scope
- In-scope: New household creation, member identity verification, channel-linked household membership, first successful list interaction.
- Out-of-scope: Swap claiming, receipt redemption, wallet payout, brand analytics.

## User Flow
1. A user messages Bob through supported channel entry points.
2. Bob identifies whether this is a new or known household.
3. Bob confirms participant identities and captures minimum household setup details.
4. Bob confirms the household is active and ready for list collaboration.

## Business Requirements

### Authentication & Authorization
- Household participants must verify control of their channel identity before performing household actions.
- Household owners can add/remove members and grant collaborator permissions.
- Non-members cannot access household list actions.

### Monitoring & Visibility
- Track onboarding starts, completions, drop-offs, and time-to-activation by channel.
- Track identity verification success/failure rates.
- Expose daily activation trend for operations review.

### Billing & Entitlements
- No paid entitlement is required for onboarding in MVP.
- Entitlement model must allow future premium onboarding experiences without breaking base flow.
- Household-level eligibility flags must persist for downstream offer and redemption logic.

### Data Requirements
- Persist household identity, member roster, verification status, and preferred communication channel.
- Retain onboarding event history for funnel analysis.
- Maintain auditable linkage between channel identities and household records.

### Performance Expectations
- Baseline onboarding latency and completion time must be measured during first 2 pilot weeks.
- Household activation feedback must feel near-real-time to end users in pilot testing.
- Throughput must support pilot demand spikes without losing onboarding requests.

### UX & Accessibility
- Onboarding prompts must be short, unambiguous, and usable from text-first interfaces.
- Web-assisted steps (if used) must meet WCAG 2.1 AA expectations.
- Flow must support common mobile devices and modern desktop browsers.

### Privacy, Security & Compliance
- Personal contact data must be protected and only used for household operations.
- Consent for messaging must be explicit and revocable.
- Access attempts and verification failures must be logged for auditability.

## Dependencies
- Upstream: None.
- Downstream: `prd-shared-list-collaboration.md`, `prd-swap-discovery-and-claiming.md`.

## Risks & Mitigations
- Channel-specific limitations may block reliable group behavior.
  Mitigation: Define approved fallback flows that preserve shared-list activation outcome.
- Identity merge errors could create duplicate households.
  Mitigation: Require deterministic merge rules and audit trail for merges.

## Acceptance Criteria (Business Validation)
- [ ] Baseline onboarding funnel is instrumented within first 2 weeks, including start, completion, and drop-off rates (source: pilot telemetry; Baseline TBD: measure in first 2 weeks).
- [ ] A verified user can create a household and add at least one member in a controlled UAT flow (binary test).
- [ ] Non-member access attempts to household list actions are denied and logged (binary test).
- [ ] Time-to-activation target is defined from measured pilot baseline and approved by product owner (binary governance gate).

## Traceability
- Parent PRD: `docs/PRD/need sourcing_ Bob@buy-anything.com.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---

**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
