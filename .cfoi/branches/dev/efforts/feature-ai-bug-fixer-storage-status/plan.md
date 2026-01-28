# Plan - feature-ai-bug-fixer-storage-status

<!-- PLAN_APPROVAL: approved by Lance at 2026-01-21T22:56:00Z -->

## Summary
Persist bug reports (notes, metadata, attachment references, status) and provide a reporter-facing status view that works without GitHub access.

## Requirements (Confirmed)
- **Access**: Open access for now (just you + investor)
- **Environments**: Works everywhere
- **Status model**: supports lifecycle states needed by AI/PR loop

## Dependencies & Execution Order
- **Ship order**: 2 of 6 (P0 / MVP)
- **Depends on**:
  - `feature-ai-bug-fixer-report-bug-ux` (ship order 1)
- **Unblocks**:
  - `feature-ai-bug-fixer-github-claude-trigger` (ship order 3)
  - `enhancement-ai-bug-fixer-diagnostics-redaction` (ship order 4)

Reference: `docs/prd/TRACEABILITY.md`

## Current Architecture (Observed)
- Backend uses SQLModel models in `apps/backend/models.py` and creates tables via `init_db()`.
- Frontend uses Next route handlers to proxy to BFF.

## Proposed Approach (MVP + Best Practices)
### Data model
- Add a `BugReport` table (and optional `BugAttachment` child table) in backend SQLModel.
- Persist:
  - ID, created/updated
  - notes, expected/actual, severity/category
  - context (route/env/build/user agent)
  - attachment refs (paths/URLs)
  - status enum and optional `preview_url`
  - optional `github_issue_url`, `github_pr_url`, `branch_name`

### Reporter status access
- Provide `GET /api/bugs/:id` and optionally `GET /api/bugs` (list) for “My reports”.
- For open access MVP:
  - allow read by ID without auth.
  - include explicit TODO to enforce auth/secret link later.

## Verification Plan (aligned to DoD)
### Thresholds
- **bug_report_get_by_id**: created report is retrievable by ID and shows status
- **bug_report_access_control**: for MVP open access, verify at minimum that IDs are unguessable (or long) and not enumerable

### Signals
- **bug_report_status_lifecycle_supported**: statuses exist and transitions are supported by API
- **bug_report_retention_policy**: retention policy is defined and implementable (time-based cleanup plan)

## Assumptions
- “Open access” means no auth gating for now; we will treat Bug IDs as non-enumerable.
- Storage of attachments is via BFF volume; backend stores references.

## Milestones
1. **Backend models + migrations-by-startup**
   - Add SQLModel tables and confirm table creation
2. **Backend endpoints**
   - `POST /api/bugs` stores bug report and attachments refs
   - `GET /api/bugs/{id}` returns status + preview URL
   - `GET /api/bugs` (list) for internal team triage view (all reports)
3. **Frontend status view**
   - Minimal status page or modal link to view (reporter)
   - Internal team triage view (list all reports for internal users)

## Manual QA Checklist
- Submit report → ID returned
- Open status view for ID → shows Captured and timestamps
- Status can be updated (manual DB update in dev) and reflected in UI
