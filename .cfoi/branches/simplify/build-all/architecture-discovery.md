# Architecture Discovery - 2026-02-15

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLModel/SQLAlchemy, Alembic, Pydantic v2
- **Frontend:** Next.js 15 (App Router), React 18, TypeScript 5.x, Zustand 5, Tailwind CSS 3.4
- **Package Manager:** pnpm 9.0 (frontend), uv (backend)
- **Database:** PostgreSQL 17 (Railway) with pgvector extension (1536-dim embeddings)
- **Testing:** pytest + pytest-asyncio (backend), Vitest + Playwright (frontend)
- **Deploy:** Railway (backend port 8080, frontend standard)
- **LLM:** Gemini (primary) + OpenRouter (fallback), OpenRouter text-embedding-3-small for embeddings
- **Email:** Resend + Twilio already in requirements.txt

## Folder Structure
- `apps/backend/` — FastAPI app, routes/, services/, sourcing/, models/
- `apps/backend/sourcing/` — Search pipeline: repository.py, service.py, scorer.py, vendor_provider.py, constants.py
- `apps/backend/services/` — LLM (llm.py), intent (intent.py), email, vendors
- `apps/backend/models/` — SQLModel: rows, bids, auth, marketplace, social, admin
- `apps/frontend/` — Next.js app, components/, utils/api.ts, store.ts
- `docs/active-dev/` — Active PRDs for this build-all run

## Key Backend Patterns
- Routes: `APIRouter` with prefix, imported in `main.py`
- LLM calls: `services/llm.py` → `make_unified_decision()` returns `UnifiedDecision`
- Intent: `services/intent.py` → `SearchIntentResult` (keywords, brand, price range)
- Search pipeline: `SourcingRepository.search_all_with_status()` → parallel provider execution
- Scoring: `sourcing/scorer.py` → `score_results()` with price/relevance/quality/diversity
- Vendor search: `sourcing/vendor_provider.py` → pgvector similarity via `VendorDirectoryProvider`
- Bid persistence: `sourcing/service.py` → `search_and_persist()` saves results as Bids
- Alembic migrations: `apps/backend/alembic/versions/`

## Key Frontend Patterns
- State: Zustand store at `app/store.ts` (Row, Bid, Offer interfaces)
- API proxy: Next.js API routes forwarding to backend with auth header
- Components: `RowStrip.tsx` (main search UI), `OfferTile.tsx`, `Chat.tsx`
- Search trigger: `RowStrip.tsx` → `refresh()` → API call → results displayed

## Constraints
- `BACKEND_URL` env var on Railway frontend
- Session cookie: `sa_session`
- Backend listens on PORT 8080 (Railway)
- No backward compatibility required (user confirmed)

## PRD Inventory (docs/active-dev/)
1. `PRD_Desire_Classification.md` — P0, prerequisite for others
2. `PRD_Quantum_ReRanking.md` — P1, parallel with outreach
3. `PRD_Autonomous_Outreach.md` — P0, depends on desire classification
- Supporting: `User_Intention_Audit.md`, `Autonomous_Outreach_Strategy.md`

## Build Order
1. Desire Classification (foundational routing change)
2. Quantum Re-Ranking (scoring improvement, no new UI)
3. Autonomous Outreach (biggest scope — new data model, UI, email infrastructure)
