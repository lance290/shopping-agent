# PRD: BuyAnything Stripe Zero-Fee Checkout, Webhook Hardening, and Vendor Claiming

## 1. Executive Summary

BuyAnything will keep Stripe Checkout and Stripe Connect available for vendors who want a smoother payment flow, but the platform fee must remain exactly `0%` at launch.

This PRD covers three launch-critical goals:

1. Preserve Stripe-powered checkout for vendors who want it.
2. Enforce the BuyAnything zero-fee policy in backend logic, tests, and merchant-facing behavior.
3. Harden the Stripe integration so it is safe to launch, including webhook verification and a manual vendor-profile claiming path.
4. **Crucially: Remove all Escrow liability.** We are not an escrow service, and any legacy paths facilitating "escrow funding" must be purged.

This is not a monetization PRD. It is a launch-readiness PRD for a zero-fee introduction platform that optionally supports vendor-owned Stripe checkout.

---

## 2. Product Decisions Locked By This PRD

### 2.1 Fee Policy
- BuyAnything charges `0%` platform fee at launch.
- Buyers pay the vendor price only.
- Vendors pay Stripe’s normal processing fees to Stripe, not to BuyAnything.
- No hidden markup, application fee skim, or service fee may be introduced in code, UI, or tests.

### 2.2 Payment Positioning & Escrow Removal
- BuyAnything is an introduction and workflow platform.
- Stripe checkout is optional merchant enablement, not a claim that BuyAnything is an escrow service or merchant of record.
- **Any existing code paths handling `deal_escrow` checkouts must be removed.** EAs will handle high-ticket payment routing off-platform.

### 2.3 Vendor Claiming
- Vendors discovered through search or outreach may already exist as records in the vendor directory.
- A vendor must be able to claim that existing profile.
- For launch, the claim workflow may be manual and ops-assisted.

---

## 3. Current Problems

### 3.1 Checkout fee ambiguity
Current checkout logic still computes commission metadata and `application_fee_amount` paths even though the policy is zero fee.

### 3.2 Escrow liability in code
`checkout.py` contains explicit handling for `checkout_type == "deal_escrow"`. This contradicts the zero-fee, non-intermediary policy.

### 3.3 Broken Stripe onboarding path
The main onboarding route references `merchant.business_name`, but the unified vendor model uses `name`.

### 3.4 Webhooks fail open
Both checkout and Stripe Connect webhook handlers skip signature verification when secrets are absent.

---

## 4. Desired Launch Behavior

### 4.1 Buyer checkout
If a priced bid belongs to a vendor with a completed Stripe Connect account:
- Buyer can use Stripe Checkout.
- Vendor receives funds through their connected Stripe account.
- BuyAnything takes `0%` application fee.

### 4.2 Vendor onboarding
A vendor with a claimed merchant profile can start Stripe onboarding without field mismatches or alias bugs.

### 4.3 Webhooks
- Non-local environments must fail closed if webhook secrets are missing or invalid.

### 4.4 Vendor claiming
For launch MVP:
- An internal ops/admin process can manually verify and attach a real merchant user to an existing vendor record.

---

## 5. Scope

### In scope
- Enforce zero platform fee in checkout session creation.
- **Delete all `deal_escrow` checkout paths and `EscrowStatus` UI components.**
- Fix Stripe onboarding bug(s) caused by unified vendor model drift.
- Harden Stripe webhook verification behavior.
- Define manual vendor claiming flow.

### Out of scope
- Introducing non-zero fees.
- Escrow or marketplace guarantees (these are actively being removed).

---

## 6. Functional Requirements

### 6.1 Zero-fee checkout
- `DEFAULT_PLATFORM_FEE_RATE` must not be used in BuyAnything checkout flows.
- `application_fee_amount` must be omitted or explicitly set to zero.

### 6.2 Escrow Removal
- Remove `if checkout_type == "deal_escrow"` blocks from webhook handlers.
- Remove UI components that claim funds are "Protected" or in "Escrow".

### 6.3 Merchant onboarding fix
- Replace invalid `merchant.business_name` references with the unified vendor field(s).

### 6.4 Secure webhooks
- Introduce explicit environment gating. Missing webhook secret must return an error in production.

---

## 7. Acceptance Criteria

### AC-1 Zero-fee enforcement & Escrow removal
- Checkout sessions never compute a non-zero BuyAnything fee.
- No escrow paths exist in the checkout router.

### AC-2 Onboarding works
- Stripe Connect onboarding can be started from a claimed merchant profile.

### AC-3 Webhooks are safe
- Production environments reject unsigned Stripe webhooks.

### AC-4 Vendor claiming is defined
- There is a written ops process for claiming a vendor profile.
