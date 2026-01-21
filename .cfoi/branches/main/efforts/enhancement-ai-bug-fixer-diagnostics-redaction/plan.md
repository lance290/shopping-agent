# Plan - enhancement-ai-bug-fixer-diagnostics-redaction

<!-- PLAN_APPROVAL: approved by Lance at 2026-01-21T22:56:00Z -->

## Summary
Capture a minimal diagnostics bundle (route/build/env, console ring buffer, network failure metadata, breadcrumbs) and enforce mandatory redaction before storing and before sending summaries to GitHub.

## Requirements (Confirmed)
- Diagnostics enabled by default
- Works everywhere (dev/staging/prod)
- Mandatory redaction: remove auth headers/cookies/tokens; truncate long payloads; store metadata only for network

## Dependencies & Execution Order
- **Ship order**: 4 of 6 (P1 / v1.1)
- **Depends on**:
  - `feature-ai-bug-fixer-storage-status` (ship order 2)
- **Unblocks**: None

Reference: `docs/prd/TRACEABILITY.md`

## Current Architecture (Observed)
- Frontend currently proxies requests through Next route handlers and BFF; auth exists via Clerk in other endpoints but bug reporting is open access for now.

## Proposed Approach (MVP + Best Practices)
### Client-side capture
- Implement lightweight in-browser ring buffers:
  - console events
  - failed network request metadata
  - UI breadcrumbs (route changes, key actions)

### Redaction
- Redact on the client before submission (defense-in-depth).
- Redact again on the server before persisting/sending to GitHub.

### Storage
- Persist diagnostics blob with the bug report in DB (as JSON/text) with truncation rules.

## Verification Plan (aligned to DoD)
### Thresholds
- **bug_report_diagnostics_attached**: diagnostics bundle attached when enabled
- **bug_report_redaction_safe**: redaction removes tokens/headers/cookies reliably

### Signals
- **diagnostics_best_effort**: diagnostics failure doesn’t block report submission
- **diagnostics_summary_safe_for_github**: GitHub issue includes summary without sensitive data

## Assumptions
- We will define a strict allowlist of diagnostic fields.
- We will not store request/response bodies by default.

## Milestones
1. **Client capture utilities**
   - console buffer
   - network failure buffer (metadata only)
   - breadcrumbs
2. **Server-side validation/redaction**
   - verify schema, redact secrets, truncate
3. **GitHub issue summary integration**
   - include top errors + last failed endpoint summary

## Manual QA Checklist
- Trigger a console error + failed request → submit bug report
- Confirm stored diagnostics exist and do not contain tokens
- Confirm GitHub issue summary is present and safe
