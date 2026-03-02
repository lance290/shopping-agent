# Affiliate Links — Progress

## Goal
Make affiliate clickout links “proper” for the majors (Amazon, eBay, Skimlinks) per `docs/PRD-buyanything.md`, with correct attribution parameters, reliable click logging, and test coverage.

Additionally, define what’s required for **distribution/referral attribution** (who referred a user) so that revenue (affiliate commissions) can be shared with referrers.

## Done Definition
- Amazon clickout URLs include affiliate tag and are routed via `/api/clickout`.
- eBay clickout URLs follow EPN tracking link format (per eBay docs) and are routed via `/api/clickout`.
- Skimlinks is available as a universal fallback when configured.
- Frontend never links directly to merchant URLs (always uses clickout).
- Clickouts are logged server-side (`ClickoutEvent`) with `merchant_domain`, `handler_name`, and `affiliate_tag`.
- Unit tests cover Amazon + eBay + Skimlinks handlers and resolver behavior.
- Required env vars are documented in `apps/backend/.env.example`.

Referral/distribution attribution done definition (future):
- Every inbound request can optionally carry a referral code (`ref`) and/or UTM parameters.
- The system persists a “first touch” (and optionally more touches) for the user.
- A referrer can be credited for downstream commerce activity.
- Reporting can answer:
  - Signups by referrer
  - Clickouts by referrer
  - (Future) commissions and payouts by referrer

## Current State
- [x] Backend `/api/out` resolves affiliate links and logs clickouts.
- [x] Frontend `/api/clickout` proxies redirect safely.
- [x] Server returns `click_url` in search results.
- [x] Row-scoped search adds `row_id` into `click_url` for attribution.
- [x] Amazon handler exists.
- [x] eBay handler updated to EPN tracking link format.
- [x] Skimlinks handler exists and is tested.

## What Exists Today (Merchant Affiliate Tracking)

### Summary
This repo already implements **merchant affiliate tracking** (click -> redirect -> affiliate-tagged link) and logs outbound clicks.

### Components
- **Backend clickout endpoint**: `apps/backend/routes/clickout.py`
  - `GET /api/out?url=...&row_id=...&idx=...&source=...`
  - Validates URL, resolves affiliate link, logs, then 302 redirects.
- **Affiliate handler registry**: `apps/backend/affiliate.py`
  - `LinkResolver` selects handler based on `merchant_domain`.
  - Handlers:
    - Amazon Associates: adds `tag=...`
    - eBay EPN: adds EPN parameters, supports a `customid`
    - Skimlinks: optional universal fallback when configured
- **Clickout event model**: `apps/backend/models.py`
  - `ClickoutEvent` logs:
    - who clicked: `user_id`, `session_id`
    - what: `row_id`, `offer_index`
    - urls: `canonical_url`, `final_url`, `merchant_domain`
    - affiliate: `handler_name`, `affiliate_tag`
    - provenance: `source`
- **Tests**: `apps/backend/tests/test_affiliate.py`

### Current merchant affiliate data flow
1) UI shows offers.
2) Offer click goes to a clickout URL (should ultimately land on backend `/api/out`).
3) Backend resolves the outbound URL via `LinkResolver`.
4) Backend logs `ClickoutEvent` asynchronously.
5) Backend issues `302` redirect to the final URL.

### Merchant affiliate configuration
Handlers read their config from environment variables:
- `AMAZON_AFFILIATE_TAG`
- `EBAY_CAMPAIGN_ID`
- `EBAY_ROTATION_ID`
- (Optional) `SKIMLINKS_PUBLISHER_ID`

If env vars are missing, handlers intentionally fall back to “no rewrite” behavior.

## What’s Missing (Distribution / Referral Attribution)

### Summary
Distribution/referral attribution is *not* the same as merchant affiliate tracking.

- **Merchant affiliate tracking** answers: “Did *we* earn commission from the merchant?”
- **Referral/distribution attribution** answers: “Which person/channel caused this user to arrive, sign up, and transact?”

The conversation goal is: “Make sure all pages you render have affiliate tracking so you can track who caused each user to come on, so when they transact the folks who helped with distribution get paid.”

That requires an additional attribution layer.

## Proposed Architecture (Add Referral Attribution Layer)

### Key design choice: identify the referrer
Support both, but start minimal:

1) **User-to-user referrals** (creator/referral programs)
   - A referrer is an existing `User`.
2) **Partner/channel referrals** (newsletter/influencer/ads)
   - A referrer is a `Partner` entity.

Implementation strategy:
- Phase 1: user-to-user (`ref=<code>` maps to a user)
- Phase 2: partners (`ref=<code>` maps to a partner)

### Referral identifiers (share links)
Recommended pattern:
- Use a stable code rather than a raw integer id:
  - `https://app.yourdomain.com/?ref=<referral_code>`
- Still allow UTMs:
  - `utm_source`, `utm_campaign`, `utm_medium`, etc.

### Capture points
You need capture at two moments:

1) **Landing capture** (anonymous)
   - If an incoming request includes `ref` and/or UTMs, persist it to a cookie.

2) **Identity binding** (when a user becomes known)
   - On signup/login/session creation, read that cookie and bind it to the newly-known user.

