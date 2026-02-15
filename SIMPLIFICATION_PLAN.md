# Codebase Simplification Plan

## Executive Summary

This codebase has **~50,000 lines of application code** serving what is fundamentally a **3-entity app** (User, Row, Bid). It has been over-engineered through 6 phases of PRD-driven development, accumulating **24 database tables**, **25 backend route files**, **44 frontend proxy routes**, and **3 separate vendor/seller models** — most of which are dead code that has never been used by a real user.

The recurring bugs aren't caused by bad developers. They're caused by **unnecessary indirection and duplication** that makes every simple change touch 4+ files across 3+ layers.

---

## The Numbers

| Metric | Count | Problem |
|--------|-------|---------|
| Backend Python LOC | 30,857 | ~60% is dead features |
| Frontend TS/TSX LOC | 19,482 | ~40% is proxy boilerplate |
| Database tables | 24 | Only ~8 are used in the core flow |
| Backend route files | 25 | Only ~8 serve the actual UI |
| Frontend API proxy routes | 44 | Pure pass-through boilerplate |
| Backend services | 10 | 3 are never imported by any route |
| PRD documents | 98 | Planning > building ratio is inverted |
| CFOI tracking files | 454 | Process overhead |
| Root-level report MDs | 12 (6,857 LOC) | AI-generated documentation noise |
| Zustand stores | 2 competing implementations | `store.ts` (599 LOC) + `stores/` (839 LOC) |

---

## Root Cause Analysis

### Problem 1: The Proxy Layer Tax (44 files of pure boilerplate)

Every API call follows this path:

```
Browser → Next.js API Route (proxy) → Backend FastAPI Route → DB
```

Each of those 44 `route.ts` files in `apps/frontend/app/api/` is a **hand-written HTTP proxy** that:
- Redefines `getAuthHeader()` (copy-pasted 9 times)
- Redefines `BACKEND_URL` (defined 6+ different ways across files)
- Adds zero business logic — just forwards request/response

**Why this keeps causing bugs:** When the backend URL changes (port, path), you have to update it in N different proxy files. Some use `bff.ts` BACKEND_URL, some hardcode their own, some use `NEXT_PUBLIC_API_URL`, some use `NEXT_PUBLIC_BACKEND_URL`. This is why likes broke (pointed to BFF port 8081 instead of backend port 8000), clickouts broke (`/api/clickout` vs `/api/out`), and every port change causes a cascade of failures.

### Problem 2: Duplicated Core Code

The `sourcing.py` (779 LOC) at the backend root is a **complete duplicate** of `sourcing/repository.py` (1,128 LOC):

| Symbol | Defined in `sourcing.py` | Defined in `sourcing/repository.py` |
|--------|--------------------------|-------------------------------------|
| `SearchResult` | ✅ | ✅ |
| `SearchResultWithStatus` | ✅ | ✅ |
| `extract_merchant_domain()` | ✅ | ✅ |
| `normalize_url()` | ✅ | ✅ |
| `compute_match_score()` | ✅ | ✅ |
| `redact_secrets` | ✅ | ✅ |

Both are actively imported. `main.py` and `routes/clickout.py` import from `sourcing.py` (root). `routes/rows_search.py` imports from both. This means bug fixes in one don't fix the other. Models drift. This is a direct source of recurring bugs.

### Problem 3: Three Vendor Entities, Zero Clarity

The codebase has three overlapping models for "a company that sells things":

| Model | Table | Purpose | Used? |
|-------|-------|---------|-------|
| `Seller` | `seller` | Attached to Bids, stores vendor name/domain | ✅ Active |
| `VendorProfile` | `vendor_profile` | Directory entry with embeddings | ✅ Seeded (162 vendors) |
| `Merchant` | `merchant` | Self-registered marketplace seller | ❌ No real merchants |

Plus: `Seller` has `email`, `domain`, `phone`, `category`. `VendorProfile` has `contact_email`, `contact_phone`, `category`, `website`. `Merchant` has `email`, `phone`, `website`, `categories`. Same data, three tables, no FK linking them reliably.

### Problem 4: Dead Feature Sprawl

Features built to PRD spec but **never used by any real user** and not wired into the UI:

