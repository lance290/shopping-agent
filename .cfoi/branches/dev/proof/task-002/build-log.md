# Build Log - task-002

## Changes
- Added OpenRouter-based classification helper to `apps/backend/routes/bugs.py`.
- Added triage decision matrix to `create_github_issue_task`:
  - Persist classification + confidence to `BugReport`.
  - Skip GitHub issue creation for confident feature requests.
  - Append triage details to GitHub issue body for bugs.

## Manual Verification (planned)
1. Submit report: "Dark mode request" → expect no GitHub issue (feature request).
2. Submit report: "App crashes on click" → expect GitHub issue.
3. Submit ambiguous report → expect GitHub issue (low confidence).

## Notes
- Email notification path will be wired in task-003.
