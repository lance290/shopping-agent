# Shopping Agent Backend

FastAPI-based backend service for the Shopping Agent application. Provides RESTful APIs, LLM chat orchestration, multi-provider search aggregation, and database management.

## Overview

This backend service handles:
- **Authentication**: Passwordless email authentication with session management
- **Chat Orchestration**: LLM-powered conversational search interface
- **Multi-Provider Search**: Aggregates results from Amazon, eBay, Google Shopping, etc.
- **Request Management**: CRUD operations for search requests (rows) and results (bids)
- **Project Organization**: Grouping and organizing search requests
- **Audit Logging**: Comprehensive activity tracking
- **Real-time Streaming**: Server-Sent Events (SSE) for live updates

## Tech Stack

- **Framework**: FastAPI 0.104+
- **Python**: 3.11+
- **Database**: PostgreSQL 14+ with asyncpg
- **ORM**: SQLModel 0.0.31 (combines SQLAlchemy + Pydantic)
- **Migrations**: Alembic 1.13+
- **Package Manager**: uv (fast Python package installer)
- **API Documentation**: Auto-generated OpenAPI/Swagger
- **Testing**: pytest with pytest-asyncio

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 14 or higher
- uv package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

### 1. Install Dependencies

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

This creates a virtual environment and installs all dependencies from `pyproject.toml`.

### 2. Database Setup

**Option A: Local PostgreSQL**

```bash
# Install PostgreSQL (macOS)
brew install postgresql@14
brew services start postgresql@14

# Create database
createdb shopping_agent
```

**Option B: Docker PostgreSQL**

```bash
docker run -d \
  --name shopping-agent-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=shopping_agent \
  -p 5435:5432 \
  postgres:14
```

### 3. Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Required Environment Variables:**

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5435/shopping_agent

# Authentication (Resend for email)
RESEND_API_KEY=your_resend_api_key
FROM_EMAIL=Agent Shopper <shopper@info.xcor-cto.com>

# At least one search provider
SERPAPI_API_KEY=your_serpapi_key
# OR
RAINFOREST_API_KEY=your_rainforest_key
# OR
VALUESERP_API_KEY=your_valueserp_key
```

See [.env.example](.env.example) for all available configuration options.

### 4. Run Database Migrations

```bash
# Run all migrations to create tables
uv run alembic upgrade head

# Verify migration status
uv run alembic current
```

### 5. Seed Test Data (Optional)

```bash
# Create test users and sessions
uv run python seed_auth.py
```

## Running the Server

### Development Mode

```bash
# Using the start script (recommended)
./start.sh

# Or directly with uvicorn
uv run uvicorn main:app --reload --port 8000

# With custom host and port
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

The server will be available at:
- API: http://localhost:8000
- Interactive API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Production Mode

```bash
# Install production dependencies
uv sync --no-dev

# Run with production settings
uv run uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4
```

## Project Structure

```
apps/backend/
├── alembic/              # Database migrations
│   ├── versions/         # Migration files
│   └── env.py            # Alembic configuration
├── routes/               # API route modules (25 files)
│   ├── auth.py           # Authentication endpoints
│   ├── chat.py           # LLM chat orchestration
│   ├── rows.py           # Search request CRUD
│   ├── bids.py           # Search result CRUD
│   ├── projects.py       # Project management
│   ├── search_enriched.py # Multi-provider search
│   ├── bugs.py           # Bug reporting
│   ├── admin.py          # Admin endpoints
│   └── ...               # Other route modules
├── services/             # Business logic
│   ├── safety.py         # Content moderation
│   ├── notify.py         # Notifications
│   └── ...
├── tests/                # Test suite
│   ├── test_routes/      # Route tests
│   ├── test_services/    # Service tests
│   └── conftest.py       # Pytest configuration
├── main.py               # FastAPI application
├── models.py             # SQLModel database models
├── database.py           # Database connection & session
├── dependencies.py       # Shared dependencies (auth, etc.)
├── sourcing.py           # Multi-provider search logic
├── audit.py              # Audit logging
├── storage.py            # File storage utilities
├── pyproject.toml        # Python dependencies
├── alembic.ini           # Alembic configuration
├── .env.example          # Environment template
└── README.md             # This file
```

## API Routes

The backend exposes 100+ endpoints organized by domain:

