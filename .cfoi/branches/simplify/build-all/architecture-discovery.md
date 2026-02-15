# Architecture Discovery - 2026-02-14

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLModel/SQLAlchemy, Alembic, Pydantic v2
- **Frontend:** Next.js 15 (App Router), React 18, TypeScript 5.x, Zustand 5, Tailwind CSS 3.4
- **Package Manager:** pnpm 9.0 (frontend), uv (backend)
- **Database:** PostgreSQL 17 (Railway) with pgvector extension
- **Testing:** pytest + pytest-asyncio (backend), Vitest + Playwright (frontend)
- **Deploy:** Railway (backend port 8080, frontend standard)

## Folder Structure
- `apps/backend/` — FastAPI app, 25 route files, 11 services, `sourcing/` package
- `apps/frontend/` — Next.js app, `app/` directory with 44 API proxy routes
- `docs/prd/simplification/` — 7 child PRDs + parent for this effort

## Patterns to Follow
- Backend routes: `APIRouter` with prefix, imported in `main.py`
- Frontend proxies: Next.js API routes forwarding to backend with auth header
- State: Zustand store at `app/store.ts` (canonical)
- Models: SQLModel classes in `models/` directory

## Constraints
- `BACKEND_URL` env var on Railway frontend
- Session cookie: `sa_session`
- Backend listens on PORT 8080 (Railway)