| Feature | Backend Route | Frontend Proxy | UI Component | Actually Used? |
|---------|--------------|----------------|--------------|----------------|
| Contracts/DocuSign | `contracts.py` (184 LOC) | ❌ | ❌ | **Dead** |
| Signals/Preferences | `signals.py` (190 LOC) | proxy exists | ❌ No UI | **Dead** |
| Stripe Connect | `stripe_connect.py` (218 LOC) | proxy exists | disclosure text only | **Dead** |
| Reputation scoring | `services/reputation.py` (179 LOC) | ❌ | ❌ | **Dead** (never imported) |
| Fraud detection | `services/fraud.py` (70 LOC) | ❌ | ❌ | **Dead** |
| Outreach monitor | `services/outreach_monitor.py` (150 LOC) | ❌ | ❌ | **Dead** |
| Vendor discovery | `services/vendor_discovery.py` (217 LOC) | ❌ | ❌ | **Dead** (never imported) |
| Seller bookmarks | route + proxy | proxy exists | ❌ No UI | **Dead** |
| Batch checkout | route + proxy | proxy exists | ❌ | **Dead** |
| Share link analytics | 5 metric fields on ShareLink | ❌ | ❌ | **Dead** |
| Personalized ranking | 6 score columns on Bid | ❌ | ❌ | **Dead** |
| Purchase events | `purchase_event` table | ❌ | ❌ | **Dead** |
| Audit log | `audit_log` table | logged but never read | ❌ | **Write-only dead** |
| Notification system | route + proxy | proxy exists | ❌ No bell icon | **Dead** |

Estimated dead code: **~8,000 LOC backend + ~1,500 LOC frontend proxies**.

### Problem 5: Two Competing State Stores

The frontend has:
- `app/store.ts` (599 LOC) — the **actual** store used by all 11 component imports
- `app/stores/` directory (839 LOC) — a "modular rewrite" that wraps the same logic in proxy getters

All components import from `'../store'`. The `stores/` directory is dead weight that adds confusion about which is canonical.

### Problem 6: JSON-in-String Anti-Pattern

At least **15 model fields** store structured data as `Optional[str]` with a comment `# JSON`. This means:
- No schema validation on write
- `json.loads()` scattered everywhere with try/catch
- Silent data corruption when JSON is malformed
- Can't query these fields in SQL

Fields affected: `choice_factors`, `choice_answers`, `search_intent`, `provider_query_map`, `chat_history`, `constraints`, `preferences`, `source_payload`, `provenance`, `service_areas` (×2), `categories`, `answers`, `attachments`, `diagnostics`, `details`.

### Problem 7: Process Overhead

| Artifact | Count | Value |
|----------|-------|-------|
| PRD documents | 98 | Planning paralysis |
| CFOI tracking files | 454 | Busywork artifacts |
| Windsurf workflows | 35 | Meta-process |
| Root-level audit/report MDs | 12 | Stale AI-generated reports |
| Alembic migrations | 25 | Many for dead features |

The ratio of planning/tracking artifacts to shipped features is deeply inverted.

---

## The Recurring Bug Pattern

From the session memories, the same bugs keep happening:

1. **Port/URL mismatch** — Likes → BFF port instead of backend. Clickout → `/api/clickout` vs `/api/out`. Frontend → `localhost` instead of Railway internal URL. Root cause: **44 proxy files with inconsistent URL definitions**.

2. **Wrong data on wrong row** — Search results appearing on the wrong card. Root cause: **complex async state management with race conditions** in a 600-line store.

3. **Likes not persisting** — Used sorted array index to update unsorted array. Root cause: **Offer identity is unstable** — `getOfferStableKey()` has 4 fallback strategies because the data model doesn't have a single clean ID.

4. **Project assignment dropping** — BFF didn't forward projectId. Root cause: **extra proxy layer** loses context.

5. **Data wipes** — Migration scripts using DELETE+INSERT instead of upserts. Root cause: **too many tables and migrations for dead features** making schema management fragile.

---

## Simplification Plan

### Phase 0: Stop the Bleeding (1 day)

**Goal:** Eliminate the #1 source of recurring bugs — the proxy layer inconsistency.

1. **Create a single `apps/frontend/app/utils/api-proxy.ts` helper** (~30 LOC) that:
   - Defines `BACKEND_URL` once
   - Exports `getAuthHeader()` once
   - Exports `proxyToBackend(request, path, method)` once

