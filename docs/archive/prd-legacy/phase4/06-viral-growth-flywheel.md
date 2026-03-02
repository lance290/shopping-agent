# PRD: Viral Growth Flywheel

**Status:** Core mechanics built — flywheel wired end-to-end  
**Last Updated:** 2026-02-06 (build-all implementation pass)

## Implementation Status (as of 2026-02-06)

| Feature | Status | Current Code |
|---------|--------|-------------|
| ShareLink model with token + click tracking | ✅ Done | `ShareLink` model — share_token, click_count, view_count |
| User referral attribution fields | ✅ Done | `User.referral_share_token`, `User.signup_source` |
| ClickoutEvent share attribution | ✅ Done | `ClickoutEvent.share_token`, `referral_user_id` |
| Share link creation API | ✅ Done | Share endpoints for projects, rows, tiles |
| Seller-to-buyer conversion prompt | ✅ Done | `POST /seller/quotes` returns `buyer_prompt` with CTA |
| Referral attribution on signup | ✅ Done | `auth/verify` accepts `referral_token`, sets on User, increments ShareLink |
| Referral graph (user → invited users) | ✅ Done | `GET /admin/growth` — top referrers with signups driven |
| K-factor measurement | ✅ Done | `GET /admin/growth` — K = avg_shares × conversion_rate |
| Collaborator-to-buyer funnel tracking | ✅ Done | `GET /admin/growth` — clicks → signups → created_rows |
| Notification system | ✅ Done | `Notification` model + CRUD routes (PRD 04) |
| Referral notification | ✅ Done | Referrer notified when invitee signs up |
| Quote received notification | ✅ Done | Buyer notified when seller submits quote |
| Frontend referral passthrough | ✅ Done | Share page stores token → auth verify passes it → backend captures |

### Remaining (frontend UI):
- Seller-to-buyer CTA component (backend returns prompt, frontend needs to render it)
- Admin growth dashboard UI (backend endpoint ready at `/admin/growth`)

## Business Outcome
- Measurable impact: Achieve viral coefficient (K-factor) ≥ 1.2 by converting sellers into buyers and leveraging collaborative sharing to acquire new users organically.
- Target users:
  - Sellers who become buyers
  - Buyers who invite collaborators
  - New users acquired via outreach or sharing

## Scope
- In-scope:
  - Seller-to-buyer conversion: every seller can also post what they need to buy
  - Outreach-driven acquisition: agent reaches out to dozens of sellers per buyer need
  - Collaborative sharing: deep-linked project sharing that onboards new users
  - Referral tracking: attribute new users to the originating buyer/seller/project
- Out-of-scope:
  - Paid acquisition channels (Google Ads, etc.)
  - Cross-posting to external platforms (e.g., eBay listing automation) — future consideration

## User Flow
1. Buyer posts a need; agent reaches out to multiple sellers.
2. Seller receives outreach, views buyer need, and submits a quote.
3. Seller is prompted: "What do you need to buy?" — becoming a buyer.
4. Seller-as-buyer posts their own needs; agent reaches out to their potential suppliers.
5. Cycle repeats across supply chain layers.
6. Buyers share project links with collaborators; collaborators onboard and may become buyers themselves.

## Business Requirements

### Authentication & Authorization
- Sellers must authenticate to submit quotes and post their own needs.
- Referral/attribution data must be tracked without exposing PII to unauthorized parties.

### Monitoring & Visibility
- Track:
  - Viral coefficient (K-factor)
  - Seller-to-buyer conversion rate
  - Collaborator-to-buyer conversion rate
  - Outreach volume per buyer need
  - Referral attribution (who brought whom)

### Billing & Entitlements
- No direct billing for viral features in MVP.
- Must support future referral incentives or credits.

### Data Requirements
- Persist:
  - Referral graph (user → invited users)
  - Seller-as-buyer flag and activity
  - Attribution per user and project

### Performance Expectations
- Referral tracking should not add latency to user flows.

### UX & Accessibility
- Seller-to-buyer prompt should be non-intrusive but discoverable.
- Shareable links should work seamlessly for new and existing users.

### Privacy, Security & Compliance
- Referral data is sensitive; access-control and audit as needed.

## Dependencies
- Upstream:
  - Multi-Channel Sourcing (outreach to sellers)
  - Seller Tiles + Quote Intake (seller onboarding)
  - Workspace + Tile Provenance (collaborative sharing)
- Downstream:
  - Analytics and growth optimization

## Risks & Mitigations
- Outreach spam → rate limits, personalization, and opt-out mechanisms.
- Low seller-to-buyer conversion → optimize prompt timing and messaging.

## Acceptance Criteria (Business Validation)
- [ ] Seller can post their own buying need after submitting a quote (binary).
- [ ] Referral attribution is tracked when a new user joins via outreach or sharing (binary).
- [ ] Viral coefficient can be measured from referral data (binary).
- [ ] Collaborator invited via project link can onboard and become a buyer (binary).

## Traceability
- Parent PRD: `docs/prd/marketplace-pivot/parent.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`
- Strategy: `need sourcing_ next ebay.md`

---
**Note:** Technical implementation decisions are made during /plan and /task.
