# PRD: Public Vendor Directory

## Business Outcome
- Measurable impact: 3,000+ unique, indexable vendor pages showcasing the breadth of our network — from local artisans to luxury brokers
- Success criteria: Visitor can search for vendors by natural language query (vector search), browse results, and request an introduction — all without logging in
- Target users: Anonymous visitors evaluating the platform, buyers researching vendors, SEO/organic traffic

## Scope
- In-scope:
  - `/vendors` — search-driven vendor browse page with a search box (vector search, NOT static categories)
  - `/vendors/[slug]` — individual vendor spotlight pages generated from DB data
  - "Request an introduction" CTA (email capture for anonymous users; one-click outreach for logged-in users)
  - Privacy: only display name, description, tagline, specialties, service areas, website. NEVER expose email or phone
- Out-of-scope:
  - Hardcoded category pages (anti-pattern — vector search IS the discovery mechanism)
  - Vendor registration/onboarding flow (exists at `/merchants/register`, separate concern)
  - Vendor-side portal or dashboard

## User Flow
1. Visitor arrives at `/vendors` (from navigation, footer link, or search engine)
2. Sees a search box: "Search our vendor network" with example queries
3. Types "caterers in San Francisco" → vector search returns matching vendors
4. Browses vendor cards: name, tagline, category badge, website link
5. Clicks a vendor → `/vendors/[slug]` detail page with full description, specialties, service areas
6. Clicks "Request an introduction" → email capture form (anonymous) or triggers outreach (logged in)

## Business Requirements

### Authentication & Authorization
- Browse and search: fully public, no auth required
- "Request an introduction" for anonymous users: collect email + name + brief (creates lead)
- "Request an introduction" for logged-in users: one-click outreach (existing `VendorContactModal` flow)

### Monitoring & Visibility
- Track: vendor page views, search queries on vendor directory, introduction request conversion rate
- Track which vendors get the most views/requests (helps prioritize vendor relationship development)

### Billing & Entitlements
- No direct billing for vendor directory access
- Introduction requests create outreach events — future commission tracking when vendor relationships are formalized
- Every introduction is logged for the "47 qualified leads this quarter" leverage conversation

### Data Requirements
- Pulls from existing `vendor` table: name, description, tagline, specialties, service_areas, website, image_url, category
- Vendor search uses existing `VendorDirectoryProvider` (pgvector cosine similarity, 1536-dim embeddings)
- Filter: only show vendors where `embedding IS NOT NULL` AND `website IS NOT NULL`
- New: may need a public API endpoint for vendor search (or reuse existing `/outreach/vendors/search`)

### Performance Expectations
- `/vendors` index page: LCP < 2s (SSG shell + client-side search)
- Vendor search results: < 500ms (pgvector query is fast)
- `/vendors/[slug]` detail pages: use ISR (revalidate every 24h) for fast load + fresh data
- With 3,000+ vendors, pagination or infinite scroll needed

### UX & Accessibility
- Search-first design: prominent search box, no category navigation
- Vendor cards: clean, professional layout matching the premium aesthetic
- Detail pages: vendor name, tagline, full description, specialties list, service areas, website link
- Mobile-responsive grid layout
- No exposed contact info (email, phone) — only website URL and "Request an introduction" CTA

### Privacy, Security & Compliance
- NEVER expose vendor email addresses or phone numbers on public pages
- Vendor description/tagline is considered public (they provided it for their business listing)
- Rate limiting on vendor search to prevent scraping
- Introduction requests from anonymous users: collect minimal info (email + name + what they need)

## Dependencies
- Upstream: PRD-00 (middleware allows `/vendors/*`), PRD-01 (public layout shell)
- Downstream: None (standalone feature, but introduction requests feed into existing outreach pipeline)

## Risks & Mitigations
- 3,000 vendors is a lot of pages to generate → Use ISR, not SSG (pages generated on first request, cached)
- Some vendors have thin descriptions → Only show vendors with `description IS NOT NULL` or fallback to tagline
- Vendor data quality varies → Display what we have; omit empty fields rather than showing placeholders

## Acceptance Criteria (Business Validation)
- [ ] `/vendors` page loads with search box, no hardcoded category navigation
- [ ] Searching "caterers" returns relevant vendor results via vector search
- [ ] `/vendors/[slug]` detail page shows vendor info without exposing email/phone
- [ ] Anonymous user can submit "Request an introduction" with email + brief
- [ ] All vendor pages accessible without login
- [ ] At least 100 vendor detail pages indexable by search engines (ISR)

## Traceability
- Parent PRD: `docs/active-dev/demo-day/parent.md`
- Product North Star: `.cfoi/branches/dev/product-north-star.md`

---
**Note:** Technical implementation decisions (ISR revalidation interval, pagination strategy, vector search endpoint) are made during /plan and /task phases, not in this PRD.
