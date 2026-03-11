# PRD: BuyAnything Admin Analytics Dashboard for Annie

## 1. Executive Summary

BuyAnything needs an internal analytics dashboard that lets operators understand how Annie is performing across search, recommendation, merchant quality, and monetization.

This dashboard is not a consumer-facing feature. It is an admin-only operating surface for answering questions like:

1. How many searches are happening today, this week, and this month?
2. Are users clicking Annie's recommendations?
3. Are users selecting quotes and completing transactions?
4. Which merchants are performing best?
5. How much money is BuyAnything actually making right now?

For launch, the dashboard should be built around the metrics we can define cleanly and defend operationally:

- Search volume
- Click-through rate
- Selected quotes
- Completed transactions
- Active users
- Affiliate revenue
- Tip jar revenue

This PRD deliberately does **not** make GMV a primary KPI for v1. GMV may be shown later once transaction attribution is reliable across affiliate clickouts, Stripe-based flows, and quote-based deals.

---

## 2. Product Decisions Locked By This PRD

### 2.1 Manual refresh is sufficient for v1
This dashboard does not need websockets or live streaming.

- Admin can reload the page to refresh data.
- Optional auto-refresh every 30-60 seconds is acceptable.
- No socket infrastructure is required.

### 2.2 Revenue in v1 means real platform revenue only
At launch, BuyAnything revenue should be defined as:

- Affiliate revenue
- Tip jar revenue

It must **not** imply platform fees, because BuyAnything is currently a zero-fee product.

### 2.3 Conversion must be split by funnel stage
A single generic "conversion rate" is too ambiguous.

The dashboard should separately report:

- Search -> clickout CTR
- Search -> selected quote rate
- Search -> completed transaction rate

### 2.4 GMV is secondary and explicitly incomplete at launch
GMV is useful, but only if it is trustworthy.

For v1:
- GMV is **not** a top-line KPI.
- If shown at all, it must be labeled clearly as an attributed or partial value.
- Completed transaction counts are more important than speculative GMV.

### 2.5 Email-derived completion signals are allowed, but must be labeled
BuyAnything may infer some completed transactions from the email/deal pipeline.

If completion is detected from email content or deal-state transitions:
- the metric must be labeled as tracked completion or email-confirmed completion
- it must not silently mix with hard purchase confirmations if confidence differs materially

### 2.6 Admin-only access
This dashboard is internal.

- Only authenticated admins should be able to access it.
- No public exposure.

---

## 3. Current Problems

### 3.1 Annie performance is hard to measure end-to-end
We can observe pieces of the funnel today, but there is no single place to answer:
- how much Annie is being used
- whether recommendations are actually working
- whether merchants are converting
- whether the business is making money

### 3.2 Monetization visibility is fragmented
Affiliate revenue, tip jar revenue, and transaction outcomes live in different systems or event flows.

### 3.3 Search quality is not operationally visible
Without dashboards, it is hard to quickly spot:
- rising empty-result rates
- search quality regressions
- merchant/source underperformance
- recommendation quality drift

### 3.4 Merchant performance is anecdotal instead of measurable
Operators need to know which merchants:
- convert well
- get selected often
- appear price-competitive
- complete orders reliably

---

## 4. Desired Launch Behavior

### 4.1 Overview page
An admin opens the dashboard and immediately sees:
- searches today / week / month
- active users
- click-through rate
- selected quote count and rate
- completed transaction count and rate
- affiliate revenue
- tip jar revenue

### 4.2 Search analytics page
An admin can evaluate search system health and usage patterns, including:
- search volume over time
- top searched categories
- average results returned per query
- failed or empty search rate

### 4.3 Merchant performance page
An admin can rank merchants by practical outcomes, including:
- click-through rate
- quote selection rate
- completed transaction rate
- average price competitiveness score
- fulfillment or completion signals where available

### 4.4 Recommendation quality page
An admin can measure whether Annie's ranking is helping users, including:
- CTR on top-ranked recommendations
- percent of sessions where the #1 recommendation was selected
- percent of sessions where the eventual winner came from Annie's top 3
- A/B performance if recommendation experiments exist

### 4.5 Reliable monetization page
An admin can view platform revenue without ambiguity:
- affiliate revenue over time
- tip jar revenue over time
- completed transactions count
- optional attributed transaction value if trustworthy

---

## 5. Scope

### In scope
- Admin-only analytics dashboard
- Express.js backend API for analytics endpoints
- PostgreSQL-backed analytics schema and migrations
- Seed data with realistic mock records
- Responsive frontend using Recharts or Chart.js
- Manual reload-based freshness
- Search, recommendation, merchant, and monetization reporting

### Out of scope
- Realtime socket streaming
- User-facing analytics
- Advanced cohort analysis
- Full finance-grade attribution
- Predictive analytics
- Fraud analytics in v1
- Declaring GMV as a canonical launch KPI

---

## 6. Core Metrics Definitions

### 6.1 Searches
A search is a single Annie query attempt recorded in the `searches` table.

Each search should capture:
- user or session identity
- raw query text
- normalized category if available
- timestamp
- result count
- success vs empty vs failed outcome
- latency

