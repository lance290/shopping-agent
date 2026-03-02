# PRD: Priority Matching Waterfall

**Status:** Not built  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P2  
**Origin:** `Competitive_Analysis_PartFinder.md` — "Priority matching waterfall: 1. Registered merchants → 2. WattData outreach → 3. Amazon/Serp"

---

## Problem Statement

The competitive analysis describes a three-tier priority system for sourcing results, positioning registered merchants as the highest-value source. Currently, all sourcing channels (marketplace APIs, WattData, registered merchants) are treated equally with no priority ordering. This means:

- Registered merchants who paid to be on the platform get no advantage over anonymous Amazon listings
- The platform has no incentive structure for merchants to register
- The "two-sided marketplace" positioning falls apart without seller-side value

**Current state:** `SourcingService.search_and_persist()` fans out to all providers in parallel and merges results by score. No priority given to registered merchants or outreach responses.

---

## Requirements

### R1: Define Waterfall Tiers (P1)

Establish a clear priority ordering for sourcing results.

**Tier ordering:**
1. **Registered merchants** (highest priority) — Bids/quotes from merchants in the Merchant Registry matching the buyer's category and service area
2. **Outreach responses** — Quotes from vendors discovered via WattData who responded to outreach
3. **Marketplace results** — Product listings from Amazon, Google Shopping, eBay, etc.

**Acceptance criteria:**
- [ ] Tier assignment stored on each `Bid` (e.g., `Bid.source_tier`: `registered`, `outreach`, `marketplace`)
- [ ] Tier visible in tile detail panel (PRD 01)
- [ ] Registered merchant tiles have a distinguishing badge ("Verified Partner")

### R2: Score Boost by Tier (P1)

Apply a score modifier based on source tier.

**Boost values:**
- Registered merchants: +20% on `combined_score`
- Outreach responses: +10% on `combined_score`
- Marketplace results: no boost (baseline)

**Acceptance criteria:**
- [ ] Boost applied in `sourcing/scorer.py` or `services/ranking.py`
- [ ] Boost values configurable (not hardcoded)
- [ ] Boost reflected in score breakdown (tile detail panel)

### R3: Instant RFP Notification for Registered Merchants (P2)

When a buyer creates a row matching a registered merchant's category, notify the merchant immediately.

**Flow:**
1. Buyer creates row with category (e.g., "HVAC repair")
2. System queries `Merchant` table for merchants with matching `categories` and `service_areas`
3. Matching merchants receive notification (Phase 5 PRD 00)
4. Merchant can submit a quote via their dashboard

**Acceptance criteria:**
- [ ] Category matching logic handles JSON array of categories
- [ ] Geographic matching via `service_areas` (state, zip, or "nationwide")
- [ ] Notification sent within 1 minute of row creation
- [ ] Only notified if merchant has available lead credits (Phase 5 PRD 04) or is on subscription

### R4: Waterfall Display in UI (P2)

Buyer sees clear labeling of where each tile came from.

**Badges:**
- "Verified Partner" — registered merchant
- "Vendor Quote" — outreach response
- "Marketplace" — API search result (no badge, default)

**Acceptance criteria:**
- [ ] Badge visible on each tile
- [ ] Badge included in tile detail panel provenance section
- [ ] Buyer understands the difference between sources

---

## Technical Implementation

### Backend

**Modified models:**
- `Bid` — Add `source_tier` field: `registered`, `outreach`, `marketplace`

**Modified files:**
- `apps/backend/sourcing/scorer.py` — Apply tier-based score boost
- `apps/backend/sourcing/service.py` — Assign `source_tier` during result persistence
- `apps/backend/routes/rows.py` — Trigger merchant matching on row creation

**New files:**
- `apps/backend/services/merchant_matcher.py` — Category + geography matching logic

### Frontend
- Badge component for source tier on `OfferTile.tsx`
- Tier label in tile detail panel

---

## Dependencies

- Phase 4 PRD 03 (multi-channel sourcing) — Outreach system must exist
- Phase 4 PRD 04 (seller tiles) — Quote intake must exist
- Phase 4 PRD 11 (personalized ranking) — Score boost integrates with scoring engine
- Phase 5 PRD 00 (notifications) — Merchant RFP notifications
- Phase 5 PRD 04 (lead fees) — Credit check before notification

---

## Effort Estimate

- **R1:** Small (half-day — tier field + assignment logic)
- **R2:** Small (half-day — score boost in scorer)
- **R3:** Medium (1-2 days — matching logic + notification trigger)
- **R4:** Small (half-day — badges in UI)
