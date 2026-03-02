# PRD: WhatsApp Expansion and Scale Operations

## Business Outcome
- Measurable impact: Expand household reach while maintaining reliability and economics at higher volume.
- Success criteria: Additional channels and scale controls increase active households without degrading core savings loop.
- Target users: Existing and new households preferring expanded channels, operations teams.

## Scope
- In-scope: Channel expansion readiness, operational scale controls, reliability governance, phased rollout gates.
- Out-of-scope: Full internationalization and non-core regional compliance programs.

## User Flow
1. Eligible households are invited to additional supported channel experiences.
2. Channel interactions continue to update the same household list/savings lifecycle.
3. Operations monitor reliability, queue health, and user outcome impact during rollout.
4. Rollout expands only after performance and quality gates pass.

## Business Requirements

### Authentication & Authorization
- Channel expansion must preserve household identity and authorization boundaries.
- Account linking across channels must require verified ownership.
- Operations overrides must be role-restricted and auditable.

### Monitoring & Visibility
- Track channel-specific activation, engagement, and failure rates.
- Track end-to-end latency, queue depth, and cross-channel delivery success.
- Define rollback triggers for degraded user outcomes.

### Billing & Entitlements
- Additional channel cost impact must be visible at household and platform levels.
- Entitlement controls must support staged access by segment.
- Economics dashboards must show savings/revenue impact by channel.

### Data Requirements
- Persist channel-link state per user/household.
- Persist rollout cohort membership and gate decisions.
- Retain reliability and incident history for postmortems.

### Performance Expectations
- Baseline channel reliability and latency must be measured before broad rollout.
- Expansion cannot reduce core loop completion metrics below approved guardrail thresholds.
- Scale thresholds and guardrails are approved after pilot baseline collection.

### UX & Accessibility
- Channel-specific messaging should remain consistent with core Bob behavior.
- Household members should understand channel limitations and fallback options.
- Support flows must be accessible from mobile-first contexts.

### Privacy, Security & Compliance
- Cross-channel identity data must be protected and minimally shared.
- Expansion must pass privacy/security review before each rollout stage.
- Incident response and audit logs must be operationally complete.

## Dependencies
- Upstream: `prd-onboarding-and-intake.md`, `prd-shared-list-collaboration.md`, `prd-referrals-growth-economics.md`.
- Downstream: None.

## Risks & Mitigations
- Channel platform constraints may reduce feature parity.
  Mitigation: Publish explicit capability matrix and fallback behavior.
- Scale incidents may degrade trust in savings loop.
  Mitigation: Use staged cohorts with rollback gates and SRE runbooks.

## Acceptance Criteria (Business Validation)
- [ ] Baseline channel-specific reliability and engagement metrics are measured in first 2 weeks of controlled rollout (source: rollout telemetry; Baseline TBD: measure in first 2 weeks).
- [ ] A linked household can use expanded channel entry while preserving shared list continuity (binary test).
- [ ] Rollout gate criteria and rollback triggers are documented and approved before expansion beyond pilot cohort (binary governance gate).
- [ ] Operations dashboard exposes channel-level health and incident indicators for on-call use (binary test).

## Traceability
- Parent PRD: `docs/PRD/need sourcing_ Bob@buy-anything.com.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---

**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
