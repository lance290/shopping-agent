# Implementation Plan: PRD 04 — Seller Verification Pipeline

**Status:** Draft — awaiting approval  
**Priority:** P1 (build first — unblocks seller search, admin management, buyer trust)  
**Estimated effort:** 2-3 days  
**Depends on:** Nothing (all infrastructure exists)

---

## Goal

Make seller onboarding actually work:
1. Merchant registers → gets verification email
2. Clicks link → email confirmed → `status: "active"`, `verification_level: "email_verified"`
3. Admin reviews → approves → `verification_level: "business_verified"`
4. Track record criteria met → auto-promotes to `trusted`
5. Admin can suspend/unsuspend at any time
6. Buyers see verification badges on seller quotes

---

## Build Order

### Phase A: Backend Model + Migration (30 min)

**File: `apps/backend/models.py`**
- Add `MerchantVerification` model after `Merchant` (audit trail for all status transitions)

```python
class MerchantVerification(SQLModel, table=True):
    __tablename__ = "merchant_verification"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    merchant_id: int = Field(foreign_key="merchant.id", index=True)
    
    # What kind of verification event
    verification_type: str  # "email_sent", "email_verified", "admin_approved", "admin_rejected", "suspended", "unsuspended", "auto_trusted"
    
    # Token for email verification
    token: Optional[str] = Field(default=None, unique=True, index=True)
    token_expires_at: Optional[datetime] = None
    
    # Who performed this action (null for system actions)
    performed_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Reason/notes
    notes: Optional[str] = None
    
    # Previous state (for rollback/audit)
    previous_status: Optional[str] = None
    previous_verification_level: Optional[str] = None
    new_status: Optional[str] = None
    new_verification_level: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**File: `apps/backend/alembic/versions/p6_merchant_verification.py`**
- New migration: create `merchant_verification` table
- No changes to `merchant` table needed (fields already exist)

---

### Phase B: Email Verification Flow (1-2 hours)

**File: `apps/backend/services/email.py`** — add one function:

```python
async def send_merchant_verification_email(
    to_email: str,
    to_name: str,
    verification_token: str,
) -> EmailResult:
```

- Uses existing Resend integration
- Template: "Verify your email to complete your seller registration"
- CTA button: `{APP_BASE_URL}/merchants/verify-email?token={token}`
- Token expires in 72 hours

**File: `apps/backend/routes/merchants.py`** — modify `register_merchant()`:

After creating the merchant, add:
```python
# Generate verification token
token = generate_magic_link_token()
verification = MerchantVerification(
    merchant_id=merchant.id,
    verification_type="email_sent",
    token=token,
    token_expires_at=datetime.utcnow() + timedelta(hours=72),
    new_status="pending",
    new_verification_level="unverified",
)
session.add(verification)
await session.commit()

# Send verification email (non-blocking, don't fail registration)
try:
    await send_merchant_verification_email(
        to_email=merchant.email,
        to_name=merchant.contact_name,
        verification_token=token,
    )
except Exception as e:
    logger.warning(f"[MERCHANT] Verification email failed (non-fatal): {e}")
