# PRD L5: Analytics & Observability

**Priority:** P1 — Pre-launch
**Target:** Week 1 (Feb 10–14, 2026)
**Depends on:** Custom domain (D1)

---

## Problem

There is no production analytics, error tracking, or uptime monitoring. When things break in production, we don't know. When users convert (or don't), we can't measure it. We can't run ads without conversion tracking.

---

## Solution

### R1 — Product Analytics (Day 1)

Install **PostHog** (recommended — open source, generous free tier, event-based) or Google Analytics 4.

Track these events:

| Event | Properties | Why |
|-------|-----------|-----|
| `page_view` | path, referrer, device | Basic traffic |
| `search_submitted` | query, category | Core action |
| `tiles_loaded` | count, row_id | Result quality signal |
| `tile_clicked` | bid_id, source, position | Engagement |
| `vendor_contacted` | vendor_name, category | Marketplace action |
| `quote_received` | row_id, vendor_id | Supply response |
| `deal_selected` | bid_id, price | Conversion |
| `checkout_completed` | amount, category | Revenue |
| `share_created` | type (link/social) | Virality |
| `signup_completed` | source, referral_token | Growth |

### R2 — Error Tracking (Day 1)

Install **Sentry** for both frontend and backend:

- Frontend: `@sentry/nextjs` — catches React errors, unhandled promises
- Backend: `sentry-sdk[fastapi]` — catches Python exceptions, slow transactions
- BFF: `@sentry/node` — catches Express errors

Configure:
- Environment tags: `production`, `staging`
- Release tracking (tied to git SHA)
- Alert rules: P0 errors → Slack/email notification within 5 minutes

### R3 — Uptime Monitoring (Day 2)

Set up **BetterStack** (or UptimeRobot, free tier):

| Endpoint | Check Interval | Alert |
|----------|---------------|-------|
| `https://buyanything.ai/` | 1 min | Slack + SMS |
| `https://api.buyanything.ai/health` | 1 min | Slack + SMS |
| `https://bff.buyanything.ai/health` (if exposed) | 5 min | Slack |

### R4 — Conversion Funnel Dashboard (Day 3)

In PostHog (or custom admin), define funnels:

1. **Buyer funnel:** Landing → Sign up → First search → Tile click → Deal select → Purchase
2. **Seller funnel:** Register → Verify → First quote → Deal won
3. **Viral funnel:** Share created → Link clicked → Sign up → First search

### R5 — Ad Conversion Tracking (Day 3)

- Google Ads conversion pixel on sign-up + purchase
- Meta Pixel on sign-up + purchase
- UTM parameter capture on landing page → store in user record

---

## Acceptance Criteria

- [ ] PostHog (or GA4) tracking on all pages
- [ ] Core events firing (search, click, contact, purchase)
- [ ] Sentry capturing errors in frontend + backend
- [ ] Uptime monitor alerting on downtime
- [ ] At least one funnel visualized in analytics dashboard
- [ ] Ad conversion pixels ready before ad spend begins
