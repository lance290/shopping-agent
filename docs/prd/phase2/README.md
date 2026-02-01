# Phase 2 PRD Documentation

**Status:** In Progress  
**Created:** 2026-01-31  
**Last Updated:** 2026-01-31

---

## Overview

Phase 2 builds on the completed Search Architecture v2 and focuses on the **marketplace experience**: buyer engagement, seller onboarding, and the closing layer.

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
| [prd-tile-provenance.md](./prd-tile-provenance.md) | P0 | MVP | 1 |
| [prd-likes-comments.md](./prd-likes-comments.md) | P0 | MVP | 2 |
| [prd-share-links.md](./prd-share-links.md) | P0 | MVP | 3 |
| [prd-quote-intake.md](./prd-quote-intake.md) | P1 | v1.1 | 4 |
| [prd-wattdata-outreach.md](./prd-wattdata-outreach.md) | P1 | v1.1 | 5 |
| [prd-stripe-checkout.md](./prd-stripe-checkout.md) | P2 | v2.0 | 6 |
| [prd-docusign-contracts.md](./prd-docusign-contracts.md) | P2 | v2.0 | 7 |

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

1. **Tile Detail & Provenance** — Click a tile, see why it was recommended
2. **Seller Quote Intake** — Sellers can submit bids without logging in
3. **WattData Outreach** — Automated vendor discovery and RFP delivery
4. **Share Links** — Collaborative workspaces with deep links
5. **Unified Closing** — Stripe checkout + DocuSign contracts

## Key Dependencies

- **WattData MCP** — Vendor contact discovery (we are investors)
- **Stripe Connect** — Payment processing
- **SendGrid/Twilio** — Outreach delivery
- **DocuSign API** — B2B contract execution
