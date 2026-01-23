<!-- TASKS_APPROVAL: approved by USER at 2026-01-23T05:34:00Z -->

# Tasks — enhancement-marketplace-pivot

> It is unacceptable to remove or edit tasks after approval. Only task `status` fields may change (in `tasks.json`).

## Task List (review)

### task-001 — Baseline click-first walkthrough + fixture data sanity
- **E2E flow**: Open app → login → create a row via chat → see offers → select a deal → clickout redirects.
- **Manual verification**:
  - Start app locally
  - Create a row by typing into chat
  - Confirm row appears and shows offers
  - Select a deal
  - Click offer → confirm redirect occurs
- **Files**: (no code changes required unless broken)
- **Tests to write after**:
  - Add/update a backend test ensuring `/api/out` responds with 302 for a valid URL
- **Dependencies**: none
- **Estimated**: 30 min
- **Error budget**: 3
- **Proof**: `.cfoi/branches/main/proof/task-001/`

### task-013 — Project hierarchy MVP: group/indent rows under a project
- **E2E flow**: Buyer creates a project group from the board UI → adds rows under it → rows render visually grouped/indented under the project header → refresh persists.
- **Manual verification**:
  - Click `New Project` in the board header
  - Name it `Trip`
  - Under the `Trip` project header, click `Add Row`
  - Create two rows: `Flights` and `Hotel`
  - Confirm both rows render under the `Trip` header (child rows are visually indented and grouped)
  - Refresh browser
  - Confirm the `Trip` project and its child rows persist and still render grouped
  - Create a row outside any project (an "Ungrouped" row) and confirm it renders outside the `Trip` grouping
- **MVP definition of "project hierarchy"**:
  - Exactly 2 levels: `Project` (group header) → `Row` (child)
  - No nested projects
  - No drag/drop reorder
  - Rows may be ungrouped (`project_id = null`)
- **Files to change**:
  - `apps/backend/models.py`
  - `apps/backend/main.py`
  - `apps/frontend/app/page.tsx`
  - `apps/frontend/app/store.ts`
  - `apps/frontend/app/components/RowStrip.tsx`
- **Tests to write after**:
  - Backend unit test for:
    - project create
    - row create with `project_id`
    - list rows returns correct project association
- **Dependencies**: task-001
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-013/`

### task-002 — Persist likes (buyer) for offers/tiles
- **E2E flow**: Buyer opens a row → clicks heart on an offer → refreshes page → like persists.
- **Manual verification**:
  - Like an offer tile
  - Refresh browser
  - Like state remains
- **Files to change**:
  - `apps/backend/models.py`
  - `apps/backend/main.py`
  - `apps/frontend/app/components/RowStrip.tsx`
  - `apps/frontend/app/store.ts`
- **Tests to write after**:
  - Backend unit test for like create/read
- **Dependencies**: task-001
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-002/`

### task-003 — Persist comments (buyer/collaborator) with extensible visibility
- **E2E flow**: Buyer opens an offer → adds a comment → comment appears in UI → refresh persists.
- **Manual verification**:
  - Add a comment to a tile
  - Confirm it displays
  - Refresh and confirm it persists
- **Files to change**:
  - `apps/backend/models.py`
  - `apps/backend/main.py`
  - `apps/frontend/app/components/RowStrip.tsx`
  - `apps/frontend/app/components/OfferTile.tsx`
- **Tests to write after**:
  - Backend unit test for comment create/read
- **Dependencies**: task-002
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-003/`

### task-004 — Share links for tile/row/project (MVP: copy link)
- **E2E flow**: Buyer clicks share on a tile/row → a tokenized link is copied → opening link in an incognito window loads the app and focuses the referenced row (or prompts login then returns).
- **Manual verification**:
  - Click share on a tile
  - Paste link in a new incognito window
  - If prompted, sign in
  - Confirm it opens the app and focuses/highlights the correct row
- **Files to change**:
  - `apps/frontend/app/components/RowStrip.tsx`
  - `apps/frontend/app/api/rows/route.ts`
  - `apps/backend/main.py`
- **Tests to write after**:
  - Backend unit test for share token validation (valid token resolves; invalid/expired token rejected)
- **Dependencies**: task-013
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-004/`

### task-005 — Tile detail view: provenance + FAQ/chat log summary (buyer)
- **E2E flow**: Buyer clicks a tile → sees detail panel with choice-factor highlights + chat/provenance snippet.
- **Manual verification**:
  - Click a tile
  - Confirm detail panel opens
  - Confirm it displays a provenance summary (even if minimal)
- **Files to change**:
  - `apps/frontend/app/components/OfferTile.tsx`
  - `apps/frontend/app/components/Chat.tsx`
  - `apps/backend/main.py`
