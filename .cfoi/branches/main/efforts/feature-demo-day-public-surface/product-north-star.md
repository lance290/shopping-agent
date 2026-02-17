# Effort North Star (Effort: feature-demo-day-public-surface, v2026-02-17)

## Goal Statement
Build a public-facing surface (no login wall) that demonstrates BuyAnything's full value proposition to investors and passes affiliate network review — covering middleware, homepage, search results, static pages, editorial guides, vendor directory, and demo polish.

## Ties to Product North Star
- **Product Mission**: "Eliminate the friction of multi-category procurement" — the public surface makes this accessible to anonymous visitors, not just logged-in users
- **Supports Metric**: GMV growth (affiliate + fees) — public search with affiliate clickouts is the primary monetization path for retail products
- **Supports Metric**: Time to first offers (<30s) — public search demonstrates instant sourcing without login friction

## In Scope
- **PRD-00**: Middleware fix — unblock all public routes for anonymous access
- **PRD-01**: Public homepage with universal search box + layout shell (header/footer)
- **PRD-02**: Public search results page with affiliate clickouts + vendor cards
- **PRD-03**: Static pages (/how-it-works, /about, /contact, /privacy, /terms)
- **PRD-04**: 5+ editorial guide pages with affiliate links and vendor CTAs
- **PRD-05**: Public vendor directory with vector search (NOT categories)
- **PRD-06**: Demo prep, social features polish, affiliate system verification
- **Remove legacy provider gating** (`_filter_providers_by_tier`) — let re-ranker handle relevance

## Out of Scope
- Vendor commission negotiations (99% unregistered)
- Payment processing or escrow
- Changes to the private workspace UI
- Affiliate network applications (post-demo)
- Filling the vendor database (parallel project)
- New search providers or adapters (pipeline already built)

## Acceptance Checkpoints
- [ ] Anonymous visitor at `/` sees public homepage (not login redirect)
- [ ] Anonymous search at `/search?q=Roblox+gift+cards` returns affiliate-linked results
- [ ] Clickout via `/api/out` logs `ClickoutEvent` with affiliate params
- [ ] 5+ editorial guides live with 800+ words each
- [ ] `/vendors` shows vector-search-driven directory (no hardcoded categories)
- [ ] Demo Scenarios A (commodity), B (vendor), C (viral loop) run end-to-end
- [ ] No broken links, no placeholder content, no "Coming soon" pages

## Dependencies & Risks
- **Dependencies**: Existing five-layer sourcing pipeline (built), affiliate link resolution (built, needs env vars), vendor database with embeddings (being populated in parallel)
- **Risks**: API quota exhaustion during demo (mitigation: pre-test queries); content looks AI-generated (mitigation: hand-edit all guides); too much scope for 4 days (mitigation: Phase 0 is the minimum viable set)

## Approver / Date
- Approved by: [Pending user approval]
- Date: 2026-02-17
