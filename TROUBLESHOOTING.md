# Troubleshooting Guide

Common issues and solutions for Shopping Agent development and deployment.

## Table of Contents

- [Database Issues](#database-issues)
- [Backend Issues](#backend-issues)
- [Frontend Issues](#frontend-issues)
- [Authentication Issues](#authentication-issues)
- [Search Provider Issues](#search-provider-issues)
- [Deployment Issues](#deployment-issues)
- [Performance Issues](#performance-issues)
- [Development Environment](#development-environment)

---

## Database Issues

### Database Connection Failed

**Symptom:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**

1. **Verify PostgreSQL is running:**
   ```bash
   # macOS (Homebrew)
   brew services list | grep postgresql

   # Start if not running
   brew services start postgresql@14

   # Docker
   docker ps | grep postgres
   ```

2. **Check DATABASE_URL in .env:**
   ```env
   # Correct format
   DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

   # Common mistake - missing asyncpg driver
   # Wrong: postgresql://...
   # Right: postgresql+asyncpg://...
   ```

3. **Test connection manually:**
   ```bash
   psql postgresql://postgres:postgres@localhost:5435/shopping_agent
   ```

4. **Check firewall rules:**
   ```bash
   # Allow PostgreSQL port
   sudo ufw allow 5432/tcp
   ```

### Migration Failed

**Symptom:**
```
alembic.util.exc.CommandError: Target database is not up to date
```

**Solutions:**

1. **Check current migration state:**
   ```bash
   cd apps/backend
   uv run alembic current
   uv run alembic history
   ```

2. **Run pending migrations:**
   ```bash
   uv run alembic upgrade head
   ```

3. **Migration conflict (multiple heads):**
   ```bash
   # Check for multiple heads
   uv run alembic heads

   # Merge heads
   uv run alembic merge heads -m "merge conflicting migrations"
   uv run alembic upgrade head
   ```

4. **Reset database (DESTRUCTIVE - development only):**
   ```bash
   # Drop and recreate database
   dropdb shopping_agent
   createdb shopping_agent

   # Run migrations from scratch
   uv run alembic upgrade head
   ```

### Table Already Exists

**Symptom:**
```
ProgrammingError: relation "user" already exists
```

**Solution:**

This usually means migrations are out of sync. Mark the current state:

```bash
# Stamp database with current migration
uv run alembic stamp head
```

### Connection Pool Exhausted

**Symptom:**
```
TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Solutions:**

1. **Increase pool size in .env:**
   ```env
   DB_POOL_SIZE=20
   DB_MAX_OVERFLOW=10
   ```

2. **Enable connection pooling debug:**
   ```env
   DB_ECHO=true  # Will log all SQL queries
   ```

3. **Check for connection leaks:**
   ```python
   # Make sure sessions are properly closed
   async with get_session() as session:
       # ... do work ...
       # Session automatically closed
   ```

---

## Backend Issues

### Backend Won't Start

**Symptom:**
```
Error loading ASGI app. Could not import module "main"
```

**Solutions:**

1. **Verify you're in the correct directory:**
   ```bash
   cd apps/backend
   pwd  # Should show .../Shopping Agent/apps/backend
   ```

2. **Check Python environment:**
   ```bash
   uv run python --version  # Should be 3.11+
   uv sync  # Reinstall dependencies
   ```

3. **Check for syntax errors:**
   ```bash
   uv run python -m py_compile main.py
   ```

4. **Check environment variables:**
   ```bash
   # Verify .env exists
   ls -la .env

   # Test loading
   uv run python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('DATABASE_URL'))"
   ```

### Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**

```bash
cd apps/backend

# Reinstall dependencies
uv sync

# If that doesn't work, clean and reinstall
rm -rf .venv
uv sync
```

### Port Already in Use

**Symptom:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**

```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
lsof -ti:8000 | xargs kill -9

# Or use a different port
uv run uvicorn main:app --reload --port 8080
```

### CORS Errors

**Symptom:**
```
Access to fetch at 'http://localhost:8000/api/rows' from origin 'http://localhost:3003' has been blocked by CORS policy
```

**Solutions:**

1. **Check CORS_ORIGINS in backend .env:**
   ```env
   CORS_ORIGINS=http://localhost:3003,http://localhost:3000
   ```

2. **Verify CORS middleware in main.py:**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=get_cors_origins(),
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **Check frontend is sending correct origin:**
   ```typescript
   // In frontend code
   const response = await fetch(`${process.env.BACKEND_URL}/api/...`, {
     credentials: 'include',  // Important for cookies
   });
   ```

---

## Frontend Issues

### Frontend Won't Start

**Symptom:**
```
Error: Cannot find module 'next'
```

**Solution:**

```bash
cd apps/frontend

# Reinstall dependencies
rm -rf node_modules pnpm-lock.yaml
pnpm install

# If pnpm not installed
npm install -g pnpm@9
pnpm install
```

### Build Failures

**Symptom:**
```
Type error: Property 'x' does not exist on type 'Y'
```

**Solutions:**

1. **Run type check to see all errors:**
   ```bash
   pnpm type-check
   ```

2. **Clear Next.js cache:**
   ```bash
   rm -rf .next
   pnpm build
   ```

3. **Check tsconfig.json is correct:**
   ```json
   {
     "extends": "next/core-web-vitals",
     "compilerOptions": {
       "strict": true
     }
   }
   ```

### API Requests Failing

**Symptom:**
```
TypeError: Failed to fetch
```

**Solutions:**

1. **Verify BACKEND_URL in .env:**
   ```env
   BACKEND_URL=http://localhost:8000
   ```

2. **Check backend is running:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy","version":"0.1.0"}
   ```

3. **Check browser console for CORS errors**

4. **Verify authentication token:**
   ```typescript
   // In browser console
   localStorage.getItem('session_token')
   ```

### Hydration Errors

**Symptom:**
```
Error: Hydration failed because the initial UI does not match what was rendered on the server
```

**Solutions:**

1. **Check for client-only code in Server Components:**
   ```typescript
   // Wrong - localStorage in Server Component
   const token = localStorage.getItem('token')

   // Right - use Client Component
   'use client'
   const token = localStorage.getItem('token')
   ```

2. **Ensure time-sensitive data is consistent:**
   ```typescript
   // Wrong - Date.now() changes between server and client
   const timestamp = Date.now()

   // Right - use suppressHydrationWarning or Client Component
   <time suppressHydrationWarning>{Date.now()}</time>
   ```

---

## Authentication Issues

### Login Code Not Sent

**Symptom:** User enters email but never receives code.

**Solutions:**

1. **Check RESEND_API_KEY in backend .env:**
   ```env
   RESEND_API_KEY=re_your_key_here
   FROM_EMAIL=Agent Shopper <shopper@info.xcor-cto.com>
   ```

2. **Check backend logs for email errors:**
   ```bash
   # In backend directory
   uv run uvicorn main:app --reload --log-level debug
   ```

3. **Verify Resend API key is valid:**
   ```bash
   curl -X POST https://api.resend.com/emails \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"from":"test@example.com","to":"test@example.com","subject":"Test","html":"Test"}'
   ```

4. **Check spam folder**

### Session Expired

**Symptom:**
```json
{"detail": "Invalid or expired session"}
```

**Solutions:**

1. **Session timeout (default 7 days) - User needs to log in again**

2. **Check auth_session table:**
   ```sql
   SELECT id, email, created_at, expires_at, last_activity_at
   FROM auth_session
   WHERE email = 'user@example.com'
   ORDER BY created_at DESC;
   ```

3. **Clear old sessions:**
   ```sql
   DELETE FROM auth_session
   WHERE expires_at < NOW();
   ```

### Authentication Loop

**Symptom:** Frontend keeps redirecting to login page.

**Solutions:**

1. **Check session token is being stored:**
   ```typescript
   // Browser console
   localStorage.getItem('session_token')
   ```

2. **Verify token is being sent in requests:**
   ```typescript
   // Should include Authorization header
   fetch('/api/rows', {
     headers: {
       'Authorization': `Bearer ${token}`
     }
   })
   ```

3. **Check backend is validating token correctly:**
   ```python
   # In dependencies.py
   async def get_current_user(token: str = Depends(oauth2_scheme)):
       # Debug: print received token
       print(f"Received token: {token[:20]}...")
   ```

---

## Search Provider Issues

### No Search Results

**Symptom:** Search returns empty results or errors.

**Solutions:**

1. **Check API keys are configured:**
   ```bash
   cd apps/backend
   grep -E "SERPAPI|RAINFOREST|VALUESERP" .env
   ```

2. **Enable mock search for testing:**
   ```env
   USE_MOCK_SEARCH=auto
   ```

3. **Check provider API limits:**
   ```bash
   # Test SerpAPI directly
   curl "https://serpapi.com/search.json?q=test&api_key=YOUR_KEY"
   ```

4. **Check backend logs for provider errors:**
   ```bash
   tail -f logs/backend.log | grep -i "search\|provider"
   ```

### Search Timeout

**Symptom:**
```
TimeoutError: Search provider took too long to respond
```

**Solutions:**

1. **Increase timeout in .env:**
   ```env
   SOURCING_PROVIDER_TIMEOUT_SECONDS=15
   ```

2. **Check network connectivity:**
   ```bash
   # Test provider endpoints
   curl -I https://serpapi.com
   curl -I https://api.rainforestapi.com
   ```

### Rate Limited

**Symptom:**
```
429 Too Many Requests
```

**Solutions:**

1. **Check API usage on provider dashboard**

2. **Implement request throttling:**
   ```env
   SEARCH_RATE_LIMIT=10  # requests per minute
   ```

3. **Use multiple providers for redundancy**

---

## Deployment Issues

### Railway Deployment Failed

**Symptom:** Build succeeds but app crashes on startup.

**Solutions:**

1. **Check Railway logs:**
   ```bash
   railway logs
   ```

2. **Verify environment variables are set in Railway dashboard:**
   - DATABASE_URL
   - RESEND_API_KEY
   - CORS_ORIGINS
   - All search provider keys

3. **Check start command:**
   ```bash
   # Should be in Procfile or railway.toml
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

4. **Verify DATABASE_URL uses public host:**
   ```env
   # Railway provides this automatically
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   ```

### Database Migration in Production

**Symptom:** App deployed but tables don't exist.

**Solutions:**

1. **Run migrations as part of deployment:**
   ```bash
   # Add to railway.toml or deployment script
   [deploy]
   buildCommand = "cd apps/backend && uv run alembic upgrade head"
   ```

2. **Manual migration on Railway:**
   ```bash
   railway run uv run alembic upgrade head
   ```

### Frontend Can't Reach Backend

**Symptom:** Frontend works but API calls fail.

**Solutions:**

1. **Check BACKEND_URL in frontend environment:**
   ```env
   # In Railway/Vercel dashboard
   BACKEND_URL=https://your-backend.railway.app
   ```

2. **Verify backend is accessible:**
   ```bash
   curl https://your-backend.railway.app/health
   ```

3. **Check CORS settings include production frontend URL**

---

## Performance Issues

### Slow Database Queries

**Symptom:** API responses taking 5+ seconds.

**Solutions:**

1. **Enable query logging:**
   ```env
   DB_ECHO=true
   DB_ENABLE_QUERY_LOGGING=true
   DB_SLOW_QUERY_THRESHOLD=1.0
   ```

2. **Check for N+1 queries:**
   ```python
   # Bad - N+1 query
   rows = session.exec(select(Row)).all()
   for row in rows:
       bids = row.bids  # Separate query for each row

   # Good - eager loading
   from sqlmodel import select
   from sqlalchemy.orm import selectinload

   rows = session.exec(
       select(Row).options(selectinload(Row.bids))
   ).all()
   ```

3. **Add database indexes:**
   ```python
   # In models.py
   class Row(SQLModel, table=True):
       user_id: int = Field(foreign_key="user.id", index=True)  # Add index=True
   ```

### High Memory Usage

**Symptom:** Backend using 500MB+ RAM.

**Solutions:**

1. **Reduce connection pool size:**
   ```env
   DB_POOL_SIZE=5
   DB_MAX_OVERFLOW=10
   ```

2. **Enable streaming for large result sets:**
   ```python
   # Stream results instead of loading all at once
   async for row in session.stream(select(Row)):
       process(row)
   ```

### SSE Connection Drops

**Symptom:** Real-time search updates stop working.

**Solutions:**

1. **Check for reverse proxy timeout:**
   ```nginx
   # nginx.conf
   proxy_read_timeout 300s;
   proxy_send_timeout 300s;
   ```

2. **Add keepalive pings:**
   ```python
   # In streaming endpoint
   async def stream_results():
       while True:
           yield ": keepalive\n\n"
           await asyncio.sleep(15)
   ```

---

## Development Environment

### uv Command Not Found

**Solution:**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to ~/.zshrc or ~/.bashrc)
export PATH="$HOME/.cargo/bin:$PATH"

# Reload shell
source ~/.zshrc
```

### Python Version Mismatch

**Symptom:**
```
This project requires Python 3.11+
```

**Solutions:**

1. **Install Python 3.11:**
   ```bash
   # macOS
   brew install python@3.11

   # Ubuntu
   sudo apt-get install python3.11
   ```

2. **Use uv to manage Python version:**
   ```bash
   uv python install 3.11
   uv venv --python 3.11
   ```

### pnpm Not Installing Packages

**Symptom:**
```
ERR_PNPM_FETCH_404  GET https://registry.npmjs.org/package-name: Not Found
```

**Solutions:**

1. **Clear pnpm cache:**
   ```bash
   pnpm store prune
   rm -rf node_modules pnpm-lock.yaml
   pnpm install
   ```

2. **Check registry:**
   ```bash
   pnpm config get registry
   # Should be: https://registry.npmjs.org/
   ```

### Git Hooks Failing

**Symptom:** Pre-commit hooks preventing commits.

**Solution:**

```bash
# Skip hooks temporarily (not recommended)
git commit --no-verify

# Or fix the hook issue
chmod +x .git/hooks/pre-commit
```

---

## Getting More Help

If your issue isn't covered here:

1. **Check the logs:**
   - Backend: `apps/backend/logs/`
   - Frontend: Browser console (F12)
   - Railway: `railway logs`

2. **Enable debug mode:**
   ```env
   DEBUG=true
   LOG_LEVEL=debug
   ```

3. **Search existing issues:**
   - GitHub Issues
   - Backend API docs: http://localhost:8000/docs

4. **Create a detailed bug report:**
   - Exact error message
   - Steps to reproduce
   - Environment (OS, Python/Node version)
   - Relevant logs
   - What you've tried

5. **Check documentation:**
   - [Architecture](docs/ARCHITECTURE.md)
   - [API Reference](docs/API.md)
   - [Contributing](CONTRIBUTING.md)
