# Coupon/Swap Sourcing: Research Findings & Architecture Decision

**Date:** March 2026  
**Status:** Scaffolding built, awaiting BD direction from Tim  
**Author:** Engineering (AI-assisted)

---

## 1. Background

The original PRDs reference **GroFlo** as the coupon/MCP integration for Pop's swap engine. After research, GroFlo is not viable as an API integration. This document summarizes the findings and the architecture we built to move forward.

---

## 2. GroFlo Assessment

**What GroFlo actually is:**
- A small receipt-upload rebate platform targeting emerging CPG brands
- Brands create campaigns, customers upload receipts, GroFlo validates and pays via PayPal/Venmo
- Pricing: $99–$399/month or $0.50/redemption on free tier
- **No API, no MCP, no programmatic access** — coupon links are manually created and take 48 hours to activate
- Contact: `jada@groflo.io`

**Verdict:** GroFlo is a manual, small-scale receipt-rebate tool — not a coupon database we can query programmatically. It cannot serve as our swap sourcing engine.

---

## 3. External API Research

### Tier A: Real APIs (hard to access)

| Platform | API? | Access | Fit |
|----------|------|--------|-----|
| **Ibotta Performance Network (IPN)** | REST API, `GET /v2/offers` | Enterprise partnership only, white-glove onboarding | **Best fit.** 2,600+ CPG offers. Requires BD relationship + volume commitments. |
| **Kroger Developer API** | Products API (catalog, locations) | Free developer signup | **No coupon endpoint.** Good for product enrichment only. |
| **Neptune Retail Solutions** (was Inmar) | No public API | Enterprise B2B only | **Not accessible** to startups. |
| **Quotient Technology** (was Coupons.com) | Acquired/defunct | N/A | **Dead end.** |

### Tier B: Affiliate Coupon APIs (wrong domain)

| Platform | What It Is | Fit |
|----------|-----------|-----|
| **CouponAPI.org** | E-commerce promo code aggregator | **No** — online discount codes, not grocery rebates |
| **Coupomated** | Same — affiliate e-commerce coupons | **No** |
| **Strackr Deals API** | Affiliate network deal feeds | **No** |

### Tier C: Consumer apps (no API)

Fetch Rewards, Checkout 51, Flipp — consumer-only, no programmatic integration available.

---

## 4. Recommendation for Tim

**Three realistic paths forward:**

### Path A: Ibotta Partnership (Best long-term)
- Reach out to IPN team for enterprise partnership
- They have exactly what we need: 2,600+ CPG offers, REST API, category/retailer filtering
- **Blocker:** Requires volume commitments and BD relationship
- **Action:** Tim/Jeremy schedule a call with Ibotta's partnerships team

### Path B: Manual Seeding + Brand Outreach (Immediate)
- Admin manually uploads swap offers via CSV or API (scaffolding already built)
- Tim/Jeremy negotiate deals with CPG brands directly (the WattData approach)
- Start with 10-20 high-value swaps in common categories (milk, eggs, cereal, etc.)
- **Pro:** Can start immediately, no external dependency
- **Con:** Doesn't scale without volume

### Path C: Hybrid (Recommended)
- Start with Path B (manual seeding) to get the product live and prove demand
- Pursue Path A (Ibotta) in parallel for long-term scale
- The architecture supports both — just plug in a new provider

---

## 5. What Was Built

### New files:

| File | Purpose |
|------|---------|
| `models/coupons.py` | `PopSwap` + `PopSwapClaim` DB models |
| `services/coupon_provider.py` | `CouponProvider` ABC + `ManualProvider`, `HomeBrewProvider`, `IbottaProvider` (stub), `AggregateProvider` |
| `routes/pop_swaps.py` | Admin CRUD API + CSV import + search endpoint |
| `alembic/versions/s11_pop_swap_tables.py` | DB migration for new tables |
| `tests/test_pop_swaps.py` | 17 tests (all passing) |

### Architecture:

```
┌─────────────┐     ┌──────────────────┐
│ Pop Chat/NLU │────▶│  CouponProvider  │ (abstract interface)
│ "add milk"   │     │  .search_swaps() │
└─────────────┘     │  .record_claim() │
                    │  .verify_receipt()│
                    └──────┬───────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Manual   │ │ HomeBrew │ │ Ibotta   │
        │ Provider │ │ Provider │ │ Provider │
        │ (CSV/API)│ │(brand    │ │(stub —   │
        │          │ │ portal)  │ │ future)  │
        └──────────┘ └──────────┘ └──────────┘
```

### API Endpoints (all under `/pop/`):

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/pop/admin/swaps` | Create a swap offer |
| `GET` | `/pop/admin/swaps` | List swaps (filters: active_only, provider, category) |
| `PATCH` | `/pop/admin/swaps/{id}` | Update a swap offer |
| `DELETE` | `/pop/admin/swaps/{id}` | Soft-deactivate a swap |
| `POST` | `/pop/admin/swaps/import-csv` | Bulk import from CSV |
| `POST` | `/pop/swaps/search` | Search swaps (uses AggregateProvider) |

### CSV Import Format:

```csv
category,swap_product_name,savings_cents,target_product,brand_name,offer_description
steak sauce,Heinz 57 Sauce,250,A1 Steak Sauce,Heinz,Save $2.50 on Heinz 57
milk,Fairlife 2% Milk,150,Store Brand Milk,Fairlife,$1.50 off Fairlife
eggs,Happy Egg Co Free Range,100,Store Brand Eggs,Happy Egg Co,$1 rebate on Happy Egg
```

### Bug Fixes (pre-existing, fixed along the way):

- `services/llm.py`: Added missing `generate_outreach_email()` function
- `services/llm.py`: Added `make_pop_decision` alias for `make_unified_decision`
- `routes/pop_processor.py` + `routes/pop_chat.py`: Fixed `_save_factors_scoped` → `_save_choice_factors` (correct function name + signature)

---

## 6. What NOT to Build Yet

- **Receipt OCR validation** — complex, defer until there are actual swaps to validate
- **Payment rails for rebates** — use Stripe Connect when ready, don't build plumbing yet
- **Brand self-serve portal UI** — the API is ready, frontend can come when brands sign up
- **Ibotta integration** — stub is ready, activate when partnership is secured

---

## 7. Next Steps

1. **Tim decision:** Which path (A, B, C) to pursue?
2. If Path B/C: Tim/Jeremy identify 10-20 initial swap deals to seed via CSV
3. Wire `AggregateProvider.search_swaps()` into `pop_list.py` to show swap offers alongside regular bids
4. Build frontend UI for swap offers on the Pop list view
