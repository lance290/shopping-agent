# PRD: Phase 7 - Social List Layer (Likes & Comments)

> **CRITICAL ARCHITECTURE NOTE:** PopSavings runs in the same monorepo as the primary `BuyAnything` application. You are free to integrate or share components, but you MUST NOT break, modify, or regress any core `BuyAnything` workflows, search APIs, or chat interfaces while implementing this PRD.

## 1. Overview
A shared list isn't just utility; it's a household social feed. By allowing members to interact with specific items on the list (e.g., liking a requested item, commenting to ask about a preferred brand), the PopSavings list becomes a collaborative, high-engagement environment that drives DAU (Daily Active Users) and retention.

## 2. Goals & Acceptance Criteria
- **Per-Item Reactions (Likes):** Any member of the list's Project can "Like" an item (Row). 
- **Per-Item Comments:** Any member can add a text comment to a specific item.
- **Activity Context:** The UI must display the name/avatar of the user who liked or commented, along with a relative timestamp (e.g., "Mom • 2h ago").
- **Acceptance Criteria:**
  - Database schema supports linking likes/comments to a specific `Row` and `User`.
  - Frontend list items render a small action bar (Like / Comment).
  - Tapping Like toggles the state instantly (optimistic UI) and persists to the backend.
  - Tapping Comment opens an inline input or bottom sheet to view/add comments.
  - Updates are visible to other household members (either on next poll, SSE, or page refresh).

## 3. Scope
- **Database:** Create `RowReaction` and `RowComment` tables.
- **Backend APIs:** CRUD endpoints for reactions and comments tied to a specific `row_id`. Include the current user's ID automatically from the auth token.
- **Frontend:** Extend the `VerticalListRow` (or equivalent list item component) to include a social action bar. Create a `RowCommentsModal` or inline thread view.

## 4. Technical Implementation Notes
### Backend (SQLModel / FastAPI)
- Models:
  ```python
  class RowReaction(SQLModel, table=True):
      id: str = Field(default_factory=generate_id, primary_key=True)
      row_id: str = Field(foreign_key="row.id")
      user_id: str = Field(foreign_key="user.id")
      reaction_type: str = Field(default="like")
      created_at: datetime

  class RowComment(SQLModel, table=True):
      id: str = Field(default_factory=generate_id, primary_key=True)
      row_id: str = Field(foreign_key="row.id")
      user_id: str = Field(foreign_key="user.id")
      text: str
      created_at: datetime
  ```
- Endpoints: `POST /rows/{row_id}/react`, `POST /rows/{row_id}/comments`, `GET /rows/{row_id}/comments`.

### Frontend (React)
- Create `ItemActionBar.tsx` with a heart/thumbs-up icon and a chat bubble icon.
- Fetch comments lazily when the comment button is clicked to keep the initial list load light.
- Use optimistic updates for the Like button to ensure it feels instantly responsive.
