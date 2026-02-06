# Architecture Discovery - 2026-02-06

## Tech Stack
- **Frontend:** Next.js 15 (App Router, standalone output), React 18, TypeScript 5.3+
- **State:** Zustand 5
- **Styling:** Tailwind CSS 3.4, clsx, tailwind-merge
- **Icons:** Lucide React
- **BFF:** Fastify 4, AI SDK (@ai-sdk/google for Gemini), TypeScript, Zod 4
- **Backend:** FastAPI (Python 3.11+), SQLModel 0.0.31, SQLAlchemy 2.0+, asyncpg
- **Database:** PostgreSQL (port 5435 via Docker Compose)
- **Package Managers:** pnpm (frontend, BFF), uv (backend)
- **Testing:** Vitest + Playwright (frontend), Vitest (BFF), pytest + pytest-asyncio (backend)
- **Email:** Resend
- **LLM:** Google Gemini via AI SDK
- **Deployment:** Railway, Docker

## Folder Structure
- `apps/frontend/` — Next.js app
  - `app/` — App Router pages and API routes
  - `app/components/` — React components
  - `app/api/` — API proxy routes (BFF_URL read at runtime)
  - `components/ui/` — Shared UI components
- `apps/bff/` — Fastify BFF server
  - `src/index.ts` — Main entry, LLM tools, streaming
- `apps/backend/` — FastAPI backend
  - `routes/` — API route modules
  - `services/` — Business logic services
  - `models.py` — SQLModel ORM models
  - `main.py` — App entry, router registration
  - `affiliate.py` — Pluggable affiliate handler registry
  - `sourcing.py` — Multi-provider search

## Patterns to Follow
- **API proxy:** Frontend uses Next.js API routes (`/app/api/*/route.ts`) to proxy to backend/BFF
- **State:** Zustand store with typed interfaces, optimistic updates for social features
- **Backend routes:** FastAPI APIRouter with prefix and tags, async handlers
- **Auth:** Email magic link → session token, `get_current_session()` dependency
- **Models:** SQLModel with `table=True`, optional fields use `Optional[type] = None`
- **Error handling:** Global exception handler in `main.py`, per-route HTTPException
- **Affiliate:** Handler registry pattern with `AffiliateHandler` ABC
- **Sourcing:** Repository pattern with `SourcingRepository`

## Constraints
- Postgres on port 5435 (not default 5432)
- Frontend port 3003, BFF port 8081, Backend port 8000
- pnpm for Node packages, uv for Python packages
- `NEXT_PUBLIC_API_URL` for backend URL, `BFF_URL` for BFF URL
- No Stripe package installed yet (needed for PRD-01)
