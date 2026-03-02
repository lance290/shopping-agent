# PRD: Analytics & Success Metrics System

**Status:** Partial — non-compliant (missing original success metrics)  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P1  
**Origin:** `PRD-buyanything.md` Section 13 ("Success Metrics")

---

## Problem Statement

The original PRD defined five core success metrics. The platform has **some admin stats and revenue endpoints**, but the **original success metrics are not computed**. Without these metrics, there is no way to measure product-market fit, optimize conversion, or report revenue to stakeholders.

**Current state (incomplete):**
- Admin stats + revenue endpoints exist but only cover high-level counts and GMV.
- Raw event data exists (clickouts, purchases, rows, bids, outreach) but no computation of time-to-first-result, CTR, clickout success, affiliate coverage, or revenue per active user.

---

## Metrics from Original PRD

| # | Metric | Original Section | Current State |
|---|--------|------------------|---------------|
| M1 | Time to first usable options per row | Section 13 | Timestamps exist on Row + Bid but not computed |
| M2 | Offer click-through rate (CTR) | Section 13 | `ClickoutEvent` logged but no CTR calculation |
| M3 | Clickout success rate (no broken redirects) | Section 13 | Not tracked — no validation of redirect targets |
| M4 | Affiliate handler coverage (% routed vs default) | Section 13 | `handler_name` logged on ClickoutEvent but not aggregated |
| M5 | Revenue per active user | Section 13 | `PurchaseEvent` exists but no revenue fields; affiliate revenue not tracked |

---

## Requirements

### R1: Backend Metrics Computation (P0)

Add a `/admin/metrics` endpoint that computes and returns:

```json
{
  "period": "last_7d",
  "rows_created": 142,
  "avg_time_to_first_result_seconds": 4.2,
  "total_clickouts": 891,
  "offer_ctr": 0.12,
  "clickout_success_rate": 0.97,
  "affiliate_coverage": {
    "amazon": 0.42,
    "ebay": 0.18,
    "skimlinks": 0.05,
    "none": 0.35
  },
  "estimated_revenue": {
    "affiliate_commissions": 45.20,
    "stripe_platform_fees": 0.00
  },
  "active_users_7d": 38,
  "revenue_per_active_user": 1.19
}
```

**Acceptance criteria:**
- [ ] Endpoint requires admin auth
- [ ] Supports `period` query param: `last_24h`, `last_7d`, `last_30d`, `all_time`
- [ ] Computes all 5 original metrics
- [ ] Response time < 2s for `last_7d`

### R2: Time-to-First-Result Tracking (P0)

Track the elapsed time between row creation and first bid/result appearing.

**Implementation:**
- `Row.created_at` already exists
- Need: first `Bid.created_at` for each row
- Compute: `first_bid.created_at - row.created_at` per row, then average

**Acceptance criteria:**
- [ ] Metric computed in `/admin/metrics`
- [ ] Handles rows with no results (excluded from average)

### R3: Clickout Success Tracking (P1)

Detect broken redirects (404s, timeouts, DNS failures) on affiliate clickouts.

**Implementation options:**
- **Option A (simple):** Log `redirect_status_code` on `ClickoutEvent` — backend HEAD-checks the final URL before redirecting
- **Option B (accurate):** Client-side beacon — after redirect, a pixel/ping confirms the merchant page loaded

**Acceptance criteria:**
- [ ] Failed redirects are tracked (broken URL, timeout, non-200)
- [ ] Success rate aggregated in `/admin/metrics`

### R4: Revenue Tracking Fields (P1)

Extend `PurchaseEvent` model with revenue fields.

**New fields:**
- `platform_fee_amount: Optional[float]` — Stripe Connect application fee
- `commission_rate: Optional[float]` — Affiliate commission percentage
- `estimated_commission: Optional[float]` — Computed affiliate revenue
- `revenue_confirmed: bool = False` — True when affiliate network confirms conversion

