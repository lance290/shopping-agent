# PRD: Seller Tiles + Quote Intake

**Status:** Partially implemented — significant gaps remain  
**Last Updated:** 2026-02-06 (gap analysis pass)

## Implementation Status (as of 2026-02-06)

| Feature | Status | Current Code |
|---------|--------|-------------|
| Seller quote submission via magic link | ✅ Done | `SellerQuote` model + magic link flow |
| Seller dashboard (inbox, quotes, profile) | ✅ Done | `routes/seller.py` + frontend `/seller` page |
| Merchant registration with auth | ✅ Done | `routes/merchants.py` — links Merchant → User |
| Quote → Bid conversion | ✅ Done | `SellerQuote` converts to `Bid` on submission |
| Seller RFP discovery feed | ❌ Not built | `find_buyers()` returns empty in mock. Sellers only see rows where outreach was explicitly triggered for them. |
| Seller commenting on buyer needs | ❌ Not built | `Comment` model exists but is buyer→bid only, not seller→RFP |
| Seller bookmarks/save | ❌ Not built | No bookmark model or endpoint |
| Notification: quote arrived for buyer | ❌ Not built | No notification system exists at all |
| Notification: matching RFP for seller | ❌ Not built | No notification system exists at all |

**Wrong assumption:** This PRD assumes sellers can proactively discover buyer needs. Currently, sellers only see rows where outreach was explicitly triggered *for them* — there is no RFP discovery feed. The `VendorDiscoveryAdapter.find_buyers()` interface exists but returns empty.

**Critical dependency:** A **notification system** (even basic email + in-app badge) is required for the two-sided marketplace loop. Without it, sellers don't know when RFPs match them, and buyers don't know when quotes arrive.

## Business Outcome
- Measurable impact: Convert more buyer intent into competitive bids by enabling sellers to discover relevant buyer needs and respond with quotes that become tiles.
- Target users:
  - Sellers/vendors (local service providers, B2B vendors, merchants)
  - Buyers receiving increased competition

## Scope
- In-scope:
  - Seller-visible representation of buyer needs (tiles of RFPs)
  - Seller tile interactions: comment/ask clarifying questions, share (where permitted), and save/bookmark
  - Quote intake: seller can answer key questions and attach links to products/services
  - Bid submission results in a buyer-visible tile within the correct project row
  - Basic seller identity and attribution sufficient for buyer decision-making
- Out-of-scope:
  - Automated vendor outreach (covered in separate slice)
  - Stripe checkout / DocuSign contracts

## User Flow
1. Seller receives an invitation/link (from outreach, sharing, or discovery) to view a buyer need.
2. Seller opens a tile representing the buyer’s RFP.
3. Seller can comment to ask clarifying questions (where permitted).
4. Seller answers key questions and attaches links to an offer.
5. Seller submits the quote.
6. Buyer sees the quote as a new tile in their row and can interact with it (thumb/select).

## Business Requirements

### Authentication & Authorization
- Sellers must only see buyer needs they are invited to see or that are explicitly discoverable by business policy.
- Buyers must control whether their RFP is shareable/discoverable to sellers.
- Seller comments are only visible to the buyer and collaborators who have access to the project, unless a future visibility scope policy is enabled.

### Monitoring & Visibility
- Track:
  - Seller invite → view conversion
  - Quote submission rate
  - Time from invite to first quote
  - Buyer select rate on seller quotes
  - Seller comments per RFP tile
  - Seller bookmarks per RFP tile

### Billing & Entitlements
- Must support future transaction fee monetization on B2B outcomes.
- No requirement to charge sellers to submit a quote in MVP unless explicitly enabled by business policy.

### Data Requirements
- Persist:
  - Seller profiles (minimal)
  - Quotes/bids and attached links
  - Mapping of quote → buyer row and provenance
  - Seller comments (user, tile/row, content, timestamp)
  - Seller bookmarks/saved items (user, tile/row, timestamp)

### Performance Expectations
- Seller can submit a quote without friction.

### UX & Accessibility
- Seller experience should mirror buyer tile UX where feasible.
- Quote intake should be achievable without requiring full onboarding when policy allows.

### Privacy, Security & Compliance
- Buyer RFP content may include sensitive details (location, budget). Access must be controlled and logged.

## Dependencies
- Upstream:
  - Buyer workspace + tile provenance
- Downstream:
  - Closing layer

## Risks & Mitigations
- Abuse/spam quotes → rate limits, verification, and reporting flows.

## Acceptance Criteria (Business Validation)
- [ ] Seller can view an invited buyer need and submit a quote with links (binary).
- [ ] Seller can comment on a buyer need tile and the buyer can see the comment (binary).
- [ ] Submitted quote appears as a tile in the buyer’s row (binary).
- [ ] Buyer can view tile detail and see provenance for a seller-submitted quote (binary).

## Traceability
- Parent PRD: `docs/prd/marketplace-pivot/parent.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---
**Note:** Technical implementation decisions are made during /plan and /task.
