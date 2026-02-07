# Review Scope - Phase 4 Build-All

## Files to Review (code only)

### Backend (Python) - 9 files
- `apps/backend/routes/auth.py` (modified) - Referral token capture in verify
- `apps/backend/routes/admin.py` (modified) - Growth metrics endpoint
- `apps/backend/routes/seller.py` (modified) - Buyer prompt + notification
- `apps/backend/routes/notifications.py` (added) - Notification CRUD
- `apps/backend/routes/checkout.py` (modified) - closing_status in webhook
- `apps/backend/models.py` (modified) - Notification, closing_status, ShareLink.permission
- `apps/backend/main.py` (modified) - Registered notifications router
- `apps/backend/alembic/versions/a1b2c3d4e5f6_add_revenue_tracking_fields.py` (modified) - Migration
- `apps/backend/sourcing/normalizers/__init__.py` (modified) - eBay normalizer registration

### BFF (TypeScript) - 1 file
- `apps/bff/src/llm.ts` (modified) - Enhanced decision prompt

### Frontend (TypeScript/React) - 8 files
- `apps/frontend/app/share/[token]/page.tsx` (modified) - Store share token
- `apps/frontend/app/utils/auth.ts` (modified) - Pass referral_token
- `apps/frontend/app/api/admin/growth/route.ts` (added) - Proxy
- `apps/frontend/app/api/notifications/route.ts` (added) - Proxy
- `apps/frontend/app/api/notifications/count/route.ts` (added) - Proxy
- `apps/frontend/app/components/Chat.tsx` (modified) - Sell link
- `apps/frontend/app/components/Board.tsx` (modified) - Become a Seller button
- `apps/frontend/app/page.tsx` (modified) - Mobile Sell tab

## Out of Scope (unchanged, pre-existing)
- `apps/backend/affiliate.py`
- `apps/backend/routes/clickout.py`
- `apps/backend/routes/merchants.py`
- `apps/backend/sourcing/scorer.py`
- `apps/backend/sourcing/adapters/ebay.py`
- `apps/backend/sourcing/normalizers/ebay.py`

## Review Started: 2026-02-06T19:10:00-08:00
