# PRD: Thursday Demo — Affiliate Readiness & Public Surface

**Status**: Active  
**Date**: 2026-02-17  
**Priority**: P0 — investor demo Thursday, affiliate applications immediately after  
**Deadline**: Wednesday EOD (demo-ready); affiliate applications Friday  
**Depends on**: Existing codebase (no new infrastructure required)

---

## 1. Context & Strategy

### What we told the investor
BuyAnything is the place to buy *anything* — from a $25 Roblox gift card to a handmade quilt from a local artisan to a $25M yacht. We earn money two ways:

1. **Affiliate commissions** on retail products found via shopping APIs (Amazon, eBay, Google Shopping)
2. **Vendor introductions** connecting buyers with the right vendor from our directory — at every tier

We are an **introduction platform**, not a seller. We connect buyers with vendors. For mass-market products, the introduction is an affiliate click. For everything else — local shops, indie makers, service providers, luxury brokers — it's a one-click outreach that sends the vendor a qualified brief.

**Critical framing**: Our vendor directory is NOT just luxury. It's 3,000+ businesses across every tier:
- Mom & pop shops selling local crafts
- Indie bookstores and specialty retailers
- Local service providers (caterers, florists, contractors)
- Specialized B2B suppliers (packaging, equipment, materials)
- Premium service providers (charter operators, yacht brokers, jewelers)

The platform works the same way at every tier. The LLM decides the routing, and the vendor vector search finds the right match regardless of price point.

### The demo goal
Show the investor a polished, content-rich platform that:
- Handles *any* request intelligently (from gift cards to private jets)
- Has a public surface that looks like a real content business (not just an app behind a login wall)
- Demonstrates the viral loop: every vendor outreach is a customer acquisition touchpoint
- Has the affiliate infrastructure already wired and ready for approval

### The affiliate approval goal (post-demo)
Apply to Amazon Associates, eBay Partner Network, and Skimlinks with confidence that:
- The public site has real, indexable content (20+ pages)
- Affiliate disclosures are visible on every page with outbound links
- There is no auth wall on the public surface
- Click tracking and attribution are fully functional
- The site looks like a legitimate content/comparison business

