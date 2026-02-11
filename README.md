# Shopping Agent

> AI-powered competitive shopping assistant that helps users source products and services through intelligent chat-based search and comparison.

## Overview

Shopping Agent is a full-stack web application that combines conversational AI with multi-provider product search to help users find the best products and services. Users describe what they're looking for in natural language, and the agent orchestrates searches across multiple platforms (Amazon, eBay, Google Shopping, etc.) to find relevant options.

### Key Features

- **Conversational Search**: Natural language interface powered by LLM chat
- **Multi-Provider Search**: Aggregates results from Amazon, eBay, Google Shopping, and more
- **Smart Comparison**: Intelligent product matching and deduplication
- **Request Tracking**: Organize searches into projects and track progress
- **Service Detection**: Automatically detects service requests vs product searches
- **Real-time Streaming**: Server-Sent Events (SSE) for live search updates

### Tech Stack

- **Frontend**: Next.js 15 (App Router), React 18, TypeScript, Tailwind CSS
- **Backend**: Python 3.11+, FastAPI, SQLModel (SQLAlchemy + Pydantic)
- **Database**: PostgreSQL 14+ with async support (asyncpg)
- **AI/LLM**: OpenRouter API for chat orchestration
- **Search Providers**: SerpAPI, RainforestAPI, ValueSERP, SearchAPI, Google CSE
- **Package Management**: pnpm (frontend), uv (backend)
- **Deployment**: Railway (production), Docker-ready

## Quick Start

### Prerequisites

