# PRD: EA Quote-to-Payment Flow

**Audience:** Engineering / product review  
**Status:** Draft  
**Product:** Buy Anything  
**Primary goal:** Turn an email-negotiated EA quote into a clear, actionable payment step inside the product, using the existing deal pipeline and Stripe flow.

---

## 1. Summary

The Executive Assistant workflow already supports quote negotiation through the Resend proxy email loop and deal pipeline.

Today, once the backend detects that a buyer and vendor have agreed on price and terms, the deal can transition to `terms_agreed`, but the system does not yet reliably surface that state to the EA in the two places where the next step matters most: the row UI and the email itself.

This spec defines the missing bridge:
- expose deal state in the row payload / SDUI generation path
- render a deal payment surface when a deal reaches `terms_agreed`
- surface the payment handoff inside the email thread itself
- allow the EA to manually mark terms as agreed when the parties are ready
- allow the EA to move the deal back into negotiation if agreement was detected too early
- give the EA a single clear action to fund escrow via Stripe
- refresh the UI as the deal progresses from `terms_agreed` to `funded`

This is not a redesign of the deal pipeline. It is an implementation spec for connecting the already-built backend state machine and webhook logic to the frontend UI.

---

## 2. Current State

### Already implemented
- The platform creates a `Deal` when outreach is sent through the authenticated EA workflow.
- Buyer/vendor email is proxied through a Resend alias.
- Inbound email replies are classified by the backend webhook.
- The deal state machine already supports:
  - `negotiating`
  - `terms_agreed`
  - `funded`
  - `in_transit`
  - `completed`
  - `disputed`
  - `canceled`
- Stripe-related deal funding routes already exist on the backend.

### Missing today
- The row response path does not reliably expose the relevant deal state to the frontend.
- The SDUI builder does not consistently render a payment-oriented block when `deal.status == "terms_agreed"`.
- The ActionRow does not consistently emit a `fund_escrow` action for agreed deals.
- The outbound email flow does not consistently surface a payment CTA or payment link once terms are agreed.
- The EA does not have a first-class manual control to mark terms agreed.
- The EA does not have a clean way to move a false-positive `terms_agreed` deal back to `negotiating`.
- The frontend does not yet complete the EA payment step from the SDUI surface for this flow.

---

## 3. Problem Statement

Once a quote is agreed over email, the EA should not have to guess what happens next.

The system must show, in both the row and the email thread:
- that a quote has been agreed
- what amount is being funded
- any summarized agreed terms
- a primary CTA to fund escrow / continue to payment

Without that bridge, the deal pipeline works internally but fails at the exact handoff where revenue should convert.

---

## 4. Goals

### Goals
- Surface the authoritative deal state for each row in the authenticated EA flow.
- Render a visible payment/status block in SDUI when the deal is active.
- Surface the same payment handoff in the proxied email experience once terms are agreed.
- Allow the EA to manually confirm that terms are agreed even if the classifier does not detect it.
- Allow the EA to explicitly continue negotiations if the agreement detection was premature.
- Show a primary `Fund Escrow` action when a deal reaches `terms_agreed`.
- Launch the existing Stripe funding flow from the frontend with minimal friction.
- Keep the row UI and email messaging updated after payment success or cancellation.

### Non-goals
- Rebuilding the email relay system.
- Replacing the deal state machine.
- Redesigning the full checkout architecture.
- Building a comprehensive dispute / fulfillment dashboard in this phase.
- Supporting unauthenticated public-search quote flows in this spec.

---

## 5. User Experience

### 5.1 Happy path
1. EA sends vendor outreach from the authenticated product.
2. Vendor and buyer negotiate over proxy email.
3. Backend classifies a reply as agreement and transitions the deal to `terms_agreed`, or the EA manually marks the deal as agreed.
4. The next row fetch or hydration shows a deal card / escrow status block in the product.
5. The next buyer-facing email touchpoint also surfaces a payment CTA or hosted payment link tied to the agreed deal.
6. The row UI clearly displays:
   - quote status
   - agreed amount
   - summarized terms if available
   - vendor identity when available
