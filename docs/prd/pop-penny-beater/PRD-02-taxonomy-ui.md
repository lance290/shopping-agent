# PRD: Phase 2 - Grocery Taxonomy & History UI

> **CRITICAL ARCHITECTURE NOTE:** PopSavings runs in the same monorepo as the primary `BuyAnything` application. You are free to integrate or share components, but you MUST NOT break, modify, or regress any core `BuyAnything` workflows, search APIs, or chat interfaces while implementing this PRD.

## 1. Overview
Currently, PopSavings relies on freeform text and dynamic `choice_factors` to manage item details. Penny AI enforces a strict, clean UX grouping items by Department, Size, Quantity, and Brand. To match this polished feel while retaining our AI flexibility, we need to introduce a structured "Edit Item" modal and display attribution history (who added what and via which channel).

## 2. Goals & Acceptance Criteria
- **Structured Edit Modal:** Introduce a frontend modal/drawer for List Items containing specific fields: `Name`, `Brand`, `Department` (dropdown/picker), `Size`, and `Quantity`.
- **Backend Taxonomy Mapping:** Ensure the backend either extracts these specific keys into the existing `choice_factors` JSONB column or introduces dedicated schema columns on the `Row` model if preferred for indexing.
- **Attribution Display:** The UI must display the `added_by` context and the `channel` (SMS, Email, Web). E.g., "Added by Mom via SMS".
- **Acceptance Criteria:**
  - Tapping a grocery item opens an Edit modal.
  - Changing the Department via the modal updates the item's categorization in the UI list immediately.
  - The item detail view explicitly states the origin (user name and channel).

## 3. Scope
- **Frontend (React):** Create the `PopItemEditor` component and integrate it into the `VerticalListRow` tap action.
- **Backend (API/DB):** Ensure the `Row` object correctly tracks and returns `channel` (this might already exist in conversational history, but needs to be promoted to the Row level).

## 4. Technical Implementation Notes
- **Taxonomy:** Define a strict list of Grocery Departments (Produce, Meat, Dairy, Pantry, Frozen, Bakery, Household, Personal Care, Pet, Other).
- **Data Model:** If `channel` (sms/email/web) is not currently stored directly on the `Row`, add it as a string field `origin_channel`. Add `origin_user_id` if we want strict attribution independent of the parent Project.
- **AI Extraction:** Update `make_pop_decision` to proactively extract these fields into `choice_factors` when a user texts something like "2 gallons of whole milk" -> `{"quantity": "2", "size": "gallon", "department": "Dairy"}`.
