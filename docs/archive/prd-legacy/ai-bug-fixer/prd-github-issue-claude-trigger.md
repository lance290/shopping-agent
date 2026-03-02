# PRD: GitHub Issue Creation & Claude Trigger

## Business Outcome
- Measurable impact: Convert bug reports into a reproducible engineering work item that triggers an AI-assisted remediation attempt, producing a reviewable PR.
- Success criteria: Each qualifying bug report creates a private GitHub issue containing sufficient context and a consistent instruction block that reliably triggers Claude Code GitHub Actions.
- Target users: Internal engineering team; indirectly the Reporter (who benefits from faster fixes).

## Scope
- In-scope:
  - Create a private GitHub issue per bug report.
  - Include structured content: reporter notes (verbatim), screenshots URLs, environment/repro context, and an AI instruction block.
  - Trigger mechanism to start Claude (e.g., via `@claude` mention semantics).
- Out-of-scope:
  - Implementing the Claude workflow itself.
  - Autonomously merging PRs.
  - Capturing diagnostics (handled by separate PRD).

## User Flow
1. Reporter submits bug report.
2. System creates an internal bug artifact.
3. System creates a private GitHub issue that references the internal bug ID.
4. Claude automation is triggered and begins work.

## Business Requirements

### Authentication & Authorization
- Who needs access?
  - Reporters do not need GitHub access.
  - GitHub issues must be created in a private repo under internal control.
- What actions are permitted?
  - System account can create issues and post comments.
- What data is restricted?
  - Issue contents must not include secrets or raw sensitive data.

### Monitoring & Visibility
- What business metrics matter?
  - % of bug reports that create a GitHub issue successfully.
  - % that result in a PR being opened.
  - Time from report submission to issue creation.
- What operational visibility is needed?
  - Failure reason visibility for GitHub API calls.
- What user behavior needs tracking?
  - Not applicable.

### Billing & Entitlements
- How is this monetized?
  - Not monetized; reduces engineering overhead and accelerates iteration.
- What entitlement rules apply?
  - Option to only trigger AI for certain severities/categories.
- What usage limits exist?
  - Rate limit handling and backoff policies are required.

### Data Requirements
- What information must persist?
  - GitHub issue URL and identifiers mapped to bug report ID.
- How long must data be retained?
  - Must retain mapping for the life of the bug report record.
- What data relationships exist?
  - bug report → GitHub issue → PR.

### Performance Expectations
- What response times are acceptable?
  - Issue creation should occur shortly after submission; delays must be visible in status.
- What throughput is expected?
  - Low volume initially; must handle occasional bursts.
- What availability is required?
  - Best-effort with retry; must not block capturing a report.

### UX & Accessibility
- What user experience standards apply?
  - Reporter-facing status should transition to “AI working” when issue creation succeeds.
- What accessibility requirements?
  - Status messaging is accessible in reporter view.
- What devices/browsers must be supported?
  - Not applicable.

### Privacy, Security & Compliance
- What regulations apply?
  - Treat screenshots/diagnostics as sensitive.
- What data protection is required?
  - Redaction rules must be applied before sending any diagnostic content.
  - Never include secrets in issues.
- What audit trails are needed?
  - Record when issue was created and by which system identity.

## Dependencies
- Upstream:
  - Bug report storage and access controls.
- Downstream:
  - PR status webhooks and preview environment linkage.

## Risks & Mitigations
- AI produces large/refactor PRs → Provide strict instruction block and guardrails; enforce minimal-change policy.
- GitHub API failures → Retry with backoff; mark bug report as blocked and visible to internal team.

## Acceptance Criteria (Business Validation)
- [ ] Creating a new bug report results in a private GitHub issue containing:
  - reporter notes (verbatim)
  - screenshot URLs
  - environment/repro context
  - AI instruction block
  (binary test)
- [ ] Bug report is updated with the GitHub issue URL (binary test).
- [ ] Reporter does not require GitHub access to complete the flow (binary test).

## Traceability
- Parent PRD: docs/prd/ai-bug-fixer/parent.md
- Product North Star: a new type of shopping platform that also allows bidding; establish a PoC for bug reporting/fixing using Claude and GitHub Actions.

---
allowed-tools: "*"
**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