### Where it fits in the repo
- **Frontend** (Next.js): capture `ref`/UTM on first request
  - store in cookie (HttpOnly is preferable if set by server)
  - keep TTL (e.g. 30 days)

- **Backend**: bind referral to user/session
  - when issuing/confirming auth session, or a dedicated endpoint like `/api/attribution/bind`

- **Backend clickout**: optionally include referrer info
  - either denormalize into `ClickoutEvent` OR join through `user_id`

## Proposed Data Model (Minimal)

These are conceptual schema suggestions (do not implement yet).

### Option A: minimal “first touch only”
- **User** gains columns:
  - `referred_by_user_id` (nullable)
  - `referred_by_partner_id` (nullable)
  - `referred_at` (nullable)
  - `referral_code` (unique, for sharing)

Pros:
- Simple.
- Easy to query.

Cons:
- Hard to represent multiple touches.

### Option B: event-style attribution touches (recommended long-term)
- New table: `AttributionTouch`
  - `id`
  - `user_id` (nullable until bound, or store against a session cookie id)
  - `anonymous_id` (cookie-generated UUID)
  - `referral_code` (nullable)
  - `referrer_user_id` (nullable)
  - `partner_id` (nullable)
  - `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content` (nullable)
  - `landing_path`
  - `created_at`

Pros:
- Supports multi-touch.
- Great for analytics.

Cons:
- More work.

### ClickoutEvent integration
Two approaches:

1) **Join-only**
   - Keep `ClickoutEvent` unchanged.
   - Report: join `ClickoutEvent.user_id -> User.referred_by_*`.

2) **Denormalize**
   - Add `referrer_user_id` / `partner_id` onto `ClickoutEvent` at log time.
   - Improves robustness if referral info changes later.

## Proposed Request Flows

### Flow 1: user shares link
1) Referrer is a known user with `referral_code`.
2) They share: `/?ref=<referral_code>`.

### Flow 2: recipient lands anonymously
1) Frontend sees `ref` and UTMs.
2) Frontend writes cookie:
   - `sa_ref=<referral_code>`
   - `sa_utm_source=...` etc (or a single JSON cookie)
   - `sa_attrib_set_at=<timestamp>`

### Flow 3: recipient becomes a known user
1) On signup/login/session creation:
   - frontend sends attribution cookie values to backend
   - backend resolves `referral_code` -> `referrer_user_id` OR `partner_id`
   - backend writes first-touch attribution to `User` or creates `AttributionTouch`
2) Backend clears attribution cookie or keeps it (depending on policy).

### Flow 4: recipient clicks a merchant offer
1) UI calls `/api/out?...` as usual.
2) Backend logs `ClickoutEvent`.
3) Reporting can now group clickouts by the referrer of the clicking user.

## Reporting (What We Should Be Able To Answer)

### Phase 1 (no conversion ingestion yet)
- Signups by referrer
- Daily/weekly active users by referrer
- Clickouts by referrer
- Clickouts by merchant/domain by referrer

### Phase 2 (conversion + commission ingestion)
- Estimated commission by referrer
- Approved vs pending vs reversed commissions
- Payouts owed/paid by referrer

## Future: Revenue Ingestion + Payout Ledger

### Conversion ingestion
Affiliate networks vary:
- Some support webhooks for conversions.
- Many require periodic report ingestion (CSV/API).

You’ll eventually need to store:
- `network` (amazon/ebay/skimlinks/etc)
- `network_click_id` / `sub_id` / `customid` (if available)
- `order_id`
- `amount`, `commission_amount`, `currency`
- `status` (pending/approved/reversed)
- `occurred_at`

### Matching conversions back to users/referrers
Matching options (best to worst):
1) network supports a per-click identifier that you can set in the outgoing link (like eBay `customid`).
2) network provides a click reference that you can map from your redirect logs.
3) probabilistic matching (weak; avoid).

Practical note:
- Today, eBay handler supports `customid` generation. This is a strong foundation for reconciliation.

### Payout ledger
Minimum viable accounting tables:
- `CommissionEvent` (per conversion)
- `Payout` (per referrer per time window)
- `PayoutLineItem` (links payout to commission events)

### Split rules
Define a deterministic policy:
- Company keeps `X%`, referrer gets `Y%` of the commission.
- Consider caps, minimum thresholds, clawbacks on refunds.

## Security / Abuse Considerations
- Don’t allow self-referral (same user as referrer).
- Don’t allow referral overwrite after the first successful bind (unless explicitly designed).
- Prefer server-set HttpOnly cookies for attribution to reduce tampering.
- Log attribution binds for auditability.

## Naming
Internally, treat these as two layers:
- **Affiliate link rewriting** (merchant/network)
- **Referral attribution** (distribution/referrer)

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

Referral/distribution attribution follow-ups (design + implementation later):
- [ ] Decide referral identity model:
  - user-to-user only, partner/channel only, or both
- [ ] Decide attribution policy:
  - first touch only vs multi-touch
  - TTL (e.g. 30/90 days)
- [ ] Add landing capture (cookie) in frontend.
- [ ] Add binding step in backend auth/session flow.
- [ ] Add reporting queries/endpoints.
- [ ] Define conversion ingestion strategy per network.
- [ ] Define payout ledger and split rules.

## References
- eBay EPN tracking link format: https://developer.ebay.com/api-docs/buy/static/ref-epn-link.html
