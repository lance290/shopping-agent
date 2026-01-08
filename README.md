# Shopping Agent (MVP)

A chat-facilitated competitive bidding marketplace.

## 🏗️ Architecture

- **Frontend**: Next.js 15 (Port: 3000)
- **BFF**: Fastify (Port: 8080) - Handles Auth, LLM orchestration, and proxies to Backend.
- **Backend**: FastAPI (Port: 8000) - Core business logic, DB access, Sourcing adapters.
- **Database**: PostgreSQL (Port: 5432)

## 🚀 Quick Start (Local)

### 1. Start Infrastructure (Postgres)
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Configure Environment
Create `.env` files in each app directory (or set globally):

**apps/bff/.env**
```env
GEMINI_MODEL=gemini-1.5-flash
GOOGLE_API_KEY=your_key_here
BACKEND_URL=http://localhost:8000
PORT=8080
```

**apps/backend/.env**
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/shopping_agent
SEARCHAPI_API_KEY=your_key_here
```

**apps/frontend/.env.local**
```env
NEXT_PUBLIC_API_URL=http://localhost:8080
```

### 3. Run Services

**Backend (Python)**
```bash
cd apps/backend
# Install uv if needed: curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run uvicorn main:app --reload --port 8000
```

**BFF (Node)**
```bash
cd apps/bff
pnpm install
pnpm dev
```

**Frontend (Next.js)**
```bash
cd apps/frontend
pnpm install
pnpm dev
```

## 📦 Deployment (Railway)

The repo is configured for Railway monorepo deployment.
1. Connect GitHub repo to Railway.
2. Railway will detect `railway.json` in each app folder.
3. Set the required environment variables in Railway for each service.
