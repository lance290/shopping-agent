# PRD 04: Seller Verification Pipeline

**Phase:** 6 — Customer Support & Trust Infrastructure  
**Priority:** P1  
**Status:** Planning  
**Parent:** [Phase 6 Parent](./parent.md)

---

## Problem Statement

Merchants can register at `/merchants/register`, but there is **no verification pipeline**. The `Merchant` model has the fields (`status`, `verification_level`, `verified_at`) but nothing transitions them. Every merchant sits at `status: "pending"` and `verification_level: "unverified"` forever.

The registration endpoint returns: *"Registration received. You will be contacted for verification."* — but no contact ever happens.

**Current state (broken):**
- `Merchant.status` = `"pending"` on registration — never changes
- `Merchant.verification_level` = `"unverified"` — never changes
- `Merchant.verified_at` = `null` — never set
- `services/reputation.py` computes a score — nothing calls it
- No admin endpoint to approve/reject/suspend merchants
- No email verification flow
- No criteria-based automatic promotion
- Buyer-facing badges reference verification levels that are never assigned

This means **any spam account can register as a merchant** and immediately appear in buyer search results with quotes. There is no quality gate.

---

## Solution Overview

Build a **multi-stage verification pipeline** that:

1. **Email verification** — Automatic on registration (click-to-verify link)
2. **Business verification** — Manual admin review (website, business license, or Stripe Connect completion)
3. **Trusted status** — Automatic promotion based on track record (transactions, dispute history, account age)
4. **Admin management** — Full CRUD for merchant status, with suspend/unsuspend and appeal
5. **Reputation scoring** — Wire up the existing `services/reputation.py` to run on transaction events

---

## Scope

### In Scope
- Email verification flow on merchant registration (token → callback → status update)
- Admin merchant management dashboard (list, approve, reject, suspend, unsuspend)
- Automatic promotion to "trusted" based on criteria
- Reputation score computation triggered by transaction events
- Verification badge display on seller quotes/bids (buyer-facing)
- Seller-facing verification status on dashboard
- Suspension with reason + appeal via support ticket (PRD 01)
- Audit log for all status transitions

### Out of Scope
- KYC/identity verification via third-party service (Stripe Identity, Persona)
- Business license document upload and review
- Automated website crawling/validation
- Seller reviews by buyers (future PRD)

---

## User Stories

**US-01:** As a new merchant, after registering I should receive a verification email so I can confirm my email address.

**US-02:** As a merchant who verified their email, I want to see my verification status on my dashboard and know what's needed for the next level.

**US-03:** As an admin, I want to see all pending merchants and approve or reject them after reviewing their business profile.

**US-04:** As an admin, I want to suspend a merchant who violates policies, with a reason that's communicated to them.

**US-05:** As a suspended merchant, I want to appeal my suspension through a support ticket.

**US-06:** As a buyer, I want to see verification badges on seller quotes so I can trust their legitimacy.

**US-07:** As a merchant with a strong track record, I want to be automatically promoted to "trusted" status.

---

## Business Requirements

### Verification Levels

| Level | Badge | How to reach | Buyer visibility |
|-------|-------|-------------|-----------------|
| `unverified` | None | Just registered, email not confirmed | No badge; quotes may be deprioritized |
| `email_verified` | ✉️ Email Verified | Clicked email verification link | Small badge |
| `business_verified` | ✅ Verified Business | Admin approved after manual review | Prominent badge |
| `trusted` | ⭐ Trusted Seller | Auto: 5+ completed transactions, 0 upheld disputes, 90+ days, reputation ≥ 3.5 | Gold badge + "Trusted" label |

### Status Transitions

```
                  register
                     │
              ┌──────▼──────┐
              │   pending    │  verification_level: unverified
              └──────┬──────┘
                     │ click email link
              ┌──────▼──────┐
              │   active     │  verification_level: email_verified
              └──────┬──────┘
                     │ admin approves
              ┌──────▼──────┐
              │   verified   │  verification_level: business_verified
              └──────┬──────┘
                     │ auto-promotion criteria met
              ┌──────▼──────┐
              │   verified   │  verification_level: trusted
              └─────────────┘

  At any point, admin can:
  ┌─────────────┐         ┌─────────────┐
  │  suspended   │ ◄─────► │  (previous)  │  (unsuspend restores previous level)
  └─────────────┘         └─────────────┘
```

### Email Verification Flow

1. Merchant registers → `status: "pending"`, `verification_level: "unverified"`
2. System sends email with verification link: `/merchants/verify-email?token=<token>`
3. Merchant clicks link → token validated → `status: "active"`, `verification_level: "email_verified"`, `verified_at: now()`
4. Token expires after 72 hours; merchant can request a new one

### Auto-Promotion Criteria (Trusted)

All must be true:
- Account age ≥ 90 days
- ≥ 5 completed transactions (quotes accepted by buyers)
- 0 upheld disputes in last 180 days
- Reputation score ≥ 3.5 (out of 5.0)
- Currently `business_verified`

Check runs: on each transaction completion + nightly batch.

### Reputation Score Triggers

Wire `services/reputation.py` to compute score when:
- A seller's quote is accepted or rejected by a buyer
- A transaction completes
- A dispute is resolved
- Nightly batch recalculation for all active merchants

### Data Requirements

