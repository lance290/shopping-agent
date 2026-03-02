# PRD: Tile Detail & Provenance

## Business Outcome
- **Measurable impact**: Increase buyer confidence → higher select rate (tied to North Star: persistence reliability)
- **Success criteria**: 60% of users who click a tile proceed to like/select it (vs baseline ~40% estimated)
- **Target users**: Buyers evaluating search results

## Scope
- **In-scope**: 
  - Click-to-expand tile detail panel
  - Display "why recommended" provenance
  - Show matched choice factors
  - Show relevant chat excerpts
- **Out-of-scope**: 
  - Editing provenance
  - AI-generated explanations (use extracted data only)

## User Flow
1. Buyer searches for a product/service
2. Results appear as tiles in the row
3. Buyer clicks a tile to see details
4. Detail panel slides out showing:
   - Product info (title, price, merchant, image, rating)
   - "Why this result" section with matched features
   - Chat excerpts that led to this recommendation
5. Buyer decides to like, comment, or select
6. Panel closes, buyer continues browsing

## Business Requirements

### Authentication & Authorization
- **Who needs access?** Any authenticated buyer viewing their own rows; collaborators with view access
- **What actions are permitted?** View provenance (read-only); Like/Comment/Select (buyers + collaborators per permission matrix)
- **What data is restricted?** Provenance data is row-owner-scoped; share link viewers can see but not act

### Monitoring & Visibility
- **Business metrics**: 
  - Tile click rate (% of visible tiles clicked)
  - Time spent on detail panel
  - Conversion: detail view → like/select
- **Operational visibility**: Panel load time, error rates
- **User behavior tracking**: Click heatmaps on provenance sections

### Billing & Entitlements
- **Monetization**: None (core feature)
- **Entitlement rules**: Available to all users
- **Usage limits**: None

### Data Requirements
- **What must persist?** Provenance data attached to each bid (already in bid.provenance JSONB)
- **Retention**: Same as bid retention
- **Relationships**: Bid → Provenance (1:1), Bid → Row → Project

### Performance Expectations
- **Response time**: Detail panel loads in <300ms
- **Throughput**: N/A (user-driven)
- **Availability**: Same as platform (99.9%)

### UX & Accessibility
- **Standards**: Slide-out panel pattern consistent with app design
- **Accessibility**: WCAG 2.1 AA; keyboard navigable; screen reader labels
- **Devices**: Desktop + tablet (mobile nice-to-have)

### Privacy, Security & Compliance
- **Regulations**: None specific
- **Data protection**: Provenance may contain user query text; no PII beyond what user submitted
- **Audit trails**: Log tile clicks for analytics

## Dependencies
- **Upstream**: Search Architecture v2 (complete) — provides bid data with provenance field
- **Downstream**: None — this is foundational UX

## Risks & Mitigations
- **Sparse provenance data** → Show "Based on your search" fallback if no specific matches
- **Long chat excerpts** → Truncate with "Show more" expansion

## Acceptance Criteria (Business Validation)
- [ ] Tile click rate: baseline TBD → target ≥20% of visible tiles clicked (industry benchmark for e-commerce product cards)
- [ ] Detail panel load time: ≤300ms p95 (current search latency baseline: ~5s, panel should be instant from cached data)
- [ ] ≥80% of panels show at least one matched feature (depends on search intent extraction quality)
- [ ] User can navigate panel entirely via keyboard
- [ ] Screen reader announces panel content correctly

## Traceability
- **Parent PRD**: docs/prd/phase2/PRD.md
- **Product North Star**: .cfoi/branches/dev/product-north-star.md

---
**Note:** Technical implementation decisions (component architecture, state management, etc.) are made during /plan and /task phases, not in this PRD.
