# Build-All Decisions Log — Phase 4 (appended to Phase 3)

## Architecture Discovery - 2026-02-06
- **Found**: Existing monorepo with 3 apps (frontend/bff/backend), pnpm + uv, Postgres on 5435
- **Decision**: Follow all existing patterns. No new frameworks or tools.
- **Confidence**: High

## Product North Star Update - 2026-02-06
- **Gap**: North Star explicitly excludes "in-app payments/checkout" but Phase 3 PRD-01 requires Stripe Checkout
- **Resolution**: Phase 3 expands scope to include checkout — this is the natural evolution the PRDs call for
- **Confidence**: High

## PRD Naming Convention - 2026-02-06
- **Gap**: Workflow expects `prd-*.md` naming but Phase 3 uses `01-stripe-checkout.md` etc.
- **Resolution**: Process all `.md` files in phase3/ except parent.md and SETUP-GUIDE.md
- **Confidence**: High

## Parallel Execution Strategy - 2026-02-06
- **Decision**: PRDs 01, 04, 05 have zero cross-dependencies and touch different parts of the stack. Implement in parallel where possible.
- **Wave 1 (parallel)**: 01-stripe-checkout + 04-provenance-enrichment + 05-social-polish
- **Wave 2**: 02-wattdata-mcp (adapter scaffold only — MCP not live for ~2 weeks)
- **Wave 3**: 03-seller-dashboard (depends on auth + merchant model, both done)
- **Wave 4**: 06-admin-dashboard + 07-mobile-responsive (P2, lower priority)
- **Confidence**: High

## Stripe Installation - 2026-02-06
- **Decision**: Add `stripe` to backend pyproject.toml dependencies. Use Stripe Python SDK v7+.
- **Source**: Stripe docs recommend latest SDK. Backend uses Python 3.11+ which is compatible.
- **Confidence**: High

## WattData MCP Scope Limit - 2026-02-06
- **Decision**: Only build adapter interface + mock wrapper + scaffold. Do NOT attempt to connect to WattData MCP (not online yet). User confirmed ~2 weeks out, API shape unknown.
- **Confidence**: High

## SETUP-GUIDE.md - 2026-02-06
- **Decision**: SETUP-GUIDE.md is documentation, not an implementable PRD. Skip in effort loop. Already complete.
- **Confidence**: High

---
# Phase 4 Decisions (2026-02-06)

## Product North Star Update (Phase 4) - 2026-02-06
- **Gap**: North Star was search-focused (Phase 3). Phase 4 is marketplace + monetization.
- **Resolution**: Updated North Star to include two-sided marketplace, seller role, revenue capture, and new OKRs (revenue per search, seller response rate, intent-to-close rate).
- **Confidence**: High

## PRD 00 Created: Revenue & Monetization - 2026-02-06
- **Gap**: No PRD addressed platform revenue. All 7 existing PRDs assumed monetization exists but none defined it.
- **Resolution**: Created PRD 00 as P0 priority. Covers 4 revenue streams: affiliate (immediate), Stripe Connect (medium-term), B2B fees (future), premium tiers (future).
- **Source**: Codebase audit — `affiliate.py` handlers coded but env vars empty, `checkout.py` has no `application_fee_amount`.
- **Confidence**: High

## PRD Naming Convention (Phase 4) - 2026-02-06
- **Decision**: Phase 4 uses `00-*.md` through `07-*.md` plus `parent.md` and `GAP-ANALYSIS.md`. Process all numbered `.md` files.
- **Confidence**: High

## PRD Gap Fill: 01-search-architecture-v2 - 2026-02-06
- **Gap**: PRD assumed architecture was 0% built. Audit found ~75% implemented.
- **Resolution**: Added Implementation Status table showing L1-L5 status. Marked phases 1-4 done, phase 5 partial (no scoring), phase 6 not started. Scoped remaining work to: eBay adapter, scoring/ranking, currency normalization, low-confidence disambiguation, cleanup.
- **Source**: Codebase audit of `sourcing/` package
- **Confidence**: High

## PRD Gap Fill: 04-seller-tiles-quote-intake - 2026-02-06
- **Gap**: PRD assumed sellers can proactively discover buyer needs. `find_buyers()` returns empty.
- **Resolution**: Flagged as wrong assumption in PRD. Seller RFP discovery feed must be built. Also flagged missing notification system as critical dependency.
- **Source**: Codebase audit of `services/vendor_discovery.py`, `routes/seller.py`
- **Confidence**: High

## PRD Gap Fill: 05-unified-closing-layer - 2026-02-06
- **Gap**: PRD mentions "transaction fees" and "affiliate model" but provides zero specifics on revenue split, Stripe Connect, or payout mechanics. Platform captures zero revenue.
- **Resolution**: Added 🚨 CRITICAL revenue gap section with 4 revenue model options. Pointed to PRD 00 as prerequisite.
- **Source**: Codebase audit of `routes/checkout.py` — no `application_fee_amount`, no connected accounts
- **Confidence**: High

## PRD Gap Fill: 06-viral-growth-flywheel - 2026-02-06
- **Gap**: Most aspirational PRD with most unbuilt surface. Depends on notification system and seller discovery, neither of which exist.
- **Resolution**: Recommended deferring to Phase 5. Added implementation status showing data infrastructure (ShareLink, referral fields) exists but zero mechanics built.
- **Source**: Codebase audit
- **Confidence**: Medium — user may disagree on deferral

## Cross-PRD Dependency: Notification System - 2026-02-06
- **Gap**: PRDs 04, 06, and 07 assume notifications exist. No notification system is built. No PRD explicitly defines it.
- **Resolution**: Flagged in GAP-ANALYSIS.md as P1 gap. Will be handled as a shared component extracted before effort loop (Step 4B).
- **Source**: Codebase grep for "notification" — only `notifications.py` for internal Slack/email bug alerts, not user-facing.
- **Confidence**: High

## Execution Order Decision - 2026-02-06
- **Decision**: Process PRDs in dependency order:
  1. PRD 00 (Revenue) — P0, no dependencies, unlocks monetization
  2. PRD 07 (Workspace) — P0, foundation for tile display
  3. PRD 01 (Search v2) — P0, remaining scoring/eBay work
  4. PRD 03 (Multi-Channel Sourcing) — mostly done, badge fix
  5. PRD 02 (AI Procurement) — BFF prompt engineering
  6. PRD 04 (Seller Tiles) — depends on 07 + notification system
  7. PRD 05 (Unified Closing) — depends on 00 (revenue)
  8. PRD 06 (Viral Flywheel) — defer to Phase 5
- **Confidence**: High
