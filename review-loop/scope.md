# Review Scope - Phase 3 Build-All

## Code Files to Review

### Backend - New
- `apps/backend/routes/checkout.py` (added)
- `apps/backend/routes/seller.py` (added)
- `apps/backend/services/vendor_discovery.py` (added)
- `apps/backend/tests/test_phase3_endpoints.py` (added)

### Backend - Modified
- `apps/backend/main.py` (modified — 2 imports + 2 includes)
- `apps/backend/routes/admin.py` (modified — stats endpoint)
- `apps/backend/routes/bids.py` (modified — batch endpoint)
- `apps/backend/sourcing/service.py` (modified — provenance enrichment)
- `apps/backend/tests/test_provenance_pipeline.py` (modified — updated assertion)
- `apps/backend/pyproject.toml` (modified — stripe dep)
- `apps/backend/.env.example` (modified — new env vars)

### Frontend - New
- `apps/frontend/app/admin/page.tsx` (added)
- `apps/frontend/app/seller/page.tsx` (added)
- `apps/frontend/app/api/checkout/route.ts` (added)
- `apps/frontend/app/api/seller/inbox/route.ts` (added)
- `apps/frontend/app/api/seller/profile/route.ts` (added)
- `apps/frontend/app/api/seller/quotes/route.ts` (added)
- `apps/frontend/app/api/admin/stats/route.ts` (added)
- `apps/frontend/app/api/bids/social/batch/route.ts` (added)

### Frontend - Modified
- `apps/frontend/app/components/OfferTile.tsx` (modified — Buy Now button)
- `apps/frontend/app/globals.css` (modified — safe-area, scrollbar)
- `apps/frontend/app/page.tsx` (modified — mobile layout)

## Out of Scope
- `docs/prd/phase3/*` — PRD documents
- `.cfoi/branches/dev/build-all/*` — process artifacts
- `apps/backend/uv.lock`, `apps/frontend/tsconfig.tsbuildinfo` — auto-generated

## Review Started: 2026-02-06T13:23:00-08:00
