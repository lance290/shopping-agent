# Competitive Analysis: PartFinder vs Shopping Agent

**Prepared for:** Investor Review  
**Date:** February 2026  
**Classification:** Confidential

---

## Executive Summary

This analysis compares **PartFinder**, an AI-powered B2B industrial parts sourcing platform, with **Shopping Agent** (our product). While both leverage AI for procurement, they target fundamentally different markets with distinct value propositions.

| Dimension | PartFinder | Shopping Agent |
|-----------|------------|----------------|
| **Target Market** | Mid-market manufacturers ($50M–$1B revenue) | Consumers & small teams |
| **Core Problem** | Multi-week B2B RFQ cycles | Personal shopping friction |
| **Vertical** | Industrial parts & components | Consumer goods + services |
| **Business Model** | SaaS ($199/mo Pro, custom Enterprise) | PLG (TBD pricing) |
| **Stage** | Pre-launch (Q1 2026 target) | Live, Phase 2 in development |

**Bottom Line:** With Phase 2, we're building PartFinder's core features (RFQ automation, quote intake, outreach tracking) while maintaining our consumer UX advantage. We can absorb their concept with **~6-8 weeks of planned work**.

---

## About PartFinder

### Company Overview
- **Founders:** Olivier Tuch (Ex-Babylon/Cirrus Logic engineer, CAIC™-certified AI architect) & Jeffrey Porter (Ex-Morgan Stanley, scaled startup to millions of views)
- **Target Market:** $25.7B supply chain software market (growing to $48.6B by 2030 @ 11% CAGR)
- **Initial Focus:** Mid-market manufacturing companies with complex procurement needs

### Problem They're Solving
| Pain Point | Impact |
|------------|--------|
| **2-week RFQ cycles** | Projects stall waiting for supplier quotes |
| **No supplier visibility** | Overpaying, suboptimal vendor selection |
| **Manual processes** | 22% of procurement time wasted (Ivalua study) |

### Their Solution
1. **Natural Language Search** — "high-torque motor" → technical specifications
2. **Automated RFQs** — One-click quote requests to multiple suppliers
3. **AI Email Agent** — Auto-generates personalized outreach using scraped contact info
4. **Communication Dashboard** — Track replies, prioritize follow-ups
5. **ERP Integration** — SAP, NetSuite (roadmap)

### Business Model
| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | 5 searches/mo, 3 RFQs/mo |
| Pro | $199/mo | Extended search, high-volume RFQs |
| Enterprise | Custom | Full ERP integration, dedicated support |

### Roadmap
- **Q1 2026:** Core search, basic RFQ, US supplier database
- **Q2 2026:** ERP integrations, supplier verification
- **Q3-Q4 2026:** Enterprise dashboards, negotiation tools
- **2027+:** Global expansion, predictive insights

---

## Competitive Positioning

### Where We Overlap

| Capability | PartFinder | Shopping Agent |
|------------|:----------:|:--------------:|
| Natural language search | ✅ | ✅ |
| Multi-source aggregation | ✅ | ✅ |
| AI-powered recommendations | ✅ | ✅ |
| Vendor/supplier outreach | ✅ | ✅ |
| Side-by-side comparisons | ✅ | ✅ |

### Where We Differ

| Dimension | PartFinder | Shopping Agent |
|-----------|------------|----------------|
| **User** | Procurement manager | Anyone |
| **Purchase Type** | Industrial parts, components | Consumer products, services |
| **Transaction** | RFQ → negotiation → PO | Click-through to merchant |
| **Data Source** | Proprietary supplier DB | Live marketplace APIs |
| **Sales Motion** | Sales-assisted | Self-serve |
| **Integrations** | SAP, NetSuite | None (lightweight) |

---

## PartFinder's Competitive Advantages

### 1. Deep Vertical Focus
Parts-specific AI models trained on technical specifications, datasheets, and engineering terminology across multiple industries—not just generic product data.

**Our response:** We can train on industrial catalogs if we pivot to B2B. Our LLM layer is model-agnostic.

### 2. RFQ Workflow Automation
Complete procurement cycle from quote request through response management.

**Our response:** **Phase 2 delivers this.** See `prd-wattdata-outreach.md` and `prd-quote-intake.md`.

### 3. Data Flywheel
Every RFQ submission enriches their supplier intelligence.

