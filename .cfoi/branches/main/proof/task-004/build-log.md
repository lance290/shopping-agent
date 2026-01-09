# Build Log - task-004

## Changes Applied
- **Frontend API Routes**: Updated `apps/frontend/app/api/rows/route.ts` and `apps/frontend/app/api/chat/route.ts` to:
  - Import `cookies` from `next/headers`.
  - Read `sa_session` cookie.
  - Attach `Authorization: Bearer <token>` to BFF fetch requests.
  - Return 401 if cookie is missing (blocking unauthenticated access).

## Verification Instructions
1. **Full App Test**:
   - Open App (http://localhost:3000).
   - Login.
   - Verify "Requests" sidebar loads (GET /api/rows succeeds).
   - Create a request via Chat (POST /api/rows succeeds).
2. **Failure Case**:
   - Clear cookies.
   - Refresh.
   - Verify sidebar fails to load or redirects to login (if handled by middleware, otherwise API returns 401).

## Alignment Check
- Closes the loop: Frontend (Cookie) -> BFF (Auth Header) -> Backend (User ID).