- **Node.js** 20.0.0 or higher
- **Python** 3.11 or higher
- **PostgreSQL** 14 or higher
- **pnpm** 9.0.0 or higher
- **uv** (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "Shopping Agent"
   ```

2. **Set up the database**
   ```bash
   # Start PostgreSQL (if using Docker)
   docker run -d \
     --name shopping-agent-db \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=shopping_agent \
     -p 5435:5432 \
     postgres:14
   ```

3. **Configure Backend**
   ```bash
   cd apps/backend

   # Copy environment template
   cp .env.example .env

   # Edit .env with your credentials:
   # - DATABASE_URL
   # - RESEND_API_KEY (for auth emails)
   # - At least one search provider API key

   # Install dependencies
   uv sync

   # Run migrations
   uv run alembic upgrade head
   ```

4. **Configure Frontend**
   ```bash
   cd apps/frontend

   # Copy environment template
   cp .env.example .env

   # Edit .env if needed (defaults work for local dev)

   # Install dependencies
   pnpm install
   ```

5. **Start Development Servers**

   **Terminal 1 - Backend:**
   ```bash
   cd apps/backend
   ./start.sh
   # Or: uv run uvicorn main:app --reload --port 8000
   ```

   **Terminal 2 - Frontend:**
   ```bash
   cd apps/frontend
   pnpm dev
   ```

6. **Open the application**

   Navigate to [http://localhost:3003](http://localhost:3003)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                    (React + Next.js)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ HTTP/SSE
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Backend (FastAPI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Auth       │  │  Chat/LLM    │  │   Search     │      │
│  │   Routes     │  │  Orchestration│  │   Routes     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Rows       │  │    Bids      │  │   Projects   │      │
│  │   (Requests) │  │   (Results)  │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ SQLModel/asyncpg
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                PostgreSQL Database                          │
│     (Users, Rows, Bids, Projects, Auth, Audit)             │
└─────────────────────────────────────────────────────────────┘
```

### Data Model (Core Tables)

- **user**: User accounts and profiles
- **auth_login_code**: Passwordless authentication codes
- **auth_session**: Active user sessions
- **row**: Search requests (what users are looking for)
- **request_spec**: Detailed specifications for each row
- **bid**: Product/service results from search providers
- **project**: Grouping mechanism for related rows
- **seller**: Vendor/seller information

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Common Commands

### Backend

```bash
cd apps/backend

# Development
./start.sh                              # Start dev server
uv run uvicorn main:app --reload        # Alternative start
uv run pytest                           # Run tests
uv run pytest --cov=. --cov-report=html # Run tests with coverage

# Database
uv run alembic upgrade head             # Run migrations
uv run alembic revision --autogenerate -m "message"  # Create migration
uv run python seed_auth.py              # Seed test data
```

### Frontend

```bash
cd apps/frontend

# Development
pnpm dev                    # Start dev server (port 3003)
pnpm build                  # Production build
pnpm start                  # Start production server
pnpm lint                   # Lint code
pnpm type-check             # TypeScript type checking

# Testing
pnpm test                   # Run unit tests (Vitest)
pnpm test:watch             # Run tests in watch mode
pnpm test:e2e               # Run E2E tests (Playwright)
pnpm test:all               # Run all tests
```

## Project Structure

```
Shopping Agent/
├── apps/
│   ├── backend/              # FastAPI backend
│   │   ├── routes/           # API route modules
│   │   ├── services/         # Business logic
│   │   ├── alembic/          # Database migrations
│   │   ├── tests/            # Backend tests
│   │   ├── models.py         # SQLModel database models
│   │   ├── database.py       # Database connection
│   │   ├── main.py           # FastAPI application
│   │   └── pyproject.toml    # Python dependencies
│   │
│   └── frontend/             # Next.js frontend
│       ├── app/              # Next.js App Router
│       │   ├── api/          # API routes (backend proxies)
│       │   ├── components/   # React components
│       │   ├── lib/          # Utilities
│       │   └── store.ts      # Zustand state management
│       ├── public/           # Static assets
│       ├── tests/            # Frontend tests
│       └── package.json      # Node dependencies
│
├── docs/                     # Documentation
│   ├── prd/                  # Product requirements
│   ├── ADR/                  # Architecture Decision Records
│   └── ARCHITECTURE.md       # Architecture details
│
├── infra/                    # Infrastructure & deployment
│   ├── docker/               # Docker configurations
│   └── pulumi/               # Infrastructure as Code
│
├── tools/                    # Development tools & scripts
│
├── .env                      # Root environment config
├── CLAUDE.md                 # Development guidelines
├── CONTRIBUTING.md           # Contribution guidelines
└── README.md                 # This file
```

## Environment Variables

### Backend (.env in apps/backend/)

**Required:**
- `DATABASE_URL`: PostgreSQL connection string
- `RESEND_API_KEY`: Email service for auth codes
- At least one search provider API key:
  - `SERPAPI_API_KEY`
  - `RAINFOREST_API_KEY`
  - `VALUESERP_API_KEY`
  - `SEARCHAPI_API_KEY`
  - `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_CX`

**Optional:**
- `OPENROUTER_API_KEY`: For LLM chat features
- `STRIPE_SECRET_KEY`: For payment processing
- `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET`: For eBay API
- `AMAZON_AFFILIATE_TAG`: For Amazon affiliate links

See [apps/backend/.env.example](apps/backend/.env.example) for complete list.

### Frontend (.env in apps/frontend/)

```env
BACKEND_URL=http://localhost:8000
```

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes with tests**
   - Backend: Write tests in `apps/backend/tests/`
   - Frontend: Write tests in `apps/frontend/tests/`

3. **Run tests and linting**
   ```bash
   # Backend
   cd apps/backend && uv run pytest

   # Frontend
   cd apps/frontend && pnpm test && pnpm lint
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create a pull request**

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## Testing

### Backend Tests

```bash
cd apps/backend
uv run pytest                           # All tests
uv run pytest tests/test_routes/        # Route tests only
uv run pytest -v                        # Verbose output
uv run pytest --cov=.                   # With coverage
```

### Frontend Tests

```bash
cd apps/frontend
pnpm test                               # Unit tests (Vitest)
pnpm test:e2e                           # E2E tests (Playwright)
pnpm test:e2e -- --headed               # E2E with browser visible
pnpm test:e2e -- --debug                # E2E debug mode
```

## Deployment

### Local Development
See Quick Start above.

### Railway (Production)
The application is deployed on Railway. See [DEPLOYMENT.md](DEPLOYMENT.md) for details.

### Docker
```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.dev.yml up

# Or build individually
docker build -t shopping-agent-backend apps/backend
docker build -t shopping-agent-frontend apps/frontend
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System architecture and design
- [API Reference](docs/API.md) - Complete API documentation
- [Backend README](apps/backend/README.md) - Backend setup and development
- [Frontend README](apps/frontend/README.md) - Frontend setup and development
- [Contributing](CONTRIBUTING.md) - How to contribute
- [Deployment](DEPLOYMENT.md) - Deployment procedures
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

## Recent Changes

- **PRD-02**: Removed BFF layer - frontend now calls backend directly
- **PRD-01**: Dead code cleanup - removed unused routes and models
- **Architecture**: Migrated LLM chat orchestration to backend
- **Search**: Multi-provider search with streaming results

## Support

For issues, questions, or contributions:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review existing [GitHub Issues](../../issues)
3. Create a new issue with detailed description

## License

Proprietary - All rights reserved.

## Contributors

See commit history for full contributor list.