### Core Routes
- `/auth/*` - Authentication (login codes, sessions)
- `/rows/*` - Search requests (CRUD, search, update)
- `/bids/*` - Search results (CRUD, enrichment)
- `/projects/*` - Project management
- `/chat/*` - LLM chat orchestration

### Search & Discovery
- `/v1/sourcing/search` - Multi-provider search
- `/search-enriched/*` - Enhanced search with LLM

### Social & Collaboration
- `/likes/*` - Like/unlike bids
- `/comments/*` - Comments on bids

### Admin & Operations
- `/admin/*` - Admin endpoints (metrics, data management)
- `/bugs/*` - Bug report submission
- `/health` - Health check
- `/health/ready` - Readiness check (with dependency verification)

### Integrations
- `/clickout/*` - Affiliate link tracking
- `/webhooks/*` - External webhooks (Stripe, etc.)

See the interactive API documentation at `/docs` when the server is running.

## Database Migrations

### Creating a New Migration

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "Add new column to user table"

# Create empty migration (for data migrations)
uv run alembic revision -m "Populate default values"

# Edit the generated migration file in alembic/versions/
```

### Running Migrations

```bash
# Upgrade to latest
uv run alembic upgrade head

# Upgrade to specific version
uv run alembic upgrade <revision_id>

# Downgrade one version
uv run alembic downgrade -1

# Check current version
uv run alembic current

# View migration history
uv run alembic history
```

### Migration Best Practices

1. **Always review auto-generated migrations** - Alembic may miss some changes
2. **Test migrations on a copy of production data** before deploying
3. **Make migrations reversible** - Write proper `downgrade()` functions
4. **Use transactions** - Wrap data migrations in transactions
5. **Avoid breaking changes** - Add new columns as nullable first

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_routes/test_auth.py

# Run specific test
uv run pytest tests/test_routes/test_auth.py::test_login_success

# Run with coverage
uv run pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures (test client, DB session)
├── test_routes/          # Route/endpoint tests
│   ├── test_auth.py
│   ├── test_rows.py
│   ├── test_bids.py
│   └── ...
├── test_services/        # Business logic tests
│   ├── test_safety.py
│   └── ...
└── test_models.py        # Model tests
```

### Writing Tests

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

