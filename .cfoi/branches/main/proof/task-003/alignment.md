# Alignment Check - task-003

## North Star Goals Supported
- **Goal Statement**: "Ensure each authenticated user can only see and operate on their own chats/searches/rows."
- **Support**: The BFF acts as the gateway; it must propagate the user's identity (via Authorization header) to the backend so the isolation logic (implemented in task-002) can function.

## Task Scope Validation
- **In scope**: 
  - Update BFF proxy routes (`/api/rows*`) to forward `Authorization` header.
  - Update Chat API (`/api/chat`) to accept and pass auth token.
  - Update LLM tools (`createRow`) to use the user's auth token.
- **Out of Scope**: 
  - Frontend sending the token (next task).

## Acceptance Criteria
- [ ] BFF `/api/rows` calls backend with `Authorization` header from incoming request.
- [ ] BFF `/api/chat` calls backend tools with `Authorization` header.
- [ ] Missing auth header in BFF request results in 401 (propagated from backend).

## Approved by: Cascade
## Date: 2026-01-09