### What we are NOT doing
- We are not negotiating vendor commissions yet (99% are unregistered)
- We are not building a payment processor or escrow system
- We are not building a full two-sided marketplace on Day 1
- We are not replacing the human as the decision maker (whether that's an EA, a small business owner, or an individual shopper)

---

## 2. The Two Surfaces

### Public Surface (no login required)
This is what affiliate network reviewers and first-time visitors see. It must be content-rich, indexable, and compliant.

| Page | Purpose | Content Type |
|------|---------|-------------|
| `/` | Homepage with universal search box | Dynamic |
| `/search?q=...` | Search results (products + vendors mixed) | Dynamic per query |
| `/how-it-works` | 3-step explanation for buyers | Static |
| `/about` | Company story, team, mission | Static |
| `/guides/[slug]` | Buying guides, gift vaults, vendor spotlights, how-tos | Static editorial |
| `/vendors` | Public vendor directory (search-driven, not categorized) | Dynamic from DB |
| `/vendors/[slug]` | Individual vendor spotlight pages | Dynamic from DB |
| `/contact` | Contact form | Static |
| `/privacy` | Privacy policy | Static |
| `/terms` | Terms of service | Static |
| `/affiliate-disclosure` | Full affiliate disclosure | Static |

### Private Surface (login required — the workspace)
This is the existing app. Used by EAs, small business owners, and anyone who wants to track requests and manage vendor conversations. No changes to auth model needed for Thursday.

| Route | Exists? | Status |
|-------|---------|--------|
| `/` (chat + board) | Yes | Working — this IS the private app today |
| Share pages (`/share/[token]`) | Yes | Working — public, no auth needed |
| Quote pages (`/quote/[token]`) | Yes | Working — public, no auth needed |

### The Bridge: No Login Conflict
The public surface and private workspace coexist. They are parallel paths, not conflicting requirements:

- **Anonymous visitor** → browses public pages → clicks affiliate links → we earn commission. No login needed.
- **Logged-in user** (EA, small business owner, anyone) → uses the workspace → searches → clicks "Request Quote" on vendors → one-click outreach using their stored identity.
- **Vendor receiving outreach** → gets a qualified lead → responds → sees "What do YOU need to buy?" prompt → enters the viral loop. This works at EVERY tier — the indie bookstore owner needs to buy shelving, the caterer needs ingredients, the charter operator needs maintenance parts.

The affiliate commission model (shopping API products) and the vendor introduction model (directory vendors at any tier) live on different surfaces. There is no conflict.

---

## 3. What Exists Today (Codebase Inventory)

### Already Built — Backend

| Feature | File(s) | Status |
|---------|---------|--------|
| **Vendor vector search** (pgvector, 1536-dim embeddings, cosine similarity) | `sourcing/vendor_provider.py` | Working, ~3,000 vendors |
| **LLM query generation** for retail providers (Gemini → optimized search terms) | `services/llm.py:triage_provider_query()` | Working |
| **Structured SearchIntent model** (brand, model, price range, condition, features, keywords) | `sourcing/models.py:SearchIntent` | Working |
| **Per-retailer query adapters** — each big retailer has its own intelligent adapter that translates a `SearchIntent` into provider-specific queries with retailer-specific filters | `sourcing/adapters/` | Working (see detail below) |
| **Multi-provider sourcing** (Rainforest/Amazon, ScaleSerp/Google Shopping, SerpAPI, ValueSerp, eBay Browse, Ticketmaster, Google CSE, vendor_directory) | `sourcing/repository.py:SourcingRepository` | Working, all run in parallel |
| **Desire-tier classification** (commodity/considered/service/bespoke/high_value/advisory) | `services/llm.py:make_unified_decision()` | Working |
| **Provider gating by tier** (skip Amazon for service/bespoke/high_value) | `sourcing/repository.py:_filter_providers_by_tier()` | **LEGACY — remove.** Contradicts parallel-search-then-rerank. The three-stage re-ranker's `tier_fit` multiplier already handles this: Amazon scores 0.2 tier_fit for bespoke queries, sinking naturally. Hard-gating prevents serendipitous discoveries and fails on edge cases (e.g., "catering equipment" IS on Amazon). |

#### Per-Retailer Adapter Detail

Each big retailer has different APIs, filter formats, and query requirements. We don't send the same string to every provider — each one gets a tailored `ProviderQuery` built by its adapter:

| Adapter | File | What it does |
|---------|------|--------------|
| **RainforestQueryAdapter** (Amazon) | `sourcing/adapters/rainforest.py` | Builds Amazon-specific queries with `min_price`/`max_price` filters, condition mapping, taxonomy metadata |
| **EbayBrowseQueryAdapter** | `sourcing/adapters/ebay.py` | Maps conditions to eBay enums (`new`→`NEW`, `refurbished`→`SELLER_REFURBISHED`), sets marketplace_id |
| **GoogleCSEQueryAdapter** | `sourcing/adapters/google_cse.py` | Builds category path for Google Custom Search, different query structure |
| **(registry)** | `sourcing/adapters/__init__.py` | `build_provider_query_map(intent, provider_ids)` → returns a `ProviderQueryMap` with per-provider queries |

The adapter base class (`sourcing/adapters/base.py`) provides shared utilities: `build_query_terms()` assembles brand + model + product_name + category + keywords + features into a deduplicated term list. Each adapter then wraps that with provider-specific filters and metadata.

**This is a key differentiator for the demo**: We don't just throw the same search string at every API. Each retailer gets an intelligently adapted query that speaks its language.
| **Affiliate link resolution** (Amazon Associates, eBay Partner Network, Skimlinks universal fallback) | `affiliate.py:LinkResolver` | Built, needs env vars for activation |
| **Clickout tracking** with fraud detection | `routes/clickout.py` + `services/fraud.py` | Working |
| **Vendor outreach pipeline** (trigger → email → track open/click/quote → reminders → unsubscribe) | `routes/outreach.py` + `services/email.py` | Working |
| **Likes** (toggle on bids) | `routes/likes.py` | Working |
| **Comments** (on bids, with visibility flag) | `routes/comments.py` | Working |
| **Share links** (row/tile/project with tokens, public resolution, access counting) | Backend share routes + `app/share/[token]/page.tsx` | Working |
| **Referral attribution** (share page stores token → verifyAuth sends it → backend captures on User model + increments ShareLink counters) | `utils/auth.ts`, `routes/auth.py`, `models/auth.py` | **Fully wired** — share → localStorage → signup → User.referral_share_token + signup_source |
| **Audit logging** | `audit.py` | Working |

### Already Built — Frontend

| Feature | File(s) | Status |
|---------|---------|--------|
| **OfferTile** with like/comment/share buttons | `components/OfferTile.tsx` | Working |
| **VendorContactModal** (one-click outreach from tile) | `components/VendorContactModal.tsx` | Working |
| **Board sharing** (copy URL with multiple `?q=` params) | `components/Board.tsx:handleShareBoard()` | Working |
| **Row sharing** (backend share link or fallback `?q=` URL) | `components/RowStrip.tsx:handleCopySearchLink()` | Working |
| **Share page** (public, no auth, with affiliate disclosure) | `app/share/[token]/page.tsx` | Working |
| **Detail panel** (bid detail with chat log provenance) | `stores/detailPanelStore.ts` | Working |

### NOT Built Yet (Required for Thursday + Affiliate Applications)

| Gap | Impact | Priority |
|-----|--------|----------|
| **Middleware blocks all public pages** — `PUBLIC_PATHS` only allows `/login`, `/sign-in`, `/sign-up`, `/marketing` | Every new public page is invisible to anonymous users | **P0 BLOCKER** |
| **No public homepage at `/`** — root is the workspace, redirects to login | Affiliate reviewers see a login wall | P0 |
| **No public search results page** (`/search?q=`) | Can't demonstrate affiliate links without login | P0 |
| **No public guides/editorial content** | Site looks thin/empty to reviewers | P0 |
| **No public vendor directory** | Missing showcase of our vendor network | P1 |
| **Disclosure not linked from all public pages** | `/disclosure` exists but isn't in footer/header of public pages | P0 |
| **No `/how-it-works` page** | Visitors don't understand the value prop | P0 |
| **No `/about`, `/privacy`, `/terms` pages** | Looks incomplete/untrustworthy | P0 |
| **Comment visibility: no public comments** | All comments are private; no social proof | P1 |

**Already exists (previously thought missing):**
- ✅ **Affiliate disclosure page** — `/disclosure` exists with full FTC-compliant content + seller fee section
- ✅ **Marketing/landing page** — `/marketing` exists with hero, feature cards, differentiators (already in PUBLIC_PATHS)
- ✅ **Referral attribution** — fully wired: share page → localStorage → verifyAuth sends token → backend captures on User model

---

## 4. Implementation Plan

### Phase 0: Public Surface Foundation (Monday–Tuesday)

**Goal**: The root domain is a real website, not a login wall. Crawlers can index content. The app still works at `/app` or behind the existing auth check.

#### 0.0 BLOCKER: Update Middleware for Public Routes
**File**: `apps/frontend/middleware.ts`

The current middleware redirects ALL non-public paths to `/login` without a `sa_session` cookie. The `PUBLIC_PATHS` whitelist only allows `/login`, `/sign-in`, `/sign-up`, `/marketing`.

**This must be fixed first** — every other task depends on it. Update `PUBLIC_PATHS` to include all public routes:
- `/search`, `/how-it-works`, `/about`, `/contact`, `/privacy`, `/terms`
- `/disclosure` (already exists)
- `/vendors`, `/vendors/*`
- `/guides`, `/guides/*`
- `/share/*` (share pages — currently blocked for anonymous users!)
- `/quote/*` (vendor quote pages — also currently blocked!)

**Alternative approach**: Invert the logic — instead of whitelisting public paths, blacklist protected paths (only `/` workspace needs auth). This is more maintainable as the public surface grows.

#### 0.1 Public Layout + Homepage
Create a public layout (`app/(public)/layout.tsx`) with:
- Persistent header: logo, search bar, "Sign In" link (not forced)
- Footer: affiliate disclosure, legal links, company info
- Homepage (`app/(public)/page.tsx`): hero with universal search box, "How it works" 3-step section, featured guides carousel, example searches ("Try: Roblox gift cards, local caterers, private jet charter")

**Universal search behavior (public)**:
- User types query in public search → redirects to `/search?q=...` results page
- The backend runs `triage_provider_query()` (LLM, not heuristics — per our architecture rule, ALL intent classification goes through Gemini) then `SourcingRepository.search_all()` with the optimized query
- Commodity/considered results → product cards with affiliate clickout links (no login needed)
- Service/bespoke/high_value results → vendor cards with "Request an introduction" CTA (email capture for anonymous; one-click outreach for logged-in EAs)
- The existing chat-based workspace stays at `/` behind session detection (see Decision 5)

#### 0.2 Public Search Results Page
Create `/search?q=...` that:
- Runs the existing `SourcingRepository.search_all()` pipeline (LLM-optimized query + all providers in parallel)
- Displays results as product/vendor cards with affiliate clickout links
- Does NOT require login (anonymous clickout tracking already works)
- Includes inline affiliate disclosure
- Shows "Sign in to save and track" CTA (not a wall)
- **No hardcoded categories.** The search box IS the category system. Vector search finds the right vendors for any query.

#### 0.3 Static Pages
Create minimal but complete pages:
- `/how-it-works` — 3-step flow: (1) Tell us what you need, (2) We find the best options, (3) You choose
- `/about` — Company mission, the problem we solve, team placeholder
- `/contact` — Simple form
- `/privacy` — Standard privacy policy (can use template)
- `/terms` — Standard terms of service (can use template)
- `/affiliate-disclosure` — ALREADY EXISTS at `/disclosure` (rename or redirect)

#### 0.4 Affiliate Disclosure Component
Create a reusable `<AffiliateDisclosure />` component that renders:
- **Inline (near outbound links)**: "Some links on this page are affiliate links. We may earn a commission at no extra cost to you."
- **Footer**: Link to full `/affiliate-disclosure` page

This component must appear on:
- Every guide page
- Every search results display
- Every share page (already has one: `share/[token]/page.tsx:178-182`)

**Implementation note**: The share page already includes this exact pattern. Reuse it.

### Phase 1: Content & SEO (Tuesday–Wednesday)

**Goal**: 20+ indexable pages with unique content. Enough substance for affiliate network reviewers.

#### 1.1 Guide Pages (10–15 pages)
Create editorial guide pages at `/guides/[slug]`. These are the "content engine" that makes us look like a real editorial business, not just a thin redirect site.

**Approach**: Use our LLM pipeline (`services/llm.py:call_gemini()`) to generate initial drafts, then hand-edit for quality. Each guide should be 800–1,500 words with:
- Unique, genuinely useful content (not AI sludge)
- Curated product recommendations with affiliate links where appropriate
- "Concierge this" CTA for complex requests
- Author attribution (even if it's "BuyAnything Editorial")

**Starter guides** (ordered by priority — build top 5 first, remainder if time permits):
1. `/guides/how-buyanything-works` — How anyone uses BuyAnything to find what they need (**must-have**: explains core value prop for all users)
2. `/guides/gift-vault-tech-lovers` — Curated tech gifts with affiliate links (**must-have**: demonstrates affiliate content)
3. `/guides/best-luggage-for-travel` — Product roundup with affiliate links (**must-have**: high affiliate potential)
4. `/guides/support-local-vendors` — Why and how to buy from local/indie vendors (**must-have**: demonstrates vendor directory breadth)
5. `/guides/home-office-setup-guide` — Product roundup with affiliate links (**must-have**: broad appeal)
6. `/guides/private-flight-essentials` — What to know before chartering (vendor CTA)
7. `/guides/corporate-gift-guide` — Bulk ordering tips + product links
8. `/guides/event-planning-checklist` — Hybrid: products + service vendors
9. `/guides/small-business-sourcing` — How small businesses use BuyAnything to find suppliers
10. `/guides/custom-jewelry-buying-guide` — Vendor-focused, concierge CTA

**Time budget**: Guides 1–5 are the minimum viable set. If we only ship 5 guides + vendor directory, that's still 5 editorial pages plus thousands of vendor detail pages.

#### 1.2 Public Vendor Directory
Create `/vendors` (browse page) and `/vendors/[slug]` (detail pages) that:
- Pull from the existing `vendor` table (3,000+ vendors with descriptions, taglines, embeddings)
- Display vendor cards with a search box (vector search, not static categories)
- Each vendor page shows: name, tagline, description, specialties, service areas, website link
- Include "Request an introduction" CTA (for logged-in users → outreach flow; for anonymous → email capture)

**Implementation**: These pages are public and indexable. They're generated from DB data, not hardcoded. This gives us thousands of unique, indexable pages from day one.

**Privacy note**: Only display vendors that have public websites. Do not expose email addresses or phone numbers on public pages.

#### 1.3 Public Search Results Page
Create `/search?q=...` that:
- Runs the existing `SourcingRepository.search_all()` pipeline
- Displays results as product cards with affiliate links (via `/api/out` clickout)
- Does NOT require login (anonymous clickout tracking already works — `clickout.py:42-48` handles `user_id=None`)
- Includes inline affiliate disclosure
- Shows "Sign in to save and track" CTA (not a wall)

**This is the single most important page for affiliate approval.** Reviewers will search for a product and expect to see results with functional affiliate links.

### Phase 2: Polish & Demo Prep (Wednesday)

**Goal**: Everything works smoothly for the investor demo.

#### 2.1 Demo Flow Preparation
Prepare two demo scenarios:

**Scenario A: "Roblox gift cards"** (Commodity retail path)
1. Type "Roblox gift cards $100" in public search
2. See curated results from Amazon/eBay/Google Shopping
3. Click "Buy" → affiliate redirect to Amazon with tracking tag
4. Show the clickout event logged in the system

**Scenario B: "I need a caterer for a 50-person corporate event"** (Vendor directory path)
1. Type the request in the workspace (logged in)
2. System searches ALL providers in parallel (shopping APIs + vendor directory via pgvector)
3. Three-stage re-ranker scores by intent fit — vendor directory caterers score high on tier_fit, Amazon results score near-zero and sink to bottom
4. User clicks "Request Quote" → one-click outreach to 3 caterers
5. Show the outreach email draft, tracking, and vendor response flow

**Scenario B-alt (for high-end demo if needed): "Charter a jet from SAN to Aspen"**
- Same flow, but with charter operators. Shows the system handles everything from local caterers to private aviation.

**Scenario C: "The viral loop"** (Tell the story)
1. Show the caterer who received our outreach
2. Explain: "This caterer is now aware of BuyAnything. They need to buy things too — serving equipment, linens, a new van, marketing materials. When they search for those, we connect them with OTHER vendors in our directory — or route them to Amazon/eBay for commodity items."
3. Show the indie bookstore angle: "The bookstore owner we connected with a buyer now needs shelving, a POS system, and shipping supplies. They become a buyer. Their suppliers see our outreach. The flywheel compounds."
4. Show the referral attribution in the share page code
5. Key insight for investor: **The flywheel spins fastest at the small/mid tier**, where vendors are also frequent buyers. A Gulfstream operator buys less often than a local bakery.

#### 2.2 Social Features Polish
The likes, comments, and sharing features exist but need UX tightening:

- **Likes**: Ensure heart icon toggles visually with count badge. Already works via `routes/likes.py` + `OfferTile.tsx`.
- **Comments**: Add display of comment count on OfferTile. Ensure comments panel is accessible from tile. Currently `private` visibility only — this is fine for MVP.
- **Share links**: Ensure share button produces working URLs. The public share page already has affiliate disclosure and "Start Shopping" CTA. Test the full flow.

#### 2.3 Affiliate System Verification
Verify the existing affiliate infrastructure is ready to activate:

- [ ] `AMAZON_AFFILIATE_TAG` env var → Amazon Associates handler adds `?tag=` to all Amazon URLs
- [ ] `EBAY_CAMPAIGN_ID` + `EBAY_ROTATION_ID` env vars → eBay Partner handler adds tracking params
- [ ] `SKIMLINKS_PUBLISHER_ID` env var → universal fallback for all other merchants
- [ ] `/api/out` clickout → logs event → redirects to transformed URL
- [ ] Fraud detection runs on every clickout (`services/fraud.py`)
- [ ] `ClickoutEvent` records: user_id, canonical_url, final_url, merchant_domain, handler_name, affiliate_tag

**No code changes needed** — the `affiliate.py:LinkResolver` is fully built. It just needs env vars set once we have the affiliate accounts.

---

## 5. Technical Architecture (How It Maps to Existing Code)

### The Five-Layer Sourcing Pipeline

This is the core technical architecture. Two parallel paths, five layers deep:

**Path A: Big retailers (shopping APIs)**
```
User query (free text)
  → Layer 1: LLM (services/llm.py)
      triage_provider_query() → optimized search term
      make_unified_decision() → desire_tier + SearchIntent
  → Layer 2: Adapters (sourcing/adapters/)
      SearchIntent → per-retailer ProviderQuery objects:
        - RainforestQueryAdapter → Amazon query + price filters + condition
        - EbayBrowseQueryAdapter → eBay query + eBay-specific condition enums + marketplace
        - GoogleCSEQueryAdapter → Google query + category path
      Each retailer gets a DIFFERENT tailored query from the same intent.
  → Layer 3: Providers (sourcing/repository.py)
      SourcingRepository runs all providers in parallel:
        - Rainforest (Amazon) → product results with prices
        - ScaleSerp (Google Shopping) → product results
        - eBay Browse → product results with shipping
        - Ticketmaster → event tickets (when query matches event keywords)
        - Google CSE → web results
  → Layer 4: Normalizers (sourcing/normalizers/)
      Per-retailer output normalization + currency conversion + URL canonicalization:
        - RainforestNormalizer → Amazon-specific field extraction
        - EbayNormalizer → eBay-specific format
        - GoogleCSENormalizer → Google CSE format
        - Generic fallback for other providers
      All produce NormalizedResult objects with provenance metadata.
  → Layer 5: Three-Stage Re-Ranking (see below)
```

**Path B: Vendor directory (vector search)**
```
User query (free text)
  → Embed query via OpenRouter (text-embedding-3-small, 1536-dim)
  → pgvector cosine similarity against vendor.embedding column
  → Filter by distance threshold (0.55)
  → Return matching vendors as SearchResult objects
```

**Both paths run in parallel and merge into the same result set.** Then the three-stage re-ranking pipeline scores everything to capture the *spirit* of the request — not just keyword matches.

### Three-Stage Re-Ranking: Spirit Over Letter

This is what makes BuyAnything different from a keyword search engine. The user says "light jet with Wi-Fi for 4 passengers" — we don't just count how many of those words appear in a title. We score on *intent fit*.

**Stage 1: Classical Scorer** (`sourcing/scorer.py`)
Five scoring dimensions, with desire-tier as a **multiplicative gate** (not additive):
```
combined = base × (0.3 + 0.7 × tier_fit)

Where base = (relevance × 0.45) + (price × 0.20) + (quality × 0.20) + (diversity × 0.15)
```

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| **Relevance** | 45% | Brand match, keyword match (title > description), product name, category fit |
| **Price** | 20% | How centered the price is within the user's budget range (not just in/out) |
| **Quality** | 20% | Rating, review count (log scale), image presence, shipping info |
| **Diversity** | 15% | Bonus for underrepresented providers (prevents Amazon from dominating) |
| **Tier fit** | Multiplier | Mismatched sources get a real penalty: Amazon scores 0.2 tier_fit for bespoke queries; vendor_directory scores 0.3 for commodity. This is the "spirit" gate. |

**Stage 2: Quantum Re-Ranking** (`sourcing/quantum/reranker.py`)
Simulated photonic quantum kernel that captures non-linear relationships cosine similarity misses:
- Maps query + candidate embeddings to quantum circuit parameters
- Runs simulated interference patterns (squeezed states → displacement → rotation → beamsplitter entanglement)
- Produces four scores per result:
  - **quantum_score**: Interference-based similarity
  - **classical_score**: Standard cosine similarity (baseline)
  - **novelty_score**: `quantum - classical` — results the quantum kernel found that keywords missed (serendipitous discoveries)
  - **coherence_score**: Match robustness — high coherence = strong, stable match
- Blended score: `(0.7 × quantum) + (0.3 × classical) + (0.1 × novelty) + (0.1 × coherence)`
- Feature-flagged via `QUANTUM_RERANKING_ENABLED` — graceful degradation to classical-only

**Stage 3: Constraint Satisfaction** (`sourcing/quantum/constraint_scorer.py`)
Scores how well each result satisfies the user's *structured* constraints (extracted by the LLM during desire classification):
- Route matching (origin/destination for travel/charter)
- Aircraft class / vehicle type
- Capacity / passengers
- Location / service area
- Feature matching (Wi-Fi, certifications, dietary requirements, etc.)
- Generic constraints (color, material, style, size, brand, cuisine)
- Additive bonuses, not hard filters — bad extraction degrades gracefully

**Why this matters for the demo**: When a user asks for "a caterer in San Francisco for 50 people who can do vegan options", the constraint scorer checks whether each vendor actually serves SF, handles 50+ people, and lists vegan capabilities — not just whether the word "caterer" appears in the title. This is the difference between *letter* and *spirit*.

### Public Search Flow (NEW)
```
User types query on public homepage → redirects to /search?q=...
  → Next.js server component calls backend
  → Both paths run in parallel (adapters + vector search)
  → Server component renders mixed results as product/vendor cards
  → Product cards: "Buy" → /api/out → affiliate.py:LinkResolver transforms URL → 302 redirect
  → Vendor cards: "Request Introduction" → email capture (anon) or one-click outreach (logged in)
```

**Technical note on rendering**: Public pages (homepage, guides, vendor directory index) should use Next.js **Static Site Generation (SSG)** or **Incremental Static Regeneration (ISR)** for fast load times and crawlability. Vendor detail pages use ISR. The `/search?q=` results page is dynamic (server-rendered per request). This matters for the LCP < 2.5s target and for search engine indexing.

### Workspace Flow (EXISTING — no changes)
```
User types request in chat (EA, small business owner, anyone logged in)
  → services/llm.py:make_unified_decision() classifies intent + desire_tier (LLM decision, not heuristics)
  → Creates Row with choice_factors
  → Sourcing pipeline runs ALL providers in parallel (no tier-based gating):
      - ALL queries → shopping APIs (Amazon, Google Shopping, etc.) + vendor directory simultaneously
      - Three-stage re-ranker scores everything by intent fit:
        commodity → retail results score high tier_fit, vendor results score lower
        service/bespoke → vendor results score high tier_fit, retail results score near-zero and sink naturally
  → Results appear as OfferTiles (mixed: retail products + directory vendors)
  → User clicks "Request Quote" on vendor tile
    → VendorContactModal opens → one-click outreach
    → routes/outreach.py:trigger_outreach() sends personalized emails
    → OutreachEvent tracks: sent, opened, clicked, quoted
```

**Key UX point**: The user never fills in contact info repeatedly. Their identity is already stored from their session. When they click "Request Quote", the system auto-generates the outreach using their stored identity + the structured request brief from the Row's `choice_factors`. 5 vendor outreaches = 5 clicks, not 5 forms. This works the same whether you're contacting a local florist or a yacht broker.

### Viral Loop Flow (PARTIALLY BUILT)
```
User sends outreach to vendor (any tier — caterer, bookstore, jeweler, charter operator)
  → Vendor receives email with quote link
  → Vendor clicks link → /quote/[token] (public page)
  → Vendor submits quote
  → [NEW] Vendor sees: "What do YOU need to buy?" CTA
  → Vendor enters their own procurement need (packaging supplies, equipment, ingredients, etc.)
  → System finds matches: some from shopping APIs (affiliate $), some from vendor directory
  → Cycle repeats: their need triggers outreach to THEIR vendors
```

**Why this works better at small/mid tier**: A local caterer buys ingredients, equipment, linens, and marketing services regularly. An indie bookstore buys shelving, a POS system, and shipping supplies. These are high-frequency buyers who also sell. A luxury charter operator buys less often. The flywheel's RPM is proportional to how often vendors are also buyers — and that's highest at the small business tier.

**What exists**: Outreach pipeline, quote page, share page with referral attribution storage.  
**What's missing**: The "What do YOU need to buy?" CTA on the quote page and referral-to-signup wiring. This is P2 (post-demo).

---

## 6. Content Generation Strategy

### Why Content Matters
Affiliate networks (especially Amazon Associates) reject sites that are:
- Behind a login wall
- Thin content (just links, no editorial value)
- "Coupon/deal" sites with no unique perspective
- Sites that appear auto-generated with no editorial voice

We need to look like a **premium procurement and shopping editorial site** with genuine expertise in both retail curation and luxury sourcing.

### Content Generation Pipeline
We have an LLM (`services/llm.py:call_gemini()`) and a vendor database with rich descriptions. The content pipeline:

1. **Guide pages**: LLM-generated first drafts → human editing. Each guide should reference specific products or vendors from our database, making them unique to BuyAnything (not generic AI content).
2. **Vendor spotlights**: Pull from `vendor.description`, `vendor.tagline`, `vendor.specialties`. Format as directory pages. These are inherently unique because they describe our specific vendor network.
3. **Search results pages**: Every unique search query generates a unique results page. These are dynamic but indexable via SSR. No static categories needed — the search box and vector search ARE the discovery mechanism.

### Content Quality Bar
- No placeholder text ("Lorem ipsum", "Coming soon", "TBD")
- No thin pages (< 300 words for guides, < 150 words for vendor spotlights)
- Every page with outbound links must have an affiliate disclosure
- Every page must have a clear CTA (either affiliate click or concierge request)
- Navigation must work — no dead links, no 404s

---

## 7. Acceptance Criteria

### For Thursday Demo
- [ ] Public homepage loads without login wall, has search box + example queries
- [ ] Public search works: any query returns results (products + vendors mixed)
- [ ] At least 5 guide pages with 800+ words each (10 is stretch goal)
- [ ] Public vendor directory shows vendors from our database
- [ ] Public search works: type "Roblox gift cards" → see Amazon results with clickout links
- [ ] Clickout tracking logs events (even without active affiliate tags)
- [ ] Demo Scenario A (commodity) flows smoothly end-to-end
- [ ] Demo Scenario B (luxury) flows smoothly end-to-end
- [ ] Demo Scenario C (viral loop) story is coherent with code evidence
- [ ] No broken links, no placeholder content, no "Coming soon" pages

### For Affiliate Application (Post-Demo)
- [ ] Affiliate disclosure visible on every page with outbound links
- [ ] `/affiliate-disclosure` full page exists and is linked from footer
- [ ] `/privacy` and `/terms` pages exist
- [ ] `AMAZON_AFFILIATE_TAG` activates Amazon Associates handler
- [ ] `EBAY_CAMPAIGN_ID` + `EBAY_ROTATION_ID` activates eBay Partner handler  
- [ ] `SKIMLINKS_PUBLISHER_ID` activates universal fallback
- [ ] Public site passes manual review: no auth wall, content-rich, functional links
- [ ] Search results render correctly for 5+ test queries across all tiers (commodity, local vendor, service, luxury)

### For Post-Demo Iteration (P2)
- [ ] Referral attribution wired from share page to signup flow
- [ ] "What do YOU need to buy?" CTA on vendor quote/outreach pages
- [ ] Public comments (social proof on product pages)
- [ ] Email capture on concierge CTA (for non-logged-in luxury requests)

---

## 8. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Affiliate networks reject us for thin content | No affiliate revenue | Build 20+ real content pages with editorial quality |
| Demo crashes on live search (API quotas) | Embarrassing | Test all demo queries beforehand; have mock fallback |
| Public search page exposes internal data | Security/privacy | Public endpoints return only public fields; no user data |
| Content looks AI-generated / generic | Reviewer flags it | Hand-edit all LLM drafts; add brand voice; reference our specific vendors |
| Vendor directory exposes contact info | Vendor privacy | Only show name, description, website. Never expose email/phone on public pages |
| Too much scope for 4 days | Nothing ships | Phase 0 (foundation) is the minimum. Phase 1 (content) is where value accrues. Phase 2 (polish) is nice-to-have |

---

## 9. Open Decisions

1. **Public search: anonymous or session-optional?** Recommendation: anonymous with optional "save" that prompts login. The search itself must never require auth.

2. **Vendor directory: all 3,000 vendors or curated subset?** Recommendation: all vendors with `embedding IS NOT NULL` and `website IS NOT NULL`. Curated is better but we don't have time to manually review 3,000.

3. **Guide content: LLM-generated or hand-written?** Recommendation: LLM-generated first draft from Gemini, then hand-edited for quality and brand voice. 10 guides in 2 days requires this approach.

4. ~~**Public URL structure**~~ — REMOVED. No static categories. Vector search is the discovery mechanism.

5. **How do we handle `/` routing?** The existing app serves the logged-in workspace at `/`. The public homepage also needs to live at `/` for affiliate reviewers. **Recommendation for Thursday**: Use session detection at `/` — if the user has a valid `sa_session` cookie, render the existing workspace; if not, render the public homepage. This is a single `page.tsx` change, not a rewrite. Post-demo, move workspace to `/app` and make `/` always public.

---

## 10. Traceability

### Inputs
- `docs/active-dev/buy-anything_prd_v1.1.md` — original external PRD with public/private surface split
- `docs/archive/buyanything-ai-ai-agent-facilitated-multi-category-marketplace-PRD.md` — original marketplace PRD with viral growth flywheel
- `docs/prd/marketplace-pivot/prd-viral-growth-flywheel.md` — viral loop mechanics
- `docs/active-dev/paused/PRD_Autonomous_Outreach.md` — outreach pipeline vision
- `docs/active-dev/paused/PRD_Desire_Classification.md` — desire tier classification
- `docs/active-dev/paused/PRD_Search_Display_Architecture.md` — search/display fixes
- `docs/active-dev/paused/User_Intention_Audit.md` — spirit vs letter gaps
- `docs/active-dev/paused/2026-02-17-codebase-audit.md` — current codebase issues

### Existing Code Referenced
- `apps/backend/sourcing/vendor_provider.py` — vendor vector search (pgvector cosine similarity)
- `apps/backend/sourcing/repository.py` — multi-provider sourcing pipeline (parallel execution, all providers for all queries)
- `apps/backend/sourcing/models.py` — SearchIntent, ProviderQuery, ProviderQueryMap, NormalizedResult models
- `apps/backend/sourcing/adapters/` — per-retailer query adapters (Rainforest/Amazon, eBay, Google CSE)
- `apps/backend/sourcing/adapters/base.py` — ProviderQueryAdapter base class + shared query building utilities
- `apps/backend/sourcing/scorer.py` — 5-dimension classical scorer with tier_fit multiplier
- `apps/backend/sourcing/quantum/reranker.py` — quantum re-ranking (simulated photonic interference, novelty/coherence scoring)
- `apps/backend/sourcing/quantum/constraint_scorer.py` — structured constraint satisfaction scoring (routes, capacity, features, location)
- `apps/backend/sourcing/normalizers/` — per-retailer output normalizers (Rainforest, eBay, Google CSE) + currency conversion + URL canonicalization
- `apps/backend/sourcing/filters.py` — unified price filter (single source of truth, replaces 4 inline implementations)
- `apps/backend/sourcing/service.py` — SourcingService orchestration (extract constraints → search → normalize → filter → score → quantum rerank → constraint satisfy → persist)
- `apps/backend/sourcing/metrics.py` — search observability (per-provider latency, result counts, error rates)
- `apps/backend/services/llm.py` — LLM decision engine + query generation
- `apps/backend/affiliate.py` — affiliate link resolution system
- `apps/backend/routes/clickout.py` — clickout tracking + fraud detection
- `apps/backend/routes/outreach.py` — vendor outreach pipeline
- `apps/backend/routes/likes.py` — likes system
- `apps/backend/routes/comments.py` — comments system
- `apps/frontend/app/share/[token]/page.tsx` — public share page with referral attribution
- `apps/frontend/app/components/OfferTile.tsx` — offer display with social features
- `apps/frontend/app/components/RowStrip.tsx` — sharing functionality
- `apps/frontend/app/components/Board.tsx` — board sharing
- `apps/frontend/app/utils/api.ts` — share link API helpers
