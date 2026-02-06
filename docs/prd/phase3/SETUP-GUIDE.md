# Standing Up APIs & Services Guide

**Phase:** 3 — Closing the Loop  
**Date:** 2026-02-06  
**Audience:** Developers, DevOps, Interns  

This guide covers how to configure every external service the platform depends on. Follow each section to go from zero to a fully functional local (or production) environment.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Local Development Stack](#2-local-development-stack)
3. [Stripe (Payments)](#3-stripe-payments)
4. [Resend (Email)](#4-resend-email)
5. [SerpAPI (Search Provider)](#5-serpapi-search-provider)
6. [Rainforest API (Amazon Data)](#6-rainforest-api-amazon-data)
7. [ValueSerp / SearchAPI (Additional Providers)](#7-valueserp--searchapi-additional-providers)
8. [Google Gemini (LLM — BFF)](#8-google-gemini-llm--bff)
9. [WattData MCP (Vendor Discovery)](#9-wattdata-mcp-vendor-discovery)
10. [DocuSign (Contracts)](#10-docusign-contracts)
11. [GitHub (Bug Fixer Automation)](#11-github-bug-fixer-automation)
12. [Amazon Associates (Affiliate)](#12-amazon-associates-affiliate)
13. [Production Deployment (Railway)](#13-production-deployment-railway)
14. [Environment Variable Reference](#14-environment-variable-reference)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Prerequisites

- **Node.js** ≥ 18 (for BFF and Frontend)
- **Python** ≥ 3.11 (for Backend)
- **uv** (Python package manager — `pip install uv` or `brew install uv`)
- **pnpm** (Node package manager — `npm install -g pnpm`)
- **Docker** + **Docker Compose** (for Postgres)
- **tmux** (for long-running dev servers — `brew install tmux`)

---

## 2. Local Development Stack

### 2.1 Start Postgres

```bash
# From repo root
docker compose -f docker-compose.dev.yml up -d
```

This starts Postgres on **port 5435** (not the default 5432, to avoid conflicts).

Verify:
```bash
docker exec -it shoppingagent-postgres-1 psql -U postgres -d shopping_agent -c "SELECT 1;"
```

### 2.2 Backend (FastAPI — port 8000)

```bash
# Install dependencies
cd apps/backend
uv sync

# Copy environment file
cp .env.example .env
# Edit .env with your API keys (see sections below)

# Run migrations (auto-runs on startup in dev)
# Start the server
uv run uvicorn main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health`

### 2.3 BFF (Fastify — port 8081)

```bash
cd apps/bff
pnpm install

# Copy environment file
cp .env.template .env
# Edit .env with your Gemini API key

pnpm dev
```

Verify: `curl http://localhost:8081/health`

### 2.4 Frontend (Next.js — port 3003)

```bash
cd apps/frontend
pnpm install

# Copy environment file
cp .env.example .env.local
# Ensure NEXT_PUBLIC_API_URL and BFF_URL are set

pnpm dev -- -p 3003
```

Verify: Open `http://localhost:3003` in browser.

### 2.5 Running All Three with tmux

Determine your tmux session name:

```bash
REPO=$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')
HASH=$(echo -n "$PWD" | shasum | cut -c1-6)
BASE="${REPO}_${HASH}"
echo "Session name: ${BASE}__dev"
```

Start all services:

```bash
SESSION="${BASE}__dev"

# Kill existing session if present
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Create new detached session with backend
tmux new-session -d -s "$SESSION" -n backend \
  "cd '$PWD/apps/backend' && uv run uvicorn main:app --reload --port 8000; read"

# Add BFF window
tmux new-window -t "$SESSION" -n bff \
  "cd '$PWD/apps/bff' && pnpm dev; read"

# Add Frontend window
tmux new-window -t "$SESSION" -n frontend \
  "cd '$PWD/apps/frontend' && pnpm dev -- -p 3003; read"

echo "Started! Attach with: tmux attach -t $SESSION"
echo "Stop with: tmux kill-session -t $SESSION"
```

---

## 3. Stripe (Payments)

### 3.1 Create a Stripe Account

1. Go to [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register).
2. Complete registration (can use test mode without business verification).

### 3.2 Get API Keys

1. In the Stripe Dashboard, toggle to **Test mode** (top-right toggle).
2. Go to **Developers → API keys**.
3. Copy:
   - **Publishable key** (`pk_test_...`)
   - **Secret key** (`sk_test_...`)

### 3.3 Set Up Webhook

1. Go to **Developers → Webhooks → Add endpoint**.
2. Endpoint URL:
   - Local: Use [Stripe CLI](#35-stripe-cli-for-local-testing) instead.
   - Production: `https://your-backend-url.com/api/webhooks/stripe`
3. Events to listen for:
   - `checkout.session.completed`
   - `checkout.session.expired`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
4. Copy the **Signing secret** (`whsec_...`).

### 3.4 Add to Backend `.env`

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### 3.5 Stripe CLI for Local Testing

The Stripe CLI forwards webhook events to your local server:

```bash
# Install
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to local backend
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

The CLI will print a webhook signing secret — use that as `STRIPE_WEBHOOK_SECRET` in your local `.env`.

### 3.6 Test a Payment

```bash
# Create a test Checkout Session via API
curl -X POST http://localhost:8000/api/checkout/create-session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -d '{"bid_id": 1, "row_id": 1, "success_url": "http://localhost:3003/?checkout=success", "cancel_url": "http://localhost:3003/?checkout=cancel"}'
```

Use Stripe test card: `4242 4242 4242 4242`, any future expiry, any CVC.

---

## 4. Resend (Email)

Used for outreach emails, quote notifications, and deal handoff emails.

### 4.1 Create Account

1. Go to [https://resend.com/signup](https://resend.com/signup).
2. Verify your email.

### 4.2 Get API Key

1. Go to **API Keys** in the Resend dashboard.
2. Create a new key with **Full access**.
3. Copy the key (`re_...`).

### 4.3 Set Up Domain (Production Only)

For production email delivery:
1. Go to **Domains → Add Domain**.
2. Add your domain (e.g., `buyanything.ai`).
3. Add the DNS records Resend provides (SPF, DKIM, DMARC).
4. Wait for verification.

For local development, Resend allows sending from `onboarding@resend.dev` without domain setup.

### 4.4 Add to Backend `.env`

```env
RESEND_API_KEY=re_...
FROM_EMAIL=noreply@buyanything.ai
FROM_NAME=BuyAnything
APP_BASE_URL=http://localhost:3003
```

### 4.5 Test Email Sending

```bash
# Trigger outreach for a row (creates magic link emails)
curl -X POST http://localhost:8000/outreach/rows/1/trigger \
  -H "Content-Type: application/json" \
  -d '{"category": "private_aviation", "vendor_limit": 3}'
```

Check the Resend dashboard **Logs** to see if emails were sent.

---

## 5. SerpAPI (Search Provider)

Primary search provider for Google Shopping results.

### 5.1 Create Account

1. Go to [https://serpapi.com/users/sign_up](https://serpapi.com/users/sign_up).
2. Free tier: 100 searches/month. Paid plans start at $50/month.

### 5.2 Get API Key

1. Go to **Dashboard → API Key**.
2. Copy your API key.

### 5.3 Add to Backend `.env`

```env
SERPAPI_KEY=your_serpapi_key_here
```

### 5.4 Verify

```bash
curl "https://serpapi.com/search?engine=google_shopping&q=headphones&api_key=YOUR_KEY" | head -c 500
```

---

## 6. Rainforest API (Amazon Data)

Used for Amazon product search and pricing.

### 6.1 Create Account

1. Go to [https://www.rainforestapi.com/](https://www.rainforestapi.com/).
2. Sign up for a plan (free trial available).

### 6.2 Get API Key

1. Dashboard → API Key.

### 6.3 Add to Backend `.env`

```env
RAINFOREST_API_KEY=your_rainforest_key_here
```

---

## 7. ValueSerp / SearchAPI (Additional Providers)

Optional additional search providers for broader coverage.

### 7.1 ValueSerp

1. Sign up at [https://www.valueserp.com/](https://www.valueserp.com/).
2. Get API key from dashboard.

```env
VALUESERP_API_KEY=your_valueserp_key_here
```

### 7.2 SearchAPI

1. Sign up at [https://www.searchapi.io/](https://www.searchapi.io/).
2. Get API key from dashboard.

```env
SEARCHAPI_KEY=your_searchapi_key_here
```

**Note:** The backend sourcing system auto-detects which providers have keys configured and only uses those. You don't need all of them — even just SerpAPI alone is sufficient for development.

---

## 8. Google Gemini (LLM — BFF)

The BFF uses Google Gemini for chat, choice factor generation, and intent extraction.

### 8.1 Get API Key

1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Create a new API key (free tier available with generous limits).

### 8.2 Add to BFF `.env`

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

The BFF defaults to `gemini-1.5-flash-latest`. To change the model, set:

```env
GEMINI_MODEL=gemini-2.0-flash
```

### 8.3 Verify

The BFF logs the model name on startup. Check that chat responses come back when you type in the frontend.

---

## 9. WattData MCP (Vendor Discovery)

**Status:** Not yet available — expected online in ~2 weeks.

### 9.1 Current State (Mock)

The system uses `services/wattdata_mock.py` with hardcoded charter aviation vendors. No configuration needed for mock mode.

### 9.2 When MCP Goes Live

```env
VENDOR_DISCOVERY_BACKEND=wattdata
WATTDATA_MCP_URL=<provided_by_wattdata>
WATTDATA_API_KEY=<if_required>
```

### 9.3 Switching Between Mock and Live

```env
# Use mock data (default)
VENDOR_DISCOVERY_BACKEND=mock

# Use live WattData
VENDOR_DISCOVERY_BACKEND=wattdata
```

The system automatically falls back to mock if WattData is unreachable.

---

## 10. DocuSign (Contracts)

**Status:** Currently in demo mode — contracts are created as database records but not sent to DocuSign.

### 10.1 Create Developer Account

1. Go to [https://developers.docusign.com/](https://developers.docusign.com/).
2. Create a free developer account.
3. You get a sandbox environment automatically.

### 10.2 Get Credentials

1. In the DocuSign Admin dashboard, go to **Apps and Keys**.
2. Create a new app (or use the default).
3. Note:
   - **Integration Key** (client ID)
   - **Secret Key** (client secret)
   - **Account ID** (from your sandbox)
   - **Base URL** (`https://demo.docusign.net` for sandbox)

### 10.3 Create an Envelope Template

1. In DocuSign, go to **Templates → Create Template**.
2. Add placeholder fields for:
   - Buyer name / signature
   - Seller name / signature
   - Deal value
   - Item description
3. Note the **Template ID**.

### 10.4 Add to Backend `.env`

```env
DOCUSIGN_INTEGRATION_KEY=your_integration_key
DOCUSIGN_SECRET_KEY=your_secret_key
DOCUSIGN_ACCOUNT_ID=your_account_id
DOCUSIGN_BASE_URL=https://demo.docusign.net
DOCUSIGN_TEMPLATE_ID=your_template_id
```

### 10.5 Webhook Setup

DocuSign Connect sends status updates when envelopes are viewed, signed, etc.

1. In DocuSign Admin → **Connect → Add Configuration**.
2. URL: `https://your-backend-url.com/contracts/webhook/docusign`
3. Events: Envelope Sent, Viewed, Completed, Declined.

---

## 11. GitHub (Bug Fixer Automation)

The AI Bug Fixer creates GitHub issues from bug reports and auto-generates fix PRs.

### 11.1 Repository Setup

Ensure these secrets are set in your GitHub repo (**Settings → Secrets and Variables → Actions**):

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Claude API key for the AI bug fixer |
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions (no setup needed) |

### 11.2 Backend Configuration

```env
GITHUB_TOKEN=ghp_...  # Personal access token with repo scope
GITHUB_REPO=your-org/shopping-agent  # owner/repo format
```

### 11.3 Webhook (for PR status updates)

If you want the backend to receive updates when fix PRs are created:

1. Go to repo **Settings → Webhooks → Add webhook**.
2. Payload URL: `https://your-backend-url.com/webhooks/github`
3. Content type: `application/json`
4. Events: Pull requests, Issues.

---

## 12. Amazon Associates (Affiliate)

For Amazon affiliate link rewriting.

### 12.1 Join the Program

1. Go to [https://affiliate-program.amazon.com/](https://affiliate-program.amazon.com/).
2. Sign up (requires a website/app and content).
3. Get your **Associate Tag** (e.g., `buyanything-20`).

### 12.2 Add to Backend `.env`

```env
AMAZON_AFFILIATE_TAG=buyanything-20
```

The `AmazonAssociatesHandler` in `affiliate.py` automatically appends this tag to Amazon URLs during clickout.

### 12.3 Other Affiliate Networks

The handler registry supports additional networks. Configure as needed:

```env
EBAY_CAMPAIGN_ID=your_campaign_id
WALMART_IMPACT_ID=your_impact_id
SKIMLINKS_SITE_ID=your_site_id
CJ_WEBSITE_ID=your_website_id
CJ_PID=your_pid
```

---

## 13. Production Deployment (Railway)

### 13.1 Railway Setup

1. Create a Railway account at [https://railway.app/](https://railway.app/).
2. Create a new project.
3. Add services:
   - **Backend** — Dockerfile at `apps/backend/Dockerfile`
   - **BFF** — Node.js service at `apps/bff/`
   - **Frontend** — Dockerfile at `apps/frontend/Dockerfile`
   - **Postgres** — Railway managed Postgres addon

### 13.2 Environment Variables

Set all the variables from this guide in each Railway service's **Variables** tab. Key differences for production:

```env
# Backend
ENVIRONMENT=production
DATABASE_URL=postgresql://...  # Railway provides this
RAILWAY_ENVIRONMENT=production

# Frontend
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
BFF_URL=https://your-bff.up.railway.app

# BFF
BACKEND_URL=https://your-backend.up.railway.app
```

### 13.3 Database Migrations

```bash
# Run from backend directory
DATABASE_URL="your_production_db_url" uv run alembic upgrade head
```

---

## 14. Environment Variable Reference

### Backend (`apps/backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Postgres connection string |
| `SERPAPI_KEY` | Yes* | SerpAPI key (at least one search provider required) |
| `RAINFOREST_API_KEY` | No | Rainforest API key |
| `VALUESERP_API_KEY` | No | ValueSerp key |
| `SEARCHAPI_KEY` | No | SearchAPI key |
| `STRIPE_SECRET_KEY` | Phase 3 | Stripe API secret |
| `STRIPE_WEBHOOK_SECRET` | Phase 3 | Stripe webhook signing secret |
| `RESEND_API_KEY` | No | Resend email API key |
| `FROM_EMAIL` | No | Sender email (default: noreply@buyanything.ai) |
| `APP_BASE_URL` | No | Frontend URL (default: http://localhost:3003) |
| `AMAZON_AFFILIATE_TAG` | No | Amazon Associates tag |
| `GITHUB_TOKEN` | No | GitHub PAT for bug fixer |
| `GITHUB_REPO` | No | GitHub repo (owner/repo) |
| `VENDOR_DISCOVERY_BACKEND` | No | `mock` (default) or `wattdata` |
| `WATTDATA_MCP_URL` | No | WattData MCP connection URL |
| `DOCUSIGN_INTEGRATION_KEY` | No | DocuSign integration key |
| `DOCUSIGN_SECRET_KEY` | No | DocuSign secret |
| `DOCUSIGN_ACCOUNT_ID` | No | DocuSign account ID |
| `E2E_TEST_MODE` | No | Set to `true` to bypass auth in tests |
| `UPLOAD_DIR` | No | File upload directory path |

### BFF (`apps/bff/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GEMINI_MODEL` | No | Model name (default: gemini-1.5-flash-latest) |
| `BACKEND_URL` | No | Backend URL (default: http://localhost:8000) |
| `PORT` | No | BFF port (default: 8081) |

### Frontend (`apps/frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | No | Backend URL (default: http://localhost:8000) |
| `BFF_URL` | No | BFF URL (default: http://localhost:8081) |

---

## 15. Troubleshooting

### "No search results"
- Check that at least one search provider key is set (`SERPAPI_KEY`, etc.).
- Check backend logs for API errors (rate limits, invalid keys).
- Try: `curl http://localhost:8000/v1/sourcing/search -X POST -H "Content-Type: application/json" -d '{"query": "headphones"}'`

### "Database connection error"
- Ensure Docker is running: `docker ps` should show the Postgres container.
- Check `DATABASE_URL` in `.env` — default is `postgresql+asyncpg://postgres:postgres@localhost:5435/shopping_agent`.

### "Chat doesn't respond"
- Check BFF is running: `curl http://localhost:8081/health`
- Check `GEMINI_API_KEY` is set in `apps/bff/.env`.
- Check BFF logs for Gemini API errors.

### "Emails not sending"
- Check `RESEND_API_KEY` is set.
- Check Resend dashboard for delivery logs.
- In development, emails may go to spam or require domain verification.

### "Stripe webhook events not received locally"
- Ensure `stripe listen --forward-to localhost:8000/api/webhooks/stripe` is running.
- Use the webhook signing secret from the CLI output (not from the dashboard).

### "Auth not working"
- For development, set `E2E_TEST_MODE=true` in backend `.env` to bypass auth.
- Or run the seed script: `cd apps/backend && uv run python seed_auth.py`

### Ports Already in Use
```bash
# Find what's using a port
lsof -i :8000
lsof -i :8081
lsof -i :3003

# Kill it
kill -9 <PID>
```
