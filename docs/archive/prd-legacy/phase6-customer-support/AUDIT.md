# Phase 6 Codebase Audit — Seller Onboarding & Support Infrastructure

**Date:** 2026-02-07  
**Auditor:** Cascade  
**Scope:** Every file that touches seller registration, verification, quoting, admin management, and buyer-seller interaction.

---

## 1. Current Seller Journey (What Actually Happens)

### Step 1: Registration (`/merchants/register`)

**Frontend:** `apps/frontend/app/merchants/register/page.tsx`
- Clean registration form: business name, contact name, email, phone, website, categories
- Requires authentication (checks `getMe()`)
- On success, shows: *"We'll review your application and contact you within 1-2 business days."*
- **Problem:** Nobody reviews anything. Nobody contacts anyone.

**Backend:** `apps/backend/routes/merchants.py` → `register_merchant()`
- Creates `Merchant` with `status="pending"`, `verification_level="unverified"`
- Creates or links `Seller` record for bid attribution
- Returns: `"Registration received. You will be contacted for verification."`
- **Problem:** That's where it ends. No email sent. No verification token. No admin notification.

### Step 2: Seller Dashboard (`/seller`)

**Frontend:** `apps/frontend/app/seller/page.tsx`
- Three tabs: Inbox, Quotes, Profile
- Fetches from `/api/seller/inbox`, `/api/seller/quotes`, `/api/seller/profile`
- If no merchant profile → shows "Register as Merchant" link
- **No verification status shown anywhere**
- **No verification badge on the profile tab**

**Backend:** `apps/backend/routes/seller.py`
- `_get_merchant()` helper: looks up `Merchant` by `user_id`, raises 403 if not found
- **Does NOT check `status` or `verification_level`** — a "pending" merchant can do everything a "verified" one can
- `seller_inbox()`: matches RFPs by category, returns them
- `submit_quote()`: creates `SellerQuote` + converts to `Bid` + notifies buyer
- `get_profile()` / `update_profile()`: basic CRUD
- Bookmarks: CRUD for saving RFPs

### Step 3: Merchant Search (used by sourcing)

**Backend:** `apps/backend/routes/merchants.py` → `search_merchants()`
- Filters by `Merchant.status == "verified"` only
- **Since no merchant ever becomes "verified", this always returns zero results**
- This means registered merchants are never prioritized in sourcing

### Step 4: Stripe Connect Onboarding

**Backend:** `apps/backend/routes/merchants.py` → `start_stripe_connect_onboarding()`
- Creates Stripe Express account, returns onboarding URL
- Updates `merchant.stripe_account_id` and `stripe_onboarding_complete`
- **Does NOT update `status` or `verification_level` after Stripe onboarding completes**

---

## 2. Model Analysis

### `Merchant` model (`models.py:681-723`)

```
status: str = "pending"                    # pending, verified, suspended — NEVER TRANSITIONS
verification_level: str = "unverified"     # unverified, email_verified, identity_verified, premium — NEVER TRANSITIONS
verified_at: Optional[datetime] = None     # NEVER SET
reputation_score: float = 0.0             # EXISTS but services/reputation.py never called
```

Fields exist, nothing uses them.

### `services/reputation.py` (180 lines)

- `compute_reputation()` — fully implemented, 5-dimension weighted score
- `update_merchant_reputation()` — computes + persists score
- **Nothing in the entire codebase calls either function**
- Tested in `test_phase4_integration.py` (unit level), but never invoked at runtime

---

## 3. What's Broken (Bugs)

| # | Bug | Impact | File |
|---|-----|--------|------|
| B1 | `search_merchants()` filters by `status == "verified"` but no merchant ever reaches that status | Registered merchants never appear in sourcing results | `routes/merchants.py:175` |
| B2 | `_get_merchant()` doesn't check merchant status — suspended/pending merchants can submit quotes | No quality gate for sellers | `routes/seller.py:83-94` |
| B3 | Registration success message promises review ("contact you within 1-2 business days") but nothing happens | Misleading UX, broken trust | `merchants/register/page.tsx:121` |
| B4 | `reputation.py` exists but is dead code — never called | Reputation scores are always 0.0 | N/A |

---

## 4. What's Missing (Gaps)

| # | Gap | Severity | Notes |
|---|-----|----------|-------|
| G1 | **Email verification flow** — no token, no email, no callback | Critical | Model has `verified_at` but nothing sets it |
| G2 | **Admin merchant management** — no list, approve, reject, suspend endpoints | Critical | Admin can see `total_merchants` count in stats but can't act on them |
| G3 | **Status transition logic** — no code transitions `pending` → anything | Critical | Status field is cosmetic |
| G4 | **Verification badge** — frontend never shows verification level | Medium | `MerchantProfile` response model doesn't include `status` or `verification_level` |
| G5 | **Admin notification on new registration** — nobody knows when a merchant registers | Medium | Could use existing email service |
| G6 | **Reputation score trigger** — no hook on transaction events | Medium | `update_merchant_reputation()` exists but is never called |
| G7 | **Auto-promotion criteria** — no logic for `business_verified` → `trusted` | Low | Future phase |

---

## 5. Existing Infrastructure We Can Leverage

| Asset | Location | State | Can Reuse? |
|-------|----------|-------|-----------|
| Email service (Resend) | `services/email.py` | Working (sends outreach, handoff, triage emails) | ✅ Yes — add `send_verification_email()` |
| `generate_magic_link_token()` | `models.py:25-27` | Working | ✅ Yes — reuse for verification tokens |
| `require_admin` dependency | `dependencies.py:56-81` | Working | ✅ Yes — for admin merchant endpoints |
| `Notification` model + `create_notification()` | `routes/notifications.py` | Working | ✅ Yes — notify admin on new registration |
| `AuditLog` model + `audit_log()` | `audit.py` | Working | ✅ Yes — log all status transitions |
| Alembic migrations | `alembic/versions/` | Working (34 migrations) | ✅ Yes — add new migration |
| `services/reputation.py` | Complete, tested | Dead code | ✅ Yes — just need to call it |

---

## 6. Frontend Proxy Routes Needed

The frontend proxies all backend calls through Next.js API routes. Existing pattern:

```
/api/seller/inbox    → backend /seller/inbox
/api/seller/quotes   → backend /seller/quotes
/api/seller/profile  → backend /seller/profile
/api/merchants/register → backend /merchants/register
```

New routes needed:
```
/api/merchants/verify-email        → backend /merchants/verify-email
/api/merchants/resend-verification → backend /merchants/resend-verification
/api/merchants/verification-status → backend /merchants/verification-status
/api/admin/merchants               → backend /admin/merchants
/api/admin/merchants/[id]/approve  → backend /admin/merchants/{id}/approve
/api/admin/merchants/[id]/reject   → backend /admin/merchants/{id}/reject
/api/admin/merchants/[id]/suspend  → backend /admin/merchants/{id}/suspend
```

---

## 7. Test Coverage Snapshot

| Test File | Count | Covers |
|-----------|-------|--------|
| `test_phase4_integration.py` | 28 tests | Signals, bookmarks, notifications, admin metrics, clickout, outreach |
| `test_reputation.py` (inferred) | 4 tests | Maturity scoring, verification scoring, unknown level |
| Seller-specific endpoint tests | **0** | No direct tests for `/seller/inbox`, `/seller/quotes`, `/seller/profile` |
| Merchant registration tests | **0** | No tests for `/merchants/register` |
| Admin merchant management tests | **0** | No admin merchant tests (endpoints don't exist yet) |

**Test gap is significant.** The entire seller/merchant surface has zero HTTP integration tests.
