<!-- PLAN_APPROVAL: approved by User at 2026-02-17T07:50:00Z -->

# Implementation Plan: Demo Day Public Surface

**Effort**: feature-demo-day-public-surface  
**Branch**: main  
**Created**: 2026-02-17  
**Deadline**: Wednesday EOD (demo Thursday)

---

## Architecture Overview

### Strategy: Route Groups + New Public Search Endpoint

The frontend uses Next.js App Router with flat page structure. We will introduce route groups to separate public and private layouts:

```
apps/frontend/app/
  layout.tsx              ← root layout (shared: HTML, body, globals.css, Skimlinks)
  (workspace)/            ← NEW route group for logged-in workspace
    layout.tsx            ← workspace-specific layout (no changes to existing)
    page.tsx              ← MOVE existing page.tsx here
  (public)/               ← NEW route group for public pages
    layout.tsx            ← public layout (header w/ search, footer w/ disclosure)
    page.tsx              ← public homepage (session detection → redirect if logged in)
    search/
      page.tsx            ← /search?q=... results page
    how-it-works/
      page.tsx
    about/
      page.tsx
    contact/
      page.tsx
    privacy/
      page.tsx
    terms/
      page.tsx
    vendors/
      page.tsx            ← vendor directory with vector search
      [slug]/
        page.tsx          ← vendor detail page (ISR)
    guides/
      page.tsx            ← guide index
      [slug]/
        page.tsx          ← individual guide pages
```

### Backend: New Public Search Endpoint

The existing `/api/search` and `/rows/{row_id}/search` both require authentication and a `row_id`. For public search, we need a lightweight endpoint that:
1. Accepts a raw query string (no row_id, no auth)
2. Runs `triage_provider_query()` → `extract_search_intent()` → builds per-retailer adapter queries
3. Runs **ALL providers in parallel** via `SourcingRepository.search_all_with_status()` — NO provider gating
4. Applies the **full three-stage re-ranking pipeline**:
   - Stage 1: Classical Scorer (`scorer.py`) — relevance, price, quality, diversity, tier_fit multiplier
   - Stage 2: Quantum Re-Ranker (`quantum/reranker.py`) — photonic interference scoring (if enabled)
   - Stage 3: Constraint Satisfaction (`quantum/constraint_scorer.py`) — structured intent matching
5. Returns `SearchResult[]` directly (no Bid persistence, no row_id)
6. Rate limiting by IP (not user_id)

```
POST /api/public/search
Body: { "query": "running shoes" }
Response: { "results": [...], "provider_statuses": [...] }
Auth: None required
Rate limit: 10/min per IP
```

### Scoring Fix: Vendor Directory tier_fit

**BUG FOUND**: `scorer.py:_tier_relevance_score()` penalizes vendor_directory results to 0.3 tier_fit for commodity/considered queries. This is wrong — our vendors include toy stores, bicycle shops, bookstores, etc. who ARE commodity sellers. The vector search similarity already handles relevance; tier_fit shouldn't double-penalize.

**Fix**: Vendor directory gets neutral-to-favorable tier_fit regardless of desire_tier:

