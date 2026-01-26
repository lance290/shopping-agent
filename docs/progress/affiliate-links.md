# Affiliate Links — Progress

## Goal
Make affiliate clickout links “proper” for the majors (Amazon, eBay, Skimlinks) per `docs/PRD-buyanything.md`, with correct attribution parameters, reliable click logging, and test coverage.

## Done Definition
- Amazon clickout URLs include affiliate tag and are routed via `/api/clickout`.
- eBay clickout URLs follow EPN tracking link format (per eBay docs) and are routed via `/api/clickout`.
- Skimlinks is available as a universal fallback when configured.
- Frontend never links directly to merchant URLs (always uses clickout).
- Clickouts are logged server-side (`ClickoutEvent`) with `merchant_domain`, `handler_name`, and `affiliate_tag`.
- Unit tests cover Amazon + eBay + Skimlinks handlers and resolver behavior.
- Required env vars are documented in `apps/backend/.env.example`.

## Current State
- [x] Backend `/api/out` resolves affiliate links and logs clickouts.
- [x] Frontend `/api/clickout` proxies redirect safely.
- [x] Server returns `click_url` in search results.
- [x] Row-scoped search adds `row_id` into `click_url` for attribution.
- [x] Amazon handler exists.
- [x] eBay handler updated to EPN tracking link format.
- [x] Skimlinks handler exists and is tested.

## Remaining / Follow-ups
- [ ] Configure production env vars:
  - `AMAZON_AFFILIATE_TAG`
  - `EBAY_CAMPAIGN_ID`
  - `EBAY_ROTATION_ID` (required)
  - `SKIMLINKS_PUBLISHER_ID`
- [ ] Verify eBay rotation ID for target marketplace(s) and set appropriately.
- [ ] Manually validate end-to-end clickouts in a deployed environment:
  - Confirm redirects work
  - Confirm `ClickoutEvent` rows are written
  - Confirm affiliate attribution in network dashboards (where possible)

## References
- eBay EPN tracking link format: https://developer.ebay.com/api-docs/buy/static/ref-epn-link.html
