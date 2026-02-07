# Phase 6 Implementation Roadmap

**Created:** 2026-02-07  
**Status:** Draft — awaiting approval

---

## Summary of Effort

| PRD | Name | Est. Lines | Est. Time | Dependencies |
|-----|------|-----------|-----------|-------------|
| 04 | Seller Verification Pipeline | ~1,150 | 2-3 days | None |
| 00 | Help Center & Self-Service | ~1,200 | 1-2 days | None |
| 01 | Support Tickets & Issue Resolution | ~1,550 | 2 days | PRD 00 |
| 03 | Buyer-Seller Messaging | ~1,360 | 2 days | PRD 04 |
| 02 | Dispute Resolution & Refunds | ~1,630 | 2-3 days | PRD 01 |
| 05 | Trust & Safety Tooling | ~1,810 | 2-3 days | PRD 01, 02, 03, 04 |
| **Total** | | **~8,700** | **~12-16 days** | |

---

## Recommended Build Order

```
Week 1
├── PRD 04: Seller Verification Pipeline  (no deps, unblocks seller search + trust)
└── PRD 00: Help Center & Self-Service    (no deps, parallel with 04)

Week 2
├── PRD 01: Support Tickets              (contact form → tickets, bridges to disputes)
└── PRD 03: Buyer-Seller Messaging       (needs verified sellers from PRD 04)

Week 3
├── PRD 02: Dispute Resolution & Refunds (needs tickets from PRD 01)
└── PRD 05: Trust & Safety Tooling       (capstone, needs everything above)
```

PRDs 04 and 00 have zero dependencies and can start immediately in parallel.
PRDs 01 and 03 can start as soon as 04 and 00 are done, also in parallel.
PRDs 02 and 05 are sequential — 02 first (disputes), then 05 (safety) last.

---

## New Backend Models (6 total)

| Model | Table | PRD | Purpose |
|-------|-------|-----|---------|
| `MerchantVerification` | `merchant_verification` | 04 | Audit trail for all merchant status transitions |
| `HelpArticle` | `help_article` | 00 | FAQ / knowledge base articles |
| `SupportTicket` | `support_ticket` | 01 | User support requests |
| `TicketMessage` | `ticket_message` | 01 | Threaded replies on tickets |
| `MessageThread` | `message_thread` | 03 | Buyer-seller conversation threads |
| `Message` | `message` | 03 | Individual messages within threads |
| `Dispute` | `dispute` | 02 | Transaction dispute records |
| `DisputeEvidence` | `dispute_evidence` | 02 | Evidence attachments on disputes |
| `ContentFlag` | `content_flag` | 05 | User-reported content flags |
| `EnforcementAction` | `enforcement_action` | 05 | Warnings, restrictions, bans |
| `SafetyRule` | `safety_rule` | 05 | Configurable automated moderation rules |

---

## New Backend Route Files (6 total)

| File | PRD | Endpoints |
|------|-----|-----------|
| `routes/merchant_verification.py` | 04 | 3 (verify-email, resend, status) |
| `routes/help.py` | 00 | 7 (articles CRUD, feedback, contact) |
| `routes/support.py` | 01 | 8 (tickets CRUD, messages, admin queue) |
| `routes/messages.py` | 03 | 8 (threads, send, read, unread, admin) |
| `routes/disputes.py` | 02 | 8 (file, evidence, resolve, admin queue) |
| `routes/trust_safety.py` | 05 | 11 (flags, enforcement, rules, dashboard) |

Plus additions to `routes/admin.py` (6 merchant management endpoints from PRD 04).

---

## New Backend Service Files (4 total)

| File | PRD | Purpose |
|------|-----|---------|
| `services/refund.py` | 02 | Stripe refund processing |
| `services/support_sla.py` | 01 | SLA breach detection + escalation |
| `services/safety_rules.py` | 05 | Automated content moderation rules |
| `services/enforcement.py` | 05 | Enforcement action expiration |

Plus additions to `services/email.py` (~8 new email functions across all PRDs).

---

## New Frontend Pages (est. 20+)

| Area | Pages | PRDs |
|------|-------|------|
| `/help/*` | Landing, category, article, contact, tickets | 00, 01 |
| `/merchants/verify-email` | Email verification landing | 04 |
| `/messages/*` | Inbox, thread detail | 03 |
| `/help/disputes/*` | File dispute, dispute list, dispute detail | 02 |
| `/admin/support/*` | Ticket queue, ticket detail | 01 |
| `/admin/disputes/*` | Dispute queue, dispute detail | 02 |
| `/admin/safety/*` | Dashboard, flags queue, rules config | 05 |
| `/account/safety` | User enforcement history | 05 |

