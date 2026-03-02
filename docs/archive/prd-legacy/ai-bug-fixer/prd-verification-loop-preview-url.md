# PRD: Verification Loop (PR Status + Preview URL to Reporter)

## Business Outcome
- Measurable impact: Close the loop with non-technical reporters by enabling verification of a proposed fix via an accessible preview URL, without GitHub access.
- Success criteria: Reporter can see when a fix is ready, open a preview, and indicate “verified” so internal team can confidently ship.
- Target users: Investor (Reporter), Internal team.

## Scope
- In-scope:
  - Reporter-facing status progression that includes PR created and preview ready.
  - Surfacing a preview URL to the reporter when available.
  - Marking states that imply “needs verification” vs “verified”.
- Out-of-scope:
  - Implementing preview deployments themselves.
  - Automated merges.

## User Flow
1. Reporter submits a bug report.
2. System triggers AI and eventually a PR is created.
3. System updates bug report status to show PR created.
4. When a preview environment is ready, system attaches preview URL and moves to “Needs verification”.
5. Reporter opens preview URL and verifies.
6. Internal team merges and system marks “Shipped”.

## Business Requirements

### Authentication & Authorization
- Who needs access?
  - Reporter can view only their reports and preview URL.
- What actions are permitted?
  - Reporter can view preview URL; optionally can mark “verified”.
- What data is restricted?
  - Preview URL must not expose sensitive data; access controls are required where needed.

### Monitoring & Visibility
- What business metrics matter?
  - Time from report → PR created.
  - Time from PR created → preview ready.
  - Verification completion rate.
- What operational visibility is needed?
  - Missing preview URL or failed status update detection.
- What user behavior needs tracking?
  - Preview link clicks; verification acknowledgement.

### Billing & Entitlements
- How is this monetized?
  - Not monetized; improves velocity.
- What entitlement rules apply?
  - Preview URL may be gated for only allowed users.
- What usage limits exist?
  - Preview environments are ephemeral; access should expire when PR closes.

### Data Requirements
- What information must persist?
  - PR URL, preview URL, and status timestamps.
- How long must data be retained?
  - Must persist status history at least through ship and short post-ship window.
- What data relationships exist?
  - Bug report ↔ PR ↔ preview URL.

### Performance Expectations
- What response times are acceptable?
  - Status page should reflect updates promptly after external events.
- What throughput is expected?
  - Low volume.
- What availability is required?
  - Best-effort with retries; internal team can intervene when blocked.

### UX & Accessibility
- What user experience standards apply?
  - Clear statuses: Captured, AI working, PR created, Preview ready, Needs verification, Verified, Shipped.
  - Preview URL appears only when usable.
- What accessibility requirements?
  - Status text and actions are accessible.
- What devices/browsers must be supported?
  - Same baseline as app.

### Privacy, Security & Compliance
- What regulations apply?
  - Treat preview access as sensitive.
- What data protection is required?
  - Preview URLs should be protected (basic auth, login requirement, or other gating).
- What audit trails are needed?
  - Status transitions tied to external events (PR opened/merged, checks complete).

## Dependencies
- Upstream:
  - Bug report storage/status.
  - GitHub issue creation and PR creation.
- Downstream:
  - Shipping workflow to update status to Shipped.

## Risks & Mitigations
- Preview URL not available → Provide a fallback flow where internal team supplies a verification environment link.
- Reporter can’t access preview due to auth → Provide clear instructions and ensure previews support the intended reporter access method.

## Acceptance Criteria (Business Validation)
- [ ] Reporter status shows “PR created” when a PR exists (binary test).
- [ ] Reporter can see and open a preview URL when “Preview ready” (binary test).
- [ ] Status can be set to “Shipped” after merge (binary test).

## Traceability
- Parent PRD: docs/prd/ai-bug-fixer/parent.md
- Product North Star: a new type of shopping platform that also allows bidding; establish a PoC for bug reporting/fixing using Claude and GitHub Actions.

---
allowed-tools: "*"
**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
