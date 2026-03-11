# PRD: PopSwaps Rebate Loop & Receipt Verification

## 1. Executive Summary
PopSwaps allows CPG brands to conquest competitor purchases by intercepting shopper intent *before* they buy. 
When a shopper builds a grocery list and adds a mainstream product (e.g., Lay's Chips), Pop presents a "PopSwap" offer for a better-for-you alternative (e.g., "$1.00 off Hippeas"). If the shopper buys that swap product at the store and scans their receipt, Pop handles the rebate payout and charges the CPG brand.

**Key difference from traditional rebates:** The shopper does not need to prove they previously bought the competitor product. The fact that they added the competitor to their list, saw the swap, and chose it demonstrates successful intent conquesting to the brand.

**Goal of this PRD:** Define the technical architecture and flow for the complete PopSwaps rebate loop, focusing heavily on secure money movement and robust receipt fraud detection.

---

## 2. Core Flows

### 2.1 The List-Building & Swap Presentation Flow

Pop's existing architecture handles swaps in two layers:
1. **Layer 1 (Organic):** LLM-classified cheaper alternatives from standard search results.
2. **Layer 2 (Sponsored/Explicit):** Injected offers from the `CouponProvider`.

This rebate flow explicitly enhances **Layer 2**.

1. **List Addition:** Shopper adds "Lay's Chips" to their Pop list.
2. **Offers Presentation:** Pop runs its standard search. Concurrently, the `CouponProvider` queries the new `Campaign` table. If it finds an active Hippeas campaign targeting Lay's (or the salty snacks category), it injects a synthetic `Bid` into the results.
3. **Implicit Acceptance (Purchase):** The injected Hippeas offer displays natively in the offers list. Its price is calculated as `(Base Price of Lay's) - (Campaign Payout)`. It features a prominent badge: *"Keep your receipt to claim your $1.00 rebate!"* No explicit "Accept" button is required; the shopper simply goes to the store, buys the PopSwap item instead of the original item, and uploads the receipt to claim the rebate.

### 2.2 Brand Campaign Funding Flow
Brands pre-fund their campaigns to ensure liquidity for payouts. Legally, these funds should be structured as **prepaid campaign credits**, not escrow in the strict regulated sense.
1. **Onboarding:** Brand signs up via Stripe Connect (`/stripe-connect/onboard` - *already built*).
2. **Campaign Creation:** Brand sets up a campaign (e.g., "Conquest Lay's") with a `start_date` and `end_date`.
3. **Funding:** Brand prepays campaign credits (e.g., $5,000 budget). Stripe charges their card.
4. **Treasury Handling:** Pop may sweep prepaid campaign credits into its operating or treasury accounts and capture any resulting float/yield while remaining contractually obligated to honor valid shopper rebates and unused-credit policies.
5. **Campaign Conclusion:** When the `end_date` is reached, active offers stop displaying. Any unspent budget remains in the vendor's platform balance to be rolled over to a new campaign, or is explicitly refunded to their original payment method via Stripe upon request.

**Initial contract requirement:** The vendor agreement must explicitly state that campaign funding is a prepaid credit purchase, that Pop may hold or sweep those funds into treasury/operating accounts, that Pop retains any associated float/interest, and that the vendor's economic rights are limited to campaign delivery plus any unused-credit refund or rollover terms defined in the contract.

### 2.3 Shopper Payout Flow
When a shopper earns a rebate, they need a secure way to receive it.
1. **Wallet Accumulation:** Rebates are initially credited to a virtual "Pop Wallet" balance.
2. **Cash Out Request:** Once the wallet reaches a minimum threshold (e.g., $5.00), the shopper requests a payout.
3. **Identity Verification (KYC):** For first-time cashouts, we must perform lightweight KYC (via Stripe Identity or Plaid) to prevent multi-account farming.
4. **Payout Rail:** We execute the payout through an approved shopper payout rail after recipient onboarding / verification. This should not assume a raw `stripe.Transfer` directly to an arbitrary consumer bank account.

---

## 3. Receipt Verification & Fraud Prevention

Receipt fraud is the largest attack vector in CPG loyalty programs. Scammers use Photoshop, AI generators, LCD screen photos, and duplicate submissions. 

### 3.1 Recommended Vendor: Veryfi
We strongly recommend using **Veryfi** (veryfi.com) for receipt OCR and fraud detection. They are the industry standard for CPG loyalty programs.

Reference links:
- Main site: `https://www.veryfi.com/`
- Receipt OCR API: `https://www.veryfi.com/receipt-ocr-api/`
- Fraud Detection: `https://www.veryfi.com/fraud-detection/`
- CPG Loyalty Programs: `https://www.veryfi.com/solutions/cpg-loyalty-program/`

**Why Veryfi over generic OCR (like Google Vision):**
- **Built-in Fraud API:** Detects digital tampering, AI-generated receipts, LCD screen photos (taking a picture of a digital receipt on another screen), and copy/paste modifications.
- **Line-Item Extraction:** Automatically parses line items, matching them against standard UPCs and product names, which is critical for verifying the exact swap product was purchased.
- **Velocity Checks:** Detects if the same receipt or identical purchasing patterns are being submitted rapidly across different accounts.

### 3.2 The Fraud Defense Pipeline

Every receipt scan must pass a multi-layered defense:

**Layer 1: Device & Context (Client-Side / Edge)**
- **Camera + Camera Roll + File Upload:** Users may submit receipts via live camera, camera roll, or file upload (required for online/email receipts). The `upload_source` is tracked on every submission for analytics and risk scoring.
- **Geolocation (when available):** Capture GPS coordinates at the time of scan. Flag receipts with major geo mismatches for manual review.
- **Receipt Freshness:** The receipt date must be within **7 days** of submission. Older receipts are rejected automatically.

**Layer 2: Image Forensics (Veryfi API)**
- Send image to Veryfi Fraud API.
- Reject if:
  - `is_tampered` == True
  - `is_screen` == True (photo of a screen)
  - EXIF metadata shows image manipulation software.

**Layer 3: Deduplication & Velocity (Backend)**
- **Strict Deduplication:** Hash the receipt data (Store + Date + Total + Transaction ID). If this hash exists in the DB, reject immediately.
- **Velocity Limits:** Max 5 receipts per day per user. Max 20 receipts per week.
- **Cross-Account Checks:** If the same payment card (last 4 digits on receipt) appears across multiple Pop accounts, flag all accounts for manual review.

**Layer 4: Line Item Verification (Business Logic)**
- Parse the Veryfi line items.
- Verify the required product (e.g., "HIPPEAS ORG CHKPEA PUFF") is present.
- Verify the purchase date is *after* the swap offer was presented to the user.

---

## 4. Required Database Models

To support this flow, the following tables must be added/updated:

### 4.1 `Campaign`
- `id`: PK
- `vendor_id`: FK to Vendor
- `name`: string
- `swap_product_name`: string
- `swap_product_image`: string (nullable)
- `swap_product_url`: string (nullable)
- `budget_total_cents`: integer
- `budget_remaining_cents`: integer
- `payout_per_swap_cents`: integer
- `target_categories`: string / CSV list for MVP matching
- `target_competitors`: string / CSV list for MVP matching
- `start_date`: datetime
- `end_date`: datetime
- `status`: string (active, paused, depleted, expired)

### 4.2 `Receipt`
- `id`: PK
- `user_id`: FK to User
- `image_hash`: string
- `store_name`: string
- `transaction_date`: datetime
- `total_amount`: float
- `fraud_score`: float (from Veryfi)
- `fraud_flags`: JSON (e.g., ["lcd_screen_detected"])
- `veryfi_document_id`: integer
- `raw_veryfi_json`: text / JSON blob for audit
- `status`: string (pending, verified, rejected, manual_review, duplicate, failed)
- `receipt_content_hash`: string (content-based deduplication)

### 4.3 `WalletTransaction`
- `id`: PK
- `user_id`: FK to User
- `amount_cents`: integer
- `source`: string (receipt_scan, campaign_rebate, debit_cashout, etc.)
- `receipt_id`: FK to Receipt (nullable)
- `campaign_id`: FK to Campaign (nullable, for credits)
- `created_at`: datetime

---

## 5. Implementation Phases

**Phase 1: Receipt Ingestion & OCR Sandbox**
- Integrate Veryfi API.
- Build / extend the `Receipt` model.
- Build an internal admin tool to upload receipts and view the Veryfi fraud analysis and line-item extraction to calibrate our confidence.

**Phase 2: The Wallet & Campaign Ledger**
- Build `Campaign` and `PopWallet` tables.
- Implement the logic: Verified Receipt -> Deduct Campaign Budget -> Credit PopWallet.

**Phase 3: Stripe Payouts**
- Integrate Stripe Connect Express (or Stripe Issuing) for shoppers.
- Build the "Cash Out" button flow, including lightweight identity verification to stop bot farms.

**Phase 4: Client-Side Security**
- Update the mobile app to enforce live-camera-only capture and capture device context (location, timestamp).
