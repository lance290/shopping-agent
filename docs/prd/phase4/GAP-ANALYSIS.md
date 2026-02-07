# Phase 4 PRD Gap Analysis

**Date:** 2026-02-06
**Scope:** All 7 Phase 4 PRDs audited against current codebase
**Focus:** "BuyAnything" intent + "make sure I get paid"

---

## 🚨 CRITICAL: How You Get Paid (Cross-cuts ALL PRDs)

This is the single biggest gap across every PRD. The platform currently has **zero revenue capture mechanisms active**.

### What exists today:
- **Affiliate link handlers** (`affiliate.py`): Amazon Associates, eBay Partner Network, Skimlinks — all coded but **all env vars are empty** (`AMAZON_AFFILIATE_TAG=`, `EBAY_CAMPAIGN_ID=`, `SKIMLINKS_PUBLISHER_ID=`).
- **Clickout tracking** (`routes/clickout.py`): Logs every outbound click with `ClickoutEvent`, but no affiliate tags are being appended.
- **Stripe Checkout** (`routes/checkout.py`): Creates payment sessions, but money goes **directly to the merchant's Stripe account** or is a generic charge — there's no `application_fee_amount`, no Stripe Connect, no platform cut.
- **PurchaseEvent** model: Tracks purchases but has no `platform_fee`, `commission_amount`, or `commission_rate` fields.

### What's missing:
1. **Affiliate tags need to be configured** — immediate money-on-the-table. Just set the env vars.
2. **Stripe Connect for marketplace fees** — required for B2B/B2C transactions where BuyAnything processes payment. Without it, Stripe Checkout collects money but you see none of it.
3. **Commission tracking** — `PurchaseEvent` needs `platform_fee_amount` and `commission_rate` fields.
4. **PRD 05 (Unified Closing Layer)** mentions "affiliate model and/or direct transaction processing" and "transaction fees" but provides zero specifics on the split, Stripe Connect onboarding, or payout mechanics.

### Recommendation:
Add a **PRD 00 — Revenue & Monetization Layer** that covers:
- Stripe Connect onboarding for sellers (so you can take a cut)
- `application_fee_amount` on checkout sessions
- Affiliate tag configuration + monitoring
- Commission model (% per category, flat fee, etc.)
- Payout dashboard for sellers
- Revenue reporting for you

---

## PRD 01 — Search Architecture v2: **75% ALREADY BUILT (PRD is stale)**

### Wrong assumption: "Current system passes a single text query to all providers"

**Reality:** The 5-layer architecture described in the PRD is largely implemented:

| PRD Layer | Status | Current Code |
|-----------|--------|-------------|
| L1: Intent Extraction | ✅ Done | `apps/bff/src/intent/index.ts` — LLM + heuristic fallback |
| L2: Provider Adapters | ⚠️ Partial | `sourcing/adapters/` — Rainforest + Google CSE done, **no eBay** |
| L3: Executors | ✅ Done | `sourcing/executors/base.py` — parallel execution with timeout |
| L4: Normalizers | ✅ Done | `sourcing/repository.py` — per-provider normalization |
| L5: Aggregator | ❌ Missing | No scoring (relevance/price/quality `combined_score`) |
| DB: search_intent column | ✅ Done | `Row.search_intent`, `Row.provider_query_map` |
| DB: Bid metadata | ✅ Done | `canonical_url`, `source_payload`, `normalized_at` |

### What's actually left to build:
1. **eBay adapter + executor** — referenced in PRD but no implementation exists
2. **Result scoring/ranking** — `combined_score`, `relevance_score`, `price_score`, `quality_score` — none computed
3. **Currency normalization** — `NormalizedResult` has `price_original`/`currency_original` fields but they're never populated
4. **Low-confidence behavior** — PRD says "if confidence < 0.6, ask clarification" — not implemented
5. **Phase 6 cleanup** — old `sourcing.py` still present alongside new architecture

