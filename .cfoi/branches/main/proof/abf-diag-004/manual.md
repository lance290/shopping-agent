# Manual Verification - abf-diag-004, 006

## Steps Performed
1.  **Server Utilities**: Created `apps/backend/diagnostics_utils.py`:
    -   `validate_and_redact_diagnostics`: Parses JSON, recursively redacts keys/values, truncates long strings, re-serializes.
    -   `generate_diagnostics_summary`: Extracts top errors, last URL, user agent, and failed network requests into Markdown.

2.  **API Integration**: Updated `create_bug_report` in `main.py`:
    -   Calls redaction utility before saving `diagnostics` to DB.

3.  **GitHub Issue Integration**: Updated `create_github_issue_task` in `main.py`:
    -   Generates markdown summary from stored diagnostics.
    -   Appends summary + full JSON (in details block) to GitHub issue body.

## Verification
-   **Code Review**: Verified recursion depth limits and key redaction logic.
-   **Integration**: Confirmed flow from API -> DB -> Background Task -> GitHub.

## Sign-off
-   **Status**: implemented
-   **Owner**: Lance
