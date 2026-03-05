# Project Pop vs. Penny (Thriftly) - Competitive Roadmap

## Objective
Thriftly (Penny AI) has a feature set and business model nearly identical to Pop Savings. They are marketing text/email/photo parsing, household shared lists, and upcoming exclusive CPG rebates.

To beat them, we will leverage our existing robust LLM routing and vector infrastructure, while rapidly closing the functional UX gaps they currently hold over us.

## Current Gaps & Competitive Analysis

| Feature | Thriftly (Penny) | Pop Savings | Gap Status |
| :--- | :--- | :--- | :--- |
| **Inbound Channels** | SMS, Email, Web App | SMS, Email, Web Chat | Parity |
| **Image Parsing (Fridge/Pantry)** | Advertised ("snap a photo") | Missing | **Critical Gap** - Pop webhook ignores Twilio `MediaUrl` and Resend attachments. |
| **Group Chat / Household** | Dedicated Household UI, Group SMS | Copylinks to `Project`, 1:1 SMS | **Medium Gap** - Pop lacks true Group MMS parsing and formal Household data modeling. |
| **Taxonomy & Editing** | Strict UI (Dept, Size, Qty, Brand) | Freeform text, `choice_factors` | **UX Gap** - Pop needs a structured editor modal for list items. |
| **Attribution** | Shows who added an item & how | Implicit via `user_id` | **UX Gap** - Pop needs to display item history. |
| **Monetization (Rebates)** | "Coming Soon" CPG partnerships | PopSwaps™ + GroFlo | Parity / Advantage - Pop is actively building this. |

---

## The Attack Plan

### Phase 1: Multimodal Inbound (The "Snap a Photo" Feature)
**Goal:** Enable Pop to receive images via SMS and Email, analyze them, and extract grocery items automatically.
- **Backend (Twilio):** Update `twilio_inbound` in `routes/pop.py` to extract `NumMedia` and `MediaUrlX` from Twilio form data.
- **Backend (Resend):** Update `resend_inbound` in `routes/pop.py` to extract and process email attachments.
- **LLM Engine:** Pass image URLs to the unified NLU engine. If images are present, route to a vision-capable model (`gemini-1.5-pro` or `gpt-4o`) with a prompt to extract missing essentials from fridge/pantry photos or ingredients from recipe cards.

### Phase 2: Grocery Taxonomy & History UI
**Goal:** Match Thriftly's clean list management UX so users feel in control of the AI's output.
- **Frontend (List Item UI):** Add an "Edit Item" modal that surfaces structured fields: `Name`, `Brand`, `Department` (dropdown), `Size`, and `Quantity`.
- **Backend Data:** Ensure `choice_factors` or new columns map cleanly to these taxonomy fields.
- **Attribution Display:** Expose the `added_by` and `channel` (SMS/Email/Web) data on the UI (e.g., "Mom added via SMS").

### Phase 3: Group Chat & Household Invites
**Goal:** Capture entire families in single threads.
- **Group SMS:** Update the Twilio parser to handle MMS group threads, ensuring Pop responds in-thread and attributes items to the correct sender phone number.
- **Household Management:** Enhance the existing `Project` copylink flow into a formal "Household" settings page (similar to `/api/settings/invite` in Thriftly) allowing users to see who is in their household.

### Phase 4: Bulk Actions (Parse & Clear)
**Goal:** Frictionless list management.
- **Paste Recipe UI:** Add a frontend component to paste raw text/recipes and hit a "Parse" API to extract items en masse.
- **Clear List UI:** Add a simple "Clear Completed" button that archives or soft-deletes checked items in bulk.

### Phase 5: Speed UX for High-Frequency List Entry
**Goal:** Make PopSavings faster than notes apps for rapid grocery entry.
- **List Expanded by Default:** Open list sections in expanded mode so newly entered items are immediately visible.
- **No Auto-Collapse on Expand:** If a user expands one section, keep other sections expanded (no forced accordion behavior).
- **Persistent Chat Focus:** After sending an item, keep cursor focus in chat input so users can type the next item without clicking.
- **Acceptance Criteria:** User can add 5 items in sequence with keyboard only, and each item is visible in-list after send.

### Phase 6: Dual CopyLink Growth System (Household + Referral)
**Goal:** Create two viral loops inside PopSavings sharing.
- **CopyLink #1 — Joint List Sharing:** Each list gets a stable, human-readable custom URL on the list page. Include a one-click "Copy Link" action for household/family collaborators.
- **CopyLink #2 — TeamPop Referral Link:** Add a second "Copy Link" that includes the sender's affiliate/referral code for rev-share attribution on signup.
- **Attribution + Wallet:** Track referred signups and route referral rewards to the inviter's wallet balance.
- **Acceptance Criteria:** Users can copy either link in one tap; backend records source link type and referral owner.

### Phase 7: Social List Layer (Per-Item Collaboration)
**Goal:** Turn each list into a collaborative social feed for households.
- **Per-Item Reactions:** Add lightweight "Like" on each item.
- **Per-Item Comments:** Add threaded comments for item-level discussion (brand preferences, substitutions, quantities).
- **Activity Context:** Show who liked/commented and when, to support multi-shopper coordination.
- **Acceptance Criteria:** Household members can react/comment without leaving the list view; updates appear in near-real-time.

### Phase 8: Coupon Network + CPG Self-Serve Activation
**Goal:** Convert shopping intent into monetizable brand action.
- **Retail MCP Integration:** Use Kroger MCP to let users pick specific purchasable items.
- **Brand Mapping:** Map selected items to CPG companies and product managers.
- **Coupon Request Routing:** Route coupon requests to PMs via Scout workflows and outreach operations.
- **Self-Serve Coupon Publishing:** Let PMs click-to-add GroFlo-powered coupons that attach directly to relevant PopSavings list items.
- **Seed Coupons via MCP:** Load initial GroFlo coupon catalog through MCP so value is available on day one.
- **Sponsored Deal Incentive:** If a brand manager drives user signup, prioritize their sponsored deal slot under matching items (policy + ranking controls required).

---

## Distribution Flywheel (PopSavings)

1. **Household Viral Loop:** Shared joint lists pull multiple shoppers into one list.
2. **Household-to-Household Loop:** TeamPop referral links expand from family nodes into adjacent households.
3. **B2B2C Loop via Scout/Tod:** Coupon demand from households routes to brand managers.
4. **Brand Amplification Loop:** PMs share coupon-embedded list links to their audiences; higher redemptions drive more sharing.
5. **Revenue Loop:** Referral attributions and brand-driven conversions flow into wallet-based rev-share payouts.
