# need sourcing: Bob@buy-anything.com

Status: done
Last updated: 2026-02-28T19:09:41.633Z

---

### Stated Requirements (from user's brief)
*   **Identity:** Agent name is "Bob" (or "Pop" in V2 context). Reachable via `bob@buy-anything.com` and a cell number.
*   **Multi-Channel Group Entry:** Users can invite Bob to an iMessage group, WhatsApp group, or group email.
*   **Conversational Onboarding:** Bob asks who is in the family and creates the group text/email for list sharing.
*   **Passive Listening:** Bob "listens" to group chats/emails to extract grocery items.
*   **MCP Integration:** Uses a general grocery MCP (Kroger specified in V2) for item details and Groflo MCP for digital coupons/swaps.
*   **Brand Bidding:** Bob proactively reaches out to brands (via Jeremy/Wattdata) to "bid" for swaps when a user adds a competitor's item.
*   **Redemption Loop:** User claims swap on a web-list → shops → scans receipt → Bob validates via OCR → money added to Bob Wallet.
*   **Affiliate Model:** 30% revenue share for the community/person who referred the user.
*   **Brand Self-Service:** Brands can verify via cell/email to post deals or respond to Bob's bidding requests.

### Inferred Requirements (added by council)
*   **The "Blue Bubble" Bridge:** Since iMessage has no official bot API for group chats, the system must use a **Twilio SMS/MMS Gateway**. When a Twilio number is added to an iMessage group, it forces the group into "Green Bubble" (MMS) mode, allowing Bob to receive and send messages to the group.
*   **Headless Browser / SMTP Parser:** For "Group Email" listening, Bob requires an inbound mail parser (Mailgun/SendGrid) to identify `FamilyID` based on the `To:` or `CC:` headers.
*   **Stateful Intent Extraction:** An LLM-based NLU layer is needed to distinguish between "I hate this milk" (chatter) and "Add milk to the list" (intent).
*   **Asynchronous OCR Pipeline:** Receipt validation is slow; it requires a background job queue (BullMQ) to process images and notify the user via text when the wallet is credited.

### Assumptions & Flags
*   **iMessage Limitation:** You cannot programmatically "invite" a bot to a native iMessage (Blue Bubble) group. Bob acts as an SMS participant. This is a genuine technical constraint of the Apple ecosystem.
*   **WhatsApp Groups:** WhatsApp Business API typically restricts bots from joining user-created groups. Bob will likely function via 1:1 threads or a "Proxy Group" managed by the platform.
*   **Brand Outreach:** We assume "Jeremy/Wattdata" refers to specific contact-sourcing tools/APIs used to find CPG brand managers.

---

# PRD: Bob (Pop) - The AI Grocery Savings Agent

## 1. Executive Summary
Bob is an AI agent that automates grocery list coordination and savings. By living inside existing family communication channels (SMS, Email, WhatsApp), Bob extracts purchase intent and triggers a real-time "bidding war" between brands. Users save $100+/month through "PopSwaps™," while the platform generates revenue through brand redemptions and a 30% affiliate sharing model.

## 2. Product Goals
*   **Frictionless Aggregation:** Zero-app-required list building via group chat.
*   **Automated Savings:** Target $2–$5 savings per item through Groflo/Brand swaps.
*   **Zero-CAC Growth:** Scale via a 30% revenue-share model for users and brands who refer others.
*   **Brand Interception:** Allow brands to "bid" for a customer at the exact moment of intent.

## 3. Target Users & Jobs-to-be-Done
*   **The Family Lead:** "Keep everyone's requests in one place without me having to play secretary."
*   **The Value Shopper:** "Get the best deals (BOGOs/Coupons) without manual clipping."
*   **The Brand Manager:** "Flip a competitor's customer by offering a swap at the point of list-making."

