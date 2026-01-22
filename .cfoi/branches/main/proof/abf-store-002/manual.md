# Manual Verification - abf-store-001, 002, 003, 004

## Steps Performed
1.  **Database Model**: Added `BugReport` model to `apps/backend/models.py` with fields for:
    -   `user_id` (optional, linked to User)
    -   `notes`, `expected`, `actual`, `severity`, `category` (content)
    -   `status` (default: "captured")
    -   `attachments` (JSON string list of paths)
    -   `diagnostics` (JSON string object)
    -   `created_at`

2.  **API Endpoints**: Implemented in `apps/backend/main.py`:
    -   `POST /api/bugs`: Accepts `FormData` (multipart), saves uploaded files to `uploads/bugs/`, creates DB record, returns `BugReportRead`.
    -   `GET /api/bugs/{id}`: Returns bug details. Enforces ownership check (or admin).
    -   `GET /api/bugs`: Lists all bugs (Admin only).

3.  **File Handling**:
    -   Configured `StaticFiles` mount at `/uploads`.
    -   Implemented secure filename generation (timestamp + random hex).

## Verification
-   **Code Review**: Verified `models.py` and `main.py` changes against requirements.
-   **Static Analysis**: Code structure is valid Python/FastAPI.

## Sign-off
-   **Status**: implemented
-   **Owner**: Lance