- **Tests to write after**:
  - Frontend component test for detail panel render
- **Dependencies**: task-003
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-005/`

### task-006 — AI procurement agent MVP: choice factors + RFP answers persisted per row
- **E2E flow**: Buyer enters intent → agent asks 2–3 questions → answers saved → search query incorporates answers.
- **Manual verification**:
  - Enter a new intent
  - Answer follow-up questions
  - Confirm subsequent search results reflect the answers (e.g., price bounds)
- **Files to change**:
  - `apps/frontend/app/components/Chat.tsx`
  - `apps/frontend/app/components/ChoiceFactorPanel.tsx`
  - `apps/backend/main.py`
- **Tests to write after**:
  - Backend unit test ensuring `choice_answers` updates and impacts `/rows/{row_id}/search` query build
- **Dependencies**: task-001
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-006/`

### task-007 — Multi-channel sourcing provider controls exposed in UI (MVP)
- **E2E flow**: Buyer refreshes row with provider filter (e.g., `rainforest`) → results reflect provider.
- **Manual verification**:
  - Use refresh controls (all vs provider-specific)
  - Confirm results change or request includes provider filter
- **Files to change**:
  - `apps/frontend/app/components/RowStrip.tsx`
  - `apps/frontend/app/utils/api.ts`
  - `apps/backend/main.py`
- **Tests to write after**:
  - Backend test: provider filter respected
- **Dependencies**: task-001
- **Estimated**: 30 min
- **Proof**: `.cfoi/branches/main/proof/task-007/`

### task-008 — Proactive outreach MVP: create outreach record + show status in row
- **E2E flow**: Buyer clicks “request more sellers” → outreach status appears (pending/sent/awaiting response).
- **Manual verification**:
  - Trigger outreach action
  - Confirm row shows outreach status
- **Files to change**:
  - `apps/backend/models.py`
  - `apps/backend/main.py`
  - `apps/frontend/app/components/RowStrip.tsx`
- **Tests to write after**:
  - Backend unit test for outreach create/read
- **Dependencies**: task-006
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-008/`

### task-009 — Seller invite-only access: generate invite link + validate
- **E2E flow**: Buyer generates a tokenized seller invite link → opening link shows seller view of the buyer need; invalid tokens are rejected.
- **Manual verification**:
  - Generate seller invite link
  - Open in incognito
  - Confirm it loads a seller-facing view of the need
  - Paste an intentionally invalid token and confirm access is denied
- **Files to change**:
  - `apps/backend/models.py`
  - `apps/backend/main.py`
  - `apps/frontend/app/page.tsx`
- **Tests to write after**:
  - Backend unit test for invite token validation (valid token works; invalid token rejected)
- **Dependencies**: task-008
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-009/`

### task-010 — Seller quote intake: submit quote → appears as buyer tile
- **E2E flow**: Seller opens invite link → submits quote (answers + link) → buyer sees new tile.
- **Manual verification**:
  - Open seller invite link
  - Submit quote
  - Return to buyer session and confirm quote tile appears
- **Files to change**:
  - `apps/backend/models.py`
  - `apps/backend/main.py`
  - `apps/frontend/app/components/RowStrip.tsx`
- **Tests to write after**:
  - Backend unit test for quote submission and row tile materialization
- **Dependencies**: task-009
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-010/`

### task-011 — Unified closing MVP: normalize clickout “close” event + status on selected tiles
- **E2E flow**: Buyer selects tile → clicks close → clickout logs event → UI shows “closed via clickout” status.
- **Manual verification**:
  - Select a tile
  - Click through
  - Confirm status in UI updates
- **Files to change**:
  - `apps/backend/models.py`
  - `apps/backend/main.py`
  - `apps/frontend/app/components/OfferTile.tsx`
- **Tests to write after**:
  - Backend unit test for clickout status entity
- **Dependencies**: task-001
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-011/`

### task-012 — Viral flywheel MVP: referral attribution on share/invite + seller→buyer prompt
- **E2E flow**: New user arrives via project share or seller invite → attribution recorded; after seller quote, seller can post a need.
- **Manual verification**:
  - Open share link in incognito
  - Confirm attribution record exists (via log output or DB inspection)
  - After seller quote, confirm prompt to “post a need”
- **Files to change**:
  - `apps/backend/models.py`
  - `apps/backend/main.py`
  - `apps/frontend/app/components/Chat.tsx`
- **Tests to write after**:
  - Backend unit test for attribution creation
- **Dependencies**: task-004, task-009, task-010
- **Estimated**: 45 min
- **Proof**: `.cfoi/branches/main/proof/task-012/`
