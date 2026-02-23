# PRD: Public Homepage & Layout

## Business Outcome
- Measurable impact: First-time visitor can reach a search box and understand BuyAnything's value prop within 10 seconds of landing
- Success criteria: Homepage passes affiliate network review (no login wall, has content, has search, has clear value prop)
- Target users: Anonymous visitors, affiliate network reviewers, vendors arriving from outreach emails

## Scope
- In-scope:
  - Public layout shell (header with search bar + "Sign In" link, footer with disclosure + legal links)
  - Public homepage with universal search box, "How it works" section, example searches, featured guides
  - Session detection at `/` — anonymous visitors see homepage, logged-in users see workspace
  - Reuse/extend existing `/marketing` page as foundation
- Out-of-scope:
  - The search results page itself (PRD-02)
  - Guide page content (PRD-04)
  - Vendor directory pages (PRD-05)
  - Changing the workspace UI

## User Flow
1. Anonymous visitor arrives at `/`
2. Sees: hero section with universal search box, tagline ("Buy anything — from gift cards to private jets"), example searches
3. Below the fold: "How it works" 3-step section, featured guides carousel, "Sign In" CTA (not forced)
4. Visitor types a query → redirected to `/search?q=...` (PRD-02)
5. Footer: link to `/disclosure`, `/privacy`, `/terms`, `/about`, `/contact`

## Business Requirements

### Authentication & Authorization
- No authentication required to view the homepage
- "Sign In" link visible but not forced — positioned in header, not as a blocking modal
- Logged-in users bypass homepage entirely (session detection renders workspace)

### Monitoring & Visibility
- Track homepage visits (anonymous vs returning)
- Track search box usage from homepage (conversion: visit → search)
- Track "Sign In" click-through rate from homepage

### Billing & Entitlements
- No direct billing — homepage drives affiliate and vendor introduction funnels
- Affiliate disclosure must be visible in footer

### Data Requirements
- No new data models needed
- Homepage content is static (not DB-driven)
- Example searches are hardcoded suggestions, not personalized

### Performance Expectations
- LCP < 2.5s on 4G (use SSG for the homepage shell)
- Search box must be interactive within 3 seconds of page load
- No backend calls needed to render homepage (pure static + client-side search redirect)

### UX & Accessibility
- Mobile-responsive: search box prominent on all screen sizes
- Clean, premium aesthetic — "always premium" principle from original PRD
- Search box placeholder: "What are you looking for?" (matches existing workspace chat input)
- WCAG 2.1 AA: proper heading hierarchy, keyboard-navigable search

### Privacy, Security & Compliance
- No user data collected on homepage (search queries only captured when submitted)
- Affiliate disclosure in footer links to existing `/disclosure` page
- Cookie consent banner if tracking cookies are used

## Dependencies
- Upstream: PRD-00 (middleware must allow anonymous access to `/`)
- Downstream: PRD-02 (search results page receives queries from homepage search box)

## Risks & Mitigations
- Homepage looks too simple/empty → Include "How it works" section, example searches, and guide links to add substance
- Session detection at `/` adds complexity → Simple cookie check in page component, not a rewrite

## Acceptance Criteria (Business Validation)
- [ ] Anonymous visitor at `/` sees public homepage with search box (not login redirect)
- [ ] Logged-in visitor at `/` sees existing workspace (no regression)
- [ ] Homepage loads in < 2.5s LCP on 4G throttled connection
- [ ] Search box submit redirects to `/search?q=[query]`
- [ ] Footer contains links to `/disclosure`, `/privacy`, `/terms`
- [ ] Mobile viewport renders correctly with prominent search box

## Traceability
- Parent PRD: `docs/active-dev/demo-day/parent.md`
- Product North Star: `.cfoi/branches/dev/product-north-star.md`

---
**Note:** Technical implementation decisions (Next.js route groups, SSG vs SSR, component library) are made during /plan and /task phases, not in this PRD.