### 6.2 Search -> Clickout CTR
CTR is:

`searches with at least one clicked result / total searches`

Secondary CTR views may include:
- result-level CTR
- CTR by merchant
- CTR by category
- CTR by source

### 6.3 Search -> Selected Quote Rate
Selected quote rate is:

`searches that led to a selected quote or chosen offer / total searches`

This metric should include both:
- direct product/offer selections
- quote/deal selections where the user or EA explicitly chose an option

### 6.4 Search -> Completed Transaction Rate
Completed transaction rate is:

`searches that led to a tracked completed transaction / total searches`

For v1, tracked completed transactions may include:
- explicit purchase records
- affiliate-attributed completed purchases
- Stripe-confirmed tips or payments where applicable
- email-confirmed deal completions when the system has sufficient evidence

If multiple completion-confidence levels exist, the UI should expose them clearly.

### 6.5 Active Users
Active users should be shown as:
- DAU
- WAU
- MAU

A user counts as active if they perform at least one meaningful action in the period, such as:
- search
- click result
- select quote
- complete purchase
- send tip

### 6.6 Affiliate Revenue
Affiliate revenue is the amount actually earned from affiliate conversions that have been attributed back to BuyAnything.

This must be based on real recorded revenue events, not estimated percentages.

### 6.7 Tip Jar Revenue
Tip jar revenue is the amount actually received through the tip flow.

If Stripe is the source of truth, the dashboard should ingest settled tip events from Stripe-backed records.

### 6.8 Price Competitiveness Score
Price competitiveness should be derived from the score assigned to a merchant's result relative to comparable results in the same query.

This metric is directional, not absolute. The UI should avoid implying perfect market coverage.

### 6.9 Recommendation Quality Metrics
Required recommendation metrics:
- top-pick CTR
- `% of searches where Annie's #1 recommendation was clicked`
- `% of searches where Annie's #1 recommendation was selected`
- `% of searches where final selected item was in Annie's top 3`

If experiment variants exist, add:
- variant A vs B CTR
- variant A vs B selection rate
- variant A vs B completion rate

---

## 7. User Experience and Pages

### 7.1 Global dashboard behavior
All pages should support:
- date-range filter
- optional category filter
- optional merchant filter
- optional source filter
- responsive desktop/tablet layout
- clean loading and empty states

### 7.2 Overview
Primary KPI cards:
- Searches today
- Searches this week
- Searches this month
- Active users
- Click-through rate
- Selected quotes
- Completed transactions
- Affiliate revenue
- Tip jar revenue

Primary charts:
- Searches over time
- Revenue over time
- Conversion funnel summary

Supporting tables:
- top merchants
- top categories
- top sources

### 7.3 Search Analytics
Charts and tables:
- search volume over time (line chart)
- top searched categories (bar chart)
- average results returned per query
- empty result rate
- failed search rate
- latency distribution or average latency
- top zero-result queries

### 7.4 Merchant Performance
Ranked merchant table with:
- merchant name
- impressions
- clicks
- CTR
- selections
- selection rate
- completions
- completion rate
- average price competitiveness score
- average results position

If fulfillment timing exists, show:
- average fulfillment speed rating

If it does not exist, do not fabricate it.

### 7.5 Recommendation Quality
Charts and tables:
- CTR on Annie's top recommendation
- top-pick selection rate
- top-3 capture rate
- selected-rank distribution
- comparison by category
- optional A/B comparison if experiments exist

### 7.6 Revenue and Transactions
Charts and tables:
- affiliate revenue over time
- tip jar revenue over time
- completed transaction count over time
- average revenue per active user
- average revenue per search
- attributed transaction value if available and clearly labeled

---

## 8. Data Model Requirements

## 8.1 Required tables
This feature requires migrations for the following tables:

- `users`
- `merchants`
- `searches`
- `search_results`
- `recommendations`
- `purchases`

If the application already has equivalent tables, the implementation may extend existing tables rather than duplicating them. The product requirement is the logical schema and metric availability.

### 8.2 `users`
Minimum fields:
- `id`
- `email` or user identifier
- `created_at`
- `last_active_at`
- `is_admin`

### 8.3 `merchants`
Minimum fields:
- `id`
- `name`
- `category`
- `created_at`
- `status`
- `fulfillment_speed_rating` nullable

### 8.4 `searches`
Minimum fields:
- `id`
- `user_id` nullable for anonymous traffic
- `session_id` nullable
- `query`
- `normalized_category` nullable
- `created_at`
- `results_count`
- `status` (`success`, `empty`, `failed`)
- `latency_ms`

### 8.5 `search_results`
One row per result shown for a search.

Minimum fields:
- `id`
- `search_id`
- `merchant_id` nullable
- `position`
- `title`
- `price` nullable
- `source`
- `price_competitiveness_score` nullable
- `clicked_at` nullable
- `selected_at` nullable

### 8.6 `recommendations`
This table records Annie's ranking layer.

Minimum fields:
- `id`
- `search_id`
- `search_result_id`
- `recommended_rank`
- `is_top_pick`
- `model_version` nullable
- `experiment_variant` nullable
- `clicked` boolean
- `selected` boolean
- `completed` boolean

