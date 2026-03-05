# PRD: Phase 8 - Coupon Network & CPG Activation

> **CRITICAL ARCHITECTURE NOTE:** PopSavings runs in the same monorepo as the primary `BuyAnything` application. You are free to integrate or share components, but you MUST NOT break, modify, or regress any core `BuyAnything` workflows, search APIs, or chat interfaces while implementing this PRD.

## 1. Overview
PopSavings aims to convert raw shopping intent into a monetizable network by connecting household lists directly to CPG (Consumer Packaged Goods) brand managers. Using a combination of Kroger MCP for item selection, Scout/Tod for automated outreach, and a self-serve portal, PMs can embed GroFlo-powered coupons directly into users' lists. This creates a B2B2C flywheel where brands are incentivized to share lists with their audiences.

## 2. Goals & Acceptance Criteria
- **Item Selection via Kroger MCP:** Users can search and select specific, purchasable retail items using the Kroger MCP integration (managed by Lance).
- **Brand Mapping & PM Outreach:** Backend maps selected items to their parent CPG brands and product managers. Jeremy provides the database of every CPG product manager. Pop/Tod executes automated outreach to these PMs.
- **Scout Referral Routing:** Kris and Peggy utilize Scout to do referred routing of the coupon requests to all of those PMs.
- **Self-Serve Coupon Publishing:** PMs receive a secure link to a portal where they can self-serve add a GroFlo-powered coupon to their product.
- **In-List Coupon Display:** When a coupon is active for an item on a user's list, the UI displays a visual badge/button to "Clip Coupon."
- **Brand Amplification Incentive:** Brand managers who refer users (via TeamPop referral links) earn top sponsored deal slots under matching categories/items, and receive rev share for signing up users in their Wallet.
- **Acceptance Criteria:**
  - A user can search "Tide" and pick a specific Kroger item.
  - The system logs an intent-to-buy and queues a Scout outreach task for the P&G PM.
  - The PM portal allows adding a discount value (e.g., "$1.00 Off") and a GroFlo redemption link.
  - The frontend displays the $1.00 Off badge next to the Tide item.

## 3. Scope
- **Backend & Database:** 
  - `Coupon` and `CouponCampaign` models linked to `Row` or `Product`.
  - Integration script connecting the existing Kroger MCP to Pop's NLU/search pipeline.
  - Webhook/Task queue for Tod/Scout outreach generation based on high-velocity items.
- **Frontend (User):** UI enhancements to show clipped/available coupons on the list item.
- **Frontend (Brand Portal):** A lightweight unauthenticated (or magic-link authenticated) React route (`/brands/claim`) for PMs to submit coupon details.
- **Seed Data:** Initial load script for existing GroFlo coupons via MCP to ensure day-zero value.

## 4. Technical Implementation Notes
### Backend Pipeline
1. **Selection:** When a user adds an item, trigger an async job to query Kroger MCP for exact UPC/SKU matches. If the user picks an exact match, save `retailer_sku` and `brand_name` to the `Row`.
2. **Outreach Queue:** If `brand_name` doesn't have an active coupon, queue an event. A background worker (Tod) checks the PM database, formats an email via Scout, and sends a magic link: `https://pop.buyanything.ai/brands/claim?token=XYZ`.
3. **Portal:** The `/brands/claim` endpoint verifies the token, shows the item intent volume ("500 users want your product"), and provides a form to paste a GroFlo URL and discount amount.
4. **Distribution:** Once submitted, the system broadcasts the new coupon state to all active rows matching that `brand_name`/`retailer_sku`.

### Sponsored Deal Slot Logic
- When querying for offers/coupons for a row, check the `referred_by_id` tree. If the referring user is flagged as a `Brand Manager` in the wallet system, their associated brand's coupons are ranked first and visually highlighted as "Sponsored."
