# Deployment Guide

Complete guide for deploying Shopping Agent to various environments.

## Table of Contents

- [Overview](#overview)
- [Environment Configuration](#environment-configuration)
- [Local Development](#local-development)
- [Railway Production Deployment](#railway-production-deployment)
- [Alternative Platforms](#alternative-platforms)
- [Database Management](#database-management)
- [Secrets Management](#secrets-management)
- [Health Checks](#health-checks)
- [Rollback Procedures](#rollback-procedures)
- [Monitoring](#monitoring)

---

## Overview

Shopping Agent uses a two-service architecture:
- **Backend**: FastAPI (Python) - Port 8000
- **Frontend**: Next.js (Node) - Port 3003

**Current Production Setup**: Railway (both services)

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Railway Platform                     │
│                                                         │
│  ┌──────────────────┐         ┌──────────────────┐    │
│  │   Frontend       │────────▶│   Backend        │    │
│  │   (Next.js)      │         │   (FastAPI)      │    │
│  │   Port: 3003     │         │   Port: 8000     │    │
│  └──────────────────┘         └─────────┬────────┘    │
│                                          │              │
│                                          ▼              │
│                                 ┌──────────────────┐   │
│                                 │   PostgreSQL     │   │
│                                 │   Database       │   │
│                                 └──────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Environment Configuration

### Backend Environment Variables

**Required (Production):**

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname

# Authentication
RESEND_API_KEY=re_xxxxx
FROM_EMAIL=Agent Shopper <shopper@info.xcor-cto.com>

# At least one search provider
SERPAPI_API_KEY=xxxxx
# OR
RAINFOREST_API_KEY=xxxxx
# OR
VALUESERP_API_KEY=xxxxx

# Environment
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend.railway.app

# Railway-specific
RAILWAY_ENVIRONMENT=production
RAILWAY_FRONTEND_URL=https://your-frontend.railway.app
```

**Optional (Production):**

```env
# LLM Features
OPENROUTER_API_KEY=sk-or-xxxxx

# Payment Processing
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# eBay Integration
EBAY_CLIENT_ID=xxxxx
EBAY_CLIENT_SECRET=xxxxx

# Performance
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
SOURCING_PROVIDER_TIMEOUT_SECONDS=8

# Monitoring
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

### Frontend Environment Variables

```env
# Backend URL (Railway provides this automatically)
BACKEND_URL=https://your-backend.railway.app

# Monitoring (optional)
NEXT_PUBLIC_SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

---

## Local Development

### Quick Start

```bash
# 1. Start PostgreSQL
docker run -d \
  --name shopping-agent-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=shopping_agent \
  -p 5435:5432 \
  postgres:14

# 2. Backend setup
cd apps/backend
cp .env.example .env
# Edit .env with your API keys
uv sync
uv run alembic upgrade head
./start.sh

# 3. Frontend setup (in new terminal)
cd apps/frontend
cp .env.example .env
pnpm install
pnpm dev
```

Access: http://localhost:3003

### Docker Compose Development

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up

# Stop services
docker-compose -f docker-compose.dev.yml down

# Rebuild
docker-compose -f docker-compose.dev.yml up --build
```

---

## Railway Production Deployment

### Prerequisites

1. Railway account: https://railway.app
2. GitHub repository connected to Railway
3. Railway CLI (optional): `npm install -g @railway/cli`

### Initial Setup

#### 1. Create Railway Project

```bash
# Login
railway login

# Create new project
railway init

# Or link existing project
railway link
```

#### 2. Add PostgreSQL Database

In Railway dashboard:
1. Click "New" → "Database" → "PostgreSQL"
2. Railway automatically provisions database
3. `DATABASE_URL` is automatically available to services

#### 3. Deploy Backend

**Option A: Via Dashboard (Recommended)**

1. Click "New" → "GitHub Repo"
2. Select your repository
3. Configure:
   - **Root Directory**: `apps/backend`
   - **Build Command**: `uv sync`
   - **Start Command**: `uv run uvicorn main:app --host 0.0.0.0 --port $PORT`

**Option B: Via railway.toml**

Create `apps/backend/railway.toml`:

```toml
[build]
builder = "nixpacks"
buildCommand = "uv sync"

[deploy]
startCommand = "uv run uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 10
```

**Option C: Via CLI**

```bash
cd apps/backend
railway up
```

#### 4. Deploy Frontend

**Via Dashboard:**

1. Click "New" → "GitHub Repo"
2. Select your repository
3. Configure:
   - **Root Directory**: `apps/frontend`
   - **Build Command**: `pnpm install && pnpm build`
   - **Start Command**: `pnpm start`
   - **Install Command**: `pnpm install`

**Via railway.toml**

Create `apps/frontend/railway.toml`:

```toml
[build]
builder = "nixpacks"
buildCommand = "pnpm install && pnpm build"

[deploy]
startCommand = "pnpm start"
```

#### 5. Configure Environment Variables

**Backend Variables (Railway Dashboard):**

```env
# Required
DATABASE_URL=${{Postgres.DATABASE_URL}}
RESEND_API_KEY=re_xxxxx
SERPAPI_API_KEY=xxxxx
CORS_ORIGINS=${{Frontend.RAILWAY_STATIC_URL}}
RAILWAY_FRONTEND_URL=${{Frontend.RAILWAY_STATIC_URL}}
ENVIRONMENT=production

# Optional
OPENROUTER_API_KEY=sk-or-xxxxx
STRIPE_SECRET_KEY=sk_live_xxxxx
```

**Frontend Variables:**

```env
BACKEND_URL=${{Backend.RAILWAY_STATIC_URL}}
```

#### 6. Run Database Migrations

```bash
# Option A: Via Railway CLI
railway run -s backend uv run alembic upgrade head

# Option B: Add migration to build
# In railway.toml [deploy] section:
buildCommand = "uv sync && uv run alembic upgrade head"
```

### Continuous Deployment

Railway automatically deploys on git push:

```bash
git add .
git commit -m "Deploy update"
git push origin main
```

**Deployment Flow:**
1. Push to GitHub
2. Railway detects commit
3. Triggers build
4. Runs migrations (if configured)
5. Deploys new version
6. Health check passes
7. Traffic switches to new deployment

### Custom Domains

1. Go to Railway project settings
2. Click "Domains" → "Custom Domain"
3. Add your domain: `app.yourdomain.com`
4. Update DNS with Railway's CNAME
5. Update `CORS_ORIGINS` in backend

---

## Alternative Platforms

### Vercel (Frontend Only)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy frontend
cd apps/frontend
vercel

# Production
vercel --prod
```

**Environment Variables in Vercel:**
- `BACKEND_URL`: Your backend URL

### Heroku

**Backend (apps/backend/Procfile):**
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4
release: alembic upgrade head
```

**Deploy:**
```bash
heroku create shopping-agent-backend
heroku addons:create heroku-postgresql:standard-0
heroku config:set RESEND_API_KEY=xxxxx
git subtree push --prefix apps/backend heroku main
```

### Docker Production

**Build Images:**

```bash
# Backend
docker build -t shopping-agent-backend:latest \
  -f apps/backend/Dockerfile apps/backend

# Frontend
docker build -t shopping-agent-frontend:latest \
  -f apps/frontend/Dockerfile apps/frontend
```

**Docker Compose Production:**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: shopping_agent
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    image: shopping-agent-backend:latest
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${DB_PASSWORD}@postgres:5432/shopping_agent
      RESEND_API_KEY: ${RESEND_API_KEY}
      SERPAPI_API_KEY: ${SERPAPI_API_KEY}
    depends_on:
      - postgres
    ports:
      - "8000:8000"

  frontend:
    image: shopping-agent-frontend:latest
    environment:
      BACKEND_URL: http://backend:8000
    ports:
      - "3003:3003"
    depends_on:
      - backend

volumes:
  postgres_data:
```

**Deploy:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Database Management

### Migrations in Production

**Before deployment:**
```bash
# Test migration on staging/local copy first
uv run alembic upgrade head

# Check for issues
uv run alembic history
```

**During deployment:**

Railway automatically runs migrations if configured in `railway.toml`:

```toml
[deploy]
buildCommand = "uv sync && uv run alembic upgrade head"
```

**Manual migration:**
```bash
railway run -s backend uv run alembic upgrade head
```

### Database Backups

**Railway Postgres:**

Railway provides automatic backups. To create manual backup:

```bash
# Export database
railway run -s postgres pg_dump > backup_$(date +%Y%m%d).sql

# Import backup
railway run -s postgres psql < backup_20260210.sql
```

**Backup Schedule (Recommended):**
- Automatic: Daily (via Railway)
- Manual: Before major migrations
- Retention: 30 days minimum

### Database Restore

```bash
# 1. Stop backend service
railway service stop backend

# 2. Drop and recreate database
railway run -s postgres dropdb shopping_agent
railway run -s postgres createdb shopping_agent

# 3. Restore from backup
railway run -s postgres psql shopping_agent < backup.sql

# 4. Start backend service
railway service start backend
```

---

## Secrets Management

### Environment Variables

**Never commit secrets to git:**
```bash
# .gitignore should include:
.env
.env.local
.env.production
```

**Railway Secrets:**

Set via dashboard or CLI:
```bash
railway variables set RESEND_API_KEY=re_xxxxx
railway variables set STRIPE_SECRET_KEY=sk_live_xxxxx
```

**Rotation Schedule:**
- API Keys: Rotate every 90 days
- Database passwords: Rotate every 6 months
- Session secrets: Rotate on security incident

### Secret Scanning

```bash
# Check for accidentally committed secrets
git log --all --full-history -- .env
git log --all --full-history -- **/*.env

# Remove secret from git history if found
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

---

## Health Checks

### Backend Health Endpoints

**Basic Health:**
```bash
curl https://your-backend.railway.app/health
# Returns: {"status":"healthy","version":"0.1.0"}
```

**Readiness Check (includes DB):**
```bash
curl https://your-backend.railway.app/health/ready
# Returns: {"status":"ready","checks":{"database":"ok"},"timestamp":"..."}
```

### Railway Health Checks

Configure in dashboard or `railway.toml`:

```toml
[deploy]
healthcheckPath = "/health/ready"
healthcheckTimeout = 100
```

### Monitoring Health

**Uptime Monitoring:**
- UptimeRobot: Free, checks every 5 minutes
- Pingdom: More detailed monitoring
- Railway built-in monitoring

**Alert Thresholds:**
- Response time > 2s: Warning
- Response time > 5s: Critical
- 5xx errors > 1%: Critical
- Health check failure: Immediate alert

---

## Rollback Procedures

### Railway Rollback

**Via Dashboard:**
1. Go to project → Deployments
2. Find last working deployment
3. Click "Redeploy"

**Via CLI:**
```bash
# List recent deployments
railway logs --deployment

# Rollback to specific deployment
railway rollback <deployment-id>
```

### Git Rollback

```bash
# Revert last commit
git revert HEAD
git push origin main

# Or rollback to specific commit
git reset --hard <commit-hash>
git push --force origin main
```

### Database Rollback

```bash
# Downgrade one migration
railway run -s backend uv run alembic downgrade -1

# Downgrade to specific revision
railway run -s backend uv run alembic downgrade <revision>
```

**⚠️ Warning:** Database rollbacks can cause data loss. Always:
1. Backup database before rollback
2. Test rollback on staging first
3. Notify users of potential downtime

---

## Monitoring

### Application Monitoring

**Sentry (Error Tracking):**

```python
# In main.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT"),
    traces_sample_rate=1.0,
)
```

**Railway Metrics:**
- CPU usage
- Memory usage
- Request count
- Response time
- Error rate

### Logs

**View logs:**
```bash
# All logs
railway logs

# Specific service
railway logs -s backend

# Follow logs
railway logs -f

# Filter by time
railway logs --since 1h
```

**Log Levels:**
- `DEBUG`: Development only
- `INFO`: Normal operations
- `WARNING`: Recoverable issues
- `ERROR`: Errors requiring attention
- `CRITICAL`: System failures

### Metrics to Monitor

**Backend:**
- Request rate (req/min)
- Response time (p50, p95, p99)
- Error rate (%)
- Database connection pool usage
- Search provider response times

**Frontend:**
- Page load time
- Time to First Byte (TTFB)
- First Contentful Paint (FCP)
- Cumulative Layout Shift (CLS)

**Database:**
- Connection count
- Query duration
- Lock wait time
- Cache hit ratio

### Alerting

**Critical Alerts:**
- Service down
- Database unreachable
- Error rate > 5%
- Response time > 5s (p95)

**Warning Alerts:**
- Error rate > 1%
- Response time > 2s (p95)
- Disk usage > 80%
- Memory usage > 80%

---

## Post-Deployment Checklist

### After Every Deployment

- [ ] Check health endpoints
- [ ] Verify frontend loads
- [ ] Test authentication flow
- [ ] Run smoke tests
- [ ] Check error logs
- [ ] Monitor for 15 minutes

### After Major Deployments

- [ ] Run full E2E test suite
- [ ] Check database migrations applied
- [ ] Verify environment variables
- [ ] Test all integrations (Stripe, search providers)
- [ ] Check performance metrics
- [ ] Update documentation if needed
- [ ] Notify team

### Monthly

- [ ] Review error logs
- [ ] Check disk usage
- [ ] Rotate API keys (if scheduled)
- [ ] Review database performance
- [ ] Update dependencies
- [ ] Backup audit

---

## Emergency Procedures

### Service Down

1. **Check Railway status**: https://railway.app/status
2. **Check health endpoints**
3. **View logs**: `railway logs -s backend -f`
4. **Restart service**: `railway service restart backend`
5. **Rollback if needed**

### Database Issues

1. **Check connection**: `railway run -s postgres psql -c "SELECT 1"`
2. **Check pool exhaustion** in logs
3. **Restart database service** (last resort)
4. **Restore from backup** if corrupted

### High Load

1. **Scale vertically**: Increase Railway plan
2. **Scale horizontally**: Add replicas (Railway Pro)
3. **Enable caching**
4. **Optimize slow queries**

---

## Support

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Project Docs**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Emergency Contact**: [Add contact info]