async def test_create_row(client: TestClient, session, auth_headers):
    """Test creating a new search request."""
    response = client.post(
        "/rows",
        headers=auth_headers,
        json={
            "title": "Looking for a bike",
            "request_spec": {
                "item_name": "mountain bike",
                "constraints": '{"budget": "500-1000"}'
            }
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Looking for a bike"
    assert data["status"] == "sourcing"
```

### Test Fixtures

The test suite provides several fixtures:

- `client` - TestClient for making requests
- `session` - Async database session
- `auth_headers` - Authentication headers for protected routes
- `test_user` - A test user object

## Database Models

Core models defined in `models.py`:

### Authentication
- **User** - User accounts
- **AuthLoginCode** - One-time login codes
- **AuthSession** - Active sessions

### Core Domain
- **Row** - Search requests ("rows" in the UI)
- **RequestSpec** - Detailed specifications for each row
- **Bid** - Product/service results from search
- **Project** - Grouping for related rows

### Vendor Directory
- **VendorProfile** - Directory of service providers and high-end vendors (162 profiles, 14 categories)
- **Merchant** - Onboarded/verified merchants (linked optionally from VendorProfile)

### Supporting
- **Seller** - Legacy vendor/merchant information
- **Comment** - User comments on bids
- **AuditLog** - Activity tracking
- **ClickoutEvent** - Affiliate link tracking

### Example Model

```python
class Row(RowBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")

    # Relationships
    bids: List["Bid"] = Relationship(back_populates="row")
    request_spec: Optional["RequestSpec"] = Relationship(back_populates="row")
    project: Optional[Project] = Relationship(back_populates="rows")
```

## Configuration

### Environment Variables

See [.env.example](.env.example) for complete list.

**Database:**
- `DATABASE_URL` - PostgreSQL connection string (required)
- `DB_SSL` - Set `false` for custom Postgres without SSL (default: `true`)
- `USE_PGVECTOR` - Set `true` when Postgres has `vector` extension (default: `false`)

**Authentication:**
- `RESEND_API_KEY` - Resend API key for email (required)
- `FROM_EMAIL` - From address for auth emails

**Search Providers (at least one required):**
- `SERPAPI_API_KEY`
- `RAINFOREST_API_KEY`
- `VALUESERP_API_KEY`
- `SEARCHAPI_API_KEY`
- `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_CX`

**Vector Embeddings (Vendor Semantic Search):**
- `EMBEDDING_MODEL` - Model name (default: `openai/text-embedding-3-small`)
- `EMBEDDING_DIMENSIONS` - Vector dimensions (default: `1536`)

Embeddings are routed through **OpenRouter** (uses `OPENROUTER_API_KEY`). The default model is **OpenAI `text-embedding-3-small`** (1536 dimensions) via the OpenRouter API. Embeddings are generated for `VendorProfile.profile_text` and stored in the `embedding` column via pgvector. Semantic vendor search uses cosine similarity over these embeddings. Lexical search (ILIKE) works as a fallback without embeddings.

**LLM (optional):**
- `OPENROUTER_API_KEY` - For chat features
- `BUG_TRIAGE_MODEL` - Model for bug triage

**Integrations (optional):**
- `STRIPE_SECRET_KEY` - Stripe payments
- `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` - eBay API
- `AMAZON_AFFILIATE_TAG` - Amazon affiliate links

**Operational:**
- `ENVIRONMENT` - `development` or `production`
- `CORS_ORIGINS` - Comma-separated allowed origins
- `SOURCING_PROVIDER_TIMEOUT_SECONDS` - Search timeout (default: 8)

### Mock Mode

For development without API keys:

```env
USE_MOCK_SEARCH=auto  # Use mocks when no API keys configured
```

## Code Style & Linting

### Ruff

```bash
# Check code style
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

Configuration in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I"]  # Errors, Pyflakes, Import sorting
```

### Type Checking

```bash
# Check types with mypy
uv run mypy .
```

## Debugging

### Local Development

```bash
# Run with auto-reload and detailed logging
uv run uvicorn main:app --reload --log-level debug

# Access Python debugger (add to code)
import pdb; pdb.set_trace()
```

### Database Debugging

```bash
# Connect to database
psql postgresql://postgres:postgres@localhost:5435/shopping_agent

# Check current migrations
uv run alembic current

# View recent audit logs
SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 20;

# Check active sessions
SELECT user_id, created_at, last_used_at FROM auth_session;
```

### Common Issues

See [../../TROUBLESHOOTING.md](../../TROUBLESHOOTING.md) for common problems and solutions.

## Performance

### Database Connection Pooling

SQLModel uses SQLAlchemy's async connection pooling:

```python
# In database.py
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_size=5,
    max_overflow=10,
)
```

### Caching

The sourcing repository uses lazy initialization to avoid unnecessary API client creation.

### Monitoring

Health check endpoints:
- `GET /health` - Simple health check
- `GET /health/ready` - Detailed readiness check (verifies DB connection)

## Security

### Authentication

- Passwordless email-based authentication
- Session tokens stored as SHA-256 hashes
- Sessions expire after inactivity

### Input Validation

- All inputs validated with Pydantic models
- SQL injection protected by SQLModel/SQLAlchemy
- Content moderation via safety service

### CORS

CORS is configured in `main.py` to allow requests from the frontend:

```python
# Development
origins = ["http://localhost:3003", "http://localhost:3000"]

# Production - set via CORS_ORIGINS environment variable
```

## Deployment

See [../../DEPLOYMENT.md](../../DEPLOYMENT.md) for deployment instructions.

### Railway Deployment

The backend is configured for Railway deployment:

```bash
# Railway automatically detects the start command from Procfile:
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Docker Deployment

```bash
# Build image
docker build -t shopping-agent-backend .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=your_db_url \
  -e RESEND_API_KEY=your_key \
  shopping-agent-backend
```

## Contributing

See [../../CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.

### Development Workflow

1. Create a feature branch
2. Make changes with tests
3. Run tests: `uv run pytest`
4. Run linter: `uv run ruff check .`
5. Create pull request

### Code Standards

- **Type hints required** on all function signatures
- **Async/await** for all I/O operations
- **Pydantic models** for request/response schemas
- **Docstrings** on public functions
- **Tests** for all new routes and services

## Support

- **Issues**: See [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)
- **API Docs**: http://localhost:8000/docs (when running)
- **Architecture**: [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)

## License

Proprietary - All rights reserved.
