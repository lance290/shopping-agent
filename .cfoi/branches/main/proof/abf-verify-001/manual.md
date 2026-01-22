# Manual Verification - abf-verify-001, 002, 003, 004

## Steps Performed
1.  **Webhook Endpoints**: Implemented `/api/webhooks/github` and `/api/webhooks/railway` in `main.py`.
2.  **Authentication**:
    -   GitHub: HMAC signature verification (sha256).
    -   Railway: Simple secret header check.
3.  **Logic**:
    -   PR Opened: Parses payload, extracts branch `fix/bug-{id}`, sets status `pr_created`, sets `github_pr_url`.
    -   PR Merged: Sets status `shipped`.
    -   Railway Deploy: Checks for `fix/bug-{id}` branch deployment, sets status `preview_ready`, sets `preview_url`.
4.  **Schema**: Updated `BugReportRead` to include `github_pr_url` and `preview_url`.

## Verification
-   **Code Review**: Verified branch parsing logic (`fix/bug-{id}`) aligns with GitHub Action naming.
-   **Security**: Signature verification enabled (skipped for dev-secret).

## Sign-off
-   **Status**: implemented
-   **Owner**: Lance