2. **Rewrite all 44 proxy routes** to use it. Each becomes ~5 lines:
   ```typescript
   import { proxyGet } from '../../utils/api-proxy';
   export const GET = (req) => proxyGet(req, '/rows');
   ```

3. **Or better: use Next.js `rewrites` in `next.config.js`** to eliminate most proxy routes entirely:
   ```javascript
   async rewrites() {
     return [
       { source: '/api/backend/:path*', destination: 'http://localhost:8000/:path*' }
     ];
   }
   ```
   This eliminates 30+ proxy files with zero behavior change.

### Phase 1: Delete Dead Code (1 day)

**Goal:** Remove ~10,000 lines of dead code.

**Backend deletions:**
- `apps/backend/sourcing.py` (779 LOC) — duplicate of `sourcing/repository.py`. Update 3 import sites.
- `apps/backend/routes/contracts.py` (184 LOC) — no UI
- `apps/backend/routes/signals.py` (190 LOC) — no UI
- `apps/backend/routes/stripe_connect.py` (218 LOC) — no UI
- `apps/backend/services/reputation.py` (179 LOC) — never imported
- `apps/backend/services/vendor_discovery.py` (217 LOC) — never imported
- `apps/backend/services/fraud.py` (70 LOC) — single callsite, no real logic
- `apps/backend/services/outreach_monitor.py` (150 LOC) — never called
- `apps/backend/services/wattdata_mock.py` (25 LOC) — unused
- Remove dead columns from Bid model: `combined_score`, `relevance_score`, `price_score`, `quality_score`, `diversity_bonus`, `source_tier`
- Remove dead columns from User: `trust_level`
- Remove dead columns from Merchant: `verification_level`, `reputation_score`, `stripe_*` fields
- Remove dead columns from ClickoutEvent: `is_suspicious`
- Remove dead metric fields from ShareLink (5 fields)

**Frontend deletions:**
- `apps/frontend/app/stores/` directory (839 LOC) — unused, all components use `../store`
- Dead proxy routes for deleted backend routes
- `apps/frontend/app/api/signals/` — no UI
- `apps/frontend/app/api/stripe-connect/` — no UI
- `apps/frontend/app/api/seller/bookmarks/` — no UI
- `apps/frontend/app/api/checkout/batch/` — no UI

**Root-level deletions:**
- `ARCHITECTURE_ANALYSIS.md`, `CODE_QUALITY_AUDIT.md`, `CODE_REVIEW_HIGHLIGHTS.md`, `CODE_REVIEW_REPORT.md`, `CODE_REVIEW_SUMMARY.md`, `DEAD_CODE_REMOVAL_ANALYSIS.md`, `SECURITY_AUDIT_REPORT.md`, `SECURITY_ACTION_PLAN.md`, `SECRETS_MANAGEMENT.md` — stale AI-generated reports (6,857 LOC)

### Phase 2: Unify the Vendor Model (2 days)

**Goal:** One entity for "a company that sells things."

1. Merge `Seller` + `VendorProfile` + `Merchant` into a single `Vendor` table:
   - `id`, `name`, `email`, `phone`, `website`, `domain`
   - `category`, `service_areas` (proper JSONB if PG, else keep as JSON string)
   - `status` (unverified, verified, suspended)
   - `embedding` (for vector search)
   - `stripe_account_id` (nullable, for future)

2. `Bid.seller_id` → `Bid.vendor_id` FK to `Vendor`

3. Write a single migration that merges existing data.

4. Delete `models/marketplace.py` VendorProfile and Merchant. Move remaining marketplace models (SellerQuote, OutreachEvent, DealHandoff, Contract) to a single `models/deals.py` if kept, or delete if dead.

### Phase 3: Fix the Data Model (2 days)

**Goal:** Eliminate JSON-in-string fields for core entities.

1. **Row.choice_factors** → proper `JSONB` column (Postgres) or keep as JSON but add a Pydantic validator that ensures it's always valid JSON on write.

2. **Row.choice_answers** → same treatment.

3. **Row.chat_history** → This should be a separate `ChatMessage` table or removed entirely if the backend chat route manages its own context.

