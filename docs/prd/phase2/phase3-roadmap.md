# Phase 3 Roadmap: Enterprise & Advanced Features

**Status:** Planning  
**Created:** 2026-02-03  
**Last Updated:** 2026-02-03

---

## Overview

Phase 3 extends the marketplace capabilities built in Phase 2 with enterprise features and advanced AI capabilities. These are informed by competitive analysis with PartFinder and market opportunity assessment.

**Phase 2 delivers:** Two-sided marketplace, RFQ automation, social features, closing layer  
**Phase 3 adds:** Enterprise integrations, advanced AI, expanded verticals

---

## Feature Candidates

### Priority 1: Enterprise Stickiness

| Feature | Description | Effort | Business Case |
|---------|-------------|--------|---------------|
| **ERP Integrations** | SAP, NetSuite connectors for procurement sync | L | Enterprise customer retention; PartFinder has this on roadmap |
| **SSO/SAML** | Enterprise identity provider integration | M | Required for enterprise sales |
| **Audit Logging** | Compliance-grade activity tracking | M | Required for regulated industries |
| **Custom Approval Workflows** | Multi-step approval for high-value purchases | M | Enterprise procurement process fit |

### Priority 2: Advanced AI

| Feature | Description | Effort | Business Case |
|---------|-------------|--------|---------------|
| **Photo-based Search** | Upload image → find matching products/parts | L | PartFinder has this; useful for industrial |
| **Parts-specific AI** | Technical spec understanding for industrial parts | L | Industrial vertical expansion |
| **Automated Negotiation** | AI counter-offers and price optimization | M | Higher margins on B2B deals |
| **Predictive Reordering** | Anticipate repeat purchases | M | Retention and revenue expansion |

### Priority 3: Expanded Verticals

| Feature | Description | Effort | Business Case |
|---------|-------------|--------|---------------|
| **Industrial Parts** | Thomasnet/Veridion integration for parts sourcing | L | Direct competition with PartFinder |
| **B2B Equipment** | Heavy machinery, industrial equipment | M | High-ACV opportunities |
| **Wholesale** | Bulk ordering, tiered pricing | M | B2B commerce expansion |
| **International** | Multi-currency, international suppliers | L | TAM expansion |

### Priority 4: Platform Enhancements

| Feature | Description | Effort | Business Case |
|---------|-------------|--------|---------------|
| **Merchant Dashboard v2** | Full seller portal with analytics | M | Seller retention and engagement |
| **Inventory Management** | Seller can manage stock levels | L | Full marketplace capability |
| **Ratings & Reviews** | Buyer reviews of sellers | M | Trust and quality signals |
| **Mobile App** | Native iOS/Android apps | L | User engagement |

---

## Dependencies on Phase 2

| Phase 3 Feature | Requires from Phase 2 |
|-----------------|----------------------|
| ERP Integrations | Merchant Registry, Quote Intake |
| Photo-based Search | Search Architecture v2 (complete) |
| Automated Negotiation | Quote Intake, Email Handoff |
| Merchant Dashboard v2 | Merchant Registry |
| Ratings & Reviews | Quote Intake, Deal Handoff (closed deals) |

---

## Competitive Gap Analysis

Based on [PartFinder competitive analysis](../Competitive_Analysis_PartFinder.md):

| Gap | Phase 2 Status | Phase 3 Action |
|-----|----------------|----------------|
| RFQ Automation | ✅ Closed | — |
| Quote Intake | ✅ Closed | — |
| Outreach Tracking | ✅ Closed | — |
| Deal Closing | ✅ Closed | — |
| ERP Integrations | ❌ Open | Add SAP/NetSuite connectors |
| Parts-specific AI | ❌ Open | Train on industrial catalogs |
| Photo-based Search | ❌ Open | Add image → product matching |
| Automated Negotiation | ❌ Open | AI counter-offer system |

**Our advantages to maintain:**
- Two-sided marketplace (Merchant Registry)
- Consumer UX (chat-driven)
- Social features (likes, comments)
- Viral mechanics (share links)
- Real-time marketplace data (Amazon, Google Shopping)

---

## B2B Expansion Strategy

### Services B2B (Phase 2 Ready)
- Local services: HVAC, roofing, plumbing, electrical
- Professional services: Legal, accounting, consulting
- Travel: Private aviation, charter
- Events: Catering, photography, venues

### Products B2B (Phase 3)
- Industrial parts: Thomasnet/Veridion integration
- Equipment: Heavy machinery, industrial equipment
- Wholesale: Bulk ordering, tiered pricing

### Enterprise B2B (Phase 3)
- ERP integration for procurement workflow
- SSO/SAML for enterprise identity
- Custom approval workflows
- Audit logging for compliance

---

## Monetization Expansion

| Phase | Revenue Model |
|-------|---------------|
| Phase 2 | Lead fees, success fees, premium tier (Merchant Registry) |
| Phase 3 | Enterprise SaaS ($X/seat), transaction fees (% of GMV), data licensing |

---

## Timeline Estimate

| Phase 3 Wave | Features | Est. Duration |
|--------------|----------|---------------|
| Wave 3a | ERP Integrations, SSO | 4-6 weeks |
| Wave 3b | Photo Search, Parts AI | 4-6 weeks |
| Wave 3c | Merchant Dashboard v2, Reviews | 3-4 weeks |
| Wave 3d | Industrial Verticals | 4-6 weeks |

**Total Phase 3:** ~15-22 weeks (4-5 months)

---

## Decision Points

Before starting Phase 3:

1. **Phase 2 Metrics Review**
   - Merchant signup rate (target: 100 in 90 days)
   - Quote submission rate (target: 20% of outreach)
   - Deal close rate (target: 10% of selections)

2. **B2B vs Consumer Focus**
   - If B2B metrics strong → prioritize ERP, Enterprise features
   - If consumer metrics strong → prioritize Photo Search, Mobile App

3. **Vertical Expansion**
   - Which service categories have highest demand?
   - Which have best supply (merchant signups)?

---

## Related Documents

- [Phase 2 PRD](./PRD.md)
- [Competitive Analysis: PartFinder](../Competitive_Analysis_PartFinder.md)
- [Merchant Registry PRD](./prd-merchant-registry.md)
- [WattData Integration](./wattdata-integration.md)

---

*This roadmap is a planning document. Specific PRDs will be written for Phase 3 features after Phase 2 completion and metrics review.*
