# PRD: Static & Legal Pages

## Business Outcome
- Measurable impact: Site passes affiliate network "legitimacy check" — has complete legal/about pages that real businesses have
- Success criteria: No 404s on footer links; every page referenced in navigation exists with real content
- Target users: Affiliate network reviewers, first-time visitors checking trust signals, regulators

## Scope
- In-scope:
  - `/how-it-works` — 3-step explanation of BuyAnything
  - `/about` — Company mission, the problem we solve, team
  - `/contact` — Contact form or contact info
  - `/privacy` — Privacy policy
  - `/terms` — Terms of service
  - Link existing `/disclosure` page into public layout footer
- Out-of-scope:
  - Affiliate disclosure content (already exists at `/disclosure`)
  - Marketing/landing page (already exists at `/marketing`)
  - Dynamic content or database-driven pages

## User Flow
1. Visitor clicks a footer link (e.g., "Privacy Policy")
2. Static page loads immediately (SSG — no backend call)
3. Visitor reads content, gains trust in the platform
4. Navigation links back to homepage or search

## Business Requirements

### Authentication & Authorization
- All pages fully public, no auth required
- No user data collected on any of these pages

### Monitoring & Visibility
- Basic page view tracking (which pages do visitors actually read?)
- Track `/how-it-works` → search conversion (did they search after reading?)

### Billing & Entitlements
- No billing impact
- `/how-it-works` should include a subtle CTA to search (drives affiliate funnel)

### Data Requirements
- No database access — pure static content
- Content can be hardcoded in page components or loaded from MDX files

### Performance Expectations
- All pages: LCP < 1s (static content, no API calls)
- Use SSG — these pages never change at runtime

### UX & Accessibility
- Consistent layout with public header/footer (from PRD-01)
- Clean, readable typography for legal text
- WCAG 2.1 AA: proper heading hierarchy, readable font sizes for legal content

### Privacy, Security & Compliance
- Privacy policy must cover: data collection, cookies, affiliate tracking, third-party data sharing
- Terms must include: BuyAnything is an introduction platform, not a seller; no warranties on vendor performance
- Both documents should be reviewed by legal counsel before production (placeholder versions acceptable for demo)

## Dependencies
- Upstream: PRD-00 (middleware allows these routes), PRD-01 (public layout shell with header/footer)
- Downstream: None

## Risks & Mitigations
- Legal content not reviewed by counsel → Use standard templates for demo; flag for legal review post-demo
- Pages look thin/boilerplate → Add BuyAnything-specific language (how we handle vendor introductions, what data we collect for search)

## Acceptance Criteria (Business Validation)
- [ ] `/how-it-works` loads with 3-step explanation and search CTA
- [ ] `/about` loads with company mission and value proposition
- [ ] `/contact` loads with a way to reach the team
- [ ] `/privacy` loads with privacy policy content (template acceptable for demo)
- [ ] `/terms` loads with terms of service content (template acceptable for demo)
- [ ] Existing `/disclosure` page is linked from public footer
- [ ] No 404s from any footer navigation link

## Traceability
- Parent PRD: `docs/active-dev/demo-day/parent.md`
- Product North Star: `.cfoi/branches/dev/product-north-star.md`

---
**Note:** Technical implementation decisions (MDX vs hardcoded, component structure) are made during /plan and /task phases, not in this PRD.
