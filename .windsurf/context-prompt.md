# Context Prompt: Shopping Agent — Revenue Channels & Stability

## Project
BuyAnything Shopping Agent — a marketplace platform at `buy-anything.com` (+ `dev.buy-anything.com`, `popsavings.com`, `dev.popsavings.com`). FastAPI backend on Railway, Next.js 15 frontend on Railway. Postgres with pgvector for vendor embeddings.

## What Was Done This Session (Mar 3, 2026)

### 1. Fixed Production 502 Error
- **Root cause**: `startup_event()` in `main.py` ran 30+ DB queries that blocked the async event loop when Postgres was unreachable. Each hung for 60s, causing Railway healthcheck to fail.
- **Fix**: Wrapped all startup migrations in `asyncio.timeout(15s/10s)`. Added `scripts/check_db.py` for DB readiness check in `start.sh`. Added asyncpg `timeout: 10s` and `command_timeout: 30s` in `database.py`.

### 2. Fixed All Revenue Channel Bugs
- **Affiliate clickout 404**: `.gitignore` had bare `out` which matched `app/api/out/` directory — the clickout route was never deployed. Changed to `/out`.
- **Stripe redirect to localhost**: Next.js API proxy wasn't forwarding `Origin`/`Referer`/`X-Forwarded-Host` headers to backend. Fixed in `api-proxy.ts` + backend `_get_app_base()` now checks `X-Forwarded-Host` first.
- **Blast outreach TypeError**: `send_custom_outreach_email` was called with wrong params (`to_name`/`company_name` instead of `to_email`/`vendor_company`).
- **DEV_EMAIL_OVERRIDE in production**: Added auto-disable when `RAILWAY_ENVIRONMENT` is set.
- **eBay clickout 422**: Empty `bid_id=` in URL. Fixed to only include when present.
- **eBay persist crash**: Streaming path called `normalize_ebay_results` (expects raw dicts) with `SearchResult` objects. Changed to `normalize_generic_results`.
- **Streaming search stuck forever with 0 results**: Row stayed in `bids_arriving` indefinitely. Added status update after SSE stream completes — 0 results → `build_zero_results_schema()`.

### 3. Vendor EA Workflow
- **Problem**: ALL vendor bids (NetJets, PrivateFly, etc.) went through affiliate clickout redirect instead of opening the outreach email modal.
- **Fix**: Backend `_hydrate_action_row` now checks `bid.source == "vendor_directory"` → emits `contact_vendor` intent. Frontend `BidCard` checks `offer.source === 'vendor_directory'` → renders green "Request Quote" button that opens `VendorContactModal`.

### 4. Source Display Pills
- Changed `rainforest_amazon` → "Amazon", `ebay_browse` → "eBay", `serpapi` → "Google", etc. in `AppView.tsx`.

### 5. HNSW Vector Index
- Added `CREATE INDEX IF NOT EXISTS vendor_embedding_hnsw_idx ON vendor USING hnsw (embedding vector_cosine_ops)` to startup migrations. Failed on first deploy due to **DB disk full** (`DiskFullError`). User is resizing the Railway Postgres volume.

### 6. DB Cleanup Script
- Created `scripts/cleanup_db.py` — trims old audit_logs, clickout_events, etc. Supports `--execute` and `--days` flags. Also shows table sizes and vendor embedding stats.

### 7. Tests Written
- `test_regression_session_fixes.py` — 27 unit tests covering every fix
- `test_e2e_revenue_flows.py` — 15 DB-backed e2e scenario tests
- `test_scenario_revenue_no_db.py` — 34 scenario tests (no DB needed)
- All 674 existing tests still pass (0 failures)

### 8. File Splitting (Partial — User Will Continue Elsewhere)
Splitting all files > 450 lines per user rules. Completed:
- `main.py`: 582→308 (extracted `startup_migrations.py`)
- `email.py`: 952→367 (extracted `services/email_handoff.py`)
- `outreach.py`: 1016→423 (extracted `outreach_vendors.py`, `outreach_blast.py`, `outreach_tracking.py`)
- `repository.py`: 1303→539 (extracted `providers_search.py`, `providers_marketplace.py`)

Still over 450: `repository.py`(539), `auth.py`(783), `llm.py`(750), `vendors.py`(729), `chat.py`(723), `admin.py`(623), `service.py`(612), `fix_schema.py`(606), `pop_list.py`(573), plus 5 test files and 2 script files.

## Open Issues / Next Steps

1. **DB disk full on Railway** — user is resizing. Once done:
   - Run `python scripts/cleanup_db.py --execute` to free space
   - HNSW index will create on next backend restart
   - Vendor vector search should start working (currently returns 0 results due to disk full errors)

2. **Vendor search returns 0 results** — the `vendor_directory` provider returned 0 results for "private jet charter" despite 3,741 vendors in DB. Likely caused by disk-full DB failing the vector query. Timing instrumentation added to `vendor_provider.py` — check Railway logs after next deploy.

3. **File splits remaining** — 12 source files + 7 test/script files still over 450 lines.

4. **Future: Audit log data lake** — User mentioned Parquet setup to offload high-volume event tables from hot Postgres.

## Key Architecture Notes
- Backend: FastAPI + SQLModel + asyncpg + pgvector
- Frontend: Next.js 15 App Router, SDUI (Server-Driven UI) architecture
- API proxy: Next.js API routes forward to backend via `api-proxy.ts`
- Affiliate: Amazon (tag), eBay (campid), clickout tracked via `/api/out`
- Outreach: Resend for transactional email, reply-to set to user's email
- SDUI: `sdui_builder.py` hydrates UI schemas from bids, `ActionRow.tsx` renders actions
- 4 domains: buy-anything.com, dev.buy-anything.com, popsavings.com, dev.popsavings.com
- Pop domain routing via Next.js middleware rewrite to `/pop-site/`

## Latest Commit
`37b0ee7` on `origin/main` — all tests passing