**Our response:** Phase 2 includes WattData integration (we're investors in WattData) + outreach tracking. Same flywheel potential.

### 4. ERP Stickiness
SAP/NetSuite integrations (planned) create high switching costs for enterprise customers.

**Our response:** Not in Phase 2, but straightforward to add. Low priority unless we pivot to enterprise.

### 5. Higher ACV Potential
$199/mo Pro + custom Enterprise = strong unit economics for a sales-assisted B2B motion.

**Our response:** Phase 2 includes entitlement tiers (free: 10 vendors/row, premium: 50). Pricing TBD.

---

## Our Competitive Advantages

### 1. Conversational UX
Full chat-driven interface with real-time constraint refinement. Users don't need procurement expertise—they just describe what they want.

### 2. Instant Results
We aggregate live consumer marketplaces (Amazon, Google Shopping, eBay) in real-time. No supplier onboarding, no database lag.

### 3. Zero Onboarding Friction
No ERP integration required. Works immediately for any user, any purchase.

### 4. Social Decision Layer
Likes, comments, and sharing features help users make decisions collaboratively—a capability PartFinder doesn't offer.

### 5. Services Expansion
We already support vendor outreach for services (private jets, HVAC, roofing). This positions us for the broader "buy anything" vision beyond physical products.

### 6. Consumer-Grade Simplicity
Built for everyone, not just procurement professionals. This dramatically expands our addressable market.

---

## Feature Gap Analysis (Updated with Phase 2)

| Feature | PartFinder | Us Today | Us After Phase 2 |
|---------|:----------:|:--------:|:----------------:|
| RFQ email drafting & send | ✅ | ⚠️ Basic | ✅ WattData Outreach |
| Quote intake (magic link) | ✅ | ❌ | ✅ `prd-quote-intake.md` |
| Outreach tracking (open/click) | ✅ | ❌ | ✅ `outreach_events` table |
| Communication dashboard | ✅ | ❌ | ✅ Buyer sees status |
| Supplier/vendor database | ✅ Proprietary | ⚠️ Mock | ✅ WattData MCP |
| **Merchant/Seller Registry** | ❌ | ❌ | ✅ `prd-merchant-registry.md` |
| **Service Provider Network** | ❌ | ⚠️ Jets/HVAC | ✅ Full taxonomy |
| Email handoff (deal closing) | ✅ | ❌ | ✅ `prd-email-handoff.md` |
| Contract generation | 🗓️ Roadmap | ❌ | ✅ DocuSign (`prd-docusign-contracts.md`) |
| Checkout/payment | 🗓️ Roadmap | ❌ | ✅ Stripe (`prd-stripe-checkout.md`) |
| ERP integrations | 🗓️ Roadmap | ❌ | ❌ (Phase 3+) |
| Photo-based search | ✅ | ❌ | ❌ (Phase 3+) |
| Social features (likes/comments) | ❌ | ✅ | ✅ Enhanced |
| Chat-based refinement | ❌ | ✅ | ✅ |
| Real-time marketplace data | ❌ | ✅ | ✅ |
| Share links (viral) | ❌ | ❌ | ✅ `prd-share-links.md` |

---

## Strategic Assessment

### Phase 2 Closes the Gap
With Phase 2 complete, we will have **feature parity** on RFQ automation while maintaining advantages in:
- Consumer UX (chat-driven)
- Real-time marketplace data (Amazon, Google Shopping)
- Social collaboration (likes, comments, share links)
- Viral distribution (K > 1.2 target)

### What Phase 2 Delivers
| PartFinder Feature | Our Phase 2 Equivalent |
|-------------------|------------------------|
| AI Email Agent | WattData Outreach + SendGrid |
| RFQ to multiple suppliers | `POST /rows/{row_id}/outreach` |
| Centralized comms dashboard | Outreach status on row |
| Response management | Quote intake + bid conversion |
| Supplier database | WattData MCP (we're investors) |
| — | **Merchant Registry** (they don't have this) |
| — | **Service Provider Network** (they don't have this) |

### Merchant Registry: Our B2B Advantage

Phase 2 includes a **Merchant Registry** (`prd-merchant-registry.md`) that PartFinder doesn't have:

- **Self-registration portal** for service providers and B2B vendors
- **Category taxonomy**: roofing, HVAC, plumbing, private aviation, catering, legal, consulting, etc.
- **Geographic matching**: zip codes, radius, regions
- **Priority matching waterfall**:
  1. Registered merchants (immediate RFP notification)
  2. WattData outreach (cold discovery)
  3. Amazon/Serp (product results)
- **"Verified Partner" badges** for registered merchants
- **Merchant dashboard** to view RFPs and submitted quotes

**This is a two-sided marketplace** — PartFinder is buyer-only with cold outreach. We're building supply-side engagement.

### Service Categories Already Planned

```yaml
services:
  home: roofing, hvac, plumbing, electrical, landscaping, cleaning, painting, remodeling
  auto: repair, detailing, towing
  professional: legal, accounting, consulting, marketing
  travel: private_aviation, charter, luxury_travel
  events: catering, photography, venues, entertainment
```

**We can absolutely go B2B.** The merchant registry + service taxonomy positions us for:
- Local services (already live: jets, HVAC, roofing)
- Professional services (legal, accounting, consulting)
- Enterprise procurement (add ERP integration later if needed)

### Remaining Gaps After Phase 2
1. **ERP Integrations** — SAP/NetSuite (enterprise stickiness)
2. **Parts-specific AI** — Technical spec understanding for industrial parts
3. **Photo-based search** — Upload image → find part
4. **Automated negotiation** — AI counter-offers

**Assessment:** Gap 1 is the only real enterprise blocker. Gaps 2-4 are nice-to-haves that don't affect our B2B services play.

### If PartFinder Wanted to Compete with Us
To match our consumer experience, they would need:
- Consumer marketplace integrations (Amazon, Google Shopping APIs)
- Conversational chat interface
- Mobile-first UX
- Social/collaborative features
- Viral sharing mechanics

**Assessment:** Unlikely pivot given their B2B positioning and sales motion.

### Data Moat Consideration
Both platforms can build defensibility through RFQ/outreach data. We have additional moat vectors:
- Purchase intent signals from consumer searches
- Social signals (likes, comments)
- Viral referral graphs
- WattData partnership (we're investors)

---

## Market Sizing Comparison

| Metric | PartFinder's TAM | Our TAM |
|--------|------------------|---------|
| Market | Supply chain software | E-commerce + services |
| Size | $25.7B → $48.6B (2030) | $6.3T US e-commerce + services |
| Growth | 11% CAGR | 10%+ CAGR |
| Our Slice | Not competing | Consumer decision layer |

---

## Recommendations

### 1. Execute Phase 2
Phase 2 delivers PartFinder's core value prop (RFQ automation) while preserving our consumer UX advantage. **This is the highest-leverage work.**

### 2. Leverage WattData Partnership
We're investors in WattData. This gives us:
- Preferred API access
- Input on roadmap
- Potential exclusivity for consumer use cases

### 3. Maintain Consumer Focus
PartFinder validates the market, but we don't need to copy their enterprise motion. Our viral/PLG approach can win the "long tail" of procurement.

### 4. We CAN Go B2B — It's Built Into Phase 2
The Merchant Registry + Service Taxonomy positions us for B2B without additional work:
- **Local services**: Already live (jets, HVAC, roofing)
- **Professional services**: Category taxonomy ready (legal, accounting, consulting)
- **Enterprise procurement**: Add ERP integration later if metrics support it

**Phase 2 monetization paths** (from `prd-merchant-registry.md`):
- Lead fees (charge merchant per RFP notification)
- Success fees (% of closed deals)
- Premium tier (priority placement, more leads)

---

## Conclusion

PartFinder and Shopping Agent started in different lanes, but **Phase 2 puts us on a collision course**. After Phase 2:

| Capability | PartFinder | Us |
|------------|:----------:|:--:|
| RFQ Automation | ✅ | ✅ |
| Quote Intake | ✅ | ✅ |
| Outreach Tracking | ✅ | ✅ |
| Deal Closing | ✅ | ✅ |
| Consumer UX | ❌ | ✅ |
| Real-time Marketplace | ❌ | ✅ |
| Social Features | ❌ | ✅ |
| Viral Mechanics | ❌ | ✅ |

**Our advantage:** We can do everything they do, PLUS consumer-grade UX and viral growth.

**Their advantage:** Enterprise sales motion, ERP integrations (future), parts-specific AI.

**Key differentiator we have that they don't:** Two-sided marketplace with Merchant Registry. They only do cold outreach; we build supply-side relationships.

**Bottom Line:** We can absorb PartFinder's concept in ~6-8 weeks (Phase 2 timeline). After that, we're a superset of their feature set with better distribution mechanics.

---

*Document prepared for internal investor discussion. Not for external distribution.*