4. **Bid.provenance** → Either use JSONB or delete (the `BidWithProvenance` response model parses it on every read).

5. **RequestSpec** table — consider inlining into `Row`. It's always 1:1, adds a JOIN for no reason, and only has `item_name` + `constraints` (which duplicates `Row.title`).

### Phase 4: Simplify the Frontend State (1 day)

**Goal:** One clean store, stable identity for offers.

1. **Kill `getOfferStableKey()`** — The Bid has an `id`. Use it. Every offer displayed should have a `bid_id` after persistence. Pre-persistence offers get a temporary client-side UUID.

2. **Simplify `store.ts`:**
   - Remove `searchResults` (legacy, unused)
   - Remove `rowProviderStatuses` (nice-to-have debug info, not core)
   - Remove `rowSearchErrors` (fold into a simpler error state)
   - Remove `moreResultsIncoming` (use `isSearching` only)
   - Remove `selectOrCreateRow` client-side heuristic — the LLM already decides this in the chat route

3. **Remove `mapBidToOffer()`** — The backend should return data in the shape the frontend needs. Having a Bid→Offer transform in the client means two representations of the same thing.

### Phase 5: Simplify the Sourcing System (2 days)

**Goal:** One search path, not two.

Currently there are two search code paths:
- `sourcing.py` (root, 779 LOC) — imported by `main.py` for `/v1/sourcing/search`
- `sourcing/` package (3,376 LOC) — used by `routes/rows_search.py` for the actual search

1. Delete `sourcing.py` root file.
2. Make `sourcing/repository.py` the single `SourcingRepository`.
3. Collapse `sourcing/service.py` + `sourcing/repository.py` if they don't justify separation (service just wraps repo with DB persistence).
4. Delete `sourcing/metrics.py` (214 LOC) if metrics aren't being consumed anywhere.

### Phase 6: Clean Up Process Artifacts (1 day)

1. Archive or delete `.cfoi/` — 454 files of process tracking
2. Archive or delete `docs/prd/` — 98 PRDs, most for dead features
3. Trim `.windsurf/workflows/` to only the 5-6 actually useful ones
4. Delete `review-loop/`, `notes/`, `tools/` if not actively used

---

## What the Codebase Should Look Like After

```
apps/
  backend/                    (~12,000 LOC, down from ~31,000)
    models/
      __init__.py
      auth.py                 (User, AuthSession, AuthLoginCode)
      core.py                 (Row, Project, Bid, Vendor)
      social.py               (Comment, ShareLink, ClickoutEvent)
      deals.py                (SellerQuote, OutreachEvent, DealHandoff)
    routes/
      auth.py
      rows.py                 (merged with rows_search.py)
      bids.py
      chat.py
      likes.py
      comments.py
      clickout.py
      shares.py
      outreach.py
      quotes.py
      projects.py
      admin.py
      bugs.py
    services/
      llm.py
      email.py
      vendors.py
      intent.py
    sourcing/                 (single implementation)
      repository.py
      service.py
      normalizers/
      adapters/
    main.py
    database.py
    
  frontend/                   (~12,000 LOC, down from ~19,000)
    app/
      api/                    (5-10 routes max, or 0 with rewrites)
      components/             (same, but with simplified data flow)
      store.ts                (single, simplified)
      page.tsx
      login/
      quote/
      share/
      admin/
```

**Target: ~24,000 LOC total (down from ~50,000), same functionality, half the bug surface.**

---

## Execution Order

| Phase | Effort | Risk | Impact |
|-------|--------|------|--------|
| 0: Fix proxy layer | 1 day | Low | Eliminates #1 recurring bug class |
| 1: Delete dead code | 1 day | Low | -10K LOC, clearer codebase |
| 2: Unify vendor model | 2 days | Medium (migration) | Eliminates confusion |
| 3: Fix data model | 2 days | Medium (migration) | Eliminates JSON parse bugs |
| 4: Simplify frontend state | 1 day | Medium | Eliminates wrong-row bugs |
| 5: Simplify sourcing | 2 days | Low-Medium | Eliminates duplicate code |
| 6: Clean process artifacts | 1 day | None | Mental clarity |

**Total: ~10 days of focused work.**

Start with Phase 0 + Phase 1. They're low risk and immediately impactful.
