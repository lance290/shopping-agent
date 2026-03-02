# need sourcing: Pop@popsavings.com

Status: done
Last updated: 2026-02-28T19:30:00.000Z

---

### Stated Requirements (from user's brief)
*   **Identity:** Agent name is **Pop**. Reachable via `pop@popsavings.com` and a cell number.
*   **V2 Entry Point:** Web-first — users go to `popsavings.com`, chat with Pop, enter phone, and get an OTP. SMS/email group listening is deferred to V3+.
*   **Group Dynamics:** Pop can create family groups. Members join via share link. V3+ adds iMessage/WhatsApp group support.
*   **Item Processing:** Pop listens in chat, parses grocery items via the **Kroger MCP** (Pantry Agent) for product enrichment, and maintains a shared list.
*   **Brand Bidding:** Pop proactively reaches out to brands to "bid" for swaps (coupons/BOGOs) when users add items in their category. Brand contacts sourced via **Wattdata/Jeremy**.
*   **Groflo Integration:** Use **Groflo MCP** for existing digital coupons and the redemption engine.
*   **Redemption Loop:** User claims a swap → shops → scans receipt → Pop validates and adds money to a "Pop Wallet."
*   **Economic Model:** Groflo pays ~$1/redemption. Platform keeps 70%; 30% goes to the referrer. Users save $2–5 per item.
*   **Self-Service Brand Portal:** Brands can sign up, verify via corporate email, and post deals or respond to Pop's outreach. Brands that refer users earn the sponsored top slot on that user's list — lifetime.

### Inferred Requirements (added by council)
*   **Web Chat First:** V2 primary interface is `popsavings.com` web chat. The channel adapter layer (SMS/Email/WhatsApp) is V3+.
*   **OCR Engine:** Asynchronous OCR/Vision (GPT-4o Vision) to match receipt line items against claimed swaps. Duplicate receipt detection via SHA-256 image hash.
*   **Stateful Conversational Logic:** Pop needs a memory of "who is in the family" to route group creation and list permissions.
*   **Durable Background Jobs:** Receipt OCR, swap search, brand outreach, and referral payout are async workflows. These are long-running and multi-step (sagas), making **Temporal** the right orchestration layer — not a simple job queue. Pop's brand outreach workflows may pause for days waiting for a brand email reply.
*   **Blue Bubble Bridge (V3+):** When SMS/email listening is added, a Twilio SMS number added to an iMessage group forces "green bubble" (MMS) mode. This is a genuine Apple ecosystem constraint.
*   **Inbound Email Parser (V3+):** Mailgun inbound parse API identifies the `FamilyID` from `To:`/`CC:` headers for email group listening.

### Assumptions & Flags
*   **V2 is web-only.** SMS/email group listening, WhatsApp, and iMessage are deferred to V3+.
*   **iMessage Limitation (V3+):** There is no official API to "invite" a bot to an iMessage group. Pop uses a Twilio SMS number; Apple converts the thread to Group MMS. Blue-bubble features are absent.
*   **WhatsApp Limitation (V3+):** WhatsApp Business API does not support joining user-created groups. Pop will use 1:1 threads or a proxy group synced to the web list.
*   **Brand Outreach:** Wattdata/Jeremy is the contact-sourcing tool for finding CPG brand product managers. V2 outreach is semi-automated (email template + internal Slack notification for ops follow-up). Full automation is V3+.
*   **Concurrent Swap Claims:** Two family members clicking "Claim" simultaneously is handled with a partial unique index: only one active claim per swap per list item, regardless of who claims it. "Claimed by Mom" is shown to other members.
*   **Receipt Fraud:** Duplicate receipt submissions are blocked via SHA-256 hash of the uploaded image. Two OCR workers processing the same user's receipts simultaneously use `SELECT ... FOR UPDATE` to prevent double-crediting.

---

# PRD: Pop (@popsavings.com) - The AI Grocery Savings Agent

## 1. Executive Summary
**Pop** is an AI grocery savings agent. V2 is web-first: users go to `popsavings.com`, chat with Pop, build a shared family shopping list, and claim PopSwaps™ — brand-sponsored product swaps sourced from the Groflo MCP and a real-time brand-bidding engine. A $1 Groflo payout per redemption supports 70% platform margin and 30% referral payouts, targeting profitability at 2K weekly active users.