Plus ~30 frontend API proxy routes.

---

## Alembic Migrations (one per PRD, 6 total)

| Migration | Tables Created |
|-----------|---------------|
| `p6_01_merchant_verification` | `merchant_verification` |
| `p6_02_help_articles` | `help_article` |
| `p6_03_support_tickets` | `support_ticket`, `ticket_message` |
| `p6_04_messaging` | `message_thread`, `message` |
| `p6_05_disputes` | `dispute`, `dispute_evidence` |
| `p6_06_trust_safety` | `content_flag`, `enforcement_action`, `safety_rule` |

No changes to existing tables needed (all new fields already exist on `Merchant`).

---

## Test Coverage Target

| Test File | Tests | PRD |
|-----------|-------|-----|
| `test_seller_onboarding.py` | 20 | 04 |
| `test_help_center.py` | 12 | 00 |
| `test_support_tickets.py` | 15 | 01 |
| `test_messaging.py` | 15 | 03 |
| `test_disputes.py` | 12 | 02 |
| `test_trust_safety.py` | 15 | 05 |
| **Total** | **89** | |

---

## Existing Bug Fixes (Include in PRD 04)

These are bugs in existing code discovered during the audit:

1. **`search_merchants()` returns zero results** — filters by `status == "verified"` but no merchant ever reaches that status. Fix: include `"active"` status.
2. **`_get_merchant()` doesn't check status** — suspended merchants can submit quotes. Fix: add status check.
3. **Registration success message misleading** — promises review that never happens. Fix: update to "check your email."
4. **`MerchantProfile` response missing verification fields** — doesn't include `status`, `verification_level`, or `reputation_score`. Fix: add to response model.
5. **`reputation.py` is dead code** — never called at runtime. Fix: wire into transaction events.

---

## Open Decisions Needed Before Building

| # | Question | Options | Recommendation |
|---|----------|---------|---------------|
| 1 | Should pending merchants be able to submit quotes? | A: Yes with badge, B: No until verified | A — keeps marketplace active |
| 2 | Add `"rejected"` as new Merchant status? | A: Yes (distinct from suspended), B: No | A — cleaner semantics |
| 3 | Auto-promotion to `trusted`: implement now or defer? | A: Now, B: Defer | B — no merchants will qualify yet |
| 4 | Admin notification on new registration: email or in-app? | A: Email, B: In-app, C: Both | C — both |
| 5 | Help articles: SSR/ISR or client-rendered? | A: SSR/ISR (SEO), B: Client | A — SEO matters for help content |
| 6 | Markdown rendering library? | A: react-markdown, B: raw HTML | A — cleaner authoring |
| 7 | Contact form: require auth? | A: Yes, B: Anonymous OK | B — reduce friction |
| 8 | Messages: immutable (no edit/delete)? | A: Yes (audit trail), B: Allow delete | A — marketplace standard |
| 9 | Dispute against non-purchase (pre-transaction)? | A: Allow, B: Post-transaction only | B — pre-transaction → support ticket |
| 10 | Safety rules: database-seeded or hardcoded? | A: DB (configurable), B: Hardcoded | A — admin can tune |

---

## Document Index

| File | Purpose |
|------|---------|
| `parent.md` | Phase 6 overview, PRD list, dependencies |
| `AUDIT.md` | Codebase findings — what exists, what's broken, what's missing |
| `ROADMAP.md` | This file — sequencing, effort estimates, decisions |
| `00-help-center.md` | PRD: Help Center & Self-Service |
| `01-support-tickets.md` | PRD: Support Tickets & Issue Resolution |
| `02-dispute-resolution.md` | PRD: Dispute Resolution & Refunds |
| `03-buyer-seller-messaging.md` | PRD: Buyer-Seller Messaging |
| `04-seller-verification.md` | PRD: Seller Verification Pipeline |
| `05-trust-safety.md` | PRD: Trust & Safety Tooling |
| `PLAN-00-help-center.md` | Implementation plan: Help Center |
| `PLAN-01-support-tickets.md` | Implementation plan: Support Tickets |
| `PLAN-02-dispute-resolution.md` | Implementation plan: Dispute Resolution |
| `PLAN-03-buyer-seller-messaging.md` | Implementation plan: Buyer-Seller Messaging |
| `PLAN-04-seller-verification.md` | Implementation plan: Seller Verification |
| `PLAN-05-trust-safety.md` | Implementation plan: Trust & Safety |
