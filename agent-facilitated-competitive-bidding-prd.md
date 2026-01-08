# PRD: Agent-Facilitated Competitive Bidding Workspace (Chat + Procurement Board)

**Owner:** Product / Engineering  
**Status:** Draft (v2 “Marketplace/Bids”)  
**Last updated:** 2026-01-08  
**Audience:** Product, Design, Engineering, QA

---

## 1. Summary

Build an **AI agent–facilitated marketplace** that turns a buyer’s natural-language requests into a **procurement board** with **rows** (each row = one thing the user wants to buy). The user chats to add or refine rows. For each row, the agent does the work to **source, invite/onboard sellers, collect bids, normalize offers, and present competitive options** as tiles to the right of the request.

**UI mental model (rows + tiles):**

- Each row starts with a **leftmost tile** that is the **buyer request** (e.g., “Looking for a Montana State long sleeve shirt, XL, blue”).
- To the right, the row contains **bid tiles** (offers from sellers/vendors).
- The user can chat to:
  - create a new row
  - filter/refine a row’s requirements
  - ask the agent to “get more bids” or “invite better sellers”
  - choose a winning offer

This is a **buyer + seller marketplace**, but **the agent is the orchestration layer**: it invites, onboards, matches, and manages bidding rounds.

---

## 2. Vision

A “**chat-native procurement board**” where the buyer never has to open ten tabs or email five vendors. They just describe what they want. The agent:

1) structures the request,  
2) finds likely suppliers,  
3) invites them into a lightweight bidding workflow,  
4) presents comparable offers, and  
5) helps the buyer pick (and optionally checkout).

---

## 3. Goals

1. **One chat → one row**: user can create a purchase request in <15 seconds.
2. **Competitive bids by default**: target ≥3 comparable bids per row when feasible.
3. **Comparable offers**: normalize price + shipping + ETA + return policy + condition + constraints.
4. **Fast loop**: first actionable offers within minutes (or clearly show status if not).
5. **Trust + clarity**: explain what the agent is doing and show provenance for each offer.

---

## 4. Non-Goals

- Building a general web-scraping engine (prefer official APIs, affiliate feeds, seller onboarding).
- Fully autonomous purchasing without user confirmation.
- “Any product in the world instantly” — initial scope should focus on categories with accessible sellers and structured offers.

---

## 5. Personas

1. **Everyday Buyer:** wants “best deal” and doesn’t want to research.
2. **Power Buyer:** wants constraints, vendor quality, and negotiation/bidding rounds.
3. **Seller/Vendor:** wants leads, easy quoting, and a clear path to closing.
4. **Marketplace Operator (internal):** wants quality control, anti-fraud, and healthy liquidity.

---

## 6. Key Concepts

### 6.1 Request Row
A single procurement unit: one item/service to purchase.

### 6.2 Bid Tile
A single seller offer, displayed as a tile in the row.

### 6.3 Agent Orchestration
An “agent” that:
- interprets intent
- expands clarifications into structured specs
- sources sellers
- sends invites
- collects bids
- normalizes/comparisons
- runs bidding rounds
- helps buyer select winner

---

## 7. UX Overview

### 7.1 Layout (v1 recommendation)
- **Left pane (Chat):** conversational control + agent status updates + change log.
- **Center/Primary pane (Board):** rows (requests) with leftmost request tile.
- **Right of each row:** horizontally scrollable bid tiles (offers), plus “Get more bids”.

> If you want to keep a strict two-pane layout: the “Board” can live in the right pane, and chat stays left.

### 7.2 Row anatomy
**Request tile (leftmost):**
- title + short spec summary
- constraints (size/color/budget/condition/location)
- status (Sourcing → Inviting → Bids arriving → Shortlisting → Ready to buy)
- actions: Edit, Pause, Cancel, Duplicate, Export

**Bid tiles (to the right):**
- seller name + verification badge (if any)
- total price (item + shipping + tax estimate)
- ETA / availability
- key differentiators (return policy, condition, warranty)
- “Open details”, “Ask seller”, “Counter”, “Select”, “Pin”