## 2. Product Goals
*   **Save Users Money:** Target $10–20/week savings per person.
*   **Generate Revenue:** $3–5/week revenue per active user.
*   **Frictionless Entry (V2):** Chat with Pop at `popsavings.com`, enter a phone number, confirm OTP — list is live. No app download. V3+ adds SMS/email group entry.
*   **Brand Utility:** Provide brands a self-service "bidding" platform to intercept intent at the moment of list-making.

## 3. Target Users & Jobs-to-be-Done
*   **The Household Manager:** Needs to aggregate "I'm out of..." requests from multiple family members without manual transcription.
*   **The Budget-Conscious Shopper:** Wants the best price/BOGO without hunting for physical or digital coupons.
*   **Brand Managers:** Want to flip a competitor's customer at the point of intent (e.g., user wants "Yogurt," brand offers "Chobani BOGO").

## 4. Core User Flow
1.  **Onboarding (V2):** User visits `popsavings.com`, chats with Pop, enters their phone, and confirms an OTP. Pop asks "Who's in the family?" and generates a share link to invite members.
2.  **Aggregation:** Family members chat with Pop (web in V2; SMS/email/WhatsApp in V3+). Pop extracts items (e.g., "get some 2% milk"), enriches via Kroger MCP, and adds them to the shared list.
3.  **Optimization:** Pop surfaces a Groflo swap under each item (e.g., "Swap for Fairlife and save $2.00").
4.  **Bidding:** If no Groflo deal exists, Pop triggers a Wattdata brand outreach workflow — brand managers are emailed and can respond to offer a real-time swap.
5.  **Claiming:** User taps "Claim" on the web list. One claim per swap per item (household-scoped).
6.  **Redemption:** User shops, uploads a receipt photo on the web. Pop's Temporal OCR workflow validates the purchase.
7.  **Payout:** Groflo confirms redemption → Pop Wallet is credited. Referrer gets 30% of the Groflo payout. (Withdrawal via Stripe Connect deferred to V3.)

## 5. Functional Requirements
*   **NLU Parser:** Must distinguish between "I love milk" (chat) and "buy milk" (intent).
*   **Group Management:** Track multiple users mapped to a single `FamilyID`. Web invite link for V2; SMS/email/WhatsApp for V3+.
*   **Kroger MCP:** Product enrichment on item add — name, image, category, UPC. Fallback: store raw text, retry enrichment async.
*   **Groflo MCP:** Real-time swap search by category/product name. Redemption confirmation after receipt OCR. Circuit breaker on both MCPs.
*   **Brand Portal:** Corporate email OTP verification. Dashboard with active swaps, demand signals, claim/redemption counts. Brand referral link = sponsored slot for referred users (lifetime).
*   **Affiliate Engine:** `ref_code` per user (e.g., `POP-a3x9k2`). First-touch attribution via 30-day cookie. 30% of Groflo payout to referrer on each redemption.
*   **Receipt OCR:** GPT-4o Vision. SHA-256 dedup to block resubmits. Fuzzy match against claimed swaps. Groflo confirmation before wallet credit.
*   **Wattdata Brand Outreach:** Aggregate demand by category weekly → contact brand managers via Wattdata/Jeremy → templated email → ops Slack fallback.

## 6. Data Model
*   **User:** `id, phone, display_name, wallet_balance_cents` (integer cents), `ref_code, referrer_id, role (consumer|brand), brand_email_verified`.
*   **FamilyGroup:** `id, owner_id, share_code`. Many-to-many with Users via `FamilyGroupMembers`.
*   **ShoppingList:** `id, family_group_id, week_of (DATE)`. One active list per family per week. Auto-archives on Monday.
*   **ListItem:** `id, shopping_list_id, raw_text, normalized_name, category, kroger_product_id, product_image_url, status (pending|swapped|bought|removed)`.
*   **PopSwap:** `id, list_item_id, brand_id, groflo_coupon_id, swap_product_name, offer_type, savings_cents, groflo_payout_cents, is_sponsored`.
*   **ClaimedSwap:** Partial unique index on `(pop_swap_id, list_item_id)` WHERE status='claimed' — one active claim per item.
*   **Receipt:** `id, user_id, image_url, image_hash (SHA-256 UNIQUE), ocr_line_items (JSONB), ocr_status`.
*   **Transaction:** `id, user_id, amount_cents, type (swap_redemption|referral_earning|withdrawal)`.
*   **BrandOutreachRequest:** `id, category, demand_count, outreach_status, outreach_channel (jeremy|wattdata|manual)`.
*   **ChatSession:** `id, user_id, messages (JSONB), state (onboarding|active|idle), context (JSONB)`.