## 4. Core User Flow
1.  **Initiation:** User emails `bob@buy-anything.com` or texts the Bob number.
2.  **Onboarding:** Bob asks for the "Family Group" members. Bob initiates a group MMS or email thread.
3.  **List Building:** Members chat (e.g., "We need A1 sauce"). Bob parses the item, enriches it via **Kroger MCP** (images/details), and adds it to the shared web-list.
4.  **The Swap:** Bob checks **Groflo MCP** for existing deals. If none exist, Bob pings category brand managers (via outreach automation) to "bid" a swap.
5.  **Claiming:** User opens the texted list link, views "PopSwaps™" (e.g., "Swap A1 for Heinz 57 and save $2.50"), and hits **Claim**.
6.  **Redemption:** User shops, texts a photo of the receipt to Bob.
7.  **Payout:** Bob validates the line item via OCR, credits the **Bob Wallet**, and triggers the 30% affiliate payout to the referrer.

## 5. Functional Requirements
*   **Multi-Channel Adapter:** Normalize inputs from Twilio (SMS), Mailgun (Email), and WhatsApp.
*   **NLU Intent Engine:** Extract items, quantities, and brands from natural conversation.
*   **Family Workspace Logic:** Map multiple phone numbers/emails to a single `FamilyID` and `SharedList`.
*   **Brand Portal:** Self-service OTP login for brands to manage bids and view "intent volume" in their category.
*   **Referral Engine:** Generate unique `RefLinks` that track 30% of lifetime revenue back to the referrer.
*   **Vision OCR:** High-accuracy receipt parsing to match "Claimed" items against "Purchased" items.

## 6. Data Model
*   **User:** `id, phone, email, wallet_balance, referrer_id`
*   **FamilyGroup:** `id, member_ids[], active_list_id`
*   **ListItem:** `id, family_id, raw_text, normalized_name, category, status (pending/claimed/redeemed)`
*   **PopSwap:** `id, brand_id, offer_details, groflo_id, savings_value`
*   **Transaction:** `id, user_id, amount, type (redemption/referral_payout)`

## 7. Suggested Tech Stack & Architecture
*   **Deployment:** Railway
*   **Frontend:** TypeScript / Next.js (for the List View and Brand Portal)
*   **Backend:** Node.js (TypeScript) for the agent logic and API.
*   **Database:** **PostgreSQL** (Primary) + **Redis** (for chat state/session management).
*   **Architecture:** **Adapter Pattern** for messaging; **Event-Driven** (BullMQ) for OCR and Brand Outreach tasks.

## 8. Integrations & APIs
*   **Messaging:** Twilio (SMS/MMS), Mailgun (Inbound Parse).
*   **Product Data:** Kroger MCP.
*   **Coupons/Redemption:** Groflo MCP.
*   **Outreach:** Jeremy / Wattdata (Brand contact discovery).
*   **AI:** OpenAI GPT-4o (NLU and Receipt Vision).

## 9. Edge Cases & Risks
*   **MMS Threading:** If a user has a mix of Android/iPhone, group MMS can break. Bob must provide a "List Link" as the source of truth.
*   **OCR Hallucinations:** Receipt items are often abbreviated (e.g., "HNZ 57 SCE"). Requires fuzzy matching against the claimed swap.
*   **Brand Spam:** Automated outreach must be throttled to avoid blacklisting.

## 10. Open Questions
1.  **iMessage Group Creation:** Answers are currently unknown.
2.  **Wallet Payouts:** Answers are currently unknown.
3.  **Groflo Sync:** Answers are currently unknown.

## 11. Suggested Milestones
*   **M1: The Chatbot (Weeks 1-3):** Basic SMS/Email parsing, Kroger item lookup, and shared web-list.
*   **M2: The Swap (Weeks 4-6):** Groflo MCP integration, "Claim" button logic, and Manual Receipt upload.
*   **M3: The Bidding (Weeks 7-9):** Automated brand outreach (Jeremy/Wattdata) and Brand Portal for self-service bids.
*   **M4: The Scale (Weeks 10+):** Affiliate tracking, automated OCR validation, and Wallet payouts.