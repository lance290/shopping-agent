# Phase 5 PRDs — Platform Maturity & Marketplace Infrastructure

**Created:** 2026-02-07  
**Status:** Planning  
**Prerequisite:** Phase 4 PRDs (00–12) substantially complete

---

## Overview

Phase 5 addresses **cross-cutting infrastructure gaps** and **advanced marketplace features** identified during the Phase 4 PRD audit. These items were found missing from the original vision documents and competitive analysis but are not required for Phase 4 delivery. They are sequenced here to avoid blocking Phase 4 work.

---

## Phase 5 Child PRDs

| # | PRD | Priority | Key Gap |
|---|-----|----------|---------|
| 00 | [Notification System](./00-notification-system.md) | P1 | No in-app or email notifications — blocks marketplace loop |
| 01 | [Tile Detail Panel](./01-tile-detail-panel.md) | P1 | Backend exists, no frontend — users can't see why tiles match |
| 02 | [Admin Affiliate & Provider Management](./02-admin-affiliate-provider-mgmt.md) | P2 | No UI to manage affiliate rules or provider keys |
| 03 | [Entitlement Tiers & Usage Limits](./03-entitlement-tiers.md) | P2 | No pricing tiers, usage limits, or feature gating |
| 04 | [Lead Fees & Merchant Monetization](./04-lead-fees-merchant-monetization.md) | P2 | Lead fees, success fees, premium placement not defined |
| 05 | [Priority Matching Waterfall](./05-priority-matching-waterfall.md) | P2 | No defined ordering: registered merchants → outreach → marketplace |

---

## Dependencies on Phase 4

- **00 (Notifications)** depends on: PRD 04 (seller tiles), PRD 12 (vendor unresponsiveness)
- **01 (Tile Detail)** depends on: PRD 07 (workspace), PRD 11 (ranking — score breakdown)
- **02 (Admin Mgmt)** depends on: PRD 00 (revenue — affiliate config), PRD 09 (analytics)
- **03 (Entitlements)** depends on: PRD 00 (revenue — Stripe billing)
- **04 (Lead Fees)** depends on: PRD 00 (revenue), PRD 04 (seller tiles)
- **05 (Waterfall)** depends on: PRD 03 (multi-channel sourcing), PRD 04 (seller tiles)