7. The primary CTA is `Fund Escrow`.
8. Clicking the CTA from the row or email launches the existing Stripe deal funding flow.
9. On successful funding, the row refreshes and the deal now appears as `funded`.
10. The CTA is replaced by a funded/in-progress status presentation in the row, and subsequent email messaging no longer asks the buyer to fund an unpaid deal.

### 5.2 False-positive / continued-negotiation path
1. The backend classifier marks a deal as `terms_agreed`, but the EA determines negotiations are still ongoing.
2. The row UI shows that the deal is currently treated as agreed, but also exposes a secondary control such as `Continue Negotiation` or `Not Agreed Yet`.
3. The EA uses that control to move the deal back to `negotiating`.
4. The row removes the payment CTA and returns to negotiation-oriented status messaging.
5. Buyer-facing email messaging also stops presenting the deal as ready to fund.

### 5.3 UX requirements
- The payment block must be visible without requiring the EA to inspect raw deal JSON or email history.
- The email itself must also clearly communicate that the quote is ready to fund.
- The CTA label must be explicit: `Fund Escrow` or `Pay Now`.
- The amount displayed must use the deal's agreed total when available.
- The block must not appear for rows that do not have an active deal.
- The block must not present a payment CTA for deals in `negotiating`, `canceled`, or `completed`.
- The email must not continue presenting an unpaid funding CTA once the deal is already `funded` or later.
- When a deal is in `negotiating`, the row should expose a control allowing the EA to manually mark terms agreed.
- When a deal is in `terms_agreed`, the row should expose a secondary control allowing the EA to continue negotiations.
- Email copy should avoid claiming the deal is definitively closed before payment succeeds.

---

## 6. Authoritative Data Rules

### 6.1 Deal selection per row
For this phase, the frontend should receive at most one "active deal summary" per row.

Recommended rule:
- choose the most recent non-canceled deal for that row
- prefer deals in these states, in order of importance:
  1. `terms_agreed`
  2. `funded`
  3. `in_transit`
  4. `completed`
  5. `negotiating`
  6. `disputed`
- if multiple deals are active, the UI should use the highest-priority / most recent deal and not render multiple payment cards in this phase

### 6.2 Amount selection
The payment UI should prefer:
1. `buyer_total` if already computed and present
2. otherwise `vendor_quoted_price`
3. otherwise no payment CTA, with status-only rendering

### 6.3 Terms summary
If `agreed_terms_summary` exists, show it in the payment/status block.
If not, the block still renders using status and amount alone.

---

## 7. Backend Requirements

### 7.1 Row payload must expose deal summary
The backend row response used by the authenticated app must expose a normalized deal summary sufficient for SDUI and direct rendering.

Recommended row-level shape:

```json
{
  "active_deal": {
    "id": 123,
    "status": "terms_agreed",
    "vendor_id": 45,
    "bid_id": 678,
    "vendor_quoted_price": 1200.0,
    "buyer_total": 1260.0,
    "currency": "USD",
    "agreed_terms_summary": "Delivery in 3 weeks. Includes framing.",
    "agreement_source": "auto_detected",
    "stripe_payment_intent_id": null,
    "terms_agreed_at": "2026-03-06T18:00:00Z",
    "funded_at": null
  }
}
```

Minimum required fields:
- `id`
- `status`
- `buyer_total` or `vendor_quoted_price`
- `currency`
- `agreed_terms_summary`
- `agreement_source` when available
- `terms_agreed_at`
- `funded_at`

### 7.2 SDUI builder must consume active deal state
The SDUI builder should incorporate `active_deal` when generating row UI.

Required behavior:
- if no active deal exists, SDUI behaves as it does today
- if active deal exists, inject a payment/status block into the schema
- if active deal status is `terms_agreed`, include a primary action for funding
- if active deal status is `terms_agreed`, also include a secondary action to continue negotiations
- if active deal status is `negotiating`, include an action that allows the EA to manually mark terms agreed
- if active deal status is `funded` or later, render status information instead of payment CTA

### 7.3 ActionRow intent
When `active_deal.status == "terms_agreed"`, the ActionRow must expose a machine-readable payment action.

