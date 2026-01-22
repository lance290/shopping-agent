# Manual Verification - abf-store-006

## Steps Performed
1.  **Retention Logic**: Implemented `cleanup_old_bug_reports` in `apps/backend/retention.py`.
    -   Queries `BugReport` table for records older than `BUG_REPORT_RETENTION_DAYS` (default 90).
    -   Parses `attachments` JSON to identify file paths.
    -   Deletes physical files from `uploads/bugs/`.
    -   Deletes DB record.
    -   Transactional (commits after batch).

2.  **Configuration**:
    -   Added env var support: `BUG_REPORT_RETENTION_DAYS`.

## Verification
-   **Code Review**: Validated logic handles missing files gracefully and uses `pathlib` safely.
-   **Implementability**: Function is async and takes a session, making it compatible with the existing `main.py` lifespan or a separate cron script.

## Sign-off
-   **Status**: implemented
-   **Owner**: Lance
