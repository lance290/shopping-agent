# BuyAnything.ai — Launch Plan

**Created:** 2026-02-07
**Status:** ACTIVE
**JetBid Demo:** 🔴 LIVE TODAY (Feb 7, 2026)
**Marketplace Beta:** Target Feb 28, 2026
**Public Launch:** Target March 31, 2026

---

## Table of Contents

1. [Today: JetBid Demo Go-Live](#1-today-jetbid-demo-go-live)
2. [Business Setup Checklist](#2-business-setup-checklist)
3. [Gap Analysis — What's Missing](#3-gap-analysis--whats-missing)
4. [Missing PRDs](#4-missing-prds)
5. [Launch Phases & Timeline](#5-launch-phases--timeline)
6. [Supply-Side Strategy](#6-supply-side-strategy-tims-network)
7. [Demand-Side Strategy](#7-demand-side-strategy-ad-budget)
8. [Success Metrics](#8-success-metrics)
9. [Risk Register](#9-risk-register)

---

## 1. Today: JetBid Demo Go-Live

**Deadline: Feb 7, 2026 EOD**
**Stakeholder:** Tim Connors (tconnors@gmail.com)
**URL:** https://frontend-dev-aca4.up.railway.app

### 1.1 Must-Ship Fixes (JetBid PRD R1–R11)

| # | Fix | Est | Status |
|---|-----|-----|--------|
| R1 | Widen VendorContactModal → `max-w-2xl`, textarea `rows={14}`, scrollable body | 15m | ⬜ |
| R2 | Add notes textarea `rows={3}` below email body | 10m | ⬜ |
| R3 | Fix "Wheels Up" time extraction — add fallback keys | 15m | ⬜ |
| R4 | Round-trip / multi-leg support in modal (category-agnostic) | 30m | ⬜ |
| R5 | Passenger names display in modal | 15m | ⬜ |
| R6 | Reply-to email = buyer email (not platform) | 10m | ⬜ |
| R7 | Add Brett Driscoll to vendor list | 5m | ⬜ |
| R8 | Remove "not a charter provider" caveat from Business Jet Advisors | 5m | ⬜ |
| R9 | Constraint-factor name alignment (B1 fix) | 30m | ⬜ |
| R10 | Email body template: include both legs, passengers, Wi-Fi, reply-to | 20m | ⬜ |
| R11 | `mailto:` fallback with clipboard copy for long bodies | 15m | ⬜ |

**Total: ~2.5 hours of engineering**

### 1.2 Demo Test Plan (Before Handing to Tim)

1. ✅ Search "private jet charter BNA to FWA" → 11+ vendor tiles appear
2. ✅ Choice factors auto-fill with itinerary details
3. ✅ Click vendor tile → VendorContactModal opens at readable size
4. ✅ Both legs visible in email body
5. ✅ Passenger names listed
6. ✅ Wheels-up times correct per leg
7. ✅ Reply-to shows tconnors@gmail.com
8. ✅ Copy-to-clipboard works for long email bodies
9. ✅ All 12 vendors contactable (including Brett Driscoll)
10. ✅ Test on mobile (Tim may use his phone)

### 1.3 Deploy Checklist

- [ ] All R1–R11 fixes committed
- [ ] `git push origin dev`
- [ ] Railway auto-deploy succeeds
- [ ] Smoke test on https://frontend-dev-aca4.up.railway.app
- [ ] Text Tim the link + brief instructions

---

## 2. Business Setup Checklist

These are non-engineering tasks that must happen before or alongside the technical build.

### 2.1 Legal & Corporate

| # | Task | Why | Status | Deadline |
|---|------|-----|--------|----------|
| B1 | **Incorporate entity** (LLC or C-Corp) | Required for Stripe, contracts, liability protection | ⬜ | Week 1 |
| B2 | **Get EIN** from IRS | Required for business bank account and Stripe | ⬜ | Week 1 |
| B3 | **Open business bank account** | Stripe payouts, ad spend, vendor payments | ⬜ | Week 2 |
| B4 | **Terms of Service** draft | Legal requirement before processing transactions | ⬜ | Week 2 |
| B5 | **Privacy Policy** draft | Required by Stripe, GDPR, CCPA | ⬜ | Week 2 |
| B6 | **Marketplace facilitator agreement** template | For sellers/vendors joining the platform | ⬜ | Week 3 |

### 2.2 Domain & Branding

| # | Task | Why | Status | Deadline |
|---|------|-----|--------|----------|
| D1 | **Register domain** (buyanything.ai or similar) | Brand identity, email, SEO | ⬜ | Week 1 |
| D2 | **Set up custom email** (hello@buyanything.ai) | Outreach emails need a real domain, not gmail | ⬜ | Week 1 |
| D3 | **SSL certificate** for custom domain | Trust signal + browser requirement | ⬜ | Week 1 |
| D4 | **Point domain to Railway** (or migrate to Vercel/Fly) | Ditch the `.up.railway.app` URL | ⬜ | Week 1 |
| D5 | **Logo & favicon** | Polish — investors and customers notice | ⬜ | Week 2 |

### 2.3 Stripe Setup

| # | Task | Why | Status | Deadline |
|---|------|-----|--------|----------|
| S1 | **Activate Stripe account** (business entity required) | Payment processing | ⬜ | Week 1 |
| S2 | **Enable Stripe Connect** (Standard or Express) | Take platform fees on seller transactions | ⬜ | Week 2 |
| S3 | **Set `application_fee_amount`** on checkout sessions | Revenue capture — currently $0 | ⬜ | Week 2 |
| S4 | **Configure webhook endpoints** in Stripe dashboard | Payment confirmations, dispute alerts | ⬜ | Week 2 |
| S5 | **Set commission rates by category** | Business model definition (e.g., 5% services, 3% products) | ⬜ | Week 2 |
| S6 | **Test mode → Live mode** cutover plan | Don't ship test keys to production | ⬜ | Week 3 |

### 2.4 Affiliate Program Keys

| # | Task | Revenue Potential | Status | Deadline |
|---|------|-------------------|--------|----------|
| A1 | **Amazon Associates** — get tag, set `AMAZON_AFFILIATE_TAG` env var | 1–10% per product sale | ⬜ | Week 1 |
| A2 | **eBay Partner Network** — get campaign ID, set `EBAY_CAMPAIGN_ID` | 1–4% per sale | ⬜ | Week 1 |
| A3 | **Skimlinks** — get publisher ID, set `SKIMLINKS_PUBLISHER_ID` | Catch-all for 48K+ merchants | ⬜ | Week 1 |
| A4 | **CJ Affiliate / ShareASale** — apply for high-value programs | Access to premium merchant programs | ⬜ | Week 2 |
| A5 | **Set env vars in Railway** production environment | Env vars are currently empty strings | ⬜ | Same day as above |

> **NOTE:** Affiliate tags are literally env vars away from revenue. Code is already written in `apps/backend/affiliate.py`. Setting A1–A3 + A5 could take 30 minutes and immediately start generating revenue on every clickout.

### 2.5 Email & Communications

| # | Task | Why | Status | Deadline |
|---|------|-----|--------|----------|
| E1 | **Resend API key** (or SendGrid) | Platform needs to actually send emails, not just `mailto:` | ⬜ | Week 1 |
| E2 | **Verify custom domain in Resend/SendGrid** | Deliverability — emails from `railway.app` go to spam | ⬜ | Week 1 |
| E3 | **Transactional email templates** (quote request, notification, welcome) | Professional outreach on behalf of buyers | ⬜ | Week 2 |
| E4 | **Unsubscribe mechanism** | CAN-SPAM compliance | ⬜ | Week 2 |

### 2.6 Analytics & Monitoring

| # | Task | Why | Status | Deadline |
|---|------|-----|--------|----------|
| M1 | **Google Analytics 4** or **PostHog** | Track user behavior, conversion funnels | ⬜ | Week 1 |
| M2 | **Sentry** (frontend + backend) | Error tracking in production | ⬜ | Week 1 |
| M3 | **Uptime monitoring** (BetterStack, Pingdom) | Know when Railway goes down | ⬜ | Week 2 |

---

## 3. Gap Analysis — What's Missing

### 3.1 Priority Matrix

| Priority | Gap | Impact | Effort | Target |
|----------|-----|--------|--------|--------|
| **P0** | **Revenue capture** (affiliate tags + Stripe Connect fees) | You're not getting paid. Period. | S | **Week 1** |
| **P0** | **Real email send** (Resend/SendGrid — not `mailto:`) | Marketplace loop is broken. Can't track outreach. | M | **Week 1** |
| **P0** | **JetBid demo fixes** (R1–R11) | Live customer waiting. Demo today. | S | **TODAY** |
| **P1** | **Tile detail panel** (frontend) | Users can't see WHY results match. Magic moment missing. | S | **Week 2** |
| **P1** | **Notification system** (email + in-app) | Sellers don't know RFPs exist. Buyers don't know quotes arrived. | M | **Week 2** |
| **P1** | **Mobile responsive** | >65% marketplace traffic is mobile. No mobile = no virality. | M | **Week 3** |
| **P1** | **Landing page** | Cold traffic has no idea what to do. Share links land in raw workspace. | S | **Week 3** |
| **P2** | **Trust infrastructure** (help center + seller verification) | High-value transactions require dispute resolution. | M | **Week 4** |
| **P2** | **Search scoring/ranking** | Results are unranked — quality perception problem. | M | **Week 4** |
| **P2** | **Seller RFP discovery feed** | Sellers can't find buyers proactively. | M | **Week 4** |
| **P2** | **Closing status visibility** | Buyers can't track purchase state after selecting a deal. | S | **Week 4** |
| **P3** | **Viral triggers** (referral rewards, social artifacts, rich share cards) | K-factor > 1.2 requires working viral loops, not just data models. | M | **Week 5** |
| **P3** | **Single-player mode** (procurement tracker without sellers) | Solves chicken-and-egg. Standalone value for buyers. | L | **Week 6** |
| **P3** | **SEO landing pages** (auto-generated from completed projects) | Organic demand aggregation without ad spend. | M | **Month 2** |
| **P3** | **Personalization flywheel** (UserSignal → search ranking) | Data moat. Every interaction makes the agent smarter. | L | **Month 2** |
| **P4** | **Image/visual search** | Mobile killer feature. "Photo → find this." | L | **Month 3** |
| **P4** | **AI negotiation** | Unique differentiator. AI counter-offers on buyer's behalf. | L | **Q2** |

### 3.2 Known Bugs Blocking Launch

| Bug | Location | Impact | Status |
|-----|----------|--------|--------|
| `search_merchants()` filters `status=="verified"` but no merchant reaches that status | `routes/merchants.py` | Merchant Registry returns 0 results always | ⬜ |
| `_get_merchant()` doesn't check status — suspended merchants can quote | `routes/seller.py` | Trust gap | ⬜ |
| Registration success says "we'll contact you" but nobody does | Merchant registration flow | Dead-end UX | ⬜ |
| `services/reputation.py` is dead code — never called at runtime | `services/reputation.py` | Wasted code, false sense of security | ⬜ |
| No email verification on merchant registration | Merchant flow | Spam risk | ⬜ |
| Affiliate env vars all empty in production | Railway env config | $0 revenue on every clickout | ⬜ |
| Stripe Checkout has no `application_fee_amount` | `routes/checkout.py` | Platform takes $0 on every transaction | ⬜ |

### 3.3 Wrong Assumptions in Existing PRDs

1. **PRD 01 (Search v2)** assumes search architecture doesn't exist — 75% is built. Needs rewrite.
2. **PRD 05 (Closing Layer)** assumes Stripe processes marketplace payments — it doesn't. Need Stripe Connect.
3. **PRD 04 (Seller Tiles)** assumes sellers can discover buyer needs — they can't. Inbox only shows explicit outreach.
4. **PRD 06 (Viral Flywheel)** assumes a notification system exists — it doesn't.
5. **PRD 03 (Multi-Channel)** assumes "instant offers" are labeled — no badge distinction exists.

---

## 4. Missing PRDs

These PRDs don't exist yet but are required for launch. See individual files in this directory.

| # | PRD | Phase | Why It's Missing |
|---|-----|-------|------------------|
| L1 | [Revenue & Monetization Layer](./L1-revenue-monetization.md) | Pre-launch | No PRD covers how the platform actually makes money |
| L2 | [Landing Page & Onboarding](./L2-landing-page-onboarding.md) | Pre-launch | No public-facing landing page or user onboarding flow |
| L3 | [Mobile Responsive Design](./L3-mobile-responsive.md) | Pre-launch | >65% of marketplace traffic is mobile. Critical for virality. |
| L4 | [Real Email Send & Deliverability](./L4-real-email-send.md) | Pre-launch | Platform uses `mailto:` links. Zero emails sent from platform. |
| L5 | [Analytics & Observability](./L5-analytics-observability.md) | Pre-launch | No GA4/PostHog, no Sentry, no conversion funnel tracking |
| L6 | [SEO & Content Strategy](./L6-seo-content-strategy.md) | Post-launch | No indexable pages. Zero organic traffic strategy. |
| L7 | [Single-Player Mode](./L7-single-player-mode.md) | Post-launch | Standalone value for buyers before supply-side exists |

---

## 5. Launch Phases & Timeline

### Phase 0: Demo Day (TODAY — Feb 7)

```
✅ JetBid demo fixes (R1–R11)
✅ Deploy to Railway
✅ Tim sends RFQs to 12 vendors
✅ Quotes come back to tconnors@gmail.com
```

**Success = Tim successfully contacts all 12 vendors through the platform.**

### Phase 1: Revenue Foundation (Week 1 — Feb 10–14)

```
→ Set affiliate env vars (A1–A3, A5) ........................... 30 min
→ Register domain (D1) + point to Railway (D4) ................ 1 day
→ Set up Resend + verify domain (E1, E2) ...................... 1 day
→ Wire real email send into outreach routes (L4 PRD) .......... 2 days
→ Incorporate entity (B1) + EIN (B2) .......................... async
→ Google Analytics / PostHog (M1) + Sentry (M2) ............... 1 day
```

**Success = Affiliate revenue flowing. Emails actually sent from platform. Custom domain live.**

### Phase 2: Marketplace Loop (Week 2–3 — Feb 17–28)

```
→ Activate Stripe account (S1) ................................ async
→ Enable Stripe Connect (S2) + application fees (S3) .......... 2 days
→ Notification system — email + in-app (Phase 5 PRD 00) ....... 3 days
→ Tile detail panel (Phase 5 PRD 01) .......................... 2 days
→ Fix search_merchants() bug (verified status) ................ 1 day
→ Landing page + onboarding (L2 PRD) .......................... 2 days
→ Mobile responsive pass (L3 PRD) ............................. 3 days
→ Terms of Service + Privacy Policy (B4, B5) .................. async
```

**Success = Two-sided marketplace loop works. Sellers notified of RFPs. Buyers notified of quotes. Platform takes a cut. Mobile works.**

### Phase 3: Trust & Quality (Week 4–5 — Mar 1–14)

```
→ Help center (Phase 6 PRD 00) ................................ 2 days
→ Seller verification pipeline (Phase 6 PRD 04) ............... 3 days
→ Search scoring/ranking (Phase 4 Gap) ........................ 3 days
→ Buyer-seller messaging (Phase 6 PRD 03) ..................... 3 days
→ Closing status visibility ................................... 1 day
→ Seller RFP discovery feed ................................... 2 days
```

**Success = Verified sellers. Help available. Results ranked by quality. Buyers can track deal status.**

### Phase 4: Growth Engine (Week 6–8 — Mar 15–31)

```
→ Viral triggers: referral rewards, rich share cards .......... 3 days
→ SEO landing pages (auto-generated) .......................... 3 days
→ Single-player mode (procurement tracker) .................... 5 days
→ Personalization flywheel (UserSignal → ranking) ............. 3 days
→ Ad campaign setup (Google, Meta, LinkedIn) .................. async
→ Support tickets + dispute resolution (Phase 6 PRDs 01–02) ... 5 days
```

**Success = K-factor measurable. Organic traffic growing. Viral loops active. Public launch ready.**

### Public Launch: March 31, 2026

---

## 6. Supply-Side Strategy (Tim's Network)

Tim is extremely well connected in aviation and beyond. The supply-side strategy leverages his network for initial inventory.

### 6.1 Seed Categories

| Category | Tim's Network | Target Sellers | How |
|----------|---------------|----------------|-----|
| **Private aviation** | 12 charter vendors already in system | 20+ | Direct intros from JetBid demo |
| **Luxury travel** | Connected to concierge/travel networks | 10+ | Personal outreach after demo success |
| **Business services** | Nashville business community | 15+ | "Get quoted on BuyAnything" pitch |
| **Home services** | Roofing, HVAC, contractors | 20+ | Local market — high demand |

### 6.2 Seller Onboarding Flow

1. Tim makes introduction → vendor gets personal invite link
2. Vendor lands on `/merchants/register` → fills profile
3. **Seller verification pipeline** (Phase 6 PRD 04) auto-verifies based on invite source
4. Vendor appears in Merchant Registry
5. Vendor gets notified of matching buyer RFPs

### 6.3 Key Metric

**Target: 50 verified sellers across 4 categories by March 15.**

---

## 7. Demand-Side Strategy (Ad Budget)

### 7.1 Channel Mix

| Channel | Audience | Ad Type | Budget/mo | Expected CAC |
|---------|----------|---------|-----------|-------------|
| **Google Ads** | "private jet charter quote" + local services | Search | $2,000 | $15–30 |
| **Meta (FB/IG)** | 25–55, homeowners, travelers | Interest-based | $1,500 | $8–15 |
| **LinkedIn** | Small business owners, procurement managers | Sponsored content | $1,000 | $25–50 |
| **Reddit** | r/aviation, r/homeimprovement, r/smallbusiness | Promoted posts | $500 | $5–12 |

### 7.2 Landing Page Requirements (L2 PRD)

Ads need somewhere to land. Currently the app dumps users into a raw workspace. Required:

- Hero: "Tell us what you need. We'll find who can deliver."
- 30-second demo video
- 3 category examples (jets, home services, products)
- Social proof (Tim's quote experience)
- "Try it free" CTA → sign up → chat workspace
- Mobile-first (ads → mobile > 80%)

### 7.3 Conversion Funnel

```
Ad impression → Landing page → Sign up → First search → Deal selected → Purchase
   100%     →     3%       →   40%   →     70%     →     15%      →    10%
```

### 7.4 Key Metric

**Target: 500 active buyers by April 15. CAC < $20 blended.**

---

## 8. Success Metrics

### 8.1 Demo Phase (Feb 7–14)

| Metric | Target |
|--------|--------|
| Vendors contacted by Tim | 12 |
| Quotes received | 6+ |
| Tim selects a charter | 1 |

### 8.2 Beta Phase (Feb 15 – Mar 14)

| Metric | Target |
|--------|--------|
| Verified sellers | 50 |
| Active buyers | 100 |
| Transactions completed | 10 |
| Affiliate revenue | $500+ |
| Platform fees collected | $1,000+ |
| NPS score | > 40 |

### 8.3 Launch Phase (Mar 15 – Apr 30)

| Metric | Target |
|--------|--------|
| Active buyers | 500 |
| Verified sellers | 200 |
| Monthly GMV | $50,000 |
| Monthly platform revenue | $5,000 |
| K-factor (viral coefficient) | > 0.5 (not yet 1.2 — realistic) |
| Mobile traffic share | > 50% |
| Support ticket resolution time | < 24 hours |

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Tim's demo fails** | Medium | High | Test all 12 vendors before handing over. Have clipboard fallback. |
| **Stripe Connect approval delays** | Medium | High | Apply immediately. Use affiliate-only revenue until approved. |
| **Email deliverability issues** | Medium | High | Verify domain in Resend. Start with low volume. Warm up sending reputation. |
| **Low seller adoption** | Low | High | Tim's personal intros. Waive fees for first 6 months. |
| **Alibaba Accio** enters consumer market | Low | Critical | Move fast. Our UX + multi-category + trust layer is differentiated. |
| **PartFinder raises** and expands to consumer | Medium | Medium | Our social layer + viral mechanics are defensible. Ship faster. |
| **Railway hosting limits** at scale | Low | Medium | Plan migration to Vercel (frontend) + Fly.io (backend) at 1K DAU. |
| **No mobile experience** kills viral loops | High | High | Mobile responsive is P1 in Week 3. Cannot skip. |
| **Legal exposure** from facilitating transactions without ToS | Medium | Critical | ToS + Privacy Policy by end of Week 2. Non-negotiable. |

---

## Appendix: File Map

```
docs/prd/LAUNCH/
├── LAUNCH-PLAN.md          ← This file (master plan)
├── L1-revenue-monetization.md
├── L2-landing-page-onboarding.md
├── L3-mobile-responsive.md
├── L4-real-email-send.md
├── L5-analytics-observability.md
├── L6-seo-content-strategy.md
└── L7-single-player-mode.md
```