### 7.3 Chat interactions (examples)
- “Looking for a Montana State long sleeve shirt in XL blue.”
- “Make it under $45 shipped and no used items.”
- “Exclude eBay. Prefer official store or reputable retailers.”
- “Invite campus bookstore, Fanatics, and 3 local print shops.”
- “Get more bids; widen to navy/royal blue.”
- “Pick the best value with delivery before next Friday.”

---

## 8. Core Workflows

### Workflow A: Create a row
1. User sends message in chat.
2. LLM produces a **RequestSpec** (structured).
3. System creates a row and shows request tile.
4. Agent begins sourcing and displays progress.

### Workflow B: Source sellers + invite
1. Agent selects channels based on category:
   - existing onboarded sellers in marketplace
   - partner catalogs / product feeds
   - vetted retailer list
   - “invite via email link” for new sellers
2. Agent sends invitations with a **Bid Link** (seller quote form).
3. Seller can quote without full account (MVP), then optionally onboard.

### Workflow C: Collect bids and normalize
1. Seller submits quote (price, shipping, ETA, SKU/link, returns).
2. System normalizes into comparable fields.
3. Bid tiles appear in row with comparable “total” and metadata.

### Workflow D: Refine / rebid
1. User changes constraints in chat or UI.
2. Agent updates RequestSpec and:
   - filters existing bids that no longer match
   - optionally triggers a “rebid round” to the same sellers
   - invites additional sellers if liquidity is low

### Workflow E: Select winner
1. User clicks “Select” on a bid tile.
2. System:
   - confirms details and total cost
   - offers either:
     - **checkout** (if marketplace handles payment), or
     - **handoff** (introduce buyer/seller + tracking)
3. Row moves to “Purchased/Closed” with audit trail.

---

## 9. Functional Requirements

### FR-1: Procurement Board
- Users can create unlimited rows (within plan limits).
- Rows are reorderable, searchable, and taggable.

### FR-2: RequestSpec generation
From chat, generate a structured RequestSpec with:
- product/service name
- attributes (size, color, brand, model)
- constraints (budget, condition, shipping deadline, location, quantity)
- preferences (seller type, allowed domains, return policy)
- disallowed sources (domains/sellers)

### FR-3: Seller sourcing engine
- Determine candidate sellers using:
  - onboarded sellers directory
  - category mappings and geo relevance
  - partner catalogs / feeds (optional)
  - curated lists (operator-managed)
- Return a ranked list with reasoning.

### FR-4: Seller invite + onboarding
- Agent can invite sellers via:
  - email (MVP)
  - SMS (optional)
  - seller portal “invite code” link
- Seller can submit a bid with minimal friction:
  - **MVP:** bid form + verification email
  - **Later:** full seller account, payouts, inventory sync

### FR-5: Bid submission + validation
Bid must include:
- offered item (SKU/link or description)
- price
- shipping cost and carrier method
- estimated delivery date / handling time
- return policy summary
- quantity available
- optional: tax inclusion, warranty, condition, photos

Validation:
- numeric checks (price/shipping)
- required fields for category
- basic fraud checks (domain, throwaway email scoring)

### FR-6: Bid normalization + comparison
- Compute “**Total Cost**” = item + shipping + estimated tax (configurable).
- Show a “**Comparable Summary**” across tiles with consistent fields.
- Deduplicate identical offers (same SKU/URL) across sellers where appropriate.

### FR-7: Agent-driven negotiation (optional, staged)
- “Counter-offer” tool:
  - buyer sets target price or asks agent to request discount
  - agent sends structured counter message to seller
  - seller can accept/decline/adjust bid

### FR-8: Row-level chat controls
User can chat in context of:
- “this row” (implicit current selection)
- “row 3” / “the Montana shirt row” (explicit)
The system must reliably bind chat instructions to the correct row.

### FR-9: Transparency + audit trail
For every row:
- show a timeline: created → sellers invited → bids received → refinements → selection
- show what the agent changed (RequestSpec diffs)
- show provenance: “from seller submission” vs “catalog feed”

### FR-10: Search fallback (when marketplace liquidity is low)
If no sellers bid:
- show “fallback tiles” from product feeds / affiliate search as non-bid options
- clearly label them as “Found listings” not negotiated bids