| Source | commodity/considered | service/bespoke/high_value |
|--------|---------------------|---------------------------|
| Big box (Amazon, eBay) | 1.0 | 0.2 (Amazon can't cater) |
| **Vendor directory** | **0.85** (was 0.3!) | **1.0** (unchanged) |

### Middleware: Invert to Protected-Path Approach

Instead of whitelisting every public route, flip to a short protected-path list:

```typescript
const PROTECTED_PREFIXES = ['/admin', '/seller', '/merchants', '/bugs'];
// Everything else is public
// Session detection at / determines workspace vs homepage
```

---

## Implementation Phases

### Phase 0: Foundation (Tasks 1-3) — ~3 hours

**Task 1: Middleware Rewrite** (PRD-00) — 30 min
- File: `apps/frontend/middleware.ts`
- Invert logic: short `PROTECTED_PREFIXES` list instead of growing `PUBLIC_PATHS`
- Add `/share/*` and `/quote/*` to public (they're currently blocked!)
- Session detection: if user has `sa_session` cookie AND hits `/`, pass through to workspace; otherwise public
- Test: incognito browser can reach `/`, `/share/x`, `/quote/x` without redirect

**Task 2: Public Layout Shell** (PRD-01) — 1.5 hours
- Create `apps/frontend/app/(public)/layout.tsx`:
  - Header: logo, search bar (redirects to `/search?q=...`), "Sign In" link
  - Footer: links to `/disclosure`, `/privacy`, `/terms`, `/about`, `/contact`
  - `<AffiliateDisclosure />` component in footer
- Create `apps/frontend/app/(public)/page.tsx`:
  - Hero with universal search box, tagline
  - "How it works" 3-step section
  - Example searches ("Try: Roblox gift cards, local caterers, private jet charter")
  - Featured guides carousel (links to /guides/*)
- Move existing `apps/frontend/app/page.tsx` → `apps/frontend/app/(workspace)/page.tsx`
  - Update imports as needed
  - Ensure workspace layout wraps it (may need `(workspace)/layout.tsx`)

**Task 3: Backend Public Search Endpoint** (PRD-02 backend) — 1 hour
- Create `apps/backend/routes/public_search.py`:
  - `POST /api/public/search` — accepts `{ query: string }`
  - Step 1: `triage_provider_query()` → LLM-optimized search terms
  - Step 2: `extract_search_intent()` → structured `SearchIntent` (brand, model, price, features, keywords)
  - Step 3: `build_provider_query_map(intent, all_provider_ids)` → per-retailer adapted queries
  - Step 4: `SourcingRepository.search_all_with_status(query, desire_tier=desire_tier)` → **ALL providers in parallel, NO gating**
  - Step 5: `score_results()` → classical scoring with tier_fit multiplier
  - Step 6: Quantum re-ranking (if `QUANTUM_RERANKING_ENABLED`) → novelty + coherence scoring
  - Step 7: Constraint satisfaction scoring → structured intent matching
  - Returns `SearchResult[]` + `provider_statuses[]` — **no persistence, no row_id**
  - Rate limiting by IP: 10/min
  - **MUST NOT call `_filter_providers_by_tier()`** — all providers, always
  - `POST /api/public/quote-intent` — logs anonymous quote interest:
    - Fields: `query`, `vendor_slug`, `vendor_name`, `timestamp`, `user_agent`, `ip_hash`
    - New `QuoteIntentEvent` table (no PII — IP is hashed, no email/name captured)
    - Gives data: "X people showed interest in vendor Y for query Z this month"
    - Useful for vendor sales conversations: "47 qualified leads clicked Request Quote"
- Register routers in `main.py`
- Create frontend API proxy route `apps/frontend/app/api/proxy/public-search/route.ts`:
  - Uses `proxyPost()` with `{ allowAnonymous: true }`

### Phase 1: Core Public Pages (Tasks 4-6) — ~5 hours

**Task 4: Public Search Results Page** (PRD-02 frontend) — 2 hours
- Create `apps/frontend/app/(public)/search/page.tsx`:
  - Reads `?q=` from URL params
  - Calls `/api/proxy/public-search` with the query
  - Renders results as a responsive card grid:
    - **Product cards**: image, title, price, merchant, rating, "Buy" button → `/api/out` clickout
    - **Vendor cards**: name, tagline, source badge, "Request Quote" button
  - "Request Quote" → opens adapted `VendorContactModal` with LLM-generated outreach template based on query + vendor type (works for anonymous — opens `mailto:` link, no login needed)
  - Logged-in users get the same modal but with stored identity auto-filled
  - Inline `<AffiliateDisclosure />` near results
  - "Sign in to save and track" CTA (not a wall)
  - Loading states / progressive rendering as results arrive
- Create `PublicOfferCard` component (simplified version of OfferTile without bid_id dependencies):
  - No likes, no comments, no selection (these require bid_id)
  - "Buy" clickout works via URL (no bid_id needed)
  - "Request Quote" opens vendor contact modal (uses `mailto:` — no login needed)
- Adapt `VendorContactModal` for public context:
  - Remove `rowId` dependency — work from search query + vendor type instead of row `choice_answers`
  - LLM generates context-appropriate outreach template per vendor type (not just aviation)
  - Example: caterer gets "event for 50 people" template, toy store gets "bulk order" template, etc.
  - Opens `mailto:` link (existing pattern) — works for anonymous AND logged-in users
  - Logged-in users get identity auto-filled; anonymous users fill in their own name/role
  - **On modal open**: fire `POST /api/public/quote-intent` to log anonymous interest (no PII)

**Task 5: Static & Legal Pages** (PRD-03) — 1.5 hours
- Create 5 pages under `apps/frontend/app/(public)/`:
  - `how-it-works/page.tsx` — 3-step explanation with search CTA
  - `about/page.tsx` — Company mission, value prop
  - `contact/page.tsx` — Contact form (or email link)
  - `privacy/page.tsx` — Privacy policy template
  - `terms/page.tsx` — Terms of service template
- All use the public layout (header + footer automatic)
- All are SSG-friendly (no backend calls)

**Task 6: Editorial Guide Pages** (PRD-04) — 1.5 hours
- Create `apps/frontend/app/(public)/guides/page.tsx` — guide index
- Create `apps/frontend/app/(public)/guides/[slug]/page.tsx` — dynamic guide page
- Create 5 guide content files (MDX or JSON data):
  1. `how-buyanything-works` — Core value prop guide
  2. `gift-vault-tech-lovers` — Tech gifts with affiliate links
  3. `best-luggage-for-travel` — Product roundup
  4. `support-local-vendors` — Vendor directory showcase
  5. `home-office-setup-guide` — Product roundup
- Each guide: 800-1,500 words, inline affiliate disclosure, "Try our search" CTA
- Affiliate links route through `/api/out` clickout endpoint
- LLM-generated first drafts via `call_gemini()`, hand-edited for quality

### Phase 2: Vendor Directory + Polish (Tasks 7-9) — ~5 hours

**Task 7: Public Vendor Directory** (PRD-05) — 2.5 hours
- Backend: Create `apps/backend/routes/public_vendors.py`:
  - `GET /api/public/vendors` — paginated list of vendors (name, tagline, slug, image)
  - `GET /api/public/vendors/search?q=...` — vector search via `VendorDirectoryProvider`
  - `GET /api/public/vendors/{slug}` — single vendor detail (no email/phone exposed)
  - No backend endpoint needed for "Request Quote" — uses `mailto:` via adapted `VendorContactModal`
  - Rate limiting by IP
- Frontend: Create vendor pages:
  - `apps/frontend/app/(public)/vendors/page.tsx` — search box + vendor cards grid
  - `apps/frontend/app/(public)/vendors/[slug]/page.tsx` — vendor detail with ISR
  - Vector search on the `/vendors` page (calls backend vector search endpoint)
  - "Request Quote" CTA → adapted `VendorContactModal` (works for both anon and logged-in via `mailto:`)
- Frontend API proxy: `apps/frontend/app/api/proxy/public-vendors/route.ts` with `allowAnonymous: true`

**Task 8: Remove Legacy Provider Gating + Fix tier_fit Scoring** — 45 min
- File: `apps/backend/sourcing/repository.py`
  - Remove or no-op `_filter_providers_by_tier()` — make it return all providers always
  - Both public search and workspace search run ALL providers in parallel
- File: `apps/backend/sourcing/scorer.py`
  - Fix `_tier_relevance_score()` — vendor_directory should NOT be penalized for commodity/considered queries
  - Change vendor_directory tier_fit from 0.3 → 0.85 for commodity/considered
  - Rationale: vendor DB includes toy stores, bicycle shops, bookstores — they ARE commodity sellers. Vector search similarity handles relevance; tier_fit shouldn't double-penalize.
  - Keep big-box penalty for service/bespoke (0.2) — Amazon genuinely can't cater events
- Verify: search for "Roblox gift cards" returns BOTH Amazon results AND relevant vendor directory toy stores
- Verify: search for "caterer" returns BOTH vendor directory caterers (scored high) AND Amazon results (scored low via tier_fit)

**Task 9: Demo Prep & Polish** (PRD-06) — 2 hours
- Pre-test demo queries:
  - "Roblox gift cards $100" → verify Amazon/eBay results with clickout
  - "caterer for 50-person corporate event" → verify vendor results score high
  - "charter a jet from SAN to Aspen" → verify charter operators appear
- Verify social features: likes toggle, comment count visible, share links produce working URLs
- Verify affiliate system:
  - Document env vars: `AMAZON_AFFILIATE_TAG`, `EBAY_CAMPAIGN_ID`, `EBAY_ROTATION_ID`, `SKIMLINKS_PUBLISHER_ID`
  - Test `/api/out` clickout → verify `ClickoutEvent` logged with `user_id=None`
- Full link audit: click every nav link on the public surface, fix any 404s
- Mobile responsive check on all public pages
- Clean demo account (fresh workspace, no stale rows)

---

## Critical Path

```
Task 1 (Middleware) ──→ Task 2 (Layout + Homepage) ──┬──→ Task 4 (Search Results)
                                                      ├──→ Task 5 (Static Pages)
                                                      ├──→ Task 6 (Guides)
                                                      └──→ Task 7 (Vendor Directory)

Task 3 (Backend Public Search) ──→ Task 4 (Search Results)
Task 3 (Backend Public Search) ──→ Task 7 (Vendor Directory)

Task 8 (Remove Gating) — independent, can be done anytime

Tasks 4-7 ──→ Task 9 (Demo Prep)
```

**Parallelization**: Tasks 1+3 can run in parallel (frontend middleware + backend endpoint). Tasks 5+6 can run in parallel with Task 4 (they don't depend on search).

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Route groups vs flat | Route groups `(public)` / `(workspace)` | Clean layout separation, shared root layout |
| Public search endpoint | New `/api/public/search` | Existing endpoints require auth + row_id; cleaner than hacking those |
| Middleware approach | Invert to protected-path list | Short list that rarely changes vs growing public list |
| Guide storage | MDX or JSON data files | Static, SSG-friendly, no DB needed |
| Vendor directory | ISR with 24h revalidation | Fast loads, fresh enough for 3,000+ pages |
| Public OfferTile | New `PublicOfferCard` component | Existing OfferTile too coupled to bid_id; simpler display-only card |
| Vendor contact (public) | Adapt `VendorContactModal` | Remove rowId dependency; LLM generates per-vendor-type outreach templates; `mailto:` works without login |
| Vendor CTA language | "Request Quote" everywhere | Matches existing codebase — we don't invent new terminology |
| Vendor tier_fit scoring | 0.85 for commodity (was 0.3) | Vendors span all tiers; vector similarity handles relevance |

---

## Assumptions

1. The existing `SourcingRepository.search_all_with_status()` can be called without a `row_id` — it just needs a query string and optional kwargs
2. `triage_provider_query()` and `extract_search_intent()` work without `row_title` and `project_title` (they accept `None`)
3. Vendor slugs can be derived from vendor name (slugify) or we add a `slug` column
4. The Skimlinks script in root layout already handles universal affiliate link conversion for non-Amazon/eBay links
5. Guide content generation via LLM happens during development, not at runtime
6. The user is filling the vendor database in a parallel effort — we work with whatever vendors exist

---

## Success Criteria (maps to DoD)

| Criterion | Task | Evidence |
|-----------|------|----------|
| Anonymous `/` shows homepage | Task 1+2 | Incognito browser test |
| Anonymous search returns affiliate results | Task 3+4 | `/search?q=Roblox+gift+cards` in incognito |
| Demo scenarios A/B/C pass | Task 9 | Live walkthrough |
| No broken links | Task 9 | Full link audit |
| 5+ guides with 800+ words | Task 6 | Word count check |
| Vendor directory with vector search | Task 7 | Search "caterers" on `/vendors` |
| Social features functional | Task 9 | Like/comment/share in demo |
| Affiliate system documented | Task 9 | Env var documentation |

---

## Time Estimates

| Task | Est. Time | Phase |
|------|-----------|-------|
| Task 1: Middleware | 30 min | Phase 0 |
| Task 2: Layout + Homepage | 1.5 hr | Phase 0 |
| Task 3: Backend Public Search | 1 hr | Phase 0 |
| Task 4: Search Results Page | 2 hr | Phase 1 |
| Task 5: Static Pages | 1.5 hr | Phase 1 |
| Task 6: Guide Pages | 1.5 hr | Phase 1 |
| Task 7: Vendor Directory | 2.5 hr | Phase 2 |
| Task 8: Remove Gating + Fix Scoring | 45 min | Phase 2 |
| Task 9: Demo Prep | 2 hr | Phase 2 |
| **Total** | **~13.25 hours** | |
