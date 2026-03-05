# PRD: Phase 4 - Bulk Actions (Parse & Clear)

> **CRITICAL ARCHITECTURE NOTE:** PopSavings runs in the same monorepo as the primary `BuyAnything` application. You are free to integrate or share components, but you MUST NOT break, modify, or regress any core `BuyAnything` workflows, search APIs, or chat interfaces while implementing this PRD.

## 1. Overview
Power users need frictionless ways to manage large lists. Adding 20 ingredients from a recipe blog one by one is tedious, and manually checking off 50 completed items clutters the UI. This phase introduces bulk parsing for quick entry and bulk clearing for list maintenance.

## 2. Goals & Acceptance Criteria
- **Paste Recipe UI (Bulk Parse):** A dedicated text area where users can paste a wall of text (like a recipe or an email from a spouse). The LLM parses it into individual grocery rows.
- **Clear List UI:** A one-click button to sweep away all "completed" (checked) items from the active view.
- **Acceptance Criteria:**
  - User pastes "Need 2 lbs chicken, taco seasoning, and a bag of tortillas" into the bulk input, clicks parse, and 3 distinct list items are created.
  - User clicks "Clear Completed", and all rows marked as `is_completed=True` (or equivalent status) disappear from the UI and are archived in the backend.

## 3. Scope
- **Frontend (React):** 
  - Add a "Paste Recipe" button that opens a large `textarea` modal.
  - Add a "Clear Completed" icon button in the list header.
- **Backend (API):**
  - Create a new endpoint `POST /projects/{project_id}/bulk_parse` that wraps the text in an LLM extraction prompt and inserts multiple rows.
  - Create a new endpoint `POST /projects/{project_id}/clear_completed` that performs a bulk SQL update to archive rows.

## 4. Technical Implementation Notes
- **Bulk Parse LLM Prompt:** The prompt should be strictly structured to return JSON: `[{"name": "chicken", "qty": "2 lbs", "department": "Meat"}, ...]`. Bypass the normal conversational NLU flow to save latency and ensure predictable array output.
- **Clear Logic:** Do not hard-delete rows. Update their status (e.g., `status = 'archived'` or `is_deleted = True`) so historical spend/analytics remain intact.
