# PRD: Editorial Guide Pages

## Business Outcome
- Measurable impact: 5–10 pages of unique, indexable editorial content that demonstrate BuyAnything is a legitimate content business (not a thin redirect site)
- Success criteria: Affiliate network reviewer reads a guide and finds genuine, useful content with natural affiliate links and vendor CTAs
- Target users: Anonymous visitors (SEO/organic), affiliate network reviewers, potential buyers researching purchases

## Scope
- In-scope:
  - 5 must-have guide pages at `/guides/[slug]` (minimum viable set)
  - Up to 5 additional guides if time permits
  - LLM-generated first drafts using existing `services/llm.py:call_gemini()`, then hand-edited
  - Each guide 800–1,500 words with curated product links (affiliate) and/or vendor CTAs
  - Inline affiliate disclosure on every guide with outbound links
- Out-of-scope:
  - Dynamic content generation at runtime (guides are pre-written static content)
  - User-generated content or comments on guides
  - SEO optimization beyond basic meta tags (future work)

## User Flow
1. Visitor discovers guide via homepage link, search engine, or shared URL
2. Reads editorial content (800–1,500 words of genuinely useful advice)
3. Sees curated product recommendations with "Buy" affiliate links (for retail guides)
4. Sees vendor spotlights with "Find a vendor" CTAs (for service/local guides)
5. Inline affiliate disclosure near outbound links
6. CTA at bottom: "Need help finding exactly the right thing? Try our search" → `/search`

## Business Requirements

### Authentication & Authorization
- All guides fully public, no auth required
- No user data collected on guide pages

### Monitoring & Visibility
- Track per-guide: page views, time on page, clickout rate (affiliate links clicked)
- Track guide → search conversion (did reader use search after reading?)
- Identify which guides drive the most affiliate revenue (post-launch)

### Billing & Entitlements
- Affiliate links in retail-focused guides go through `/api/out` → `LinkResolver`
- Vendor CTAs in service-focused guides drive vendor introduction funnel
- No direct billing — guides are content marketing for both funnels

### Data Requirements
- Guide content stored as static files (MDX or TSX pages), not in database
- No new data models needed
- Product recommendations can reference real search results from our pipeline (but are curated/frozen, not live)

### Performance Expectations
- Guide pages: LCP < 1.5s (static content with images)
- Use SSG — content doesn't change at runtime
- Images should be optimized (Next.js Image component)

### UX & Accessibility
- Clean editorial layout: readable typography, proper heading hierarchy, generous whitespace
- Product recommendation cards within guides should match the OfferTile aesthetic
- Mobile-responsive: single-column reading experience
- Author attribution: "BuyAnything Editorial" or specific author name

### Privacy, Security & Compliance
- Affiliate disclosure required on every guide that contains outbound product links
- No tracking beyond standard page view analytics
- Content must be genuinely useful (not thin AI sludge) — editorial quality bar

## Guide List (Priority Ordered)

### Must-Have (ship these 5):
1. **`/guides/how-buyanything-works`** — How anyone uses BuyAnything to find what they need (explains core value prop)
2. **`/guides/gift-vault-tech-lovers`** — Curated tech gifts with affiliate links (demonstrates affiliate content)
3. **`/guides/best-luggage-for-travel`** — Product roundup with affiliate links (high affiliate potential)
4. **`/guides/support-local-vendors`** — Why and how to buy from local/indie vendors (demonstrates vendor directory breadth)
5. **`/guides/home-office-setup-guide`** — Product roundup with affiliate links (broad appeal)

### Nice-to-Have (if time permits):
6. `/guides/private-flight-essentials` — Chartering guide (vendor CTA)
7. `/guides/corporate-gift-guide` — Bulk ordering tips + product links
8. `/guides/event-planning-checklist` — Hybrid: products + service vendors
9. `/guides/small-business-sourcing` — How small businesses find suppliers
10. `/guides/custom-jewelry-buying-guide` — Vendor-focused, concierge CTA

## Content Quality Bar
- Minimum 800 words per guide (no thin pages)
- Unique content that references our specific vendor network or search capabilities
- No placeholder text, no "Coming soon", no lorem ipsum
- Hand-edited after LLM generation — must pass a "would a human find this useful?" test
- Natural affiliate link placement (not forced or spammy)

## Dependencies
- Upstream: PRD-00 (middleware allows `/guides/*`), PRD-01 (public layout with header/footer)
- Downstream: None (guides are standalone content)

## Risks & Mitigations
- Content looks AI-generated → Hand-edit every guide; add brand voice; reference specific products/vendors from our DB
- Not enough guides for affiliate approval → 5 guides + vendor directory pages (3,000+) = substantial content volume
- Guide affiliate links break → Use `/api/out` clickout endpoint (same as search results)

## Acceptance Criteria (Business Validation)
- [ ] At least 5 guide pages live at `/guides/[slug]` with 800+ words each
- [ ] Each guide with product links has inline affiliate disclosure
- [ ] Affiliate links go through `/api/out` and are logged as `ClickoutEvent`
- [ ] Guides are accessible without login
- [ ] Content passes editorial quality check (not obviously AI-generated, genuinely useful)

## Traceability
- Parent PRD: `docs/active-dev/demo-day/parent.md`
- Product North Star: `.cfoi/branches/dev/product-north-star.md`

---
**Note:** Technical implementation decisions (MDX vs TSX, content generation pipeline, image sourcing) are made during /plan and /task phases, not in this PRD.
