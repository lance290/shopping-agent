# PRD: EA Payout Onboarding via Stripe Connect

**Audience:** Engineering / product review  
**Status:** Draft  
**Product:** Buy Anything  
**Depends on:** PRD 02 (EA Quote-to-Payment Flow)  
**Primary goal:** Make it stupid easy for an EA-sourced vendor to get set up to receive payouts, so the quote-to-payment pipeline never stalls on "vendor can't get paid."

---

## 1. Summary

PRD 02 implemented the quote-to-payment bridge: once a deal reaches `terms_agreed`, the buyer can fund escrow via Stripe Checkout. But that Checkout session only routes money to the vendor if the vendor has a completed Stripe Connected Account (`stripe_account_id` + `stripe_onboarding_complete = true`).

Today, Connect onboarding exists but is only reachable through the **self-service merchant registration flow** (`/merchants/register` → `/seller` dashboard). Vendors discovered through search or outreach — the primary EA pipeline — have no path to get onboarded unless someone manually creates a merchant profile for them first.

This spec closes that gap so:
- the system knows when a vendor can't receive payouts and surfaces that clearly
- the EA or platform can trigger a vendor onboarding invite
- the vendor completes Stripe-hosted onboarding with minimal friction
- the deal pipeline automatically unblocks once onboarding is complete
- duplicate onboarding code paths are consolidated

---

## 2. Current State (Audit Findings)

### What already exists

| Component | Location | Status |
|-----------|----------|--------|
| Express account creation | `routes/stripe_connect.py` | Works, but requires existing Merchant profile |
| Onboarding link generation | `routes/stripe_connect.py` + `routes/merchants.py` | **Duplicated** — two separate endpoints do the same thing |
| Onboarding status check | `routes/stripe_connect.py` + `routes/merchants.py` | **Duplicated** |
| Vendor model fields | `models/bids.py` (Vendor) | `stripe_account_id`, `stripe_onboarding_complete`, `default_commission_rate` exist |
| Merchant registration UI | `/merchants/register` | Works for self-service sellers |
| Seller dashboard | `/seller` | Shows inbox, quotes, profile — no Stripe status |
| Deal funding route | `routes/deals.py` | Checks `vendor.stripe_account_id` and `stripe_onboarding_complete` for Connect routing |
| Checkout webhook | `routes/checkout.py` | Handles `checkout.session.completed` for deal escrow |

### What's missing or broken

| Gap | Impact |
|-----|--------|
| No vendor-invite-to-onboard flow | EA can negotiate a deal with a vendor found via search, but that vendor has no Stripe account and no way to get one without self-registering |
| No `account.updated` webhook handler | Platform doesn't learn when a vendor completes Stripe onboarding unless someone manually polls `/connect/status` |
| Duplicate onboarding endpoints | `stripe_connect.py` and `merchants.py` both create Express accounts and generate AccountLinks — maintenance risk and confusion |
| No deal-level "vendor not onboarded" signal | When a deal reaches `terms_agreed` but the vendor can't receive funds, neither the EA nor buyer is told why funding won't route correctly |
| Seller dashboard doesn't show Stripe status | A registered merchant has no visibility into whether their Stripe onboarding is complete |
| No admin/EA trigger for vendor onboarding | Only the vendor themselves can initiate onboarding, and only after self-registering |

---

## 3. Problem Statement

The quote-to-payment flow (PRD 02) works end-to-end when the vendor has a completed Stripe Connected Account. But EA-sourced vendors — the primary revenue path — typically don't have one.

Without a frictionless onboarding path:
- deals stall at `terms_agreed` because the platform can't route funds
- EAs have to manually coordinate vendor Stripe setup outside the product
- the buyer sees a `Fund Escrow` button that silently falls back to platform-only collection

The fix must be:
1. detect when a vendor needs onboarding
2. let the EA or platform trigger it
3. make the vendor's onboarding experience one-click
4. automatically unblock the deal once onboarding completes

---

## 4. Goals

