# PRD: Auto-Captured Diagnostics & Redaction

## Business Outcome
- Measurable impact: Increase the % of bug reports that are “actionable on first pass” by attaching a minimal, safe diagnostics bundle.
- Success criteria: Diagnostics capture improves reproducibility while enforcing mandatory redaction and minimizing sensitive exposure.
- Target users: Internal engineering team; Reporter benefits indirectly.

## Scope
- In-scope:
  - Capture a minimal diagnostics bundle when enabled.
  - Apply mandatory redaction rules before storage and before sending to GitHub.
  - Make diagnostics available to internal team and as a summarized payload in the GitHub issue.
- Out-of-scope:
  - Full request/response body capture by default.
  - Session replay.

## User Flow
1. Reporter opens Report Bug modal; “Include diagnostics” is ON by default.
2. Reporter submits the report.
3. System attaches diagnostics bundle (redacted) to the internal bug artifact and provides a summary for AI.

## Business Requirements

### Authentication & Authorization
- Who needs access?
  - Internal team can access full stored diagnostics.
  - Reporter may be shown a simplified status only; diagnostics visibility to reporter is optional.
- What actions are permitted?
  - System can capture/store; internal team can view.
- What data is restricted?
  - Diagnostics must not leak secrets and must not be globally accessible.

### Monitoring & Visibility
- What business metrics matter?
  - % of reports with diagnostics attached.
  - % of reports deemed “enough context to attempt fix”.
- What operational visibility is needed?
  - Diagnostics capture errors and redaction failures.
- What user behavior needs tracking?
  - Opt-out rate for diagnostics toggle.

### Billing & Entitlements
- How is this monetized?
  - Not monetized; reduces engineering time.
- What entitlement rules apply?
  - Optionally restrict diagnostics capture based on environment (prod vs staging) or user role.
- What usage limits exist?
  - Ring buffer sizes and payload truncation.

### Data Requirements
- What information must persist?
  - App context (route, build ID, env, browser/OS).
  - Console ring buffer (last ~200 events).
  - Network failures ring buffer (last ~20 failures), storing metadata only.
  - Breadcrumbs (last ~20 user actions).
- How long must data be retained?
  - Defined retention window and deletion policy for diagnostics.
- What data relationships exist?
  - Diagnostics belong to a bug report.

### Performance Expectations
- What response times are acceptable?
  - Diagnostics capture must not materially degrade report submission.
- What throughput is expected?
  - Low volume; capture must be efficient.
- What availability is required?
  - Capture is best-effort; failure should not block report submission.

### UX & Accessibility
- What user experience standards apply?
  - Toggle is understandable and transparent (“Includes console + network errors; sensitive data removed”).
- What accessibility requirements?
  - Toggle and explanatory text are accessible.
- What devices/browsers must be supported?
  - Same baseline as app.

### Privacy, Security & Compliance
- What regulations apply?
  - Treat diagnostics as potentially containing PII even after redaction.
- What data protection is required?
  - Mandatory redaction of auth headers, cookies, tokens.
  - Truncate large payloads.
  - Default to storing metadata only for network requests.
- What audit trails are needed?
  - Record whether redaction was applied successfully; failures must be surfaced to internal team.

## Dependencies
- Upstream:
  - Bug report capture UX.
  - Bug report storage.
- Downstream:
  - GitHub issue creation to include diagnostic summaries.

## Risks & Mitigations
- Redaction misses a secret → Conservative redaction, strict allowlist, and validation checks.
- Diagnostics volume grows → Ring buffers and truncation; retention policy.

## Acceptance Criteria (Business Validation)
- [ ] When enabled, bug reports include: route/build/env, console ring buffer, network failure metadata, breadcrumbs (binary test).
- [ ] Redaction removes auth headers/cookies/tokens reliably (binary test).
- [ ] Capturing diagnostics does not prevent report submission if capture fails (binary test).

## Traceability
- Parent PRD: docs/prd/ai-bug-fixer/parent.md
- Product North Star: a new type of shopping platform that also allows bidding; establish a PoC for bug reporting/fixing using Claude and GitHub Actions.

---
allowed-tools: "*"
**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
