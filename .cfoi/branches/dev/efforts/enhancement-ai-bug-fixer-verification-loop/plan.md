# Plan - enhancement-ai-bug-fixer-verification-loop

<!-- PLAN_APPROVAL: approved by Lance at 2026-01-21T22:56:00Z -->

## Summary
Expose AI progress to the reporter: PR created, preview ready, needs verification, shipped. Show the preview URL once available so the investor can verify without GitHub.

## Requirements (Confirmed)
- Reporter has no GitHub access
- Works everywhere
- Preview URL should be shown when available

## Dependencies & Execution Order
- **Ship order**: 5 of 6 (P1 / v1.1)
- **Depends on**:
  - `feature-ai-bug-fixer-github-claude-trigger` (ship order 3)
- **Unblocks**: None

Reference: `docs/prd/TRACEABILITY.md`

## Current Architecture (Observed)
- BFF is the central HTTP entry point for `/api/*`.
- Backend owns DB state.
- Railway PR environments may provide per-PR URLs.

## Proposed Approach (MVP + Best Practices)
### Status updates
- Backend provides status fields on `BugReport` and exposes them via `GET /api/bugs/{id}`.

### Webhooks
- Add webhook endpoints (backend) to receive:
  - GitHub PR opened → update status to `pr_created`
  - GitHub PR merged → update status to `shipped`
  - CI complete (optional)
  - Railway preview URL available (if Railway provides webhook) → update status to `preview_ready`
- On webhook receipt, update bug report status + preview URL.

### Reporter UX
- Status page shows state progression and preview link.
- Optional: “Mark verified” action (may be deferred if you prefer manual verification).

## Verification Plan (aligned to DoD)
### Thresholds
- **bug_report_pr_status_visible**: status changes to PR created when PR exists
- **bug_report_preview_url_visible**: preview URL visible and clickable when ready

### Signals
- **webhook_status_updates_verified**: webhook events update DB correctly
- **preview_access_control_validated**: preview link access approach validated (basic auth/login/etc.)

## Assumptions
- GitHub webhooks secret is configured.
- Railway preview URL retrieval mechanism is available (webhook or polling); exact method will be chosen during implementation.

## Milestones
1. **Backend webhook endpoints + verification**
   - GitHub PR opened/merged webhooks
   - Railway preview URL webhook (or polling fallback)
   - Status transitions: `ai_working` → `pr_created` → `preview_ready` → `shipped`
2. **Status UI updates**
   - Show PR created, preview ready, shipped states
3. **Preview URL integration**
   - Display clickable preview link when available
4. **Merge → Shipped transition**
   - Ensure merge webhook updates status to `shipped`

## Manual QA Checklist
- Simulate PR opened webhook → status updates to `pr_created`
- Simulate preview URL webhook → status updates to `preview_ready`, URL appears
- Simulate PR merged webhook → status updates to `shipped`
