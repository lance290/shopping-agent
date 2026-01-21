# Manual Verification - abf-ux-003

## Steps Performed
1. Created `apps/frontend/app/api/bugs/route.ts` as a Next.js route handler.
   - Accepts POST requests.
   - Reads `FormData` (important for file uploads).
   - Forwards to BFF `/api/bugs` with Clerk auth header (if present).
   - Handles errors and non-200 responses.
2. Updated `apps/frontend/app/utils/api.ts` with `submitBugReport` helper.
   - Sends `FormData` to `/api/bugs`.
   - Includes a development-only mock fallback (returns success with a mock ID) to unblock UI testing before the backend is ready (Task 004).

## Verification
- **Build**: Passed (`npm run build`).
- **Code Review**: `route.ts` correctly handles `FormData` and auth forwarding. `api.ts` provides a typed interface.

## Sign-off
- **Status**: Ready for wiring UI (Task 004)
- **Owner**: Lance