### Goals
- Consolidate duplicate Stripe Connect onboarding code into a single backend path
- Surface vendor onboarding status in the deal/row payload so the UI can act on it
- Allow EAs to send a vendor onboarding invite (email with a Stripe-hosted onboarding link)
- Allow vendors to complete onboarding from a single link without creating a BuyAnything account first
- Handle the `account.updated` Stripe webhook to sync onboarding completion automatically
- Show the EA when a deal is blocked on vendor onboarding vs. ready to fund
- Show registered merchants their Stripe Connect status in the seller dashboard

### Non-goals
- Custom (non-Stripe-hosted) onboarding UI — use Stripe's hosted flow
- KYB/KYC logic beyond what Stripe handles
- Multi-currency payout configuration in this phase
- Vendor payout scheduling (Stripe handles this automatically)
- Express Dashboard embedding (future phase)

---

## 5. User Experience

### 5.1 EA triggers vendor onboarding
1. EA has a deal in `terms_agreed` with a vendor who hasn't completed Stripe onboarding.
2. The row/SDUI shows a status indicator: "Vendor payout setup incomplete."
3. The `Fund Escrow` button is still visible but includes a note: funds will be held until vendor setup is complete (or: the button prompts the EA to invite the vendor first).
4. The EA clicks "Invite Vendor to Connect" (or equivalent).
5. The backend creates an Express Connected Account for the vendor (using their email from the Vendor record) and sends an onboarding email with a Stripe-hosted link.
6. The vendor receives the email, clicks through, completes Stripe's identity + bank account flow.
7. Stripe fires `account.updated` → the platform marks `stripe_onboarding_complete = true`.
8. The next row fetch shows the vendor as onboarded. The `Fund Escrow` button now routes funds to the vendor via Connect.

### 5.2 Self-service merchant flow (existing, improved)
1. Vendor registers at `/merchants/register` (unchanged).
2. Vendor visits the seller dashboard → profile tab.
3. Profile tab now shows Stripe Connect status:
   - Not connected → "Set up payouts" button → Stripe-hosted onboarding
   - Pending → "Complete setup" button → resume onboarding
   - Complete → green badge, earnings summary
4. After onboarding, deals with this vendor automatically route via Connect.

### 5.3 Webhook-driven status sync
1. Vendor completes Stripe onboarding (or updates bank details later).
2. Stripe sends `account.updated` to the platform webhook endpoint.
3. Platform updates `Vendor.stripe_onboarding_complete` based on `charges_enabled`.
4. No manual polling required.

---

## 6. Backend Requirements

### 6.1 Consolidate onboarding endpoints
- Remove duplicate onboarding logic from `routes/merchants.py` (lines 188–285)
- Keep the canonical onboarding in `routes/stripe_connect.py`
- Update all frontend callers to use the canonical path

### 6.2 Vendor-direct onboarding (no Merchant profile required)
Add a new endpoint that creates a Stripe Express account directly from a Vendor record:

```
POST /stripe-connect/onboard-vendor
Body: { "vendor_id": 45 }
Auth: EA must be authenticated
```

Behavior:
- Look up `Vendor` by ID
- If vendor already has `stripe_account_id`, generate a new AccountLink
- If not, create an Express account using vendor's email/name, store `stripe_account_id`
- Return `{ onboarding_url, account_id }`

### 6.3 Vendor onboarding invite email
After creating the onboarding link, optionally send an email to the vendor with:
- the Stripe-hosted onboarding URL
- a clear explanation: "BuyAnything needs you to complete payout setup to receive payment for Deal #X"
- the agreed deal amount for context

### 6.4 `account.updated` webhook handler
Add a handler for the Stripe `account.updated` event:

```
POST /api/webhooks/stripe-connect
```

Behavior:
- Verify Stripe webhook signature
- Extract `account.id` and `charges_enabled`
- Find the Vendor with matching `stripe_account_id`
- If `charges_enabled` is true and `stripe_onboarding_complete` is false, update to true
- If `charges_enabled` is false and `stripe_onboarding_complete` is true, update to false

