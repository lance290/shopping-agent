# PRD: Unified Chat & List Architecture

## Business Outcome
- **Measurable impact:** Increase daily active user (DAU) retention by 15% and increase cross-category purchases (e.g., users buying both groceries and high-ticket items).
- **Success criteria:** Zero regression in Pop user engagement metrics; 50% of active BuyAnything users adopt the new unified list within 30 days of feature flag rollout.
- **Target users:** All users across both "Pop" (budget optimizing) and "BuyAnything" (high-ticket/service) personas.

## Scope
- **In-scope:** Transitioning the entire frontend experience to a two-pane (Chat + List) mobile-first layout. Allowing users to maintain multiple shareable lists (`Projects`). Implementing "Zero-Shame" UX principles where $5 items and $5M items exist in the same visual hierarchy.
- **Out-of-scope:** The backend logic that dynamically renders the items (this is handled in `prd-sdui-comparison.md`).

## User Flow
1. User opens the application and lands on their default "Active List" view alongside a chat input.
2. User asks the agent to find an item (e.g., "Find me cheap paper towels" or "Charter a jet to Aspen").
3. The chat confirms understanding, and a new "Row" instantly appears on the list indicating a search is in progress.
4. User can share the URL of this list with a collaborator (spouse, assistant) to view or edit together.

## Business Requirements

### Authentication & Authorization
- **Who needs access?** Registered users and invited collaborators.
- **What actions are permitted?** List owners can add/remove items and invite members. Invited members inherit read/write access based on their project role.
- **What data is restricted?** Lists are strictly private unless explicitly shared via collaboration links.

### Monitoring & Visibility
- **What business metrics matter?** DAU, List creation rate, collaboration link share rate, cross-category request rate.
- **What operational visibility is needed?** Page load times for the list view, WebSocket/SSE connection stability for live list updates.
- **What user behavior needs tracking?** Which items are added to which lists, frequency of switching between lists.

### Billing & Entitlements
- **How is this monetized?** N/A for the list structure itself (monetization happens via item actions).
- **What entitlement rules apply?** No paywalls for creating or sharing lists.
- **What usage limits exist?** Standard anti-abuse rate limits on list creation and sharing endpoints.

## Data Requirements
- **What information must persist?** `Projects` (lists) and user membership to those projects.
- **How long must data be retained?** Indefinitely, until explicitly deleted by the user.

### Performance Expectations
- **What response times are acceptable?** Initial list load <500ms. Real-time updates via SSE must reflect on the screen in <100ms.
- **What availability is required?** 99.9% uptime for core list reading/writing.

### UX & Accessibility
- **What user experience standards apply?** Zero-Shame UX (premium feel for all items), mobile-first bottom navigation, desktop split-pane.
- **What accessibility requirements?** WCAG AA compliance, full screen-reader support for list traversal.
- **What devices/browsers must be supported?** iOS Safari, Android Chrome, modern desktop browsers.

### Privacy, Security & Compliance
- **What data protection is required?** UHNW user lists require strict confidentiality; vendor names in chat must respect NDA requirements.

## Dependencies
- **Upstream:** None. This is the foundational layout.
- **Downstream:** Requires `prd-sdui-comparison.md` to actually render the contents of the lists.

## Risks & Mitigations
- **Risk:** Existing BuyAnything users reject the vertical list format in favor of the old horizontal board.
- **Mitigation:** Roll out via an opt-in feature flag first. Monitor engagement metrics before deprecating the old board.

## Acceptance Criteria (Business Validation)
- [ ] Initial list load time ≤500ms (current baseline: ~800ms for heavy boards).
- [ ] List sharing link successfully grants access to an unauthenticated user post-signup.
- [ ] Mobile view correctly displays Chat and List as separate, easily navigable tabs.

## Traceability
- Parent PRD: `docs/active-dev/sdui-universal-list/parent.md`