### Recommendation:
**Rewrite this PRD** to reflect current state. Rename it "Search Quality Improvements" and scope it to: eBay provider, scoring/ranking, low-confidence disambiguation. Delete the 80% that's already done.

---

## PRD 02 — AI Procurement Agent: Partially built, key UX gap

### What exists:
- Chat interface with LLM (Gemini via BFF)
- Choice-factor extraction via `choice_answers` on Row
- `request_spec` with constraints/preferences
- `extractSearchIntent()` with LLM prompt

### Gaps:
1. **No structured RFP builder flow** — The agent currently asks freeform questions. There's no explicit "I've identified these 3 choice factors for your category, let me ask about each" flow.
2. **No disambiguation step** — PRD says "prioritize Discovery questions before results." Currently, any input immediately triggers search.
3. **No RFP summary/approval** — PRD says "buyer approval of generated RFP summary before vendor outreach." Not implemented.
4. **No choice-factor tracking metrics** — No logging of how many factors identified or questions asked per RFP.

### Recommendation:
This is mostly a **BFF prompt engineering + UX flow** issue, not a backend architecture gap. The data models are ready.

---

## PRD 03 — Multi-Channel Sourcing + Outreach: Mostly built

### What exists:
- `routes/outreach.py` — trigger outreach, track status, vendor response intake
- `services/vendor_discovery.py` — `VendorDiscoveryAdapter` with mock + WattData scaffold
- `SellerQuote` model for vendor responses
- Email outreach via Resend
- Outreach status tracking (sent, delivered, responded)

### Gaps:
1. **No "instant offer" badge distinction** — PRD says "buyer should clearly understand which tiles are instant offers vs. vendor-provided quotes." Frontend shows `is_service_provider` badge but no "instant offer" vs "quote" labeling.
2. **WattData integration blocked** — adapter scaffolded but MCP not live yet.
3. **No outreach volume metrics** — PRD wants "outreach volume per row" and "vendor response rate" tracked. Partially there via AuditLog but no aggregated dashboard.

### Recommendation:
Low-gap PRD. Mostly waiting on WattData MCP. Add the badge distinction to the frontend.

---

## PRD 04 — Seller Tiles + Quote Intake: Significant gaps

### What exists:
- `SellerQuote` + magic link quote submission
- Seller dashboard (inbox, quotes, profile)
- `Merchant` model with auth linkage (just fixed)
- `find_buyers()` on VendorDiscoveryAdapter (returns empty in mock)

### Gaps:
1. **Sellers can't discover buyer needs** — `find_buyers()` returns empty. No RFP discovery feed for sellers. The seller inbox only shows rows where outreach was explicitly triggered for them.
2. **No seller commenting on buyer needs** — `Comment` model exists but is buyer→bid only, not seller→RFP.
3. **No seller bookmarks** — No model or endpoint for sellers to save/bookmark interesting RFPs.
4. **Missing: quote→buyer tile flow** — `SellerQuote` converts to a `Bid` but the buyer experience of seeing "a seller responded to your RFP" isn't polished. No notification system.
5. **No notification system at all** — Seller gets no notification when a matching RFP appears. Buyer gets no notification when a quote arrives. This is a fundamental gap for the marketplace loop.

### Recommendation:
Add notification system (even simple — email + in-app badge). Without it the two-sided marketplace can't function.

---

## PRD 05 — Unified Closing Layer: Scaffold only

### What exists:
- Stripe Checkout for single-bid retail purchase
- `PurchaseEvent` tracking
- `Contract` model (DocuSign scaffold — no API integration)
- `Bid.is_selected` flag

### Gaps:
1. **No multi-vendor checkout** — Can only buy one bid at a time. PRD requires "support closing more than one selected tile in a project."
2. **No closing status per tile** — PRD says "buyer can see whether a selected tile is pending payment/contract/completed." No `closing_status` field on Bid or PurchaseEvent-linked state.
3. **DocuSign is 100% scaffold** — `Contract` model has columns but zero API integration. No envelope creation, no signing URL, no webhook for completion.
4. **No C2C flow** — PRD mentions C2C support but nothing addresses it.
5. **No platform revenue** — See Critical section above.

