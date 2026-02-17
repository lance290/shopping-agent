# Decisions Log - feature-demo-day-public-surface

> Why we chose X over Y. Reference this when questions arise later.

## Decisions

### 2026-02-17: Route groups over flat structure
- **Context**: Frontend has flat page structure under `app/`
- **Decision**: Use Next.js route groups `(public)` / `(workspace)` for layout separation
- **Alternatives**: Keep flat + conditional layout rendering per page
- **Rationale**: Clean layout separation, shared root layout, each group gets its own header/footer

### 2026-02-17: New `/api/public/search` endpoint vs modifying existing
- **Context**: Existing `/api/search` and `/rows/{row_id}/search` require auth + row_id
- **Decision**: Create new public search endpoint
- **Alternatives**: Make existing endpoints optionally anonymous
- **Rationale**: Cleaner separation; public endpoint has no persistence, no row_id; avoids breaking workspace search

### 2026-02-17: Middleware inversion (protected-path list)
- **Context**: Current middleware whitelists public paths (growing list)
- **Decision**: Flip to short protected-path list (`/admin`, `/seller`, `/merchants`, `/bugs`)
- **Alternatives**: Keep adding to `PUBLIC_PATHS` array
- **Rationale**: Short list that rarely changes; every new public page works automatically

### 2026-02-17: "Request Quote" not "Request Introduction"
- **Context**: PRDs introduced "Request Introduction" terminology
- **Decision**: Keep "Request Quote" everywhere — matches existing codebase
- **Alternatives**: Use "Request Introduction" on public surface
- **Rationale**: Don't invent new terminology. Codebase uses "Request Quote" in OfferTile and VendorContactModal.

### 2026-02-17: Adapt VendorContactModal for public (no LeadCaptureModal)
- **Context**: VendorContactModal requires rowId; considered building new LeadCaptureModal
- **Decision**: Adapt existing VendorContactModal to work from search context (query + vendor type)
- **Alternatives**: New LeadCaptureModal with email capture form
- **Rationale**: Existing modal opens mailto: link (no login needed). LLM generates per-vendor-type templates. Reuses existing pattern.

### 2026-02-17: Vendor directory tier_fit fix (0.3 → 0.85 for commodity)
- **Context**: `_tier_relevance_score()` penalizes vendor_directory to 0.3 for commodity/considered queries
- **Decision**: Change to 0.85 — vendors span all tiers (toy stores, bicycle shops, bookstores)
- **Alternatives**: Keep 0.3 (wrong), remove tier_fit entirely (loses the Amazon-for-service penalty)
- **Rationale**: Vector search similarity handles vendor relevance. tier_fit should only penalize big-box APIs for service/bespoke queries.

### 2026-02-17: QuoteIntentEvent for anonymous tracking
- **Context**: Want to document leads from "Request Quote" without capturing PII
- **Decision**: New `QuoteIntentEvent` table logged via `POST /api/public/quote-intent`
- **Alternatives**: Frontend-only analytics, ClickoutEvent reuse
- **Rationale**: Backend event gives durable data for vendor sales conversations ("47 qualified leads this quarter")
