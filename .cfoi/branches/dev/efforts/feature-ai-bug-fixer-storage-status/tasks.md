# Tasks - feature-ai-bug-fixer-storage-status

> **Task list protection**: After approval, it is unacceptable to remove or edit tasks. Only `status` may change in `tasks.json`.

## Task Summary
| ID | Description | Estimate |
|---|-------------|----------|
| abf-store-001 | Add backend `BugReport` model (+ attachment ref fields) | 45m |
| abf-store-002 | Implement `POST /api/bugs` to persist report + attachment refs | 45m |
| abf-store-003 | Implement `GET /api/bugs/{id}` for reporter status | 45m |
| abf-store-004 | Implement `GET /api/bugs` list for internal triage | 30m |
| abf-store-005 | Frontend reporter status view for a bug ID | 45m |
| abf-store-006 | Define retention policy mechanism (config + cleanup plan) | 30m |

---

## abf-store-001 — Add backend `BugReport` model
- **E2E flow to build**
  - Backend can create/read a bug report record with status + metadata.
- **Manual verification**
  - Start backend
  - Confirm tables create successfully
- **Files**
  - `apps/backend/models.py`
  - `apps/backend/database.py` (only if needed)
- **Tests to write AFTER**
  - Unit test for model serialization (optional)
- **Dependencies**
  - None
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-store-001/manual.md`
  - Automated: N/A
  - Human sign-off: Lance

## abf-store-002 — `POST /api/bugs`
- **E2E flow to build**
  - Creating a bug report via API returns an unguessable ID and initial status `captured`.
- **Manual verification**
  - `curl`/Postman POST a sample payload
  - Verify response contains `id` + `status`
- **Files**
  - `apps/backend/main.py`
  - (optional) `apps/backend/schemas/...` if you add request/response models
- **Tests to write AFTER**
  - API test for happy path
- **Dependencies**
  - `abf-store-001`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-store-002/manual.md`
  - Automated: API test added later
  - Human sign-off: Lance

## abf-store-003 — `GET /api/bugs/{id}`
- **E2E flow to build**
  - Reporter can retrieve a stored report by ID and see current status + preview URL if present.
- **Manual verification**
  - Create a report
  - GET by ID
  - Verify payload includes status/timestamps
- **Files**
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - API test: create then fetch
- **Dependencies**
  - `abf-store-002`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-store-003/manual.md`
  - Automated: API test added later
  - Human sign-off: Lance

## abf-store-004 — Internal triage list `GET /api/bugs`
- **E2E flow to build**
  - Internal team can list bug reports for triage.
- **Manual verification**
  - Create 2 reports
  - GET list
  - Verify newest-first ordering
- **Files**
  - `apps/backend/main.py`
- **Tests to write AFTER**
  - API test: list returns expected count
- **Dependencies**
  - `abf-store-002`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-store-004/manual.md`
  - Automated: API test added later
  - Human sign-off: Lance

## abf-store-005 — Frontend reporter status view
- **E2E flow to build**
  - User can open a status page/view and see status progression and preview link when present.
- **Manual verification**
  - Submit report (from UX)
  - Navigate to status view
  - Verify status shows `Captured`
- **Files**
  - `apps/frontend/app/...` (status page/view)
  - `apps/frontend/app/utils/api.ts`
- **Tests to write AFTER**
  - Playwright (can be in UX effort or here depending on structure)
- **Dependencies**
  - `abf-store-003`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-store-005/manual.md`
  - Automated: N/A
  - Human sign-off: Lance

## abf-store-006 — Retention policy mechanism
- **E2E flow to build**
  - Retention policy is defined (env/config) and there is a documented/implemented cleanup approach.
- **Manual verification**
  - Verify config values exist
  - Verify cleanup job/command is documented (and implemented if feasible)
- **Files**
  - `apps/backend/...` and/or `apps/bff/...` (depending on where attachments live)
- **Tests to write AFTER**
  - N/A
- **Dependencies**
  - `abf-store-001`
- **Error budget**: 3
- **Evidence**
  - Manual: `.cfoi/branches/main/proof/abf-store-006/manual.md`
  - Automated: N/A
  - Human sign-off: Lance
