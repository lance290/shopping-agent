# Manual Verification - abf-polish-002, 003, 004

## Steps Performed
1.  **Notification System**: Created `apps/backend/notifications.py`.
    -   Defines severity levels (Low=0 to Blocking=3).
    -   Implements `should_notify` policy based on `NOTIFICATION_THRESHOLD` (default: High).
    -   Implements `check_rate_limit` (max 10/hour).
    -   Implements `send_internal_notification` logic (Slack webhook + Log).

2.  **API Integration**: Wired notification trigger into `create_bug_report` in `main.py` using `BackgroundTasks`.

## Verification
-   **Code Review**: Verified logic correctly checks thresholds and rate limits before sending.
-   **Safety**: Uses `BackgroundTasks` so it doesn't block the API response.

## Sign-off
-   **Status**: implemented
-   **Owner**: Lance
