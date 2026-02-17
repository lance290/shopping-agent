# Task Breakdown: Demo Day Public Surface

**Effort**: feature-demo-day-public-surface  
**Plan approved**: 2026-02-17T07:50:00Z  
**Tasks**: 12 (plan's 9 tasks split into <45min chunks)  
**Estimated total**: ~13.25 hours

---

## Phase 0: Foundation

### task-001: Middleware Rewrite (PRD-00)
**Est**: 30 min | **Depends on**: none | **Error budget**: 3

**E2E Flow**: Anonymous visitor hits `/` in incognito browser → sees page content (not login redirect). Logged-in user hits `/` → sees existing workspace.

**Files to modify**:
- `apps/frontend/middleware.ts` — invert logic from public-path whitelist to protected-path blacklist

**Manual Verification**:
1. Open incognito browser → go to `http://localhost:3000/` → should NOT redirect to `/login`
2. Open incognito → go to `http://localhost:3000/share/test-token` → should NOT redirect to `/login`
3. Open incognito → go to `http://localhost:3000/quote/test-token` → should NOT redirect to `/login`
4. Open incognito → go to `http://localhost:3000/admin` → SHOULD redirect to `/login`
5. Open incognito → go to `http://localhost:3000/seller` → SHOULD redirect to `/login`
6. Log in with valid credentials → go to `/` → should see existing workspace (no regression)

**Tests to write after**:
- `apps/frontend/e2e/middleware-public-routes.spec.ts` — test anonymous access to public routes and blocked access to protected routes

**Success criteria**: Anonymous users can reach `/`, `/share/*`, `/quote/*`, `/search`, `/vendors`, `/guides` without redirect. Protected routes (`/admin`, `/seller`, `/merchants`) still require auth.

---

### task-002: Public Layout Shell (PRD-01 — layout only)
**Est**: 45 min | **Depends on**: task-001 | **Error budget**: 3

**E2E Flow**: Anonymous visitor at `/` sees a page with: header (logo + search bar + "Sign In" link), footer (disclosure link, privacy, terms, about, contact links). Search bar submit redirects to `/search?q=...`.

**Files to create**:
- `apps/frontend/app/(public)/layout.tsx` — public layout with header + footer
- `apps/frontend/app/(public)/page.tsx` — placeholder homepage (hero + search box)
- `apps/frontend/components/PublicHeader.tsx` — header with logo, search bar, sign-in link
- `apps/frontend/components/PublicFooter.tsx` — footer with disclosure, legal links
- `apps/frontend/components/AffiliateDisclosure.tsx` — reusable inline disclosure component

**Files to modify**:
- `apps/frontend/app/page.tsx` → move to `apps/frontend/app/(workspace)/page.tsx`
- May need `apps/frontend/app/(workspace)/layout.tsx` for workspace-specific wrapping

**Manual Verification**:
1. Open incognito → `http://localhost:3000/` → see public homepage with search bar in header
2. Type "running shoes" in search bar → submit → URL changes to `/search?q=running+shoes`
3. Click "Sign In" in header → navigates to `/login`
4. Footer shows links to `/disclosure`, `/privacy`, `/terms`, `/about`, `/contact`
5. Log in → go to `/` → see existing workspace (not the public homepage)

**Tests to write after**:
- `apps/frontend/e2e/public-layout.spec.ts` — test header/footer rendering, search redirect, session detection

**Success criteria**: Public layout renders for anonymous users with working header search bar and footer links. Workspace still works for logged-in users.

---

### task-003: Public Homepage Content (PRD-01 — content)
**Est**: 30 min | **Depends on**: task-002 | **Error budget**: 3

**E2E Flow**: Anonymous visitor at `/` sees: hero section with tagline + search box, "How it works" 3-step section, example search links, featured guides carousel placeholder.

**Files to modify**:
- `apps/frontend/app/(public)/page.tsx` — flesh out homepage content

**Manual Verification**:
1. Open incognito → `http://localhost:3000/` → see hero with "Buy anything" tagline and search box
2. Below fold: "How it works" section with 3 steps
3. Example searches visible ("Try: Roblox gift cards, local caterers, private jet charter")
4. Click an example search → redirects to `/search?q=...`
5. Mobile viewport → search box prominent, content stacks properly

**Tests to write after**: Covered by task-002 E2E tests (extend if needed)

**Success criteria**: Homepage looks like a real content business, not a blank page. Mobile responsive. Example searches link to `/search`.

---

### task-004: Backend Public Search Endpoint (PRD-02 — backend)
**Est**: 45 min | **Depends on**: none (parallel with task-001/002/003) | **Error budget**: 3

**E2E Flow**: `curl -X POST http://localhost:8000/api/public/search -d '{"query":"running shoes"}'` → returns JSON with `results[]` and `provider_statuses[]`. ALL providers run in parallel. Three-stage re-ranking applied.

**Files to create**:
- `apps/backend/routes/public_search.py` — public search + quote-intent endpoints
- `apps/backend/models/quote_intent.py` — `QuoteIntentEvent` model

**Files to modify**:
- `apps/backend/main.py` — register new router

**Manual Verification**:
1. Start backend: `cd apps/backend && python main.py`
2. `curl -X POST http://localhost:8000/api/public/search -H 'Content-Type: application/json' -d '{"query":"running shoes"}'`
3. Verify response has `results` array with items from multiple providers
4. Verify response has `provider_statuses` array showing all providers ran
5. Verify NO auth header needed (200 without Bearer token)
6. Send 11 requests in 1 minute → 11th should return 429 (rate limit)
7. `curl -X POST http://localhost:8000/api/public/quote-intent -H 'Content-Type: application/json' -d '{"query":"caterers","vendor_slug":"test-vendor","vendor_name":"Test Caterer"}'` → 200

**Pipeline verification** (critical):
8. Search "caterer for corporate event" → verify vendor_directory results appear alongside retail results
9. Check that `_filter_providers_by_tier()` is NOT called in this endpoint
10. Verify `provider_statuses` shows rainforest, ebay_browse, vendor_directory all attempted

**Tests to write after**:
- `apps/backend/tests/test_public_search.py` — test endpoint returns results, rate limiting, no auth required

**Success criteria**: Public search endpoint runs full 7-step pipeline (LLM → intent → adapters → all providers parallel → score → rerank → constraint), returns results without auth, has rate limiting.

---

### task-005: Frontend Public Search API Proxy
**Est**: 15 min | **Depends on**: task-004 | **Error budget**: 3

**E2E Flow**: Frontend can call `/api/proxy/public-search` without auth and get search results back from the backend.

**Files to create**:
- `apps/frontend/app/api/proxy/public-search/route.ts` — proxies to backend `/api/public/search` with `allowAnonymous: true`
- `apps/frontend/app/api/proxy/quote-intent/route.ts` — proxies to backend `/api/public/quote-intent` with `allowAnonymous: true`

**Manual Verification**:
1. Start both frontend and backend
2. Open browser console → `fetch('/api/proxy/public-search', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({query:'shoes'})}).then(r=>r.json()).then(console.log)`
3. Verify results come back (no 401)

**Tests to write after**: Covered by task-006 E2E tests

**Success criteria**: Frontend proxy routes work for anonymous users.

---

### task-006: Public Search Results Page (PRD-02 — frontend)
**Est**: 45 min | **Depends on**: task-002, task-005 | **Error budget**: 3

**E2E Flow**: Anonymous visitor at `/search?q=running+shoes` → sees loading state → results appear as card grid with product cards (Buy button → clickout) and vendor cards (Request Quote button).

**Files to create**:
- `apps/frontend/app/(public)/search/page.tsx` — search results page
- `apps/frontend/components/PublicOfferCard.tsx` — simplified offer card (no bid_id dependencies)

**Manual Verification**:
1. Open incognito → `http://localhost:3000/search?q=Roblox+gift+cards`
2. See loading indicator, then results appear
3. Product cards show: image, title, price, merchant, "Buy" button
4. Click "Buy" on a product → opens `/api/out?url=...` → redirects to retailer
5. Vendor cards show: name, tagline, "Request Quote" button, source badge
6. Inline affiliate disclosure visible near results
7. "Sign in to save and track" CTA visible (not blocking)
8. Mobile viewport → single-column layout

**Tests to write after**:
- `apps/frontend/e2e/public-search.spec.ts` — test search results rendering, clickout links

**Success criteria**: Anonymous search works end-to-end with affiliate clickouts. Mixed product + vendor results displayed.

---

### task-007: Adapt VendorContactModal for Public Context
**Est**: 45 min | **Depends on**: task-006 | **Error budget**: 3

**E2E Flow**: Anonymous visitor on search results clicks "Request Quote" on a vendor card → modal opens with LLM-generated outreach template appropriate for the vendor type → user can send via mailto: or copy body. `QuoteIntentEvent` logged on modal open.

**Files to modify**:
- `apps/frontend/app/components/VendorContactModal.tsx` — add public mode that works without `rowId`, generates template from search context
- `apps/frontend/components/PublicOfferCard.tsx` — wire "Request Quote" button to modal

**Manual Verification**:
1. Open incognito → search for "caterers san francisco"
2. Click "Request Quote" on a vendor card
3. Modal opens with pre-filled email body appropriate for catering (not aviation)
4. "Send Email" button opens mailto: link
5. "Copy Body" button copies text to clipboard
6. Check backend logs → `QuoteIntentEvent` was logged with query + vendor info
7. Search for "Roblox gift cards" → vendor card "Request Quote" → template appropriate for retail/toy context (not aviation)

**Tests to write after**:
- Unit test for template generation logic

**Success criteria**: VendorContactModal works without rowId, generates context-appropriate templates, logs QuoteIntentEvent.

---

## Phase 1: Content

### task-008: Static & Legal Pages (PRD-03)
**Est**: 45 min | **Depends on**: task-002 | **Error budget**: 3

**E2E Flow**: Anonymous visitor clicks footer links → each page loads with real content, not placeholder. All pages use public layout.

**Files to create**:
- `apps/frontend/app/(public)/how-it-works/page.tsx`
- `apps/frontend/app/(public)/about/page.tsx`
- `apps/frontend/app/(public)/contact/page.tsx`
- `apps/frontend/app/(public)/privacy/page.tsx`
- `apps/frontend/app/(public)/terms/page.tsx`

**Manual Verification**:
1. Open incognito → click each footer link:
   - `/how-it-works` → 3-step explanation with search CTA
   - `/about` → company mission, value prop
   - `/contact` → contact form or info
   - `/privacy` → privacy policy (template OK for demo)
   - `/terms` → terms of service (template OK for demo)
2. Each page uses public header/footer
3. `/disclosure` link in footer → existing disclosure page loads
4. No 404s from any footer link

**Tests to write after**:
- `apps/frontend/e2e/static-pages.spec.ts` — test each page loads without 404

**Success criteria**: All 5 static pages exist with real content. No broken footer links.

---

### task-009: Editorial Guide Pages (PRD-04)
**Est**: 45 min | **Depends on**: task-002 | **Error budget**: 3

**E2E Flow**: Anonymous visitor navigates to `/guides` → sees guide index → clicks a guide → reads 800+ words of editorial content with affiliate links and search CTAs.

**Files to create**:
- `apps/frontend/app/(public)/guides/page.tsx` — guide index page
- `apps/frontend/app/(public)/guides/[slug]/page.tsx` — dynamic guide renderer
- Guide content data files (5 guides, MDX or JSON)

**Manual Verification**:
1. Open incognito → `http://localhost:3000/guides` → see list of 5+ guides
2. Click "How BuyAnything Works" → 800+ word guide loads
3. Click "Gift Vault: Tech Lovers" → guide with product links loads
4. Product links in guides use `/api/out` for clickout
5. Each guide has inline affiliate disclosure
6. Each guide has "Try our search" CTA at bottom
7. Mobile viewport → readable single-column layout

**Tests to write after**:
- `apps/frontend/e2e/guides.spec.ts` — test guide index and individual guides load

**Success criteria**: 5 guide pages live with 800+ words each, affiliate disclosure, and search CTAs.

---

## Phase 2: Vendor Directory + Polish

### task-010: Public Vendor Directory (PRD-05 — backend + frontend)
**Est**: 45 min | **Depends on**: task-002, task-005 | **Error budget**: 3

**E2E Flow**: Anonymous visitor at `/vendors` → sees search box → types "caterers" → vector search returns matching vendors → clicks vendor → detail page with description, specialties, website link, "Request Quote" CTA.

**Files to create**:
- `apps/backend/routes/public_vendors.py` — vendor list, search, detail endpoints
- `apps/frontend/app/api/proxy/public-vendors/[...path]/route.ts` — proxy with `allowAnonymous`
- `apps/frontend/app/(public)/vendors/page.tsx` — vendor directory with search
- `apps/frontend/app/(public)/vendors/[slug]/page.tsx` — vendor detail page

**Files to modify**:
- `apps/backend/main.py` — register vendor router

**Manual Verification**:
1. Open incognito → `http://localhost:3000/vendors` → search box visible
2. Type "caterers" → vendor results appear (vector search)
3. Vendor cards show: name, tagline, website link (NO email/phone)
4. Click a vendor → `/vendors/[slug]` detail page loads
5. Detail page shows: description, specialties, service areas, website link
6. "Request Quote" button → opens adapted VendorContactModal
7. No email addresses or phone numbers visible anywhere

**Tests to write after**:
- `apps/backend/tests/test_public_vendors.py` — test vendor endpoints
- `apps/frontend/e2e/vendor-directory.spec.ts` — test search and detail pages

**Success criteria**: Vendor directory with vector search works anonymously. No PII exposed. "Request Quote" functional.

---

### task-011: Remove Legacy Provider Gating + Fix tier_fit Scoring
**Est**: 30 min | **Depends on**: none (independent) | **Error budget**: 3

**E2E Flow**: Search for "Roblox gift cards" → results include BOTH Amazon products AND relevant toy store vendors from directory. Search for "caterer" → vendor directory caterers score highest, Amazon results score low but still appear.

**Files to modify**:
- `apps/backend/sourcing/repository.py` — make `_filter_providers_by_tier()` pass-through (return all providers)
- `apps/backend/sourcing/scorer.py` — change vendor_directory tier_fit from 0.3 → 0.85 for commodity/considered

**Manual Verification**:
1. Start backend
2. Search "Roblox gift cards" via public endpoint → verify vendor_directory results appear (if matching vendors exist)
3. Search "caterer for corporate event" → verify both vendor and retail results appear
4. Check score provenance: vendor results for "caterer" should have high tier_fit (1.0), retail results should have low tier_fit (0.2)
5. Check score provenance: vendor results for "Roblox gift cards" should have tier_fit 0.85 (not 0.3)

**Tests to write after**:
- `apps/backend/tests/test_tier_scoring.py` — test tier_fit values for various source/tier combinations

**Success criteria**: No provider gating. Vendor directory gets fair tier_fit across all desire tiers. Re-ranker handles relevance.

---

### task-012: Demo Prep & Polish (PRD-06)
**Est**: 45 min | **Depends on**: all previous tasks | **Error budget**: 3

**E2E Flow**: Run all 3 demo scenarios end-to-end without errors. All public pages accessible. No broken links.

**Files to modify**: Various (bug fixes found during testing)

**Manual Verification — Demo Scenario A** ("Roblox gift cards"):
1. Open incognito → `http://localhost:3000/`
2. Type "Roblox gift cards $100" in search → redirected to `/search?q=...`
3. See Amazon/eBay results with prices and images
4. Click "Buy" → `/api/out` redirect → lands on retailer site
5. Check DB: `ClickoutEvent` logged with `user_id=None`

**Manual Verification — Demo Scenario B** ("caterer for 50 people"):
1. Log in → workspace
2. Type "I need a caterer for a 50-person corporate event"
3. See vendor directory caterers scored high, Amazon results scored low
4. Click "Request Quote" on a caterer → VendorContactModal opens with catering template
5. Outreach email draft looks correct

**Manual Verification — Demo Scenario C** (viral loop story):
1. Show quote page: `/quote/[token]` renders for anonymous vendor
2. Show referral attribution code path
3. Explain flywheel narrative

**Full Link Audit**:
4. Click every nav link on public surface — no 404s
5. Check all footer links work
6. Verify mobile responsive on all pages

**Affiliate Verification**:
7. Document env vars: `AMAZON_AFFILIATE_TAG`, `EBAY_CAMPAIGN_ID`, `EBAY_ROTATION_ID`, `SKIMLINKS_PUBLISHER_ID`
8. Verify `/api/out` clickout logs events even without active affiliate tags

**Social Features**:
9. Like a tile → heart toggles with count
10. Comment on a tile → comment appears
11. Share a tile → URL copies, share page renders

**Tests to write after**: None (this is QA/polish, not new features)

**Success criteria**: All 3 demo scenarios run smoothly. No broken links. No placeholder content. Social features functional. Affiliate system documented.

---

## Task Summary

| ID | Description | Est | Phase | Depends On |
|----|-------------|-----|-------|------------|
| task-001 | Middleware rewrite | 30m | 0 | — |
| task-002 | Public layout shell | 45m | 0 | 001 |
| task-003 | Homepage content | 30m | 0 | 002 |
| task-004 | Backend public search endpoint | 45m | 0 | — |
| task-005 | Frontend search API proxy | 15m | 0 | 004 |
| task-006 | Public search results page | 45m | 1 | 002, 005 |
| task-007 | Adapt VendorContactModal | 45m | 1 | 006 |
| task-008 | Static & legal pages | 45m | 1 | 002 |
| task-009 | Editorial guide pages | 45m | 1 | 002 |
| task-010 | Public vendor directory | 45m | 2 | 002, 005 |
| task-011 | Remove gating + fix scoring | 30m | 2 | — |
| task-012 | Demo prep & polish | 45m | 2 | all |
