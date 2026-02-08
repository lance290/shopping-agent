# Architecture Audit — Shopping Agent

**Date:** 2026-02-08  
**Auditor:** Cascade  
**Verdict: You're not paranoid. This codebase is significantly over-engineered for its stage.**

---

## Executive Summary

This is an early-stage product with **~1 core user flow** (chat → search → see offers → pick one), but the codebase has been built out as if it were a mature marketplace with paying merchants, fraud rings, and enterprise compliance needs. The result is a system that is **hard to reason about, fragile to change, and full of dead code**.

**By the numbers:**

| Layer | Count | Lines |
|---|---|---|
| Postgres tables (models.py) | **22 tables** | 801 |
| Backend route files | **20 files** | 5,400+ |
| Backend services | **8 files** | 2,000+ |
| Frontend API proxy routes | **44 files** | 1,966 |
| Frontend components | **20 files** | 5,172 |
| Frontend pages | **11 pages** | — |
| BFF (index.ts) | **1 file** | **2,231** |
| Frontend store (store.ts) | **1 file** | 757 |

For context, a well-scoped MVP of this product should have ~5-7 tables, ~5 route files, ~10 frontend API routes, and no BFF.

---

## 🔴 Critical Issues

### 1. Massive over-modeling: 22 Postgres tables for a pre-PMF product

**Tables that are essential (6):**
- `user`, `auth_login_code`, `auth_session` — auth
- `row`, `request_spec`, `bid` — core product (search requests + results)

**Tables that are premature (16):**
- `project` — grouping feature, nice-to-have, not core
- `seller` — no real sellers onboarded
- `comment` — social feature with no users
- `audit_log` — enterprise compliance, no users yet
- `clickout_event` — affiliate tracking before any affiliate revenue
- `purchase_event` — Stripe tracking before any purchases
- `share_link`, `share_search_event` — viral loop tracking before any viral loops
- `notification` — notification system with no notification delivery
- `seller_quote`, `outreach_event`, `deal_handoff` — B2B marketplace machinery with zero live merchants
- `merchant` — merchant registry with zero merchants
- `contract` — DocuSign integration with no DocuSign account
- `user_signal`, `user_preference` — ML personalization with no training data
- `seller_bookmark` — seller feature with no sellers
- `bug_report` — could be a GitHub issue

**Impact:** Every schema migration touches a tangle of foreign keys. Every test needs to set up a web of related objects. Adding a simple column requires understanding 22 models and their relationships.

### 2. The "likes" system — your exact concern, validated

You mentioned likes specifically. Here's what exists for a "like" feature:

- **`Bid.is_liked`** and **`Bid.liked_at`** columns on the Bid table (reasonable)
- **`routes/likes.py`** — 218 lines, 5 endpoints: `POST /likes`, `DELETE /likes`, `GET /likes`, `GET /likes/counts`, `POST /likes/{bid_id}/toggle`
- **`apps/frontend/app/api/likes/route.ts`** — 117 lines (proxy)
- **`apps/frontend/app/api/likes/counts/route.ts`** — 61 lines (proxy)
- **`apps/frontend/app/components/LikeButton.tsx`** — 62 lines
- **`store.ts`** — ~100 lines of social data management (`BidSocialData`, `loadBidSocial`, `toggleLike`, optimistic updates)
- **`apps/frontend/app/api/bids/social/batch/route.ts`** — 28 lines (proxy)

**That's ~580+ lines of code across 7 files for a heart icon toggle that a single user sees.** There's no multi-user collaboration yet, so "like count" is always 0 or 1. The `GET /likes/counts` endpoint literally returns `{f"bid_{b.id}": 1 for b in liked_bids}` — it's always 1.

**What it should be:** `is_liked` boolean on `Bid` (already exists), a single PATCH endpoint, no dedicated route file.

### 3. The BFF is a 2,231-line God Object

`apps/bff/src/index.ts` is a monolithic file that:

- Manually loads `.env` files (lines 8-27)
- Implements its own HTTP client with retry logic (lines 31-87)
- Implements SSE streaming (lines 93-177)
- Contains hardcoded product-specific heuristics for bikes, racquets, socks, shoes (lines 179-323) — **directly violating the project's own rule against regex/keyword matching**
- Proxies bugs, merchants, clickout to backend (lines 389-489)
- Has a 300-line "deterministic chat fallback" (lines 607-913) that reimplements price parsing, row creation, and search
- Has the "real" LLM chat handler spanning lines 918-1500+ with massive code duplication

The `create_row` and `context_switch` handlers (lines 1080-1331) are nearly **identical copy-paste blocks** — same vendor fetch logic, same search logic, same error handling, duplicated 250+ lines.

### 4. Triple-proxy architecture adds latency and failure modes

Every user action traverses: **Browser → Next.js API route → BFF (Fastify) → Backend (FastAPI) → Postgres**

That's **3 network hops** where most apps have 1. The Next.js API routes are almost entirely dumb proxies — 44 files that just forward headers and bodies. Examples:

- `app/api/signals/route.ts` — 25 lines, just proxies to backend
- `app/api/signals/preferences/route.ts` — 19 lines, just proxies
- `app/api/stripe-connect/earnings/route.ts` — 19 lines, just proxies
- `app/api/admin/metrics/route.ts` — 21 lines, just proxies

**The BFF was introduced for LLM orchestration (chat).** Everything else should talk directly to the backend.

### 5. Dead code / services that can never execute