## 7. Suggested Tech Stack & Architecture
*   **Deployment:** Railway.
*   **Frontend:** Next.js 14 (App Router, Tailwind CSS) for `popsavings.com` — chat widget, shopping list, brand portal, wallet.
*   **Backend:** TypeScript (Node.js) for high-concurrency message handling.
*   **Database:** **PostgreSQL** (primary — transactions, wallets, lists) + **Redis** (session cache, Temporal worker state).
*   **Background Jobs:** **Temporal** (not BullMQ). Reasons:
    *   Receipt OCR is a multi-step saga (upload → OCR → Groflo confirm → wallet credit → referral payout) — durable execution survives pod restarts.
    *   Brand outreach workflows pause for days waiting for a brand email reply (`waitForSignal`).
    *   Referral payouts require exactly-once semantics (idempotent by workflow ID).
    *   Temporal Cloud runs over HTTP — no extra Railway service required. Free tier covers <10K actions/month.
*   **V2 Architecture:** Web chat → Next.js API routes → PostgreSQL + Temporal workers. Channel adapters (SMS/Email/WhatsApp) are V3+.

## 8. Integrations & APIs
*   **Auth:** Twilio Verify (phone OTP). V3+ adds Mailgun inbound parse.
*   **Email:** `pop@popsavings.com` (Resend).
*   **Product Data:** Kroger MCP (Pantry Agent) — product search, images, UPC, pricing.
*   **Coupons/Redemption:** Groflo MCP — swap search, redemption confirmation.
*   **Brand Contacts:** Wattdata / Jeremy — CPG brand manager contact discovery for outreach.
*   **Payments:** Stripe Connect (wallet payouts — deferred to V3; wallet is display-only in V2).
*   **AI:** OpenAI GPT-4o (NLU for chat, Vision for receipt OCR).
*   **Storage:** Cloudflare R2 (receipt images — zero egress fees, S3-compatible).

## 9. Edge Cases & Risks
*   **Receipt Fraud:** SHA-256 hash unique index blocks resubmitting the same image. Concurrent OCR jobs use `SELECT ... FOR UPDATE` on claimed swaps to prevent double-crediting.
*   **Concurrent Swap Claims:** Partial unique index enforces one active claim per swap per item. Expired/rejected claims don't block new ones.
*   **Brand Response Latency:** Temporal `waitForSignal` handles async brand email replies without polling. Auto-bid rules for brands are a V3 feature.
*   **Groflo Rejected After OCR Match:** Never credit wallet optimistically — Groflo `create_redemption` must return `approved` first. If Groflo is down, Temporal retries with exponential backoff.
*   **Stale List Links:** Archived lists are read-only. UI shows a banner linking to the current week's list.
*   **MMS Reliability (V3+):** Group MMS is flaky across carriers. The shared web list is always the source of truth.

## 10. Open Questions
1.  **Groflo MCP specs:** Confirm whether `create_redemption` API is available and what the payout-per-redemption rate is. (~$1 assumed.)
2.  **Wallet payouts:** Minimum withdrawal threshold TBD. V2 wallet is display-only; Stripe Connect deferred to V3.
3.  **Kroger MCP availability:** Is the Pantry Agent publicly accessible, or do we need to build our own wrapper around the Kroger Developer API?
4.  **Temporal Cloud vs. self-hosted:** Free tier likely covers V2 scale (<10K actions/month). Validate before launch.
5.  **Wattdata API contract:** Confirm API availability and cost for brand manager contact sourcing.

## 11. Milestones

**V2 — Web-First MVP (popsavings.com)**
*   **Phase 1 (Wk 1-2):** Auth (phone OTP), web chat with Pop, shared list, family invite link, referral ref codes.
*   **Phase 2 (Wk 3):** Kroger MCP enrichment — product images, category, UPC on each list item.
*   **Phase 3 (Wk 4-5):** Groflo MCP swap search, SSE real-time updates, Claim flow, Temporal job infrastructure.
*   **Phase 4 (Wk 6-7):** Receipt upload (R2), Temporal OCR workflow, fuzzy matching, wallet credit.
*   **Phase 5 (Wk 8-9):** Brand portal, Wattdata outreach Temporal workflow, brand referral sponsored slot.

**V3 — Channel Expansion**
*   SMS/Twilio group MMS listening.
*   Mailgun inbound email parsing.
*   WhatsApp (1:1 proxy → shared list).
*   Stripe Connect wallet withdrawals.