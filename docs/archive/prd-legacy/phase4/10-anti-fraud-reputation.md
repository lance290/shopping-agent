# PRD: Anti-Fraud & Reputation System

**Status:** Partial — non-compliant (baseline controls only)  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P2  
**Origin:** `PRD-buyanything.md` Section 8.1 (deferred from MVP as "Phase 2+")

---

## Problem Statement

As a two-sided marketplace, BuyAnything.ai is exposed to fraud and trust risks from both buyers and sellers:

- **Fake merchants** registering to harvest buyer RFP data or phish
- **Spam bids/quotes** from sellers with no real inventory or capability
- **Fake reviews/likes** inflating seller credibility
- **Clickout fraud** — bots generating affiliate clicks to game commissions
- **Buyer abuse** — filing false disputes or abusing refund policies

The platform currently has **baseline protections only** (e.g., clickout rate limiting). The `Merchant.status` field supports `pending`/`verified` but verification is manual with no criteria. There is **no reputation scoring, no fraud flags, and no trust signals** exposed to buyers or sellers.

**Current state (incomplete):**
- Clickout requests are rate-limited, but no suspicious flags or IP/user-agent tracking.
- Merchant verification is a single `status` field without levels or criteria.

---

## Requirements

### R1: Merchant Verification Pipeline (P1)

Establish a structured verification flow for registered merchants.

**Verification levels:**
| Level | Badge | Criteria |
|-------|-------|----------|
| `pending` | None | Just registered |
| `email_verified` | ✉️ | Confirmed email via verification link |
| `business_verified` | ✅ | Manual review: website exists, business license, or Stripe Connect completed |
| `trusted` | ⭐ | 5+ successful transactions, no disputes, 90d+ account age |

**Acceptance criteria:**
- [ ] Email verification sent on merchant registration (link with token)
- [ ] `Merchant.verification_level` field replaces binary `status`
- [ ] Admin can manually promote/demote verification level
- [ ] Frontend shows appropriate badge on seller bids/quotes

### R2: Seller Reputation Score (P2)

Compute a reputation score based on seller behavior.

**Inputs:**
- Response rate to RFPs (% of outreach responded to)
- Average response time
- Quote-to-acceptance rate (buyer selected their bid)
- Transaction completion rate
- Dispute/complaint count

**Score:** 0-100, displayed as stars (e.g., 80+ = 5 stars, 60-79 = 4 stars)

**Acceptance criteria:**
- [ ] Score computed nightly via background job or on-demand
- [ ] Stored on `Merchant.reputation_score`
- [ ] Visible to buyers on seller bids
- [ ] Sellers can see their own score on dashboard

### R3: Clickout Fraud Detection (P2)

Detect and flag suspicious clickout patterns.

**Signals:**
- High clickout volume from single IP/user in short window
- Clickouts with no preceding search or tile view
- Bot-like user agents
- Geographic anomalies (user claims US, clicks from offshore proxy)

**Acceptance criteria:**
- [ ] Rate limiting on `/api/out` endpoint (max 30 clickouts/min per user)
- [ ] `ClickoutEvent.is_suspicious` flag
- [ ] Suspicious clickouts excluded from affiliate commission estimates
- [ ] Admin alert when anomalous pattern detected

### R4: Bid/Quote Quality Signals (P3)

Flag low-quality or spammy seller bids.

**Signals:**
- Bid price dramatically below market (possible bait-and-switch)
- Seller has no website or unresolvable domain
- Bid description is generic/templated (no specifics matching the RFP)
- Multiple identical bids across different rows

**Acceptance criteria:**
- [ ] `Bid.quality_score` field (0-100)
- [ ] Low-quality bids deprioritized in tile ordering
- [ ] Admin can review flagged bids

### R5: Buyer Trust Score (P3)

Lightweight trust signal for buyers (primarily for seller-side visibility).

**Inputs:**
- Account age
- Email verified
- Has completed at least 1 transaction
- No disputes filed

**Acceptance criteria:**
- [ ] `User.trust_level` field: `new`, `verified`, `established`
- [ ] Visible to sellers when viewing RFPs
- [ ] Sellers can filter RFP feed by buyer trust level

---

## Technical Implementation

### Backend

**Models to modify:**
- `Merchant` — Add `verification_level`, `reputation_score`, `verified_at`
- `Bid` — Add `quality_score`
- `User` — Add `trust_level`
- `ClickoutEvent` — Add `is_suspicious`, `ip_address`, `user_agent`

**New files:**
- `apps/backend/services/reputation.py` — Score computation logic
- `apps/backend/services/fraud_detection.py` — Clickout fraud rules

**Endpoints:**
- `POST /merchants/{id}/verify-email` — Email verification callback
- `GET /admin/fraud/alerts` — Suspicious activity feed

### Frontend
- Badge components for verification levels
- Reputation stars on seller bids
- Admin fraud alerts page

---

## Dependencies

- `prd-merchant-registry.md` — Merchant model must exist (✅ done)
- `04-seller-tiles-quote-intake.md` — Quote intake must exist for bid quality scoring
- `00-revenue-monetization.md` — Affiliate fraud detection only matters once affiliates are active

---

## Effort Estimate

- **R1:** Medium (1-2 days — email verification + admin controls)
- **R2:** Medium (1-2 days — score computation + display)
- **R3:** Small (rate limiting + flag field)
- **R4-R5:** Medium (2-3 days total)
