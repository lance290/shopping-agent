# App State Learnings + Gotchas

## Search regressions (do not repeat)
- Search is triggered in the frontend only when an explicit query is sent. If the LLM stream does not emit a search marker, fallback must still call `runSearchApi` after chat completes (see @apps/frontend/app/components/Chat.tsx).
- Backend must not append stored constraints/choice answers when the client already supplies `body.query`. This bloats queries and causes providers (Rainforest) to return 0 or timeout.
- Backend sanitizes queries to <= 8 words before provider calls. Keep this in place to avoid long constraint strings.
- **CRITICAL**: Price patterns like "$50", "over $50", "under $100" MUST be stripped from search queries before sending to Rainforest/Amazon. Amazon interprets these as filters, not search terms, causing completely wrong results (e.g., "Roblox Gift Cards over $50" returns "over 50" fitness books instead of gift cards). The backend now removes these patterns in `main.py` search sanitization.

## Provider gotchas
- SerpAPI and SearchAPI keys can 429 quickly. When they 429, results are empty.
- Rainforest can return `request_info success=true` with 0 results; retries only help when the query is clean.
- Google CSE only works if both `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_CX` are set.
- Mocks are disabled by explicit user request.

## Likes persistence gotcha (do not repeat)
- Do NOT call backend `/likes` directly from the frontend. It bypasses the Next.js auth proxy and can 404 due to mismatched tokens/row ownership. Always use `/api/likes`.
- **CRITICAL**: The Next.js `/api/likes` route MUST proxy to the **BACKEND** (port 8000), NOT the BFF (port 8081). The BFF does NOT have likes endpoints. This has been broken multiple times by routing to BFF_URL instead of BACKEND_URL.
  - Correct: `${BACKEND_URL}/likes` → `http://127.0.0.1:8000/likes`
  - Wrong: `${BFF_URL}/api/likes` → 404 because BFF has no likes routes
- When adding new API proxy routes, always verify which service owns the endpoint:
  - **Backend (8000)**: `/likes`, `/rows`, `/projects`, `/search`, auth endpoints
  - **BFF (8081)**: `/chat`, `/stream`, LLM-related endpoints only

## Project assignment regression (do not repeat)
- Recurring bug: user selects a project (e.g. "Zac’s Birthday") and creates a request, but the new row lands under "Other requests" instead of the selected project.
- Invariant: if a request is created while a project is selected/armed, the created row must persist `project_id=<active project id>` through the entire chain:
  - frontend state -> Next.js API route/proxy -> BFF chat/tooling -> backend row creation.
- This has multiple creation paths and all must preserve `project_id`:
  - UI "Add Request" (non-LLM)
  - Chat/LLM tool path
  - Chat fallback/non-tool path
- This must be guarded by regression tests.

## Tests added to prevent regressions
- Backend tests assert explicit query bypasses constraints, and constraints are used only when query is omitted: @apps/backend/tests/test_rows_authorization.py.