```

Also update the return message:
```python
return {
    "status": "registered",
    "merchant_id": merchant.id,
    "message": "Registration received. Check your email to verify your account.",
}
```

---

### Phase C: Verification Callback + Resend (1 hour)

**New file: `apps/backend/routes/merchant_verification.py`**

Three endpoints:

#### 1. `GET /merchants/verify-email?token=xxx`
- Look up `MerchantVerification` by token
- Check not expired (72h)
- Update `Merchant.status` → `"active"`, `Merchant.verification_level` → `"email_verified"`, `Merchant.verified_at` → now
- Create new `MerchantVerification` record (type: `"email_verified"`)
- Audit log the transition
- Return success JSON (frontend renders a confirmation page)

#### 2. `POST /merchants/resend-verification`
- Requires auth
- Find merchant for this user
- Check merchant is still `"pending"` / `"unverified"`
- Invalidate old token (or reuse if not expired)
- Generate new token, send new email
- Rate limit: max 3 resends per 24 hours

#### 3. `GET /merchants/verification-status`
- Requires auth
- Return current `status`, `verification_level`, `verified_at`, `reputation_score`
- Include `next_steps` array explaining what's needed for next level

Register router in `main.py`.

---

### Phase D: Admin Merchant Management (1-2 hours)

**File: `apps/backend/routes/admin.py`** — add 5 endpoints:

#### 1. `GET /admin/merchants`
- Query params: `?status=`, `?verification_level=`, `?page=`, `?per_page=`
- Returns paginated merchant list with counts per status
- Requires `require_admin`

#### 2. `GET /admin/merchants/{id}`
- Full merchant detail + verification history (all `MerchantVerification` records)
- Requires `require_admin`

#### 3. `POST /admin/merchants/{id}/approve`
- Sets `verification_level` → `"business_verified"`
- Sets `status` → `"verified"` (if currently `"active"`)
- Creates `MerchantVerification` record (type: `"admin_approved"`)
- Sends notification email to merchant
- Audit log
- Body: `{ "notes": "optional reason" }`

#### 4. `POST /admin/merchants/{id}/reject`
- Sets `status` → `"rejected"` (new status value)
- Creates `MerchantVerification` record (type: `"admin_rejected"`)
- Sends email with reason
- Body: `{ "reason": "required rejection reason" }`

#### 5. `POST /admin/merchants/{id}/suspend`
- Sets `status` → `"suspended"`
- Saves previous status/level for potential unsuspend
- Creates `MerchantVerification` record (type: `"suspended"`)
- Sends email with reason
- Body: `{ "reason": "required suspension reason" }`

#### 6. `POST /admin/merchants/{id}/unsuspend`
- Restores previous status/level
- Creates `MerchantVerification` record (type: `"unsuspended"`)
- Body: `{ "notes": "optional" }`

---

### Phase E: Fix Existing Bugs (30 min)

**File: `apps/backend/routes/seller.py`**

Modify `_get_merchant()` to enforce status check:
```python
async def _get_merchant(session: AsyncSession, user_id: int) -> Merchant:
    result = await session.exec(
        select(Merchant).where(Merchant.user_id == user_id)
    )
    merchant = result.first()
    if not merchant:
        raise HTTPException(403, "No merchant profile found. Register at /merchants/register first.")
    if merchant.status == "suspended":
        raise HTTPException(403, "Your merchant account is suspended. Contact support for assistance.")
    return merchant
```

**Decision: Should `pending` merchants be allowed to submit quotes?**

Option A: **Yes (recommended for MVP)** — Let them quote but show "unverified" badge. This keeps the marketplace active while verification is processing.

Option B: **No** — Block quoting until email verified. Cleaner trust signal but may kill early engagement.

**Recommendation:** Option A. Allow `pending` and `active` to quote. Only block `suspended`. Show badge to buyers.

**File: `apps/backend/routes/merchants.py`**

Fix `search_merchants()` to include `active` status:
```python
query = select(Merchant).where(Merchant.status.in_(["active", "verified"]))
```

---

### Phase F: Seller Dashboard Updates (1 hour)

**File: `apps/backend/routes/seller.py`**

Update `MerchantProfile` response model to include verification info:
```python
class MerchantProfile(BaseModel):
    id: int
    business_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    categories: Optional[str] = None
    service_areas: Optional[str] = None
    website: Optional[str] = None
    # NEW
    status: Optional[str] = None
    verification_level: Optional[str] = None
    verified_at: Optional[str] = None
    reputation_score: Optional[float] = None
