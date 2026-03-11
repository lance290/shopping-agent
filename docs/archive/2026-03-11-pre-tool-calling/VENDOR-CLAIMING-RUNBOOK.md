# Vendor Claiming — Ops Runbook (Launch MVP)

## Purpose

Vendors discovered through search or outreach exist as records in the vendor directory before they know about BuyAnything. When a real vendor wants to manage their profile and/or onboard to Stripe Connect, an ops team member must manually verify ownership and link the vendor record to a user account.

## When This Happens

A vendor contacts BuyAnything (via email, outreach reply, or the merchant registration page) and says:
- "I received an RFP from your platform — how do I manage my profile?"
- "I want to accept payments through BuyAnything."

## Prerequisites

- The vendor must have created a user account (phone auth via `/auth/start`).
- The vendor record must already exist in the `vendor` table.

## Steps

### 1. Identify the vendor record

Find the vendor by name, email, or domain:

```sql
SELECT id, name, email, domain, user_id, stripe_account_id
FROM vendor
WHERE email ILIKE '%vendoremail.com%'
   OR domain ILIKE '%vendordomain.com%'
   OR name ILIKE '%Vendor Name%'
LIMIT 10;
```

### 2. Identify the user account

Find the user who is claiming:

```sql
SELECT id, email, phone_number, name, company
FROM "user"
WHERE email ILIKE '%vendoremail.com%'
   OR phone_number = '+1XXXXXXXXXX'
LIMIT 5;
```

### 3. Verify ownership

Before linking, verify the claimant owns the vendor identity:
- **Email match:** Vendor record email domain matches user email domain.
- **Domain match:** Vendor website domain matches the user's company or email.
- **Outreach thread:** The vendor replied to an outreach email from BuyAnything (check `outreach_message` table).

If none of these match, request additional proof (business card, LinkedIn, website admin screenshot).

### 4. Link user to vendor

```sql
UPDATE vendor
SET user_id = [USER_ID],
    status = 'verified',
    updated_at = NOW()
WHERE id = [VENDOR_ID]
  AND user_id IS NULL;
```

**Safety:** Only link if `user_id IS NULL` to prevent overwriting an existing claim.

### 5. Notify the vendor

Send a confirmation email:
- "Your vendor profile on BuyAnything has been verified."
- "You can now onboard to Stripe Connect to accept payments directly."
- Include link to `/seller/stripe-connect`

### 6. Stripe Connect onboarding

Once linked, the vendor can use the existing self-serve flow:
- `POST /stripe-connect/onboard` — creates Stripe Express account and returns onboarding URL.
- `GET /stripe-connect/status` — checks onboarding completion.

No ops intervention needed for this step.

## Edge Cases

### Vendor record doesn't exist
If the vendor is not in the directory, they should use `/merchants/register` to create a new profile. No claim needed.

### Multiple vendor records for same business
Identify the canonical record (most bids, most outreach, has embedding). Merge manually if needed, then link.

### Vendor already claimed by another user
Do NOT overwrite. Investigate — could be a duplicate account, shared business, or fraud attempt.

## Future: Self-Serve Claiming

This manual process will be replaced by a self-serve flow in a future PRD:
1. Vendor clicks "Claim this profile" on their vendor page.
2. System sends verification email to the vendor's on-file email.
3. Vendor clicks confirmation link → profile linked automatically.

Until that flow is built, all claims go through this manual runbook.
