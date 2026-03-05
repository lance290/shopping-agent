# PRD: Phase 3 - Group Chat & Household Invites

> **CRITICAL ARCHITECTURE NOTE:** PopSavings runs in the same monorepo as the primary `BuyAnything` application. You are free to integrate or share components, but you MUST NOT break, modify, or regress any core `BuyAnything` workflows, search APIs, or chat interfaces while implementing this PRD.

## 1. Overview
Grocery shopping is a multiplayer task. While PopSavings currently supports sharing a list via Copylinks, the inbound SMS experience is strictly 1:1. Penny AI succeeds by allowing entire families to sit in a single Group MMS thread where the AI responds in-thread and correctly attributes items. We need to formalize Household management and Group MMS parsing.

## 2. Goals & Acceptance Criteria
- **Group MMS Parsing:** Update the Twilio webhook logic to handle Group MMS. Twilio passes multiple numbers in group texts; Pop needs to recognize the originating `Project` based on the group thread identity.
- **Household Management UI:** Upgrade the current Copylink sharing flow into a formal "Household" settings page.
- **Acceptance Criteria:**
  - If a user adds Bob (Pop) and their spouse to a group text and says "we need milk", Pop adds milk to their shared household list and replies to the group thread.
  - The UI shows a "Household" section listing the names/avatars of people who have joined the list.
  - A user can remove a member from the Household via the UI.

## 3. Scope
- **Backend (Twilio):** Parse MMS `To`/`From` structures to detect multi-participant threads. 
- **Backend (Auth/Projects):** Formalize `ProjectMember` visualization and management APIs.
- **Frontend:** Build a `/settings/household` or equivalent modal.

## 4. Technical Implementation Notes
- **Twilio Group Context:** Twilio handles Group MMS by broadcasting messages. The webhook payload includes `To` and `From` but might require state management to track which "Group" maps to which `Project`. We will likely need a `GroupThread` table mapping a hash of phone numbers to a `project_id`.
- **Reply Logic:** When replying to a group MMS, Pop must use Twilio's Messaging Service or explicitly include all numbers in the reply array so it doesn't break the thread.
- **Household API:** Endpoints to `GET /projects/{id}/members`, `DELETE /projects/{id}/members/{user_id}`.
