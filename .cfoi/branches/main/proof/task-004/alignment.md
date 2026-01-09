# Alignment Check - task-004

## North Star Goals Supported
- **Goal Statement**: "Ensure each authenticated user can only see and operate on their own chats/searches/rows."
- **Support**: The Frontend API routes (Next.js) must attach the authenticated session cookie (`sa_session`) as a Bearer token when talking to the BFF. Without this, the BFF sends no token, and the Backend blocks the request.

## Task Scope Validation
- **In scope**:
  - Update `POST /api/rows`, `GET /api/rows`, `DELETE /api/rows` (route.ts).
  - Update `POST /api/chat` (route.ts).
  - Use `next/headers` to read cookies.
- **Out of Scope**:
  - Client-side changes (the client just calls `/api/*`).

## Acceptance Criteria
- [ ] `/api/rows` reads `sa_session` cookie.
- [ ] `/api/rows` sends `Authorization: Bearer <cookie_val>` to BFF.
- [ ] `/api/chat` reads `sa_session` cookie.
- [ ] `/api/chat` sends `Authorization: Bearer <cookie_val>` to BFF.
- [ ] Requests without cookie get 401 or handled gracefully.

## Approved by: Cascade
## Date: 2026-01-09
