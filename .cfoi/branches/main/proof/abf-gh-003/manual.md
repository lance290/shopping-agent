# Manual Verification - abf-gh-003, 004, 005

## Steps Performed
1.  **Issue Creation Logic (`abf-gh-003`)**:
    -   Implemented `create_github_issue_task` in `apps/backend/main.py`.
    -   Formats issue body with Description, Expected/Actual, Metadata, Attachments list, and Diagnostics details.
    -   Adds special instruction block: `<!-- CLAUDE-INSTRUCTION: ... -->`.
    -   Adds labels: `bug`, `severity:X`, `category:Y`.

2.  **Persistence (`abf-gh-004`)**:
    -   Updated `BugReport` model with `github_issue_url`.
    -   In `create_github_issue_task`, upon success:
        -   Updates `bug.github_issue_url`.
        -   Updates `bug.status` to `sent`.
        -   Commits to DB.

3.  **Reliability (`abf-gh-005`)**:
    -   Implemented `GitHubClient.create_issue` in `apps/backend/github_client.py`.
    -   Added retry loop (3 attempts) for network errors and 5xx/429 status codes.
    -   Added exponential backoff.
    -   Added logging for success/failure.

## Verification
-   **Code Review**: Verified logic flow:
    -   `POST /api/bugs` -> Saves DB -> Adds Background Task.
    -   Background Task -> Fetches Bug -> Calls GitHub -> Updates DB.
-   **Integration**: Uses `github_client` singleton which reads env vars.

## Sign-off
-   **Status**: implemented
-   **Owner**: Lance
