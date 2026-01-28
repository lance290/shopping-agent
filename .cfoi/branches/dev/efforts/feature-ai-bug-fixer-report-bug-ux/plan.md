# Plan - feature-ai-bug-fixer-report-bug-ux

<!-- PLAN_APPROVAL: approved by Lance at 2026-01-21T22:56:00Z -->

## Summary
Add an in-app “Report Bug” entry point and modal that lets a non-technical stakeholder submit 1+ screenshots and notes, then receive a stable Bug ID receipt.

## Requirements (Confirmed)
- **Access**: Open access for now (just you + investor)
- **Environments**: Works everywhere (dev/staging/prod)
- **Submission inputs**:
  - Required: 1+ screenshots + notes
  - Optional: expected/actual, severity, category, include diagnostics toggle (default ON)
- **Receipt**: returns a stable Bug ID and initial status

## Dependencies & Execution Order
- **Ship order**: 1 of 6 (P0 / MVP)
- **Depends on**: None
- **Unblocks**:
  - `feature-ai-bug-fixer-storage-status` (ship order 2)
  - `enhancement-ai-bug-fixer-polish-routing-notifications` (ship order 6)

Reference: `docs/prd/TRACEABILITY.md`

## Current Architecture (Observed)
- **Frontend**: Next.js App Router (`apps/frontend/app`)
  - Next route handlers under `apps/frontend/app/api/*` proxy to BFF (see `app/api/rows/route.ts`)
- **BFF**: Fastify (`apps/bff/src/index.ts`) proxies `/api/*` to backend
- **Backend**: FastAPI + SQLModel (`apps/backend/main.py`, `models.py`)

## Proposed Approach (MVP + Best Practices)
### UX surface
- Add a “Report Bug” UI entry point (header/help menu) and a modal.
- Ensure the modal is keyboard accessible and screen-reader friendly.

### API contract
- Introduce `POST /api/bugs` (frontend route handler) that forwards to BFF `/api/bugs`.
- BFF forwards to backend endpoint (recommend `POST ${BACKEND_URL}/api/bugs`).

### Open access (for now)
- Do not require Clerk auth for bug report endpoints initially.
- Keep the API shape compatible with adding auth later.

## Verification Plan (aligned to DoD)
### Thresholds
- **bug_report_submit_success**:
  - User submits screenshots + notes → receives Bug ID and success response
- **bug_report_entrypoints_available**:
  - Entry point exists in header/help
  - **Note**: Error boundary entry point is OUT OF SCOPE for this effort; covered by `enhancement-ai-bug-fixer-polish-routing-notifications` (ship order 6). DoD for this effort validates header/help entry point only.

### Signals
- **e2e_bug_report_submit**:
  - Playwright covers opening modal → attaching screenshot → submitting → receipt shown
- **metrics_bug_report_submit_instrumented**:
  - Submission success/failure and latency is measurable (logging/metrics mechanism chosen in implementation)

## Assumptions
- We will add the “error boundary” entry point in the later polish effort; this effort focuses on baseline entry point + modal.
- Upload storage uses the Railway volume via BFF (mount path TBD) and returns secure URLs.

## Milestones
1. **Frontend UI**
   - Add entry point button
   - Add modal fields + validation
   - Add receipt display
2. **Frontend API plumbing**
   - Add `POST /api/bugs` route handler and client helper
3. **E2E test + instrumentation**
   - Add Playwright happy path
   - Add basic measurable logging around submit

## Manual QA Checklist
- Open app → click Report Bug → modal opens
- Attach 1+ images, enter notes → submit
- Receipt shows Bug ID and Captured status