Recommended intent:
- `fund_escrow`

Additional required intents:
- `mark_terms_agreed`
- `continue_negotiation`

Recommended payload:

```json
{
  "type": "action",
  "intent": "fund_escrow",
  "deal_id": 123,
  "label": "Fund Escrow",
  "amount": 1260.0,
  "currency": "USD"
}
```

Recommended reopen payload:

```json
{
  "type": "action",
  "intent": "continue_negotiation",
  "deal_id": 123,
  "label": "Continue Negotiation"
}
```

### 7.4 Email surfacing requirements
Once `active_deal.status == "terms_agreed"`, the deal pipeline should also surface the payment handoff in the email channel.

Required behavior:
- the buyer-facing email flow should include a clear payment CTA or hosted payment link tied to the agreed deal
- the email should show the agreed amount when available
- the email should include the agreed terms summary when available
- the email CTA must resolve to the same authoritative funding flow as the in-product row CTA
- once the deal is `funded` or later, subsequent emails must stop presenting the unpaid payment CTA

Recommended implementation shape:
- generate a canonical deal funding URL from the existing deal funding path or Stripe session bootstrap flow
- inject that URL into the appropriate buyer-facing email template or relay augmentation step after `terms_agreed`
- avoid requiring the recipient to manually search the product for the row in order to pay

### 7.5 Funding endpoint contract
The frontend should call the existing deal funding endpoint rather than inventing a new checkout path.

Expected backend behavior:
- validate user owns the row / deal
- validate the deal is in a payable state (`terms_agreed`)
- create the Stripe funding object / checkout session as implemented by the existing deal route
- return the redirect URL or session metadata required by the frontend

### 7.6 Manual agreement and reopen contract
The backend must support both:
- explicit EA transition from `negotiating` to `terms_agreed`
- explicit EA transition from `terms_agreed` back to `negotiating`

Required behavior:
- manual agreement should optionally accept agreed price and terms summary edits from the EA
- reopening negotiation should preserve message history and deal linkage
- reopening negotiation should remove payment CTAs from row/email surfaces derived from `terms_agreed`
- audit/system messaging should record whether the state change was AI-detected or user-initiated

---

## 8. Frontend Requirements

### 8.1 SDUI rendering
The frontend must render the injected deal payment/status block in the row view.

The block should display:
- status label
- amount
- terms summary when available
- primary CTA when payable
- secondary negotiation-state controls when applicable

### 8.2 CTA handling
When the user triggers `fund_escrow`:
- call the existing backend deal-funding endpoint
- redirect to Stripe Checkout or open the payment flow required by the returned payload
- on success / cancel, refresh row data so the latest deal state is shown

When the user triggers `mark_terms_agreed`:
- call the existing deal transition endpoint or equivalent backend contract
- allow the EA to confirm or edit amount / terms if the UX includes that step
- refresh row data so the latest status and CTA set is shown

When the user triggers `continue_negotiation`:
- call the backend transition path to return the deal to `negotiating`
- refresh row data so payment CTAs disappear

### 8.3 State handling
The frontend must handle these states:
- `negotiating`: show negotiation status, plus manual `mark_terms_agreed` action
- `terms_agreed`: show payment CTA and continue-negotiation action
- `funded`: show funded confirmation / next-step status
- `in_transit`: show in-transit status
- `completed`: show completed status
- `disputed`: show dispute status, no payment CTA
- `canceled`: either hide the block or show canceled status without action

### 8.4 Failure handling
If funding initiation fails:
- show a clear error message
- keep the row intact
- do not remove the CTA unless the deal state actually changed

---

## 9. Acceptance Criteria

### Backend
- Row fetches include a normalized active deal summary for relevant rows.
- SDUI generation uses the active deal summary when present.
- Rows with `terms_agreed` deals receive a `fund_escrow` action.
- Rows with `negotiating` deals can expose a manual `mark_terms_agreed` action.
- Rows with `terms_agreed` deals can expose a `continue_negotiation` action.
- Buyer-facing email flow includes a payment CTA or payment link when the deal reaches `terms_agreed`.
- Buyer-facing email flow stops showing an unpaid CTA after the deal is `funded`.
- Backend supports explicit transition from `terms_agreed` back to `negotiating`.
- The funding endpoint rejects deals not in a payable state.

