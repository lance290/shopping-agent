# Product Requirements Document: Standalone AI Bug Fixer Service

## 1. Executive Summary
**Project Name:** AI Bug Fixer (Standalone)
**Goal:** Create a drop-in, zero-config bug reporting and autonomous fixing service that can be integrated into any web application without sharing codebase dependencies.
**Core Value:** Reduces the "Reporting -> Fixing" loop from hours/days to minutes by leveraging AI to autonomously analyze reports, reproduce issues, and open Pull Requests.

## 2. Problem Statement
*   **Fragmentation:** Bug reporting logic is currently coupled to specific application codebases (`apps/frontend`), making it hard to reuse across other company projects.
*   **Data Persistence:** Ephemeral container filesystems lose data on restart. We must use **Persistent Volumes** (Railway Volumes) to ensure screenshots and logs survive deployments.
*   **Access Control:** External or sister projects cannot import internal components directly; they need a clean, standard integration boundary (SDK/API).

## 3. Solution Architecture
The system will be architected as a **Standalone Service** consisting of two distinct artifacts:

### 3.1. The "Client SDK" (Frontend)
A lightweight NPM package (or embeddable script) that host applications install.
*   **Responsibility:** Renders the "Report Bug" trigger and modal UI within the host app.
*   **Isolation:** Encapsulates all UI logic, styles, and API communication.
*   **Integration:**
    ```tsx
    // Host App usage
    import { BugFixerWidget } from '@company/ai-fixer-sdk';

    export default function App() {
      return (
        <BugFixerWidget
          projectId="proj_123"
          apiUrl="https://api.bugfixer.company.com"
        />
      );
    }
    ```

### 3.2. The "Fixer Core" (Backend Service)
A centralized API and worker service.
*   **Responsibility:** Receives reports, manages storage, interfaces with GitHub, and orchestrates the AI Agent.
*   **Stack:** Python (FastAPI), Postgres (Metadata), **Railway Volume** (Artifacts).

---

## 4. Functional Requirements

### 4.1. Bug Reporting Experience (End User)
*   **Trigger:** A subtle, floating "Report Bug" button (bottom-right default) or a keyboard shortcut (e.g., `Cmd+Shift+Y`).
*   **Capture Modal:**
    *   **Screenshot:** Users must be able to **paste** (Ctrl+V) images directly or drag-and-drop.
    *   **Description:** "What happened?" (Required) and "Expected behavior" (Optional).
    *   **Context:** The SDK automatically captures:
        *   Current URL
        *   Browser/OS User Agent
        *   Console Logs (Last 50 lines)
        *   Network Errors (Last 10 failed requests)
*   **Feedback:** Instant "Report Submitted" confirmation with a link to track status.

### 4.2. Storage & Persistence (Railway Volumes)
*   **Constraint:** We do NOT use S3. We use **Railway Volumes** for persistence.
*   **Requirement:** All uploaded content (screenshots, logs) must be written to a dedicated persistent mount point.
*   **Implementation:**
    *   **Storage Adapter Pattern:** Backend implements `IStorageProvider`.
    *   **Disk Adapter:** The primary (and only) implementation writes files to a local path defined by `STORAGE_PATH` (e.g., `/data/uploads`).
    *   **Serving Files:** The FastAPI app must serve static files from this directory (e.g., mounted at `/static/uploads`), ensuring correct MIME types.
    *   **Database:** Store metadata (notes, severity) in Postgres, and store the *relative path* to the file in the DB (e.g., `uploads/bug-123.png`).

### 4.3. GitHub Integration & AI Loop
*   **Issue Creation:** Backend authenticates as a GitHub App (or Bot) to create an Issue in the *target* repository (configured via `projectId`).
*   **Trigger Label:** Automatically applies label `ai-fix`.
*   **AI Agent Execution:**
    *   Listens for `ai-fix` webhook.
    *   Reads Issue + Screenshots (via public URL served by API) + Context Logs.
    *   (Optional) Attempts to reproduce via E2E test generation.
    *   Generates code fix.
    *   Opens Pull Request.
*   **Two-Way Sync:** When the PR is merged, the status in the Client SDK/Dashboard updates to "Fixed".

---

## 5. Design & User Experience (Look & Feel)

### 5.1. Aesthetic
*   **Style:** "Clean Corporate" — minimalist, high contrast, professional.
*   **Component Library:** Shadcn/UI (Radix Primitives + Tailwind).
*   **Typography:** Inter or system-sans.
*   **Theme:** Auto-detect light/dark mode from host OS.

### 5.2. Component States
1.  **Idle:** Small generic bug icon (fab).
2.  **Active (Modal):**
    *   Backdrop blur (`backdrop-blur-sm`).
    *   Card-based layout with clear hierarchy.
    *   "Smart" attachments area (shows previews of pasted images).
3.  **Success:** Green checkmark animation with "Issue #123 created" link.

---

## 6. Technical Specifications

### 6.1. API Endpoints
*   `POST /v1/reports`
    *   Payload: `multipart/form-data` (JSON metadata + file binaries).
    *   Returns: `{ id: string, issueUrl: string, status: 'queued' }`.
*   `GET /v1/reports/{id}/status`
    *   Returns: `{ status: 'open' | 'fixing' | 'pr_ready' | 'shipped', prUrl: string }`.

### 6.2. Security
*   **API Keys:** Host apps identify via `X-Project-ID` and `X-API-Key`.
*   **CORS:** Backend must whitelist host domains.
*   **Sanitization:** AI Agent must redact secrets (API keys, PII) from console logs before uploading.

### 6.3. Development vs. Production
*   **Configuration:** Controlled via `STORAGE_PATH` env var.
    *   **Local Dev:** `STORAGE_PATH=./uploads` (Gitignored).
    *   **Production (Railway):** `STORAGE_PATH=/data/uploads` (Mounted Volume).
*   **Docker:** The Dockerfile must declare the volume mount point or ensure permissions are correct for the `STORAGE_PATH`.

---

## 7. Implementation Roadmap

### Phase 1: Core Service (The "Sister Project")
1.  Initialize `apps/bug-fixer-api` (FastAPI).
2.  Implement `DiskStorageProvider` using `STORAGE_PATH`.
3.  Implement `GitHubClient` (Issue creation).

### Phase 2: The SDK
1.  Initialize `packages/bug-reporter-sdk` (React + Tailwind).
2.  Port existing `ReportBugModal` logic.
3.  Add "Context Capture" (Console/Network interception).
4.  Publish as private NPM package or build artifact.

### Phase 3: AI Integration
1.  Wire up the `ai-fix` label trigger.
2.  Deploy to Railway (mapping the Volume to `/data`).
3.  Verify end-to-end flow: Report -> Disk Write -> GitHub Issue -> PR.