### 8.7 `purchases`
This table records monetization and completion events.

Minimum fields:
- `id`
- `user_id` nullable
- `search_id` nullable
- `merchant_id` nullable
- `purchase_type` (`affiliate`, `tip`, `direct`, `quote_completion`, `email_confirmed_completion`)
- `gross_amount` nullable
- `platform_revenue_amount` nullable
- `currency`
- `status`
- `external_reference` nullable
- `completed_at`

### 8.8 Recommended indexing
Add indexes for:
- `searches.created_at`
- `searches.user_id`
- `search_results.search_id`
- `search_results.merchant_id`
- `recommendations.search_id`
- `purchases.completed_at`
- `purchases.purchase_type`
- `purchases.search_id`
- `purchases.merchant_id`

---

## 9. Backend Requirements

### 9.1 Preferred backend stack
- Express.js
- PostgreSQL
- SQL migration system
- background job support for backfills and aggregate refreshes

### 9.2 Analytics endpoints
The backend should provide admin analytics endpoints such as:

- `GET /admin/analytics/overview`
- `GET /admin/analytics/search`
- `GET /admin/analytics/merchants`
- `GET /admin/analytics/recommendations`
- `GET /admin/analytics/revenue`

Each endpoint should support a date range and relevant filters.

### 9.3 Aggregation strategy
For v1, simple SQL queries are acceptable if performance is good.

If queries become expensive, the implementation may add:
- summary tables
- materialized views
- scheduled aggregate refresh jobs

### 9.4 Revenue ingestion
The backend should support ingesting:
- affiliate revenue events
- tip jar payment events from Stripe or equivalent payment source
- explicit purchase confirmations
- email-confirmed completion events where available

### 9.5 Admin authorization
All analytics routes must require admin authorization.

---

## 10. Frontend Requirements

### 10.1 Preferred frontend behavior
- clean admin UI
- responsive layout
- fast page loads
- readable KPI cards and tables
- export-friendly tables later if needed

### 10.2 Charting library
Preferred charting approach:
- Recharts for v1

Chart.js is acceptable if the implementation team prefers it, but the UX should remain clean and responsive.

### 10.3 Core UI components
Required UI building blocks:
- KPI cards
- line charts
- bar charts
- ranked data tables
- date-range picker
- filters
- empty states
- loading skeletons
- last updated timestamp

### 10.4 Refresh behavior
- Manual reload must work cleanly.
- Optional refresh button is recommended.
- Optional polling is acceptable.
- No websocket dependency.

---

## 11. Seed Data Requirements

The feature should include realistic mock seed data so the dashboard is immediately demoable.

Seed data should include:
- users with realistic activity patterns
- diverse search queries across categories
- searches with successful, empty, and failed outcomes
- search results from multiple merchants
- recommendation ranks and outcomes
- purchases across affiliate, tip, and quote-completion flows
- multiple merchants with varied performance

Seed distributions should feel realistic enough to make charts useful:
- some merchants should overperform
- some queries should fail or return zero results
- some categories should be clearly more popular than others
- Annie's #1 recommendation should be good but not perfect

---

## 12. Acceptance Criteria

### AC-1 Overview visibility
An admin can open the dashboard and see:
- searches today, week, month
- active users
- click-through rate
- selected quotes
- completed transactions
- affiliate revenue
- tip jar revenue

### AC-2 Search analytics visibility
An admin can inspect:
- search volume over time
- top searched categories
- average results returned
- empty search rate
- failed search rate

### AC-3 Merchant ranking visibility
An admin can view a ranked merchant table with:
- conversion-related performance
- price competitiveness
- selection/completion signals

### AC-4 Recommendation quality visibility
An admin can measure:
- CTR on Annie's top picks
- percent of cases where the #1 recommendation was selected
- top-3 capture rate

### AC-5 Revenue clarity
Revenue is clearly separated into:
- affiliate revenue
- tip jar revenue

The dashboard must not imply platform fees are being charged.

### AC-6 Honest transaction reporting
Completed transactions derived from different evidence levels are labeled appropriately.

### AC-7 Demo readiness
The seeded development environment renders meaningful charts and ranked tables without requiring live production traffic.

---

## 13. Open Questions

1. Should email-confirmed completions appear in the same widget as hard purchase confirmations, or in a separate sub-metric?
2. Do we want to show attributed transaction value before we have trustworthy GMV coverage?
3. Can Stripe be the canonical source for tip jar revenue, or do we need an internal revenue mirror table?
4. Should anonymous traffic count toward active users, or only authenticated users?
5. Do we want a separate "data coverage" or "tracking confidence" panel in v1?

---

## 14. Suggested Implementation Order

1. Finalize metric definitions and labels
2. Create migrations for the six logical tables
3. Add realistic seed data
4. Build backend analytics endpoints
5. Build Overview page
6. Build Search Analytics page
7. Build Merchant Performance page
8. Build Recommendation Quality page
9. Build Revenue and Transactions page
10. Validate numbers against known affiliate/tip data sources
