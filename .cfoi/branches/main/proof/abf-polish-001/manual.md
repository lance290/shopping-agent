# Manual Verification - abf-polish-001

## Steps Performed
1.  **Error Boundary**: Created `apps/frontend/app/error.tsx` (Next.js Error Boundary).
2.  **Report Bug Entry**:
    -   Added "Report Bug" button to the error page.
    -   Wired it to `useShoppingStore` to open the modal.
    -   Added `console.error` logging to capture the crash in the ring buffer.

## Verification
-   **Code Review**: Verified standard Next.js error boundary structure.
-   **Store Integration**: Uses `setReportBugModalOpen` correctly.

## Sign-off
-   **Status**: implemented
-   **Owner**: Lance
