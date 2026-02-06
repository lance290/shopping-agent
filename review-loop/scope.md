# Review Scope - phase2-full-implementation (Iteration 3)

## Files to Review

### Backend (modified)
- `apps/backend/main.py` (modified — router registration)
- `apps/backend/models.py` (modified — Merchant, Contract, PurchaseEvent models)
- `apps/backend/routes/outreach.py` (modified — unsubscribe + reminders)
- `apps/backend/routes/quotes.py` (modified — close-handoff endpoint)
- `apps/backend/services/email.py` (modified — reminder email + unsubscribe link fix)

### Backend (added)
- `apps/backend/routes/contracts.py` (added)
- `apps/backend/routes/merchants.py` (added)
- `apps/backend/tests/test_phase2_endpoints.py` (added)

### Frontend (modified)
- `apps/frontend/app/components/OfferTile.tsx` (modified — aria-pressed, count badges)
- `apps/frontend/app/components/RowStrip.tsx` (modified — mergeLikes/mergeComments, share wiring)
- `apps/frontend/app/quote/[token]/page.tsx` (modified — dynamic choice_factors)
- `apps/frontend/app/store.ts` (modified — like_count, comment_count)

### Frontend (added)
- `apps/frontend/app/api/shares/route.ts` (added)
- `apps/frontend/app/api/shares/[token]/route.ts` (added)
- `apps/frontend/app/api/merchants/register/route.ts` (added — pass 1 fix)
- `apps/frontend/app/share/[token]/page.tsx` (added)
- `apps/frontend/app/merchants/register/page.tsx` (added, fixed in pass 1)
- `apps/frontend/app/utils/bff.ts` (added — pass 1 DRY extraction)

## Review Pass 2 Started: 2026-02-06T12:22:00-08:00
