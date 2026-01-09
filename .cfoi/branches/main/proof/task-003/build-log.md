# Build Log - task-003

## Changes Applied
- **BFF Proxies**: Updated `apps/bff/src/index.ts` to forward `Authorization` header for `/api/rows` endpoints.
- **Chat API**: Updated `/api/chat` to extract and pass `Authorization` to `chatHandler`.
- **LLM Tools**: Updated `apps/bff/src/llm.ts` to accept `authorization` and include it in `createRow` backend calls.

## Verification Instructions
**Note**: Browser verification will fail until `task-004` (Frontend) is complete. Verify via `curl` for now.

1. **Get Token**: Login via backend or check DB for valid `session_token`.
2. **Test Success**:
   ```bash
   curl -v -H "Authorization: Bearer <your_token>" http://localhost:8080/api/rows
   ```
   - Expected: 200 OK (List of rows)
3. **Test Failure**:
   ```bash
   curl -v http://localhost:8080/api/rows
   ```
   - Expected: 401 Unauthorized

## Alignment Check
- Ensures the BFF layer doesn't break the chain of custody for user identity.
