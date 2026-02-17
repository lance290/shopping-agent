# PRD: Public Search Results Page

## Business Outcome
- Measurable impact: Anonymous visitors can search for any product/vendor and see results with functional affiliate clickout links — the core monetization path
- Success criteria: Affiliate network reviewer can type "Roblox gift cards", see Amazon/eBay results, click through, and verify the affiliate redirect works
- Target users: Anonymous visitors, affiliate network reviewers, anyone arriving via shared search link (`?q=...`)

## Scope
- In-scope:
  - Public `/search?q=...` page that calls existing backend sourcing pipeline
  - Mixed results display: retail products (from shopping APIs) alongside vendor matches (from pgvector)
  - Affiliate clickout links via existing `/api/out` endpoint (works anonymously)
  - Inline affiliate disclosure on results page
  - "Sign in to save and track" CTA (not a wall)
- Out-of-scope:
  - Changing the backend sourcing pipeline (it's already built — 5-layer pipeline)
  - Building new search providers or adapters
  - The workspace chat-based search flow (stays as-is)
  - Vendor outreach from search results (requires login — handled by workspace)

## User Flow
1. User arrives at `/search?q=running+shoes` (from homepage search, shared link, or direct URL)
2. Backend runs the existing five-layer sourcing pipeline:
   - LLM optimizes query → per-retailer adapters build tailored queries → providers run in parallel → normalizers standardize output → three-stage re-ranking scores by intent fit
   - Vendor directory vector search runs in parallel
3. Results render as a mixed grid: product cards (with price, image, rating) + vendor cards (with description, "Request Introduction" CTA)
4. Product cards: "Buy" button → `/api/out` → affiliate link resolution → 302 redirect to retailer
5. Vendor cards: "Request Introduction" → email capture form (anonymous) or one-click outreach (logged in)
6. Affiliate disclosure visible near the results grid

## Business Requirements

### Authentication & Authorization
- No authentication required to search or view results
- Anonymous clickout tracking already works (`ClickoutEvent` supports `user_id=None`)
- "Request Introduction" for vendors: anonymous users see email capture; logged-in users get one-click outreach
- Backend search endpoint must accept anonymous requests (update API proxy to `allowAnonymous`)

### Monitoring & Visibility
- Track: search queries, result counts, clickout rates, provider response times
- Existing `sourcing/metrics.py` already captures per-provider latency, result counts, error rates
- Track anonymous search → signup conversion (did they create an account after searching?)

### Billing & Entitlements
- Every product clickout goes through `/api/out` → `affiliate.py:LinkResolver` → affiliate tag applied
- Amazon Associates tag, eBay Partner Network params, Skimlinks universal fallback — all already built
- No new billing logic needed — just ensure env vars are set when affiliate accounts are approved

### Data Requirements
- No new data models for anonymous search (results are ephemeral, not persisted to rows)
- `ClickoutEvent` already persists: canonical_url, final_url, merchant_domain, handler_name, affiliate_tag, user_agent, ip_address
- Search queries from anonymous users are not persisted (privacy-by-default)

### Performance Expectations
- Search results page: first results visible within 3 seconds (streaming/progressive render)
- Full results within 10-12 seconds (p95, matching existing workspace search performance)
- Individual provider failures degrade gracefully — partial results shown immediately

### UX & Accessibility
- Results displayed as cards in a responsive grid (similar to existing OfferTile layout)
- Product cards: image, title, price, merchant, rating stars, "Buy" button
- Vendor cards: name, tagline, "Request Introduction" button, source badge ("From our vendor network")
- Mobile-responsive: single column on small screens
- Price display: quote-based vendors show "Request Quote" not "$0.00"

### Privacy, Security & Compliance
- Anonymous search queries not stored in database
- Affiliate disclosure inline near results grid + link to `/disclosure` page
- Rate limiting on anonymous search to prevent scraping/abuse
- No PII collected unless user opts into email capture on vendor cards

## Dependencies
- Upstream: PRD-00 (middleware allows `/search` for anonymous), PRD-01 (homepage search box redirects here)
- Downstream: None (this is a leaf — fully functional independently)

## Risks & Mitigations
- Shopping API quotas exhausted during demo → Test demo queries beforehand; have known-good cached results
- Search returns 0 results for demo query → Pre-test "Roblox gift cards", "running shoes", "local caterers" queries
- Slow search times on public page → Use streaming/progressive rendering (show results as each provider completes)

## Acceptance Criteria (Business Validation)
- [ ] Anonymous user at `/search?q=Roblox+gift+cards` sees Amazon/eBay product results (baseline: currently requires login)
- [ ] Clicking "Buy" on a product → `/api/out` redirect → lands on retailer site with affiliate params in URL
- [ ] `ClickoutEvent` logged with `user_id=None`, `merchant_domain`, `handler_name` (verify in DB)
- [ ] Vendor directory results appear alongside product results for service queries (e.g., "caterer san francisco")
- [ ] Inline affiliate disclosure visible on results page
- [ ] Page renders usable results within 5 seconds for standard queries

## Traceability
- Parent PRD: `docs/active-dev/demo-day/parent.md`
- Product North Star: `.cfoi/branches/dev/product-north-star.md`

---
**Note:** Technical implementation decisions (SSR vs client-side fetching, component reuse from OfferTile, streaming approach) are made during /plan and /task phases, not in this PRD.
