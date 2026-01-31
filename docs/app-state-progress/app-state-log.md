# App State Learnings + Gotchas

## Search regressions (do not repeat)
- Search is triggered in the frontend only when an explicit query is sent. If the LLM stream does not emit a search marker, fallback must still call `runSearchApi` after chat completes (see @apps/frontend/app/components/Chat.tsx).
- Backend must not append stored constraints/choice answers when the client already supplies `body.query`. This bloats queries and causes providers (Rainforest) to return 0 or timeout.
- Backend sanitizes queries to <= 8 words before provider calls. Keep this in place to avoid long constraint strings.
- **CRITICAL**: Price patterns like "$50", "over $50", "under $100" MUST be stripped from search queries before sending to Rainforest/Amazon. Amazon interprets these as filters, not search terms, causing completely wrong results (e.g., "Roblox Gift Cards over $50" returns "over 50" fitness books instead of gift cards). The backend now removes these patterns in `main.py` search sanitization.

## Price filtering (Jan 2026 fix)
- **min_price/max_price** stored in `row.choice_answers` and `row.search_intent`
- Backend extracts price constraints in `sourcing/service.py` `_extract_price_constraints()`
- Price filtering happens in two places (keep in sync):
  - `sourcing/service.py` lines 104-128
  - `routes/rows_search.py` lines 234-256
- **Non-shopping sources bypass price filtering**: `google_cse` added to `non_shopping_sources` set since it doesn't return prices
- Results with `price=0` or `price=None` are filtered out (shopping sources must have valid prices)
- **Options card refresh button** now triggers search via `runSearchApiWithStatus()` in `RequestTile.tsx` `handleManualRefresh()`

## Provider gotchas
- SerpAPI and SearchAPI keys can 429 quickly. When they 429, results are empty.
- Rainforest can return `request_info success=true` with 0 results; retries only help when the query is clean.
- **Rainforest searches Amazon only** - won't find specialty brands like Bianchi bicycles that Amazon doesn't carry.
- Google CSE only works if both `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_CX` are set.
- **Google CSE is NOT a shopping API** - it doesn't return prices. Results bypass price filtering via `non_shopping_sources` set.
- **Scale SERP (Google Shopping)** - Added Jan 2026. Uses `SCALESERP_API_KEY` from Traject Data (same account as Rainforest). Returns actual Google Shopping results with prices, images, merchant info.
  - Timeout: 15s (slower than other providers)
  - Supports `shopping_price_min` and `shopping_price_max` params
  - Image URLs are Google's encrypted thumbnails - may not persist well
- Mocks are disabled by explicit user request.
- **Provider timeout** set via `SOURCING_PROVIDER_TIMEOUT_SECONDS` env var (default 8s, increased to 15s for Scale SERP).

## Performance Issues (Jan 2026 - INVESTIGATE)
- **Search results are slow** - user reports feeling like it's not working
- Google Shopping and Amazon are fast natively, so bottleneck is in our implementation
- Potential causes to investigate:
  - Sequential provider calls instead of parallel?
  - Database persistence overhead during search?
  - BFF -> Backend -> Provider chain latency?
  - Too many providers being queried (5+ at once)?
  - Network/API key throttling?
- Current observed latencies:
  - Rainforest: 4-8 seconds (often timeouts)
  - Scale SERP (Google Shopping): 7-8 seconds
  - SerpAPI/SearchAPI: rate limited (429)
  - Google CSE: ~500ms (but returns 0 results)
- **TODO**: Profile the search pipeline, consider provider prioritization or parallel execution

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

## Dev UX regressions (do not repeat)
- **"New Project" failing in local dev**
  - **Symptom**: Clicking "New Project" fails (often 401s) when no existing `sa_session` cookie/dev token is present.
  - **Root cause**: Next.js `/api/projects` route returned 401 immediately instead of minting a dev session token on-demand.
  - **Fix**: `apps/frontend/app/api/projects/route.ts` now uses `ensureAuthHeader()` to mint `/test/mint-session` when Clerk is disabled/unconfigured, sets `sa_session` cookie, then proxies to BFF.
  - **Regression test**: `apps/frontend/app/tests/chat-board-sync.test.ts` → `Projects API mints dev session token when missing and sets sa_session cookie`.

- **Options panel stuck on "Analyzing request…"**
  - **Symptom**: Options/Requirements panel never populates; refresh does nothing; user sees perpetual spinner.
  - **Root cause**: Backend `PATCH /rows/{id}` did not support `regenerate_choice_factors`, and row creation could leave `choice_factors` null.
  - **Fix**: `apps/backend/routes/rows.py`
    - default-populates `choice_factors` on `POST /rows` when missing
    - supports `regenerate_choice_factors` on `PATCH /rows/{id}`
  - **Regression tests**:
    - Backend: `apps/backend/tests/test_rows_authorization.py`
      - `test_row_creation_populates_choice_factors_by_default`
      - `test_regenerate_choice_factors_repopulates_on_patch`
    - Frontend: `apps/frontend/app/tests/board-display.test.ts`
      - `Options Refresh triggers regenerate_choice_factors PATCH when factors missing`

## Chat state + response parsing (LLM-only)
- Previous approach (do not return to): streaming plain text from chat and then having the frontend infer state transitions by parsing assistant text (regex/heuristics).
  - This is brittle under partial streams, retries, empty output, and LLM tool-call failures.
- Current approach: **LLM-only JSON plan + SSE events**.
  - BFF `/api/chat` asks Gemini for a strict JSON plan (no tool-calling) and executes it against the backend.
  - BFF streams `text/event-stream` events:
    - `assistant_message` (initial assistant text)
    - `action_started` (e.g. `{type:"search"}` for UI spinner)
    - `row_created` / `row_updated` (authoritative row payload)
    - `search_results` (authoritative results payload)
    - `done`
    - `error` (authoritative error payload)
  - Frontend consumes SSE frames and updates state **only** from events (no regex, no heuristics, no local fallback search).
- Auth gotcha:
  - Calling BFF `/api/chat` directly without `Authorization` yields `error: Not authenticated` because the plan execution hits backend `/rows` and `/search`.
  - The Next.js `/api/chat` proxy injects the proper auth header (Clerk JWT or `sa_session`), so browser traffic should go through that proxy.
