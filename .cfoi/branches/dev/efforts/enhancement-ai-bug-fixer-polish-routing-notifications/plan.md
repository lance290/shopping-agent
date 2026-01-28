# Plan - enhancement-ai-bug-fixer-polish-routing-notifications

<!-- PLAN_APPROVAL: approved by Lance at 2026-01-21T22:56:00Z -->

## Summary
Add polish: error boundary “Report Bug” entry point, severity/category routing policies, and internal notifications for high-severity/blocked reports.

## Requirements (Confirmed)
- Still open access for now
- Works everywhere
- Claude triggers every time (routing may affect internal notification priority, not AI trigger)

## Dependencies & Execution Order
- **Ship order**: 6 of 6 (P2 / Future)
- **Depends on**:
  - `feature-ai-bug-fixer-report-bug-ux` (ship order 1)
- **Unblocks**: None

Reference: `docs/prd/TRACEABILITY.md`

## Current Architecture (Observed)
- Next App Router UI
- BFF proxies to backend
- Backend has an audit log system (`audit_log`) that can be reused for tracking system events

## Proposed Approach (MVP + Best Practices)
### Error boundary entry point
- Add `error.tsx` (or equivalent) UI entry for crash reporting.

### Routing policy
- Define a simple severity/category mapping for:
  - notification on High/Blocking
  - internal triage views

### Notifications
- Initially: log-only or email/Slack hook (configurable) that sends Bug ID + link, not raw attachments.

## Verification Plan (aligned to DoD)
### Thresholds
- **error_boundary_report_bug_entrypoint**: crash screen offers Report Bug
- **bug_report_notifications_high_sev**: High/Blocking triggers notification

### Signals
- **ai_trigger_routing_policy_configurable**: routing config exists (even if AI still triggers always)
- **notifications_rate_limited**: spam controls

## Assumptions
- Notification destination (Slack/email) is available and configured via env.

## Milestones
1. **Error boundary entry point**
2. **Routing config**
3. **Notification sender + rate limiting**

## Manual QA Checklist
- Force a crash → error UI shows Report Bug
- Submit High severity → notification triggers
