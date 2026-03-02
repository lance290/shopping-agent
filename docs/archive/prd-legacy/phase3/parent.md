# Phase 3: Closing the Loop — Parent PRD

**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Owner:** Product  

---

## Problem Statement

Phase 2 delivered the **structural foundation** of the BuyAnything.ai marketplace: chat-driven RFP building, Netflix-style tile rows, multi-provider sourcing, affiliate clickout, seller quote intake, outreach, and merchant registry. However, several critical paths remain **wired to mock data or model-only implementations**:

- Users **cannot actually purchase** anything through the platform (Stripe unwired).
- Contracts exist as DB rows but **never reach DocuSign**.
- Tile provenance panels mostly show a generic "Based on your search" fallback.
- The seller loop runs against **hardcoded mock vendors** (WattData MCP goes live in ~2 weeks).
- Sellers have **no dashboard** to view buyer RFPs or manage quotes.
- Social features (likes/comments) are untested end-to-end.
- No admin UI despite backend admin routes existing.
- Mobile layout is minimal.

Phase 3 closes these gaps to deliver **an end-to-end functional marketplace** where a buyer can discover, compare, negotiate, and purchase — and a seller can discover ICPs, receive RFPs, and close deals.

---

## Child PRDs

| # | PRD | Priority | Est. Effort | Dependency |
|---|-----|----------|-------------|------------|
| 1 | [Stripe Checkout Integration](./01-stripe-checkout.md) | P0 | 3–5 days | Stripe account + API keys |
| 2 | [WattData MCP Integration](./02-wattdata-mcp.md) | P0 | 3–5 days | WattData MCP online (~2 weeks) |
| 3 | [Seller Dashboard](./03-seller-dashboard.md) | P1 | 5–7 days | Quote intake (done), Auth (done) |
| 4 | [Tile Provenance Enrichment](./04-provenance-enrichment.md) | P1 | 2–3 days | Sourcing pipeline (done) |
| 5 | [Social Features Completion](./05-social-polish.md) | P1 | 2–3 days | Likes/Comments models (done) |
| 6 | [Admin Dashboard](./06-admin-dashboard.md) | P2 | 3–5 days | Admin routes (done) |
| 7 | [Mobile Responsive Layout](./07-mobile-responsive.md) | P2 | 3–5 days | None |

---

## Sequencing

```
Week 1-2:  [01] Stripe Checkout  +  [04] Provenance Enrichment  +  [05] Social Polish
Week 2-3:  [03] Seller Dashboard (can start before WattData)
Week 3-4:  [02] WattData MCP Integration (when MCP goes live)
Week 4-5:  [06] Admin Dashboard  +  [07] Mobile Responsive
```

**Note:** PRD-02 (WattData) has an external dependency — the MCP server is expected online in ~2 weeks. Design work and adapter scaffolding can begin immediately; live integration starts when the MCP is available.

---

## Success Criteria (Phase 3 Complete)

1. A buyer can **search → compare → purchase** an item entirely within the platform (Stripe Checkout).
2. A seller can **log in → see buyer RFPs → submit quotes** via a dedicated dashboard.
3. Tile detail panels show **rich provenance** (matched features, chat excerpts) for ≥60% of tiles.
4. WattData MCP replaces mock data for vendor discovery (when available).
5. Likes and comments **persist across sessions** and influence tile ordering.
6. Admin can view system health, user activity, and outreach metrics via a UI.
7. The app is **usable on mobile** (vertical stack layout, touch-friendly tiles).

---

## Companion Documents

- [Standing Up APIs & Services Guide](./SETUP-GUIDE.md) — How to configure Stripe, DocuSign, Resend, WattData, and other external dependencies.

---

## Non-Goals (Phase 3)

- Real-time bidding / auction mechanics (Phase 4+)
- Photo-based search (Phase 4+)
- ERP integrations (Phase 4+)
- OAuth / Google SSO (defer to Phase 4)
- Automated negotiation agent (Phase 4+)
- Multi-currency / i18n (Phase 4+)
