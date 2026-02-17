# Traceability Matrix: Demo Day PRDs

**Parent PRD**: `docs/active-dev/demo-day/parent.md` (Thursday Demo — Affiliate Readiness & Public Surface)  
**Product North Star**: `.cfoi/branches/dev/product-north-star.md`  
**Created**: 2026-02-17  
**Deadline**: Wednesday EOD (demo Thursday)

## Child PRD Map

| Child PRD | Priority | Phase | Ship Order | Status | Dependencies | North Star Tie |
|-----------|----------|-------|------------|--------|-------------|----------------|
| **prd-00-middleware-public-routes** | P0 BLOCKER | MVP | 1 | Draft | None | Revenue per search: can't earn if anonymous users can't search |
| **prd-01-public-homepage-layout** | P0 | MVP | 2 | Draft | PRD-00 | Search success rate: homepage is the entry point to all searches |
| **prd-02-public-search-results** | P0 | MVP | 3 | Draft | PRD-00, PRD-01 | Revenue per search: this IS the affiliate monetization page |
| **prd-03-static-legal-pages** | P0 | MVP | 4 | Draft | PRD-00, PRD-01 | Trust/legitimacy: affiliate networks require legal pages |
| **prd-04-editorial-guides** | P0 | MVP | 5 | Draft | PRD-00, PRD-01 | Revenue per search: guides drive affiliate clicks + vendor introductions |
| **prd-05-public-vendor-directory** | P1 | MVP | 6 | Draft | PRD-00, PRD-01 | Seller response rate: showcases vendor network, drives introductions |
| **prd-06-demo-prep-polish** | P0 | MVP | 7 | Draft | PRD-00 through PRD-05 | All metrics: demo must show the full platform working end-to-end |

## Dependency Graph

```
PRD-00 (Middleware) ──┬──→ PRD-01 (Homepage) ──┬──→ PRD-02 (Search Results)
                      │                        ├──→ PRD-03 (Static Pages)
                      │                        ├──→ PRD-04 (Guides)
                      │                        └──→ PRD-05 (Vendor Directory)
                      │
                      └──→ (also unblocks /share/* and /quote/* for anonymous users)

PRD-00 through PRD-05 ──→ PRD-06 (Demo Prep — final polish after everything else ships)
```

## Critical Path

**Monday**: PRD-00 (middleware fix — 1 hour) → PRD-01 (homepage + layout — 4 hours)  
**Tuesday**: PRD-02 (search results page — 4 hours) → PRD-03 (static pages — 2 hours)  
**Wednesday**: PRD-04 (guide content — 4 hours) → PRD-05 (vendor directory — 3 hours) → PRD-06 (demo polish — 2 hours)

## Cross-Cutting Verification

| Concern | PRD-00 | PRD-01 | PRD-02 | PRD-03 | PRD-04 | PRD-05 | PRD-06 |
|---------|--------|--------|--------|--------|--------|--------|--------|
| Auth/anon access | ✅ Primary | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Monitoring | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Affiliate disclosure | — | ✅ Footer | ✅ Inline | ✅ Links | ✅ Per-guide | ✅ — | ✅ Verify |
| Performance (LCP) | — | ✅ <2.5s | ✅ <3s first results | ✅ <1s | ✅ <1.5s | ✅ <2s | ✅ Verify |
| Privacy | ✅ | ✅ | ✅ No PII | ✅ Policy page | ✅ | ✅ No vendor email/phone | ✅ |
| Mobile responsive | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Verify |

## What Already Exists (Not Requiring New PRDs)

These features are fully built and working — no new PRDs needed:

- ✅ Five-layer sourcing pipeline (LLM → Adapters → Providers → Normalizers → Re-ranking)
- ✅ Vendor vector search (pgvector, 3,000+ vendors)
- ✅ Per-retailer query adapters (Rainforest/Amazon, eBay, Google CSE)
- ✅ Three-stage re-ranking (classical scorer + quantum reranker + constraint satisfaction)
- ✅ Affiliate link resolution (Amazon Associates, eBay Partner Network, Skimlinks)
- ✅ Clickout tracking with fraud detection
- ✅ Vendor outreach pipeline with email tracking
- ✅ Likes, comments, share links with public pages
- ✅ Referral attribution (share → signup → User.referral_share_token)
- ✅ Affiliate disclosure page at `/disclosure`
- ✅ Marketing/landing page at `/marketing`
- ✅ Desire-tier classification (feeds into re-ranker's tier_fit multiplier; legacy provider gating function exists but is marked for removal — re-ranker handles this)
- ✅ Unified price filter (single source of truth)
- ✅ Search observability/metrics
