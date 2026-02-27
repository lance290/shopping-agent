# PRD: Deal Pipeline & Proxy Messaging (The Prelier Model)

## 1. Overview & Objectives
**Goal:** Prevent platform leakage and capture monetization on high-value, human-led transactions (e.g., jet charters, luxury goods, bespoke services) by keeping buyer-seller communication and payments entirely on-platform.
**Strategy:** Implement an Airbnb/Craigslist-style proxy email system using Resend Inbound Routing, paired with a structured Deal State Machine and Stripe Connect escrow.
**Outcome:** Buyers and sellers negotiate via email, but our platform intercepts, records, and AI-analyzes the messages to seamlessly inject a "Deal Card" for 1-click escrow funding.

## 2. Core Architecture

### 2.1 The Proxy Email System (Resend Inbound Routing)
- **Unique Aliases:** When a buyer requests a quote, the backend generates a unique email alias (e.g., `quote-a7f9b2@messages.buy-anything.com`).
- **Inbound Webhook:** Resend catches any emails sent to this subdomain and POSTs the parsed JSON payload to our backend (`/api/webhooks/resend/inbound`).
- **Relay Mechanism:** 
  - When the **Vendor** replies to the alias, we relay the email to the **Buyer's** real email, setting the `Reply-To` back to the alias.
  - When the **Buyer** replies to the alias, we relay the email to the **Vendor's** real email.
- **Data Sanitization:**
  - Use `email-reply-parser` to strip out bloated historical threads. We only want the *new* text.
  - Download attachments from Resend, upload to our secure storage (Railway Volume/S3), and replace them with secure links in the relayed email.

### 2.2 System of Record (The GoDo Ledger)
- Every intercepted message is saved as plain text in the `Message` table.
- This creates an immutable audit trail for dispute resolution, trust & safety, and AI analysis.

### 2.3 The AI Intercept
- A lightweight LLM call evaluates the content of every inbound vendor message.
- **Trigger:** If the LLM detects "Terms Agreed" (e.g., "Yes, we can do $14,000 for that date" or "I've attached the final contract"), it flags the transaction state.
- **Action:** Instead of just relaying the text, the platform injects a **Deal Card / Checkout Link** into the relayed email:
  > *"The vendor has confirmed the terms. [Click Here to Secure Funds via Stripe]"*

### 2.4 The Deal Card & Stripe Escrow
- **Deal Card UI:** A structured UI component in the buyer's Workspace showing the item, agreed price, and terms.
- **Escrow:** The buyer pays via Stripe. Funds are held in a connected account or platform escrow.
- **Take Rate:** Platform subtracts the concierge/platform fee (e.g., 1%) and holds the rest.
- **Payout:** Funds are released to the vendor only when fulfillment milestones are met.

## 3. Database Schema Updates (SQLModel)

### `Deal` Model
Tracks the financial and fulfillment state of the agreement.
- `id`: UUID
- `row_id`: FK to Row
- `bid_id`: FK to Bid (the specific offer)
- `vendor_id`: FK to Vendor
- `status`: Enum (`NEGOTIATING`, `TERMS_AGREED`, `FUNDED`, `IN_TRANSIT`, `COMPLETED`, `DISPUTED`, `CANCELED`)
- `agreed_price`: Float
- `platform_fee`: Float
- `stripe_payment_intent_id`: String
- `proxy_email_alias`: String (e.g., `quote-a7f9b2`)

### `Message` Model
The immutable ledger of communication.
- `id`: UUID
- `deal_id`: FK to Deal
- `sender_type`: Enum (`BUYER`, `VENDOR`, `SYSTEM`)
- `content_text`: String (the stripped, raw message)
- `attachments`: JSONB (list of secure URLs)
- `created_at`: Timestamp

## 4. Workflows & State Transitions

1. **Initiation (`NEGOTIATING`):** Buyer clicks "Request Quote". Backend creates a `Deal` record, generates `proxy_email_alias`, and sends the initial outbound email to the Vendor via Resend.
2. **Conversation Loop:** Vendor replies. Resend webhook fires. Backend saves `Message`, LLM analyzes it, and relays it to Buyer. Buyer replies -> relayed to Vendor.
3. **Agreement (`TERMS_AGREED`):** LLM detects agreement (or Vendor clicks a "Submit Final Quote" button in their email). Deal status updates. Buyer receives the Deal Card.
4. **Funding (`FUNDED`):** Buyer clicks "Pay Now" on the Deal Card. Stripe captures funds. Vendor is notified: *"Funds secured. Please proceed with fulfillment."*
5. **Release (`COMPLETED`):** Buyer clicks "Confirm Delivery/Service" on their dashboard. Backend triggers Stripe Connect transfer to Vendor, minus our fee.

## 5. Technical Risks & Requirements
- **Deliverability:** The subdomain `messages.buy-anything.com` MUST have strictly configured SPF, DKIM, and DMARC records to prevent vendor/buyer emails from hitting spam.
- **Thread Stripping:** Parsing email replies is notoriously messy. We must rely on battle-tested libraries (like Python's `email_reply_parser`) and have a fallback for edge cases.
- **Security:** Attachments must be scanned or strictly limited by file type (PDF, JPG, PNG) to prevent malware relaying.
- **Trust & Alias UX:** Random hashes (`quote-a7f9b2`) look like spam. We must mask the routing infrastructure:
  - **Friendly "From" Names:** Emails should appear as `Vendor Name (via BuyAnything)` so standard email clients hide the raw alias.
  - **Legible Aliases:** Use readable formats like `netjets-quote-284@messages.buy-anything.com`.
  - **Trust Footer:** Every relayed email must include a branded footer: *"This message is securely routed through BuyAnything to enable 1-click escrow payments and buyer protection."*

## 6. Implementation Phases
**Phase 1: DNS & Resend Setup**
- Configure `messages.buy-anything.com` in DNS and Resend.
- Set up the Inbound Webhook endpoint `POST /webhooks/resend/inbound`.

**Phase 2: Data Models & Proxy Logic**
- Create `Deal` and `Message` models.
- Implement the bidirectional email relay, thread stripping, and attachment handling.

**Phase 3: AI Intercept & Deal Card UI**
- Add the lightweight LLM classification step in the webhook handler.
- Build the `DealCard` UI component in the frontend chat feed.

**Phase 4: Stripe Connect Integration**
- Wire the Deal Card to Stripe Payment Intents.
- Implement manual (admin) or automated payout logic for `FUNDED` -> `COMPLETED`.