```

Update `get_profile()` and `update_profile()` to include new fields.

**File: `apps/frontend/app/seller/page.tsx`**

Add verification status card to Profile tab:
- Show current level with appropriate badge/icon
- If `unverified`: "Check your email to verify" + resend button
- If `email_verified`: "Email verified ✉️ — Admin review pending"
- If `business_verified`: "Verified Business ✅"
- If `trusted`: "Trusted Seller ⭐"
- If `suspended`: red banner with contact support link

**File: `apps/frontend/app/merchants/register/page.tsx`**

Update success message: "Check your email to verify your account" instead of "We'll review your application."

---

### Phase G: Verification Email Landing Page (30 min)

**New file: `apps/frontend/app/merchants/verify-email/page.tsx`**

Simple page that:
1. Reads `?token=` from URL
2. Calls `GET /api/merchants/verify-email?token=xxx`
3. Shows success/expired/invalid state
4. Success: "Email verified! Go to your seller dashboard →"
5. Expired: "Link expired. Click to resend." + resend button

**New file: `apps/frontend/app/api/merchants/verify-email/route.ts`**

Proxy route to backend.

---

### Phase H: Wire Reputation Scoring (30 min)

**File: `apps/backend/routes/seller.py`** → `submit_quote()`

After the bid is created and committed, trigger reputation update:
```python
# Update seller reputation score
try:
    from services.reputation import update_merchant_reputation
    await update_merchant_reputation(session, merchant.id)
except Exception as e:
    logger.warning(f"[SELLER] Reputation update failed (non-fatal): {e}")
