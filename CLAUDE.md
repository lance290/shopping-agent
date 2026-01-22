# Claude Code Guidelines

## Commands
- **Frontend Dev**: `cd apps/frontend && npm run dev`
- **Frontend Build**: `cd apps/frontend && npm run build`
- **Frontend Test**: `cd apps/frontend && npm run test`
- **Frontend E2E**: `cd apps/frontend && npm run test:e2e`
- **Backend Dev**: `cd apps/backend && ./start.sh` (or `uv run uvicorn main:app --reload`)
- **Backend Test**: `cd apps/backend && uv run pytest`
- **Database**: `cd apps/backend && uv run alembic upgrade head`

## Code Style
- **Frontend**: 
  - TypeScript, React (Next.js App Router), Tailwind CSS.
  - Components in `components/ui` (shadcn-like) or feature folders.
  - Use `lucide-react` for icons.
  - Strict typing, no `any`.
  - Functional components with hooks.
- **Backend**: 
  - Python 3.11+, FastAPI, SQLModel (Pydantic + SQLAlchemy).
  - Async/await for all I/O.
  - Type hints required.
  - Pydantic models for schemas.

## Architecture
- **Monorepo**: `apps/frontend` and `apps/backend`.
- **API**: REST (FastAPI). Frontend proxies via Next.js Route Handlers (`/api/...`).
- **Auth**: Clerk (Frontend) -> Bearer Token -> Backend Validation.
- **Database**: PostgreSQL (via SQLModel).

## Workflow
- **Errors**: Check `apps/backend/audit.py` or frontend console logs.
- **State**: Backend is source of truth. Frontend uses Zustand (`store.ts`) for local state.
