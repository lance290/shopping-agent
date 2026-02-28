# need sourcing: Bob@buy-anything.com

Status: done
Last updated: 2026-02-28T02:05:23.401Z

---

### Stated Requirements (from user's brief)
*   **Multi-Channel Entry:** Bob must be reachable via email (bob@buy-anything.com) and a cell number (iMessage/WhatsApp).
*   **Group Dynamics:** Bob must be able to join or create group chats/emails to facilitate family shopping lists.
*   **Item Processing:** Bob listens to group messages, parses grocery items via an MCP (Model Context Protocol), and maintains a shared list.
*   **Brand Bidding:** Bob proactively reaches out to brands to "bid" for swaps (coupons/BOGOs) when users add items in their category.
*   **Groflo Integration:** Use Groflo’s MCP for existing digital coupons and the redemption engine.
*   **Redemption Loop:** User claims a swap → shops → scans receipt → Bob validates and adds money to a "Bob Wallet."
*   **Economic Model:** $2–5 savings for user per redemption; $1–2 revenue for Groflo; 30% affiliate payout to referrers.
*   **Self-Service Brand Portal:** Brands can sign up, verify via cell/email, and post deals or respond to Bob’s outreach.

### Inferred Requirements (added by council)
*   **Message Normalization:** Since Bob interacts across SMS, Email, and WhatsApp, a normalization layer is required to turn fragmented messages into a single "List State."
*   **OCR Engine:** To support "scan receipt," an asynchronous OCR/Vision processing service is needed to match line items against claimed swaps.
*   **Stateful Conversational Logic:** Bob needs a memory of "who is in the family" to correctly route the initial group creation and list permissions.
*   **Web-Based List View:** While Bob texts links, a lightweight web frontend is required for the "search at top" and "claim" functionality, as these are high-friction in pure text.
*   **Vendor Integration:** Bob will leverage the existing "Shopping Agent" backend infrastructure (specifically the `Vendor` and `Bid` models) rather than building a redundant brand portal from scratch. The existing system already handles vendor profiles, stripe onboarding, and category matching.

### Assumptions & Flags
*   **iMessage Limitation:** **Critical Flag.** There is no official API to "invite" a bot to an iMessage group. The system must use a Twilio/SMS number. When an SMS number is added to an iMessage group, Apple converts the thread to "Group MMS." Bob can function here, but blue-bubble features (typing indicators, etc.) will be absent.
*   **WhatsApp Limitation:** The official WhatsApp Business API does not support joining "Groups" in the traditional sense. **Assumption:** Bob will likely manage WhatsApp "Groups" by acting as a proxy or using 1:1 threads that sync to a shared web list.
*   **Brand Outreach:** The brief mentions Bob "reaches out to brands." **Assumption:** This implies an automated cold-outreach system (Email/LinkedIn/API) triggered by high-volume demand for a specific category.

---

# PRD: Bob (@buy-anything.com) - The AI Family Shopping Agent

## 1. Executive Summary
Bob is an AI agent designed to sit inside family communication channels (Email, SMS, WhatsApp) to automate grocery list building and maximize savings. By integrating with the Groflo MCP and a custom brand-bidding engine, Bob turns a simple text ("we need milk") into a revenue-generating opportunity for brands and a cost-saving event for consumers.

## 2. Product Goals
*   **Save Users Money:** Target $10–20/week savings per person.
*   **Generate Revenue:** $3–5/week revenue per active user.
*   **Frictionless Entry:** Allow users to start a group list simply by CC'ing an email or adding a phone number to a text thread.
*   **Brand Utility:** Provide brands a self-service "bidding" platform to intercept intent at the moment of list-making.

## 3. Target Users & Jobs-to-be-Done
*   **The Household Manager:** Needs to aggregate "I'm out of..." requests from multiple family members without manual transcription.
*   **The Budget-Conscious Shopper:** Wants the best price/BOGO without hunting for physical or digital coupons.
*   **Brand Managers:** Want to flip a competitor's customer at the point of intent (e.g., user wants "Yogurt," brand offers "Chobani BOGO").