| Service | Issue |
|---|---|
| `services/reputation.py` (180 lines) | Never called at runtime. Previous audit (Phase 6) confirmed this. |
| `services/fraud.py` (71 lines) | In-memory rate limiting that resets on every deploy. Not useful. |
| `services/notify.py` (164 lines) | Creates `Notification` records, but no delivery mechanism (no email, no push, no websocket). |
| `services/outreach_monitor.py` (150 lines) | Monitors vendor outreach timeouts. No vendors exist. |
| `routes/stripe_connect.py` (218 lines) | Stripe Connect onboarding. No Stripe Connect account configured. |
| `routes/contracts.py` (184 lines) | DocuSign integration. No DocuSign account. |
| `routes/signals.py` (190 lines) | ML signal collection. No ML pipeline. |
| `routes/seller.py` (486 lines) | Full seller portal. No sellers. |
| `routes/checkout.py` (396 lines) | Batch checkout + Stripe. No checkout flow in UI. |
| `routes/merchants.py` (318 lines) | Merchant registry. Zero registered merchants. |
| `routes/notifications.py` (147 lines) | Notification CRUD. No notification UI in main app. |

**That's ~2,500+ lines of backend code that cannot produce any user-visible effect.**

### 6. Frontend store is a 757-line monolith

`store.ts` manages:
- Row CRUD + ordering
- Search results per row (with complex dedup/merge logic)
- Provider status tracking
- Social features (likes, comments)
- Sidebar state
- Bug report modal state
- Pending delete with undo
- Sort modes per row
- Card click queries

This should be 3-4 smaller stores or at minimum split into slices.

---

## 🟡 Moderate Issues

### 7. JSON-in-columns pattern used excessively

`choice_factors`, `choice_answers`, `chat_history`, `provenance`, `source_payload`, `search_intent`, `provider_query_map`, `diagnostics`, `attachments`, `answers`, `categories`, `service_areas` — all stored as JSON strings in text columns.

This means no indexing, no type safety, `JSON.parse` scattered everywhere with try/catch, and silent failures when the shape changes.

### 8. `BidWithProvenance` is a 80-line copy-paste of `Bid`

`models.py:383-465` duplicates every field from `Bid` into a response model, then adds computed properties. If a field is added to `Bid`, `BidWithProvenance` silently goes stale.

### 9. Two chat paths, one dead

The BFF has two complete chat implementations:
1. `runDeterministicChatFallback` (lines 607-913) — the "no LLM" path
2. The SSE-based LLM chat handler (lines 918-1500+)

The fallback is 300 lines of procedural code that reimplements row creation, price parsing, and search. It's a maintenance trap — changes to one path don't propagate to the other.

### 10. Hardcoded category heuristics in BFF violate project rules

`buildBasicChoiceFactors` (lines 179-323) uses regex to detect bikes, racquets, socks, shoes and returns hardcoded form fields. This directly contradicts the project memory that says:

> *"CRITICAL: Never use heuristics, regex, or keyword matching for decision-making."*

---

## 🟢 What's Actually Good

1. **Backend route decomposition** — splitting from a 1750-line `main.py` into modular route files was the right call. The individual route files are mostly clean.

2. **SQLModel + async** — good choice for the Python ORM layer. Models are well-typed.

3. **Auth pattern** — simple session tokens with hashed storage. Appropriate for stage.

4. **Streaming search** — SSE-based streaming of search results from multiple providers is legitimately useful and well-implemented.

5. **Safety service** — lightweight content moderation on row titles is appropriate.

6. **The core flow works** — chat → create row → search → display results → like/select. The happy path is functional.

---

## Recommendations

### Phase 1: Delete dead weight (1-2 days)

Remove the ~2,500 lines of backend code that can never execute. Specifically:
- Delete `routes/stripe_connect.py`, `routes/contracts.py`, `routes/signals.py`, `routes/checkout.py`, `routes/merchants.py`, `routes/notifications.py`
- Delete `services/reputation.py`, `services/fraud.py`, `services/notify.py`, `services/outreach_monitor.py`
- Delete corresponding models: `Contract`, `Merchant`, `Notification`, `UserSignal`, `UserPreference`, `SellerBookmark`, `PurchaseEvent`, `ShareSearchEvent`
- Delete corresponding frontend proxy routes
- Keep the migration history but mark tables as deprecated

### Phase 2: Collapse the BFF (2-3 days)

- Move LLM chat orchestration into the backend as a route
- Remove the BFF service entirely
- Frontend talks directly to backend (1 hop instead of 3)
- Delete all 44 proxy route files in `apps/frontend/app/api/`; replace with direct backend calls or a single catch-all proxy

### Phase 3: Simplify likes/comments/social (1 day)

- Collapse likes into a single `PATCH /bids/{id}` with `{is_liked: true/false}`
- Remove `routes/likes.py`, the 5 endpoints, and the 3 frontend proxy files
- Remove social data management from store.ts (~100 lines)

### Phase 4: Split the store (1 day)

- Core store: rows, activeRowId, projects
- Search store: rowResults, providerStatuses, sorting
- UI store: sidebar, modals, pending deletes

---

## Bottom Line

**You're not paranoid. The architecture has real structural problems — but the feature set is the right one.**

The marketplace revenue infrastructure (contracts, Stripe Connect, fraud detection, signals, notifications, seller portal, checkout) is all in the vision doc and all needed. That code stays.

What's actually wrong:

- **The BFF is a 2,231-line God Object** that should be collapsed into the backend — this is the #1 problem
- **The triple-proxy** (Browser → Next.js → BFF → Backend) adds 2 unnecessary hops and 44 boilerplate proxy files
- **Likes are 580 lines across 7 files** for a boolean toggle — that's the kind of over-engineering that makes the codebase feel fragile
- **Some services are built but disconnected** (reputation scoring, outreach monitor) — they need wiring, not deletion

The core product and the revenue features are sound. The delivery architecture (BFF + proxy layer + social feature plumbing) is where the unnecessary complexity lives.

See `docs/prd/pruning/` for the execution plans.
