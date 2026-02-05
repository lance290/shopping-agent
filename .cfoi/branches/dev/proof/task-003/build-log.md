# Build Log - task-003

## Changes
- Modified `apps/backend/services/email.py`: Added `send_triage_notification_email` using Resend (or console log fallback).
- Modified `apps/backend/routes/bugs.py`: Imported and wired the email service to the triage flow.

## Verification
- Unit tests in `tests/test_bug_triage.py` verify that `send_triage_notification_email` is called with correct parameters for feature requests and low-confidence reports.