**Acceptance criteria:**
- [ ] Fields added via Alembic migration
- [ ] Populated on Stripe Checkout completion (platform fee)
- [ ] Populated on affiliate clickout (estimated commission based on handler rates)

### R5: Admin Dashboard UI (P2)

Surface metrics in the existing admin panel.

**Acceptance criteria:**
- [ ] Dashboard page at `/admin/metrics`
- [ ] Shows all 5 metrics with period selector
- [ ] Charts for: clickouts over time, revenue over time, CTR trend
- [ ] Auto-refreshes every 60s

### R6: Funnel Tracking (P2)

Track the full user funnel: `visit → row_created → search → clickout → purchase`.

**Acceptance criteria:**
- [ ] Each stage count available in `/admin/metrics`
- [ ] Drop-off rates between stages computed
- [ ] Filterable by time period

### R7: Expanded Success Metrics (P2)

The expanded PRD defines additional success metrics beyond the original 5:

| # | Metric | Source | Current State |
|---|--------|--------|---------------|
| M6 | NPS 70+ for multi-category projects | Expanded PRD | Not tracked — no NPS survey mechanism |
| M7 | Time from intent to Select reduced 50% vs baseline | Expanded PRD | Row + Bid timestamps exist but no baseline or comparison |
| M8 | Viral coefficient (K-factor) ≥ 1.2 | Expanded PRD | ShareLink + referral fields exist but no K-factor computation |
| M9 | Monthly GMV growth rate (target 20%) | Expanded PRD | PurchaseEvent.amount exists but no month-over-month calculation |
| M10 | Seller-to-buyer conversion rate | Expanded PRD + Competitive Analysis | No tracking of merchants who also create buyer rows |

**Acceptance criteria:**
- [ ] K-factor computed: `(invites per user) × (conversion rate of invites)` from ShareLink + User.referral_share_token
- [ ] GMV growth rate computed month-over-month in `/admin/metrics`
- [ ] Seller-to-buyer conversion tracked: merchants who also have buyer rows
- [ ] Intent-to-close funnel tracked (Mixpanel or equivalent event pipeline)
- [ ] NPS survey mechanism deferred to Phase 5+ but metric placeholder defined

---

## Technical Implementation

### Backend

**Files to modify/create:**
- `apps/backend/routes/admin.py` — Add `/admin/metrics` endpoint
- `apps/backend/models.py` — Extend `PurchaseEvent` with revenue fields
- `alembic/versions/` — Migration for new PurchaseEvent columns

**Query patterns:**
```python
# M1: Avg time to first result
SELECT AVG(first_bid.created_at - row.created_at)
FROM row
JOIN LATERAL (
  SELECT created_at FROM bid WHERE bid.row_id = row.id ORDER BY created_at LIMIT 1
) first_bid ON true
WHERE row.created_at >= :period_start;

# M2: Offer CTR
SELECT COUNT(DISTINCT clickout.id)::float / NULLIF(COUNT(DISTINCT bid.id), 0)
FROM bid LEFT JOIN clickoutevent clickout ON ...;

# M4: Affiliate coverage
SELECT handler_name, COUNT(*) FROM clickoutevent
WHERE created_at >= :period_start GROUP BY handler_name;
```

### Frontend
- `apps/frontend/app/admin/metrics/page.tsx` — New page (P2)

---

## Success Metrics (Meta)

- All 5 original PRD metrics computable within 1 deploy
- Admin can view metrics without SQL access
- Revenue tracking enables monthly investor reporting

---

## Dependencies

- `00-revenue-monetization.md` — Revenue fields meaningless until affiliate tags + Stripe Connect configured
- `08-affiliate-disclosure-ui.md` — Disclosure required before ramping affiliate traffic

---

## Effort Estimate

- **R1-R2:** Medium (1-2 days — queries + endpoint)
- **R3:** Small (half-day)
- **R4:** Small (migration + model changes)
- **R5-R6:** Medium (1-2 days — frontend dashboard)
