# Phase 6 PRDs — Customer Support & Trust Infrastructure

**Created:** 2026-02-07  
**Status:** Planning  
**Prerequisite:** Phase 4 PRDs (00–12) complete; Phase 5 PRDs in progress

---

## Overview

Phase 6 addresses the **complete absence of customer support, dispute resolution, and trust infrastructure** in the platform. As a two-sided marketplace handling real money (affiliate commissions, Stripe checkout, seller platform fees), the lack of support channels is a critical gap.

**Current state:** When buyers or sellers encounter problems, their only option is a bug-report button that creates GitHub Issues for the engineering team. There is no help center, no support tickets, no dispute flow, no buyer-seller messaging, and no seller verification pipeline.

---

## Phase 6 Child PRDs

| # | PRD | Priority | Key Gap |
|---|-----|----------|---------|
| 00 | [Help Center & Self-Service](./00-help-center.md) | P0 | No FAQ, knowledge base, or contact page |
| 01 | [Support Tickets & Issue Resolution](./01-support-tickets.md) | P0 | No way to track/resolve user problems |
| 02 | [Dispute Resolution & Refunds](./02-dispute-resolution.md) | P1 | No recourse when transactions go wrong |
| 03 | [Buyer-Seller Messaging](./03-buyer-seller-messaging.md) | P1 | No direct communication between parties |
| 04 | [Seller Verification Pipeline](./04-seller-verification.md) | P1 | Registration exists but no approval/verification flow |
| 05 | [Trust & Safety Tooling](./05-trust-safety.md) | P2 | No admin moderation, content review, or enforcement |

---

## Why This Is Urgent

1. **Legal exposure** — Marketplace facilitating payments without dispute resolution creates liability
2. **User trust** — Buyers won't transact if there's no recourse when things go wrong
3. **Seller quality** — Unverified sellers with no accountability erode buyer confidence
4. **Retention** — Users who can't get help don't come back
5. **Compliance** — Payment processors (Stripe) require dispute handling processes

---

## Dependencies on Earlier Phases

- **00 (Help Center)** — Standalone, no hard dependencies
- **01 (Support Tickets)** — Needs: `Notification` model (Phase 4 PRD 04), `User` auth
- **02 (Disputes)** — Needs: `PurchaseEvent` model (Phase 2), `Contract` model (Phase 2), Stripe integration (Phase 4 PRD 00)
- **03 (Messaging)** — Needs: `User` auth, `Notification` model, `Row`/`Bid` models for context
- **04 (Seller Verification)** — Needs: `Merchant` model (Phase 2), email service (Phase 2), admin routes (Phase 4 PRD 09)
- **05 (Trust & Safety)** — Needs: all of the above; depends on 01, 02, 04

---

## Implementation Order

```
Week 1:  00 (Help Center) + 04 (Seller Verification)
Week 2:  01 (Support Tickets) + 03 (Buyer-Seller Messaging)
Week 3:  02 (Dispute Resolution)
Week 4:  05 (Trust & Safety Tooling)
```

Help Center and Seller Verification are independent and can ship immediately. Support Tickets and Messaging are the foundation for Dispute Resolution. Trust & Safety is the capstone that ties everything together.