### FR-11: Export + share
- export row (RequestSpec + bids) to Markdown/CSV
- share a read-only link to a row (optional)

---

## 10. Roles & Permissions

### Buyer
- create/edit rows
- approve counters
- select winner
- export/share

### Seller
- receive invites
- submit bids
- respond to counters/questions
- manage profile and fulfillment details (later)

### Operator/Admin
- manage seller verification
- manage category policies and curated seller lists
- handle disputes/fraud flags
- set commission/fees and payout rules

---

## 11. Trust, Safety, and Quality

### Seller verification tiers
- **Tier 0:** invited, email-verified only (MVP)
- **Tier 1:** business verification (domain, tax ID, etc.)
- **Tier 2:** verified payouts + track record

### Anti-fraud / anti-spam
- rate limits on seller submissions
- domain reputation checks
- duplicate account detection
- buyer-side “report seller” and “hide seller”

### Policy constraints
- disallow restricted categories (configurable)
- require disclosures for used/refurbished
- prevent the agent from “inventing” bids—every bid tile must map to a real seller submission or verified feed item.

---

## 12. Revenue Model (Options)

1. **Buyer subscription:** premium for agent-managed bidding.
2. **Seller lead fee:** charge per qualified bid request.
3. **Transaction commission:** percentage of completed purchases.
4. **Hybrid:** subscription + lower commission.

MVP can start with subscription + “lead credit” model to avoid payment complexity.

---

## 13. Metrics

### Marketplace liquidity metrics
- bids per row (target ≥3)
- time to first bid
- seller response rate
- rebid success rate (improves bids after refinements)

### Buyer value metrics
- conversion rate (rows closed/purchased)
- savings vs median bid
- satisfaction score / thumbs up on selected bid

### Seller metrics
- invite → bid conversion
- close rate per seller
- time-to-quote

---

## 14. Architecture (High Level)

### Services
- **LLM Orchestrator:** converts chat → RequestSpec + actions
- **Sourcing Service:** finds candidate sellers and/or feed listings
- **Invite Service:** email/SMS dispatch + tracking
- **Bidding Service:** bid intake forms, validation, normalization
- **Board Service:** sessions, rows, state machine, audit trail
- **Notifications:** buyer updates when bids arrive

### Integrations (optional, phased)
- Email provider (SendGrid/Postmark)
- SMS (Twilio)
- Catalog feeds / affiliate networks
- Payments (Stripe Connect) if marketplace handles checkout/payouts

---

## 15. MVP Scope (Competitive Bid “Starter”)

### Must-have
- Board with multiple rows
- Chat creates/edits rows
- Agent sourcing from a **curated seller directory** + web listings fallback
- Seller invite via email link
- Seller bid form (no full account required)
- Bid tiles per row + comparisons
- RequestSpec diff visibility + audit timeline
- Buyer selects a bid → generates handoff (email + tracking page)

### Nice-to-have
- Counter-offers / negotiation
- Seller accounts + inventory sync
- Payments + escrow
- “Compare rows” and “bundle deals”
- Reputation scores and verified badges

---

## 16. Open Questions

- Initial categories: apparel only, or broader retail/services?
- Should checkout be in-product (Stripe Connect) or handoff in v1?
- Seller acquisition strategy: curated invites vs open marketplace signup?
- Minimum viable verification needed to prevent scams?
- How do we define “competitive” (≥3 bids, or within X% of median, etc.)?

---

## 17. Example: “Montana State long sleeve shirt in XL blue”

**Row 1 Request Tile:**  
“Montana State long sleeve shirt — XL — blue — budget $45 shipped — new only — delivery by next Friday”

**Agent actions (timeline):**
1) Structured RequestSpec created  
2) Invited sellers:
- campus bookstore
- major fan apparel retailer
- 2 print-on-demand shops
- 1 local screen printer
3) 4 bids received  
4) Agent highlights:
- best price
- fastest delivery
- best return policy

User chats: “Widen to navy/royal, allow used if like-new.”  
Agent updates spec, re-requests bids, and the row updates with new tiles.

---
