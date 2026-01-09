# Task-003 Verification

## Manual Verification
- **Status**: Passed
- **Reason**: Verified via `curl` requests to BFF proxy endpoints.
- **Steps Attempted**:
  1. Minted valid token via backend script.
  2. `curl -H "Authorization: Bearer <token>" http://localhost:8080/api/rows` -> 200 OK (Backend accepted).
  3. `curl http://localhost:8080/api/rows` -> 401 Unauthorized (Backend blocked).

## Automated Evidence
- **Test File**: `apps/bff/src/index.test.ts` (N/A - manual curl used).
- **Result**: BFF correctly forwards Authorization header and propagates 401 errors.

## Sign-Off
- **Owner**: Lance
- **Approved**: Verified manually via curl.
