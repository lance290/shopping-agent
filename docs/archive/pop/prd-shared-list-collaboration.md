# PRD: Shared List Collaboration and Item Capture

## Business Outcome
- Measurable impact: Increase successful item capture and list collaboration across household members.
- Success criteria: Higher proportion of household messages converted into actionable list state.
- Target users: Household members contributing grocery needs asynchronously.

## Scope
- In-scope: Natural-language item capture, shared list updates, member-visible list status, basic list management actions.
- Out-of-scope: Financial crediting, payout workflows, advanced brand analytics.

## User Flow
1. A household member sends a message containing shopping intent.
2. Bob interprets intent and updates the shared list.
3. Household members view updated list state through messaging feedback and web list view.
4. Members confirm, edit, or remove items as needed.

## Business Requirements

### Authentication & Authorization
- Only verified household members can add, edit, or remove list items.
- Household owners retain override permissions for list integrity.
- Access to list history is restricted to household participants.

### Monitoring & Visibility
- Track item capture rate, correction rate, and ignored-message rate.
- Track list update activity by household and channel.
- Provide visibility into unresolved parsing failures requiring follow-up.

### Billing & Entitlements
- Base list collaboration remains included for all households.
- Entitlement hooks must support future premium collaboration features.
- Collaboration usage metrics must be available for pricing analysis.

### Data Requirements
- Persist list items with creator, status, and change history.
- Preserve household list history for reconciliation and learning.
- Maintain canonical item/category mapping sufficient for downstream offer matching.

### Performance Expectations
- Baseline message-to-list-update completion time is measured in pilot window.
- List state must remain consistent when multiple members update concurrently.
- Reliability target must be defined after initial telemetry collection.

### UX & Accessibility
- Item add/edit/remove interactions must be understandable in text and web views.
- List view must preserve readability for large lists and screen-reader navigation.
- User actions must provide clear success/failure feedback.

### Privacy, Security & Compliance
- Message content retained for list operations must be minimized to business necessity.
- Household data must not leak across group boundaries.
- Access and mutation events require audit visibility.

## Dependencies
- Upstream: `prd-onboarding-and-intake.md`.
- Downstream: `prd-swap-discovery-and-claiming.md`.

## Risks & Mitigations
- Misclassified intent may reduce trust in automation.
  Mitigation: Provide simple correction path and track correction frequency.
- Concurrent edits may create conflicting list state.
  Mitigation: Define deterministic conflict resolution and event history.

## Acceptance Criteria (Business Validation)
- [ ] Baseline item-capture accuracy and correction rate are measured in first 2 weeks (source: pilot telemetry; Baseline TBD: measure in first 2 weeks).
- [ ] Household members can add, edit, and remove list items from at least one supported channel and from web list view (binary test).
- [ ] Concurrent list edits from two members do not produce data loss in UAT scenarios (binary test).
- [ ] Product owner approves quantitative reliability target after baseline collection (binary governance gate).

## Traceability
- Parent PRD: `docs/PRD/need sourcing_ Bob@buy-anything.com.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---

**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
