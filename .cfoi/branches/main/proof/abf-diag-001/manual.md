# Manual Verification - abf-diag-001, 002, 003, 005

## Steps Performed
1.  **Client Diagnostics**: Implemented `apps/frontend/app/utils/diagnostics.ts` with:
    -   `RingBuffer` class for logs and network events.
    -   Console overrides (`log`, `warn`, `error`) to capture logs.
    -   Fetch interceptor to capture network errors.
    -   Global error handlers (`error`, `unhandledrejection`).
    -   `redactDiagnostics` helper to scrub sensitive keys (token, password, etc.).

2.  **Breadcrumbs**: Added `addBreadcrumb` API and wired it:
    -   Route changes (`DiagnosticsInit.tsx` via `usePathname`).
    -   UI actions (Modal open, file attach, submit in `ReportBugModal.tsx`).

3.  **Integration**:
    -   Added `DiagnosticsInit` component to `RootLayout`.
    -   Updated `ReportBugModal` to capture diagnostics on submit.
    -   Wrapped capture in `try/catch` to ensure **best-effort** submission (failures log warning but don't block).

## Verification
-   **Code Review**: Verified log capture logic and redaction list.
-   **Safety**: Redaction runs before `JSON.stringify` in the modal.

## Sign-off
-   **Status**: implemented
-   **Owner**: Lance