### Recommendation:
Split into two phases: (a) Fix monetization now (Stripe Connect + affiliate config), (b) DocuSign + multi-vendor later.

---

## PRD 06 — Viral Growth Flywheel: Mostly not built

### What exists:
- `ShareLink` model with `share_token`, click/view counts
- `User.referral_share_token` and `signup_source`
- `ClickoutEvent.share_token` and `referral_user_id`

### Gaps:
1. **No seller-to-buyer conversion prompt** — The key flywheel mechanic ("What do you need to buy?") doesn't exist anywhere.
2. **No referral graph** — No explicit model mapping user → invited users. Attribution is tracked on `User.referral_share_token` but there's no way to query "who did User X bring in?"
3. **No K-factor measurement** — No analytics endpoint or calculation.
4. **No collaborator-to-buyer conversion tracking** — Share links exist but there's no funnel tracking from "viewed shared project" → "signed up" → "created own row."

### Recommendation:
This PRD has the most unbuilt surface area. It's also the most aspirational. Consider deferring to Phase 5 and focusing on the core buy/sell loop first.

---

## PRD 07 — Workspace + Tile Provenance: Substantially built

### What exists:
- Split-pane workspace (chat left, tiles right)
- Projects + Rows + Bids
- `BidWithProvenance` with `matched_features`, `chat_excerpts`, `product_info`
- Likes, Comments, ShareLinks
- Tile detail endpoint

### Gaps:
1. **No collaborator permission levels** — `ShareLink` has no `permission` field (view-only vs can-comment vs can-select). Anyone with the link gets the same access.
2. **Row-level likes/comments missing** — `Like` and `Comment` models have `row_id` but the PRD expects likes/comments on rows themselves (not just bids within rows). The frontend only shows bid-level social.
3. **No tile detail panel in frontend** — `BidWithProvenance` endpoint exists in backend but no frontend panel renders it. Users can't click a tile and see "why this was recommended."

### Recommendation:
Small gaps. Add `permission` to ShareLink, add row-level social UI, build the tile detail panel.

---

## Summary: Priority Order

| Priority | Gap | Impact | Effort |
|----------|-----|--------|--------|
| **P0** | **Revenue capture (affiliate config + Stripe Connect)** | You're not getting paid | Medium |
| **P1** | Notification system (email + in-app) | Marketplace loop broken without it | Medium |
| **P1** | Tile detail panel (frontend) | Core UX missing — users can't see why tiles match | Small |
| **P2** | Search scoring/ranking | Results are unranked — quality perception | Medium |
| **P2** | Seller RFP discovery feed | Sellers can't find buyers proactively | Medium |
| **P2** | Closing status visibility | Buyers can't track purchase state | Small |
| **P3** | eBay provider | Expands sourcing coverage | Medium |
| **P3** | DocuSign integration | B2B closing | Large |
| **P3** | Collaborator permissions | Share link access control | Small |
| **P4** | Viral flywheel mechanics | Growth — defer until core loop works | Large |
| **P4** | Multi-vendor checkout | Edge case until more transactions | Medium |

---

## Wrong Assumptions in PRDs

1. **PRD 01 assumes search architecture v2 doesn't exist** — 75% is built. PRD needs rewrite.
2. **PRD 05 assumes Stripe processes marketplace payments** — it doesn't. Stripe Checkout sends money to the merchant, not you. Need Stripe Connect.
3. **PRD 04 assumes sellers can discover buyer needs** — they can't. The seller inbox only shows explicitly-outreached rows.
4. **PRD 06 assumes a notification system exists** — it doesn't. The flywheel can't spin without notifications.
5. **PRD 03 assumes "instant offers" are labeled** — they aren't. No badge distinction between search results and vendor quotes.
6. **All PRDs reference `.cfoi/branches/main/product-north-star.md`** — this file may or may not exist and may be stale.
