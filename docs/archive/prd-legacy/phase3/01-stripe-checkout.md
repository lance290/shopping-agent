# PRD: Stripe Checkout Integration

**Phase:** 3 — Closing the Loop  
**Priority:** P0  
**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Parent:** [Phase 3 Parent](./parent.md)

---

## 1. Problem Statement

The platform can source products, display tiles, and track affiliate clickouts — but **there is no way to complete a purchase within the platform**. The `PurchaseEvent` model exists with Stripe fields (`stripe_session_id`, `stripe_payment_intent_id`), but no Checkout Session is ever created. Buyers must click out to external merchant sites to buy.

This means:
- No revenue capture beyond affiliate commissions.
- No purchase confirmation or order tracking.
- The "Unified Closing Layer" promised in Phase 2 remains unbuilt for retail transactions.

---

## 2. Solution Overview

Wire Stripe Checkout into the existing tile flow:
1. **"Buy Now" button** on eligible `OfferTile` components.
2. Backend creates a **Stripe Checkout Session** with the product details.
3. Buyer completes payment on Stripe's hosted page.
4. Webhook confirms payment → `PurchaseEvent` record created → Row status updated.

For B2B/service quotes (where price is negotiated), the flow uses **Stripe Payment Links** or manual invoicing via the existing `DealHandoff` path.

---

## 3. Scope

### In Scope
- Stripe Checkout Session creation endpoint
- "Buy Now" button on OfferTile (retail products only, not service providers)
- Stripe webhook handler for `checkout.session.completed`
- `PurchaseEvent` creation on successful payment
- Row status update to "purchased" / "closed"
- Success/cancel redirect pages
- Purchase history visible on Board (status badge on row)

### Out of Scope
- Stripe Connect (marketplace payouts to sellers) — Phase 4
- Subscription billing — not applicable
- Refund flow — Phase 4
- Multi-item cart / combined checkout — Phase 4

---

## 4. User Stories

**US-01:** As a buyer, I want to click "Buy Now" on an offer tile so I can purchase the item without leaving the platform.

**US-02:** As a buyer, I want to see a confirmation after purchase so I know the transaction succeeded.

**US-03:** As the platform, I want every purchase logged as a `PurchaseEvent` so I can track GMV and attribution.

**US-04:** As the platform, I want affiliate clickout to remain the default for merchants where we don't handle checkout, so we don't break existing monetization.

---

## 5. Acceptance Criteria

| ID | Criteria |
|----|----------|
| AC-01 | Clicking "Buy Now" on a retail offer tile redirects to Stripe Checkout with correct product name, price, image, and currency. |
| AC-02 | After successful payment, buyer is redirected to a success page showing order confirmation. |
| AC-03 | A `PurchaseEvent` is created with `payment_method="stripe_checkout"`, correct `stripe_session_id`, `bid_id`, `row_id`, and `amount`. |
| AC-04 | The row's status updates to reflect the purchase. |
| AC-05 | If payment is cancelled, buyer returns to the board with no state change. |
| AC-06 | Service provider tiles and tiles without a price do NOT show "Buy Now". |
| AC-07 | The existing affiliate clickout path (`/api/out`) remains unchanged for tiles that don't support direct checkout. |

---

## 6. Technical Design

### 6.1 Backend: New Endpoint

```
POST /api/checkout/create-session
```

**Request:**
```json
{
  "bid_id": 42,
  "row_id": 7,
  "success_url": "https://app.buyanything.ai/?checkout=success&session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://app.buyanything.ai/?checkout=cancel"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_live_..."
}
```

**Logic:**
1. Look up `Bid` by `bid_id`, validate it exists and belongs to the user's row.
2. Create a Stripe Checkout Session:
   - `mode: "payment"`
   - `line_items`: one item with bid's `item_title`, `price`, `currency`, `image_url`
   - `metadata`: `{ bid_id, row_id, user_id }`
   - `success_url` / `cancel_url` from request
3. Return the session URL.

### 6.2 Backend: Webhook Handler

```
POST /api/webhooks/stripe
```

**Logic:**
1. Verify webhook signature using `STRIPE_WEBHOOK_SECRET`.
2. On `checkout.session.completed`:
   - Extract `bid_id`, `row_id`, `user_id` from `metadata`.
   - Create `PurchaseEvent` with `payment_method="stripe_checkout"`.
   - Update Row status.
   - Create `AuditLog` entry.
3. Return 200.

### 6.3 Frontend: "Buy Now" Button

In `OfferTile.tsx`, add a "Buy Now" button:
- **Show condition:** `!isServiceProvider && safePrice > 0 && offer.bid_id`
- **Click handler:** POST to `/api/checkout/create-session`, then `window.location.href = checkout_url`.
- **Loading state:** Show spinner while session is being created.

### 6.4 Frontend: Success Page

Handle `?checkout=success` query param in `page.tsx`:
- Show a confirmation toast or modal.
- Refresh the row to reflect updated status.

### 6.5 Existing Models (no changes needed)

The `PurchaseEvent` model already has all required fields:
- `stripe_session_id`, `stripe_payment_intent_id`
- `bid_id`, `row_id`, `user_id`
- `amount`, `currency`, `payment_method`, `status`

---

## 7. Environment Variables Required

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Stripe API secret key (sk_live_... or sk_test_...) |
| `STRIPE_WEBHOOK_SECRET` | Webhook endpoint signing secret (whsec_...) |
| `STRIPE_PUBLISHABLE_KEY` | For frontend (if needed for Elements — not needed for Checkout redirect) |

See [SETUP-GUIDE.md](./SETUP-GUIDE.md) for configuration instructions.

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Checkout conversion rate (click Buy Now → complete payment) | >5% within first month |
| PurchaseEvent records created per week | >0 (proves the flow works) |
| Webhook delivery success rate | >99% |
| Zero orphaned sessions (created but never resolved) | Monitored via Stripe Dashboard |

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Stripe account not approved for live payments | Use test mode for development; apply early |
| Price mismatch between tile and checkout | Pull price from Bid record at session creation time, not from frontend |
| Webhook delivery failures | Implement idempotent handler; Stripe retries automatically |
| Users double-clicking Buy Now | Disable button after first click; check for existing session |

---

## 10. Implementation Checklist

- [ ] Install `stripe` Python package in backend
- [ ] Create `POST /api/checkout/create-session` endpoint
- [ ] Create `POST /api/webhooks/stripe` endpoint
- [ ] Add Stripe env vars to `.env.example`
- [ ] Add "Buy Now" button to `OfferTile.tsx`
- [ ] Add success/cancel query param handling to `page.tsx`
- [ ] Add frontend API proxy route `/api/checkout/` → backend
- [ ] Write tests for checkout session creation
- [ ] Write tests for webhook handler
- [ ] Test end-to-end with Stripe test mode