```

Also wire it into quote acceptance (when a buyer selects a seller's bid) — this is in `routes/bids.py` or wherever bid selection happens.

---

### Phase I: Frontend Proxy Routes (20 min)

New Next.js API routes (following existing pattern):

| Route file | Method | Proxies to |
|-----------|--------|-----------|
| `app/api/merchants/verify-email/route.ts` | GET | `/merchants/verify-email` |
| `app/api/merchants/resend-verification/route.ts` | POST | `/merchants/resend-verification` |
| `app/api/merchants/verification-status/route.ts` | GET | `/merchants/verification-status` |
| `app/api/admin/merchants/route.ts` | GET | `/admin/merchants` |
| `app/api/admin/merchants/[id]/approve/route.ts` | POST | `/admin/merchants/{id}/approve` |
| `app/api/admin/merchants/[id]/reject/route.ts` | POST | `/admin/merchants/{id}/reject` |
| `app/api/admin/merchants/[id]/suspend/route.ts` | POST | `/admin/merchants/{id}/suspend` |
| `app/api/admin/merchants/[id]/unsuspend/route.ts` | POST | `/admin/merchants/{id}/unsuspend` |

---

### Phase J: Tests (1-2 hours)

**New file: `apps/backend/tests/test_seller_onboarding.py`**

Using existing test patterns from `test_phase4_integration.py`:

| # | Test | Endpoint | Expected |
|---|------|----------|----------|
| 1 | Register merchant (happy path) | `POST /merchants/register` | 200, status=pending, verification email sent |
| 2 | Register requires auth | `POST /merchants/register` | 401 |
| 3 | Register duplicate email | `POST /merchants/register` | 409 |
| 4 | Register duplicate user | `POST /merchants/register` | 409 |
| 5 | Verify email (valid token) | `GET /merchants/verify-email?token=xxx` | 200, merchant.status=active |
| 6 | Verify email (expired token) | `GET /merchants/verify-email?token=xxx` | 400, "expired" |
| 7 | Verify email (invalid token) | `GET /merchants/verify-email?token=bad` | 404 |
| 8 | Resend verification | `POST /merchants/resend-verification` | 200 |
| 9 | Verification status (unverified) | `GET /merchants/verification-status` | status=pending, level=unverified |
| 10 | Verification status (verified) | `GET /merchants/verification-status` | status=active, level=email_verified |
| 11 | Admin list merchants | `GET /admin/merchants` | 200, list with counts |
| 12 | Admin list requires admin | `GET /admin/merchants` | 403 for non-admin |
| 13 | Admin approve | `POST /admin/merchants/{id}/approve` | merchant.verification_level=business_verified |
| 14 | Admin reject | `POST /admin/merchants/{id}/reject` | merchant.status=rejected |
| 15 | Admin suspend | `POST /admin/merchants/{id}/suspend` | merchant.status=suspended |
| 16 | Admin unsuspend | `POST /admin/merchants/{id}/unsuspend` | previous status restored |
| 17 | Suspended merchant can't quote | `POST /seller/quotes` | 403 |
| 18 | Pending merchant CAN quote | `POST /seller/quotes` | 200 (per Option A) |
| 19 | Merchant search returns active+verified | `GET /merchants/search` | Only active/verified merchants |
| 20 | Profile includes verification fields | `GET /seller/profile` | status, verification_level in response |

---

## Files Changed Summary

| File | Change Type | Lines Est. |
|------|------------|-----------|
| `apps/backend/models.py` | Add `MerchantVerification` model | +25 |
| `apps/backend/services/email.py` | Add `send_merchant_verification_email()` | +60 |
| `apps/backend/routes/merchants.py` | Wire verification email on register, fix search | +25, ~5 modified |
| `apps/backend/routes/merchant_verification.py` | **New file** — verify, resend, status | ~150 |
| `apps/backend/routes/admin.py` | Add 6 merchant management endpoints | +200 |
| `apps/backend/routes/seller.py` | Fix `_get_merchant()`, update `MerchantProfile` | ~20 modified |
| `apps/backend/main.py` | Register new router | +2 |
| `apps/backend/alembic/versions/p6_merchant_verification.py` | **New file** — create table | ~30 |
| `apps/backend/tests/test_seller_onboarding.py` | **New file** — 20 tests | ~400 |
| `apps/frontend/app/merchants/register/page.tsx` | Update success message | ~5 modified |
| `apps/frontend/app/merchants/verify-email/page.tsx` | **New file** — verification landing | ~80 |
| `apps/frontend/app/seller/page.tsx` | Add verification status to profile tab | ~40 |
| `apps/frontend/app/api/merchants/verify-email/route.ts` | **New file** — proxy | ~15 |
| `apps/frontend/app/api/merchants/resend-verification/route.ts` | **New file** — proxy | ~15 |
| `apps/frontend/app/api/merchants/verification-status/route.ts` | **New file** — proxy | ~15 |
| `apps/frontend/app/api/admin/merchants/route.ts` | **New file** — proxy | ~15 |
| `apps/frontend/app/api/admin/merchants/[id]/approve/route.ts` | **New file** — proxy | ~15 |
| `apps/frontend/app/api/admin/merchants/[id]/reject/route.ts` | **New file** — proxy | ~15 |
| `apps/frontend/app/api/admin/merchants/[id]/suspend/route.ts` | **New file** — proxy | ~15 |
| `apps/frontend/app/api/admin/merchants/[id]/unsuspend/route.ts` | **New file** — proxy | ~15 |

**Total:** ~1,150 lines across 21 files (10 new, 11 modified)

---

## Open Questions (Need Decision)

1. **Should pending merchants be able to quote?** (Recommended: Yes, with "unverified" badge)
2. **Should we add `"rejected"` as a new Merchant.status value?** (Recommended: Yes — distinct from `"suspended"`)
3. **Auto-promotion to `trusted`**: implement now or defer? (Recommended: Defer — no merchants will meet criteria yet)
4. **Admin notification on new registration**: email or in-app? (Recommended: Both — email via existing service + in-app via `create_notification()`)
5. **Verification badge on buyer-facing offer tiles**: implement in this phase or separate? (Recommended: This phase, but keep it simple — just a small icon)

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Email delivery fails (Resend not configured) | Medium | Already handled — demo mode logs to console |
| Migration fails on existing data | Low | No schema changes to `merchant` table — only new table |
| Existing tests break | Low | We're adding, not changing, existing endpoints |
| Seller confusion about verification steps | Medium | Clear messaging in email + dashboard + registration success page |