### Frontend
- An EA viewing a row with a `terms_agreed` deal sees a visible payment card or status block.
- The block displays the agreed amount.
- Clicking `Fund Escrow` launches the Stripe funding flow.
- After successful funding, the UI refreshes and no longer shows the unpaid CTA.
- An EA viewing a negotiating deal can manually mark terms agreed.
- An EA viewing a false-positive `terms_agreed` deal can return it to negotiation.

### End-to-end
- A real deal progressed from email negotiation to `terms_agreed` becomes payable from both the row UI and the email flow without manual intervention.
- A real deal can be manually marked agreed by the EA without waiting for the classifier.
- A false-positive `terms_agreed` state can be safely reverted to `negotiating` without breaking the deal thread.

---

## 10. Testing Plan

### Backend verification
- Create or use a row with an associated deal in `negotiating`.
- Transition the deal to `terms_agreed` through the existing webhook path or test helper.
- Verify the row API returns `active_deal`.
- Verify the generated SDUI includes the payment/status block and `fund_escrow` action.
- Verify the buyer-facing email content includes a payment CTA or hosted funding link.
- Manually transition a deal from `negotiating` to `terms_agreed` and verify the same outputs appear.
- Transition a deal from `terms_agreed` back to `negotiating` and verify payment surfaces are withdrawn.

### Frontend verification
- Load a row with an attached `terms_agreed` deal.
- Confirm the CTA renders with the expected amount.
- Trigger the funding action and verify the Stripe flow launches.
- Return from Stripe and verify row state refreshes.
- Load a row with a `negotiating` deal and confirm the EA can manually mark terms agreed.
- Load a false-positive `terms_agreed` deal and confirm the EA can continue negotiation.

### Email verification
- Open or inspect the email generated after `terms_agreed`.
- Confirm it includes the agreed amount and a payment CTA or hosted funding link.
- Confirm the email CTA resolves into the same funding flow as the in-product CTA.
- After funding, confirm subsequent email messaging no longer presents an unpaid CTA.
- After reopening negotiation, confirm the email flow no longer presents the deal as ready to fund.

### Regression checks
- Rows without deals should render exactly as before.
- Negotiating deals should not show a payment CTA.
- Funded deals should not show a second payment CTA.
- Emails for negotiating deals should not prematurely include a payment CTA.
- Reopening negotiation should not break message history or deal retrieval.

---

## 11. Open Questions

1. Should the CTA label be `Fund Escrow` everywhere, or should some surfaces say `Pay Now`?
2. Should canceled/completed deals remain visible as status history in the row, or should only active/payable deals render?
3. If multiple deals exist for a row, is the priority rule in Section 6 sufficient for Phase 1, or does the product need a deal picker?
4. Should the frontend redirect directly to Stripe Checkout, or open a modal first with a final review step?
5. Should manual `mark_terms_agreed` require a confirmation modal with editable amount and terms, or be a one-click action when the data is already present?

---

## 12. Recommended Implementation Order

1. Expose `active_deal` on the row response, including agreement-source metadata when available.
2. Extend the backend transition model to support EA manual agreement and reopening negotiation.
3. Inject deal-aware status/payment UI into the SDUI builder.
4. Add `fund_escrow`, `mark_terms_agreed`, and `continue_negotiation` actions as appropriate.
5. Wire the frontend intent handlers to the existing deal funding and transition routes.
6. Verify end-to-end with real or seeded auto-detected, manually-agreed, and reopened-negotiation deals.

---

## 13. Decision Summary

This feature should be implemented as a thin integration layer between:
- the existing Resend-powered deal pipeline
- the existing deal state machine
- the existing Stripe funding path
- the existing SDUI frontend architecture

The key requirement is not new payment infrastructure. The key requirement is making the current deal state visible and actionable at the exact moment the EA is ready to fund the transaction.
