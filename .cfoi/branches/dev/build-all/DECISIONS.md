# Build-All Decisions Log — Phase 3

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