**MerchantVerification model (new):**
```
id
merchant_id (FK merchant)
verification_type: email | business | trusted | suspension | unsuspension
status: pending | completed | expired | rejected

# Email verification
token (str, unique, nullable)
token_expires_at (datetime, nullable)

# Admin review
reviewed_by_user_id (FK user, nullable)
review_notes (text, nullable)
rejection_reason (text, nullable)

# Suspension
suspension_reason (text, nullable)

created_at, completed_at
```

**Merchant model updates (existing fields, now actively used):**
- `status`: `pending` → `active` → `verified` → `suspended`
- `verification_level`: `unverified` → `email_verified` → `business_verified` → `trusted`
- `verified_at`: Set on first email verification
- `reputation_score`: Updated by reputation service

### Authentication & Authorization
- **Email verification callback:** Public (token-authenticated)
- **Request re-send verification:** Authenticated merchant
- **Admin merchant list/approve/reject/suspend:** `require_admin`
- **View own verification status:** Authenticated merchant

### Performance
- Email verification callback < 500ms
- Admin merchant list with filters < 500ms
- Reputation score computation < 2s per merchant

---

## Technical Design

### Backend

**New file:** `routes/merchant_verification.py`

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /merchants/verify-email` | Public (token) | Email verification callback |
| `POST /merchants/resend-verification` | Merchant | Re-send verification email |
| `GET /merchants/verification-status` | Merchant | Current verification level + next steps |

**Updates to:** `routes/admin.py`

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /admin/merchants` | Admin | List all merchants with filters (status, verification_level) |
| `GET /admin/merchants/{id}` | Admin | Merchant detail + verification history |
| `POST /admin/merchants/{id}/approve` | Admin | Promote to business_verified |
| `POST /admin/merchants/{id}/reject` | Admin | Reject with reason |
| `POST /admin/merchants/{id}/suspend` | Admin | Suspend with reason |
| `POST /admin/merchants/{id}/unsuspend` | Admin | Restore previous status |

**Updates to:** `routes/merchants.py`
- After registration, trigger verification email send
- Add verification token generation

**Updates to:** `services/reputation.py`
- Add `trigger_reputation_update(merchant_id)` function callable from transaction events
- Add `check_trusted_promotion(merchant_id)` for auto-promotion

**Updates to:** `routes/seller.py`
- Seller profile shows verification status and progress

### Frontend

| Page/Component | Description |
|---------------|-------------|
| `/merchants/verify-email` | Email verification landing page (success/expired/invalid) |
| Seller dashboard (Profile tab) | Verification status card with progress steps |
| Admin `/admin/merchants` | Merchant management table with approve/reject/suspend actions |
| Admin `/admin/merchants/[id]` | Merchant detail with verification history |
| `VerificationBadge` component | Reusable badge shown on seller quotes/bids |

### Email Templates

| Email | Trigger | Content |
|-------|---------|---------|
| Verification email | Registration | "Click to verify your email" + token link |
| Verification reminder | 48h after registration if not verified | "Don't forget to verify" |
| Approved | Admin approves | "Your business has been verified!" |
| Rejected | Admin rejects | "Your verification was not approved" + reason |
| Suspended | Admin suspends | "Your account has been suspended" + reason + appeal instructions |
| Unsuspended | Admin unsuspends | "Your account has been restored" |
| Trusted promotion | Auto-promotion | "Congratulations! You've earned Trusted Seller status" |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Email verification rate (within 72h) | > 70% |
| Business verification approval rate | > 80% |
| Time from registration to email_verified | < 24 hours (median) |
| Time from email_verified to business_verified | < 5 business days |
| Trusted seller count (after 6 months) | > 10% of verified merchants |
| Buyer click-through on verified vs. unverified seller quotes | Verified > 2x |

---

## Acceptance Criteria

- [ ] New merchant registration triggers verification email with tokenized link
- [ ] Clicking valid token sets `verification_level: "email_verified"` and `status: "active"`
- [ ] Expired tokens (>72h) show error and offer re-send option
- [ ] Merchant dashboard shows current verification level and steps to next level
- [ ] Admin can list all merchants filtered by status and verification level
- [ ] Admin can approve a merchant → sets `verification_level: "business_verified"`
- [ ] Admin can reject a merchant → sets status back, sends email with reason
- [ ] Admin can suspend a merchant → sets `status: "suspended"`, removes from buyer search results
- [ ] Admin can unsuspend → restores previous status and verification level
- [ ] Verification badges appear on seller quotes visible to buyers
- [ ] Unverified sellers' quotes are deprioritized in tile ordering
- [ ] Auto-promotion to "trusted" triggers when criteria met
- [ ] All status transitions logged in `MerchantVerification` audit table
- [ ] Reputation score recalculated on transaction events

---

## Dependencies
- **PRD 01 (Support Tickets):** Suspended merchants appeal via support ticket
- **PRD 05 (Trust & Safety):** Provides the enforcement layer for suspensions
- **Phase 4 PRD 10 (Anti-Fraud):** `verification_level` and `reputation_score` fields already exist on model
- **Email service:** `services/email.py` for verification and notification emails

## Risks
- **Low verification completion** — Merchants drop off at email verification → add reminder email at 48h
- **Admin bottleneck** — Manual business verification doesn't scale → define clear criteria to speed reviews
- **Gaming trusted status** — Sellers create fake transactions → require real PurchaseEvents with payment
- **False suspensions** — Bad admin action → require suspension reason; auto-create appeal ticket
