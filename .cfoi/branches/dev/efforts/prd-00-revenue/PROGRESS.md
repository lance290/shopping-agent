# PRD 00 — Revenue & Monetization: PROGRESS

## Status: Complete (2026-02-06)

## Tasks Completed
1. **Model changes** — Added `platform_fee_amount`, `commission_rate`, `revenue_type` to `PurchaseEvent`. Added `stripe_account_id`, `stripe_onboarding_complete`, `default_commission_rate` to `Merchant`.
2. **Migration** — `a1b2c3d4e5f6_add_revenue_tracking_fields.py`
3. **Stripe Connect checkout** — `checkout.py` now looks up merchant's connected account, adds `application_fee_amount` and `stripe_account` params, records platform fee on PurchaseEvent.
4. **Stripe Connect onboarding** — `merchants.py` — `POST /merchants/connect/onboard` + `GET /merchants/connect/status`
5. **Admin revenue endpoint** — `GET /admin/revenue` — breakdown by stream, clickout stats, Stripe Connect status.
6. **Admin stats** — Added `revenue.platform_total` and `clickouts.with_affiliate_tag` to existing stats endpoint.
7. **Frontend proxies** — `/api/admin/revenue`, `/api/merchants/connect/onboard`, `/api/merchants/connect/status`

## Files Changed
- `apps/backend/models.py` — PurchaseEvent + Merchant extensions
- `apps/backend/alembic/versions/a1b2c3d4e5f6_add_revenue_tracking_fields.py` — NEW
- `apps/backend/routes/checkout.py` — Stripe Connect support + fee tracking
- `apps/backend/routes/admin.py` — Revenue endpoint + stats extension
- `apps/backend/routes/merchants.py` — Stripe Connect onboarding endpoints
- `apps/frontend/app/api/admin/revenue/route.ts` — NEW
- `apps/frontend/app/api/merchants/connect/onboard/route.ts` — NEW
- `apps/frontend/app/api/merchants/connect/status/route.ts` — NEW

## Remaining (deferred)
- Affiliate tag env var configuration (user action — sign up for affiliate programs)
- Frontend admin revenue dashboard UI component
- Frontend seller dashboard Stripe Connect button
