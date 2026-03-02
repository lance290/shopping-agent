# Phase 2 PRD Documentation

**Status:** In Progress  
**Created:** 2026-01-31  
**Last Updated:** 2026-02-03

---

## Overview

Phase 2 builds on the completed Search Architecture v2 and focuses on the **marketplace experience**: buyer engagement, seller onboarding, and the closing layer.

### Competitive Positioning

Phase 2 delivers **feature parity with PartFinder** (B2B industrial parts sourcing) while maintaining our consumer UX advantage. See [Competitive Analysis](../Competitive_Analysis_PartFinder.md) for details.

**Key differentiators we're building:**
- Two-sided marketplace (Merchant Registry) — they only do cold outreach
- Service provider network with category taxonomy
- Social features (likes, comments, share links)
- Viral distribution mechanics

**We can go B2B.** The Merchant Registry + WattData integration positions us for enterprise if metrics support it.

## Documents

### Parent PRD & Specs
| Document | Description | Status |
|----------|-------------|--------|
| [PRD.md](./PRD.md) | Main Phase 2 PRD (parent) | Draft |
| [wattdata-integration.md](./wattdata-integration.md) | WattData MCP integration spec | Draft |
| [identity-model.md](./identity-model.md) | Buyer/Seller/Collaborator identity | Draft |
| [quote-intake-schema.md](./quote-intake-schema.md) | Seller bid/quote data model | Draft |

### Child PRDs (Sliced)
| Document | Priority | Phase | Ship Order |
|----------|----------|-------|------------|
| [prd-tile-provenance.md](./prd-tile-provenance.md) | P0 | Wave 1 | 1 |
| [prd-likes-comments.md](./prd-likes-comments.md) | P0 | Wave 1 | 2 |
| [prd-share-links.md](./prd-share-links.md) | P0 | Wave 1 | 3 |
| [prd-merchant-registry.md](./prd-merchant-registry.md) | P1 | Wave 2 | 4 |
| [prd-wattdata-outreach.md](./prd-wattdata-outreach.md) | P1 | Wave 2 | 5 |
| [prd-quote-intake.md](./prd-quote-intake.md) | P1 | Wave 2 | 6 |
| [prd-email-handoff.md](./prd-email-handoff.md) | P1 | Wave 2 | 7 |
| [prd-stripe-checkout.md](./prd-stripe-checkout.md) | P2 | Wave 3 | 8 |
| [prd-docusign-contracts.md](./prd-docusign-contracts.md) | P2 | Wave 3 | 9 |
| [prd-private-jet-demo.md](./prd-private-jet-demo.md) | P1 | Demo | — |

## Phase 1 Completion Status (Prerequisites)

| Feature | Status | Notes |
|---------|--------|-------|
| Search Architecture v2 | ✅ Complete | 5-layer architecture, streaming, observability |
| Project Hierarchy | ✅ Complete | Rows can be grouped under projects |
| Intent Extraction | ✅ Complete | LLM extracts SearchIntent from queries |
| Provider Adapters | ✅ Complete | Rainforest, Google CSE, SerpAPI, SearchAPI |
| Streaming Search | ✅ Complete | SSE-based progressive result loading |
| Basic Likes | ⚠️ Partial | Backend exists, click-test pending |
| Comments | ⚠️ Partial | Backend exists, click-test pending |

## What Phase 2 Delivers

### Wave 1: Buyer Engagement
1. **Tile Detail & Provenance** — Click a tile, see why it was recommended
2. **Likes & Comments** — Persistent social engagement on tiles
3. **Share Links** — Collaborative workspaces with deep links

### Wave 2: Seller Loop (Two-Sided Marketplace)
4. **Merchant Registry** — Service providers self-register, receive RFP notifications
5. **WattData Outreach** — Automated vendor discovery and RFP delivery
6. **Seller Quote Intake** — Sellers can submit bids via magic link (no account)
7. **Email Handoff** — MVP closing via buyer-seller introduction

### Wave 3: Formal Closing Layer
8. **Stripe Checkout** — Retail purchase with affiliate tracking
9. **DocuSign Contracts** — B2B contract execution for high-value deals

## Key Dependencies

- **WattData MCP** — Vendor contact discovery (we are investors — preferred access)
- **Stripe Connect** — Payment processing
- **SendGrid** — Email outreach delivery + tracking
- **DocuSign API** — B2B contract execution

## B2B Expansion Path

Phase 2 positions us for B2B without additional work:

| Capability | Status |
|------------|--------|
| RFQ Automation | ✅ WattData Outreach |
| Quote Intake | ✅ Magic link flow |
| Merchant Network | ✅ Registry + taxonomy |
| Deal Closing | ✅ Email Handoff + DocuSign |
| Service Categories | ✅ Home, auto, professional, travel, events |

**Phase 3+ for full enterprise:** ERP integrations (SAP/NetSuite), parts-specific AI, photo-based search.

See [EXECUTION_ORDER.md](./EXECUTION_ORDER.md) for detailed implementation plan.

## Related Documents

- [Competitive Analysis: PartFinder](../Competitive_Analysis_PartFinder.md)
- [Phase 3 Roadmap](./phase3-roadmap.md) (future capabilities)
