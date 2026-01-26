# Product North Star (v2026-01-23.1)

## Mission
Eliminate the friction of multi-category procurement by providing an AI agent that transforms natural-language intent into structured RFPs and a project-based workspace—sourcing vendors across channels, collecting comparable bids/offers, and closing transactions (retail + B2B) through a unified payments and contracting layer.

## Target Users & Core Jobs

### Primary: Everyday Buyer
- **Job**: Buy goods and services across categories (retail + local/B2B) without stitching together multiple platforms
- **Pain**: Comparison fatigue, fragmented workflows, and unclear tradeoffs across vendors

### Secondary: Power Buyer  
- **Job**: Run a project-based procurement process with structured requirements, stakeholder review, and vendor outreach
- **Pain**: Manual RFQs, disorganized quotes, and slow vendor follow-up

### Tertiary: Seller/Vendor
- **Job**: Receive structured RFPs and submit quotes quickly (without learning a new platform), with a clear path to closing
- **Pain**: Unqualified leads, unclear requirements, and slow back-and-forth

## Differentiators

1. **Conversational RFP builder**: Chat extracts specs/constraints and generates structured requirements
2. **Split-pane workspace**: Persistent chat + interactive tiles/rows for comparison and collaboration
3. **Multi-channel sourcing**: Aggregators/APIs for instant offers plus proactive vendor outreach for hard-to-source needs
4. **Unified closing layer**: Retail checkout (Stripe) and B2B contracts (DocuSign) in a consistent flow
5. **Project-based procurement**: Row hierarchy for multi-item projects with stakeholder sharing and selection
6. **Tile detail provenance**: Tile click opens a consistent detail view (FAQ + chat log) explaining choice-factor highlights and “why this tile”
7. **Two-sided marketplace UX**: Sellers have a tile-based view of buyer needs (RFPs) and can submit bids/quotes that appear as tiles for buyers

## Success Metrics / OKRs

| Metric | Target | Rationale |
|--------|--------|-----------|
| Time to first project row | <30 seconds | Fast path from intent to workspace |
| Time to first offers | <30 seconds | Immediate value via instant sourcing |
| Offers/bids per row | ≥3 | Competitive set for decision-making |
| % of B2B selections with contract flow completed | High | Validate unified closing layer |
| GMV growth (affiliate + fees) | 20% MoM | Marketplace monetization trajectory |

## Non-Negotiables

1. **No invented offers**: Tiles must map to real vendor offers, verified listings, or seller-submitted quotes
2. **User confirms purchases**: No autonomous purchasing without explicit user approval
3. **Auditability**: Key agent actions and outbound vendor communications are tracked
4. **Unified closing for trust**: Payments/contracts must use secure, reputable providers (Stripe/DocuSign)
5. **Project-first UX**: Multi-item projects and collaboration are first-class
6. **Seller quote intake is first-class**: Sellers can submit bids/quotes by answering key questions and attaching links to products/services

## Exclusions (Out of Scope)

- Proprietary logistics, warehousing, or delivery networks
- Replacing existing merchant storefronts or inventory management systems
- Fully autonomous purchasing

## References

- **Original brief**: `need sourcing_ next ebay.md`

## Approver / Date
- **Updated to align with**: `buyanything-ai-ai-agent-facilitated-multi-category-marketplace-PRD.md`
- **Date**: 2026-01-23
- **Status**: Approved
- **Approver**: Approved (user)
