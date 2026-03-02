# PRD-02: Kill the BFF

**Priority:** P0 — highest-impact architectural change  
**Effort:** 2-3 days  
**Dependencies:** None (can run in parallel with PRD-01)  
**Net effect:** Delete entire `apps/bff/` service (~2,231 lines), eliminate 1 network hop from every request

---

## Problem

Every user action currently traverses: **Browser → Next.js API route → BFF (Fastify) → Backend (FastAPI) → Postgres**

That's 3 network hops. The BFF was introduced to handle LLM orchestration for the chat flow, but it has grown into a 2,231-line God Object that also:

- Proxies non-LLM requests (bugs, merchants, clickout) with zero value-add
- Contains 250+ lines of copy-pasted logic between `create_row` and `context_switch`
- Has two complete chat implementations (deterministic fallback + LLM path)
- Uses hardcoded regex heuristics for product categories (bikes, racquets, socks, shoes) — violating the project's own "no keyword matching" rule
- Implements its own HTTP client with retry/timeout logic
- Manually loads `.env` files

**All of this belongs in the backend.**

---

## Goal

Move the LLM chat orchestration into a new FastAPI route in the backend. Delete the BFF entirely. The architecture becomes:

**Browser → Next.js (or direct) → Backend (FastAPI) → Postgres**

One hop. One codebase to debug. One place where business logic lives.

---

## What Moves to Backend

### 1. LLM Chat Handler → new `routes/chat.py`

The unified chat handler (BFF lines 918-1500+) becomes a FastAPI SSE endpoint:

```
POST /api/chat
Content-Type: application/json
Accept: text/event-stream
```

This route will:
- Accept `{ message, row_id, project_id, conversation_history }`
- Call `makeUnifiedDecision()` (ported from `bff/src/llm.ts`)
- Handle each action type: `create_row`, `update_row`, `search`, `context_switch`, `ask_clarification`, `disambiguate`
- Stream SSE events back to the client

### 2. LLM Decision Logic → new `services/llm.py`

Port `bff/src/llm.ts` → Python:
- `make_unified_decision()` — calls OpenRouter/Gemini API
- `generate_choice_factors()` — LLM generates choice factors for an item
- `build_basic_choice_factors()` — **delete the regex version**, replace with a simple LLM call or remove entirely (the LLM already generates factors)

### 3. Search Streaming → new `services/search_stream.py`

Port `streamSearchResults()` from BFF (lines 93-177) into a Python async generator that yields SSE events. The backend already has the sourcing pipeline (`sourcing/`); this just wraps it in SSE.

### 4. Intent Types → `schemas/chat.py`

Port `bff/src/types.ts` intent/action types to Pydantic models.

---

## What Gets Deleted (entire BFF)

| File | Lines | Notes |
|---|---|---|
| `apps/bff/src/index.ts` | 2,231 | Main server — everything |
| `apps/bff/src/llm.ts` | ~200 | LLM calls — port to Python |
| `apps/bff/src/intent/index.ts` | ~100 | Intent parsing — port to Python |
| `apps/bff/src/types.ts` | ~80 | Type definitions — port to Pydantic |
| `apps/bff/package.json` | — | Node.js dependency manifest |
| `apps/bff/Dockerfile` | — | Container definition |
| `apps/bff/tsconfig.json` | — | TypeScript config |
| `apps/bff/test/` | — | BFF tests — rewrite as backend tests |

**Total: ~2,600 lines deleted, ~400 lines of Python added.**

---

## What Gets Deleted from BFF That We DON'T Port

| BFF Code | Lines | Why Not Port |
|---|---|---|
| `runDeterministicChatFallback()` | ~300 | Dead fallback path. The LLM path is the real one. |
| `buildBasicChoiceFactors()` regex heuristics | ~140 | Violates "no keyword matching" rule. LLM generates factors. |
| Manual `.env` loading | ~20 | FastAPI has its own config pattern. |
| Custom HTTP client with retry | ~60 | Backend calls itself directly — no HTTP needed. |
| Bug/merchant/clickout proxy routes | ~100 | Frontend will call backend directly. |