## 4. Core User Flow
1.  **Onboarding:** User texts/emails Bob. Bob asks, "Who's in the family?" and provides a link to invite them or creates a group thread.
2.  **Aggregation:** Family members chat naturally. Bob "listens," extracts items (e.g., "get some 2% milk"), and adds them to the cloud-synced list.
3.  **Optimization:** Bob sends a link to the list. Under "Milk," Bob shows a Groflo swap: "Swap for Fairlife and save $2.00."
4.  **Bidding:** If no Groflo deal exists, Bob pings registered brands in that category to see if they want to offer a "Real-time BOGO."
5.  **Claiming:** User taps "Claim" on the web-list.
6.  **Redemption:** User shops, takes a photo of the receipt, and sends it to Bob.
7.  **Payout:** Bob’s OCR verifies the purchase; funds are credited to the Bob Wallet (payout via Stripe/Venmo).

## 5. Functional Requirements
*   **NLU Parser:** Must distinguish between "I love milk" (chat) and "buy milk" (intent).
*   **Group Management:** Ability to track multiple users mapped to a single `FamilyID`.
*   **MCP Integration:** Client-side implementation of Groflo MCP for real-time coupon fetching.
*   **Brand Portal:**
    *   Cell/Email verification (OTP).
    *   Dashboard to set "Bidding Rules" (e.g., "Always offer $1 off if a user adds 'detergent'").
*   **Affiliate Engine:** Generate unique `RefID` links; track 30% revenue share for referrers.
*   **Receipt OCR:** Extract store name, date, and line items to validate "Claims."

## 6. Data Model (Mapped to Shopping Agent)
Bob will not recreate core e-commerce data structures. Instead, Bob acts as a conversational adapter that maps directly to the existing **Shopping Agent** database schema:

*   **User:** Maps directly to Shopping Agent's `User` model.
*   **FamilyGroup:** Maps to a Shopping Agent `Project`. We will introduce a lightweight mapping table (e.g., `GroupChat` or `ProjectShare`) to tie an SMS/Email thread ID to a specific `Project.id`.
*   **ListItem:** Maps directly to a `Row` within the `Project`.
*   **Swap/Deal:** Maps directly to a `Bid` tied to the `Row` and a `Vendor`.
*   **Transaction:** (Bob-specific) For tracking OCR receipt validation, cash back, and wallet payouts.

## 7. Suggested Tech Stack & Architecture
*   **Deployment:** Railway (Same as Shopping Agent).
*   **Frontend:** Next.js (Tailwind CSS) for the Shopping List Web View.
*   **Backend:** TypeScript (Node.js) or Python (FastAPI) to share code directly with Shopping Agent.
*   **Database:** **PostgreSQL** (Direct connection to the existing Shopping Agent DB).
*   **Architecture:**
    *   **Adapter Pattern:** Webhooks for Resend (Inbound Email) and Twilio (SMS).
    *   **NLU Router:** Parses incoming messages and translates them into `RowCreate` or `Bid` fetching actions via the Shopping Agent core logic.
    *   **Event Queue:** BullMQ / Celery to handle receipt OCR processing asynchronously.

## 8. Integrations & APIs
*   **Messaging:** Twilio (SMS/MMS), Resend (Inbound Webhooks).
*   **Coupons:** Groflo MCP.
*   **Payments:** Stripe Connect (for Wallet payouts and Brand billing).
*   **AI:** OpenAI GPT-4o (for NLU and Receipt Vision/OCR).

## 9. Edge Cases & Risks
*   **MMS Reliability:** Group MMS can be flaky across different carriers.
*   **Receipt Fraud:** Users scanning the same receipt multiple times or fake receipts. (Requires duplicate detection logic).
*   **Brand Response Latency:** If a brand "bids" too late, the user is already at the store. (Requires "Auto-bid" rules for brands).

## 10. Open Questions
1.  **Groflo MCP Specs:** Does the Groflo MCP support real-time "bidding" or only static coupon retrieval?
2.  **Wallet Payouts:** What is the minimum threshold for a user to withdraw money from their Bob Wallet?
3.  **Brand Outreach:** Should Bob's "outreach" to new brands be via automated LinkedIn/Email, or is there a pre-existing brand database?

## 11. Suggested Milestones
1.  **V1 (MVP):** Email-only group list + Groflo MCP integration (No receipt scanning yet).
2.  **V2:** SMS/Twilio integration + "Claim" functionality + Manual receipt verification.
3.  **V3:** Automated OCR + Affiliate tracking. Connect to existing Shopping Agent backend for vendor discovery and dynamic deal sourcing.
4.  **V4:** WhatsApp integration and scaling.