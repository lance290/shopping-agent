# PopSwaps™: 0-to-1 CPG Sales & Outreach Playbook

**Context:** This document outlines the initial go-to-market and business development strategy for acquiring CPG (Consumer Packaged Goods) offers for Pop Savings. Because Pop is starting from zero users, we must manually seed the first batch of offers to prove the model before unlocking enterprise aggregator APIs.

---

## Phase 1: The "0 to 1" Manual Seeding Strategy

Since we cannot access large aggregator APIs without proven user volume, we must manually recruit 10-20 brands to offer "PopSwaps" (e.g., swapping A1 Sauce for Heinz 57).

### 1. Target "Challenger" Brands
Do not attempt to email legacy conglomerates (Kraft, Coca-Cola, P&G). They move too slowly and require massive scale. Target venture-backed or mid-market "challenger" brands who are hungry to steal market share from incumbents.
*   **Examples:** Magic Spoon (cereal), Poppi/Olipop (soda), Primal Kitchen (condiments), Truff, Liquid Death, Siete.
*   **Why them?** They have digital-first marketing teams, high customer lifetime value (LTV), and are accustomed to experimenting with higher Customer Acquisition Costs (CAC).

### 2. Find the Right Person
Use LinkedIn or email finders (like Hunter.io/Apollo) to find the decision-makers at these specific brands.
*   **Titles to search:** 
    *   Director of Shopper Marketing
    *   VP of Growth
    *   VP of E-commerce
    *   Head of Performance Marketing

### 3. The Pitch (Cold Email / LinkedIn)
Keep the outreach under 4 sentences. The core value proposition is **risk-free competitor conquesting**. They only pay for proven, receipt-verified conversions.

**Template:**
> **Subject:** Stealing market share from [Incumbent Brand, e.g., A1 Sauce]
> 
> Hi [Name],
> 
> I'm building Pop, an AI grocery assistant that intercepts shoppers right as they add items to their grocery list. 
> 
> When a user types "add A1 Sauce", Pop suggests swapping it for [Their Brand, e.g., Heinz 57] instead, backed by a digital rebate. You only pay us a flat fee if the user actually scans a receipt proving they bought your product.
> 
> Can I show you a 60-second demo of how this looks for the consumer?

### 4. The Deal Structure
Keep the friction to absolute zero to get a quick "Yes". 
*   **The Ask:** Request a very small pilot budget (e.g., $500). 
*   **The Economics:** Agree on a rebate amount to give the user (e.g., $1.50 off) and a platform fee for Pop (e.g., $0.50). Total cost to the brand: $2.00 per verified sale.
*   **Fulfillment:** You collect the $500 upfront via Stripe. We manually input their offer into the Pop CSV importer (`POST /pop/admin/swaps/import-csv`). As users scan receipts, you pay out the rebate via GroFlo/Venmo/PayPal and keep the $0.50 margin.

---

## Phase 2: Scaling via Ibotta (The IPN)

Ibotta is the ultimate scale solution. They run the **Ibotta Performance Network (IPN)**, which exposes a REST API containing over 2,600+ live CPG offers from major brands. 

### How to transition to scale:
1. **Do things that don't scale (Phase 1):** Close 10-20 manual pilot deals using the playbook above.
2. **Drive Volume:** Use these high-value, exclusive deals to acquire your first 1,000 users via the Pop referral network (copylinks).
3. **The Flip:** Once you have ~1,000 active users and a healthy MoM growth rate in receipt scans, contact Ibotta's BD/Partnerships team. You now have the required metrics to prove you are a viable publisher.
4. **Integrate:** Sign the Ibotta enterprise publisher agreement, plug their API into the `IbottaProvider` scaffolding we already built in the backend, and instantly expand from 20 manual deals to thousands of automated deals.