---

## Frontend Changes

### Replace BFF URL with Backend URL

The frontend currently calls the BFF at port 8080 for chat and proxies everything else through Next.js API routes. After this change:

1. **Chat endpoint:** `POST /api/chat` on the backend (port 8000) — SSE streaming, same event format
2. **All other endpoints:** Already on backend. Frontend API routes that were proxying through BFF can proxy directly to backend, or be removed entirely (see PRD-04).

### Update `apps/frontend/app/api/chat/route.ts`

Currently proxies to BFF. Change target URL from `http://localhost:8080/api/chat` to `http://localhost:8000/api/chat`.

### Update `apps/frontend/app/store.ts`

The SSE event parsing in the store should remain unchanged — the backend will emit the same event names and payloads as the BFF currently does.

---

## Implementation Steps

### Step 1: Create backend LLM service (~200 lines)

New file: `apps/backend/services/llm.py`

- Port `makeUnifiedDecision()` from TypeScript to Python
- Use `httpx` async client for OpenRouter API calls
- Use the same Gemini model (`gemini-3-flash-preview`) and prompt
- Return the same decision structure (intent + action + message)

### Step 2: Create backend chat route (~300 lines)

New file: `apps/backend/routes/chat.py`

- SSE endpoint using `fastapi.responses.StreamingResponse`
- Same event format: `event: <type>\ndata: <json>\n\n`
- Handle each action type by calling existing backend code directly:
  - `create_row` → call `Row` creation logic directly (no HTTP)
  - `search` → call sourcing pipeline directly
  - `update_row` → call Row update logic directly
  - etc.

### Step 3: Create backend choice factor generator

New file or addition to `services/llm.py`:

- Port `generateAndSaveChoiceFactors()` from BFF
- This calls the LLM to generate choice factors for an item/service
- Saves directly to the Row via SQLModel (no HTTP round-trip)

### Step 4: Wire chat route into main.py

```python
from routes.chat import router as chat_router
app.include_router(chat_router)
```

### Step 5: Update frontend chat proxy

Change `apps/frontend/app/api/chat/route.ts` to point to backend instead of BFF.

### Step 6: Test the chat flow end-to-end

1. Start backend only (no BFF)
2. Start frontend
3. Chat: "I need a mountain bike under $500"
4. Verify: row created, choice factors generated, search results streamed
5. Verify: SSE events match old format

### Step 7: Delete `apps/bff/` directory

Once chat works through backend, delete the entire BFF.

### Step 8: Update Docker/infra

- Remove BFF from `docker-compose.dev.yml`
- Remove BFF Dockerfile reference
- Update any CI/CD that builds the BFF

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Python async SSE is trickier than Node.js streams | FastAPI `StreamingResponse` with async generators is well-documented. Test thoroughly. |
| LLM API call patterns differ in Python vs Node | Use `httpx` async client. Same API, different syntax. |
| Frontend SSE parsing breaks | Keep exact same event names and payload shapes. Write a compatibility test. |
| Search streaming breaks | The backend already has the sourcing pipeline. The BFF was just proxying it. Direct call is simpler. |

---

## Verification

1. **Chat flow works:** Send a message, get back SSE events with `assistant_message`, `row_created`, `search_results`, `done`
2. **No BFF process needed:** `lsof -i :8080` returns nothing, app still works
3. **Search results stream:** Multiple `search_results` events arrive over time (not all at once)
4. **Choice factors generate:** New row has non-empty `choice_factors` after chat creates it
5. **Context switch works:** Change topic mid-conversation, new row is created
6. **All existing backend tests pass:** `pytest tests/ -x`

---

## Environment Variables to Move

These currently live in `apps/bff/.env` and need to move to `apps/backend/.env`:

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | LLM API access |
| `GEMINI_MODEL_NAME` | Model selection (keep `gemini-3-flash-preview`) |
| `BACKEND_URL` | No longer needed — backend calls itself |