### 6.5 Deal payload: vendor onboarding status
Extend the `active_deal` summary returned in the row payload:

```json
{
  "active_deal": {
    ...existing fields...,
    "vendor_stripe_onboarded": true,
    "vendor_name": "NetJets"
  }
}
```

### 6.6 SDUI augmentation
When a deal is in `terms_agreed` and `vendor_stripe_onboarded` is false:
- Add a warning badge: "Vendor payout setup incomplete"
- Add an action: `invite_vendor_connect` with `vendor_id` and `deal_id`
- The `fund_escrow` button should still appear but with a note that funds will be held on platform until vendor onboarding completes

---

## 7. Frontend Requirements

### 7.1 ActionRow: new intent
Add `invite_vendor_connect` intent handling:
- Calls `POST /stripe-connect/onboard-vendor` with the vendor ID
- Shows a confirmation: "Onboarding invite sent to [vendor email]"
- Refreshes row

### 7.2 Seller dashboard: Stripe status
In the `/seller` profile tab:
- Show Stripe Connect status (not connected / pending / complete)
- "Set up payouts" or "Complete setup" button that calls the existing onboarding endpoint
- After returning from Stripe, poll `/connect/status` and update UI

### 7.3 Deal card: vendor status
When `vendor_stripe_onboarded` is false and deal is `terms_agreed`:
- Show a yellow/amber badge: "Vendor payout setup needed"
- Show the invite action alongside the fund action

---

## 8. Acceptance Criteria

### Backend
- Duplicate onboarding code in `merchants.py` is removed; single canonical path in `stripe_connect.py`
- `POST /stripe-connect/onboard-vendor` creates or reuses a Connected Account for any Vendor by ID
- `account.updated` webhook syncs `stripe_onboarding_complete` without manual polling
- Row payload includes `vendor_stripe_onboarded` in the active deal summary
- SDUI augmentation shows vendor status warning and invite action when vendor isn't onboarded

### Frontend
- `invite_vendor_connect` action works from the ActionRow
- Seller dashboard profile tab shows Stripe Connect status and onboarding CTA
- Deal card shows vendor onboarding status when relevant

### End-to-end
- An EA can take a vendor from "no Stripe account" to "onboarded and ready to receive funds" without leaving the product
- The deal pipeline automatically detects onboarding completion and unblocks fund routing
- Self-service merchants can also complete onboarding from the seller dashboard

---

## 9. Testing Plan

### Backend
- Create a Vendor without `stripe_account_id`
- Call `POST /stripe-connect/onboard-vendor` and verify account creation + link generation
- Simulate `account.updated` webhook and verify `stripe_onboarding_complete` updates
- Verify row payload includes `vendor_stripe_onboarded: false` for un-onboarded vendors
- Verify SDUI includes invite action for `terms_agreed` deals with un-onboarded vendors

### Frontend
- Render a row with `terms_agreed` deal where vendor is not onboarded
- Verify warning badge and invite action appear
- Trigger invite and verify confirmation
- Render seller dashboard profile and verify Stripe status display

### Regression
- Existing merchant registration flow still works
- Existing deal funding flow still works for already-onboarded vendors
- Rows without deals render as before

---

## 10. Implementation Order

1. Consolidate duplicate onboarding endpoints
2. Add `POST /stripe-connect/onboard-vendor` for vendor-direct onboarding
3. Add `account.updated` webhook handler
4. Extend row payload with `vendor_stripe_onboarded`
5. Extend SDUI augmentation for vendor status + invite action
6. Add `invite_vendor_connect` frontend intent handler
7. Add Stripe status to seller dashboard profile tab
8. Verify end-to-end

---

## 11. Open Questions

1. Should the vendor onboarding email come from BuyAnything or from Stripe directly? (Stripe sends their own onboarding emails; we could just provide the link.)
2. Should we block the `Fund Escrow` button entirely when the vendor isn't onboarded, or allow funding with a note that payouts will be held?
3. Should vendor onboarding status be visible to the buyer, or only to the EA?
