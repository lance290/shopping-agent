# PRD: Dynamic Monetization Integration

## Business Outcome
- **Measurable impact:** Increase affiliate click-throughs by 10%; increase grocery swap claims by 15%; establish baseline metrics for the new "Tip Jar" mechanism.
- **Success criteria:** Zero regression in CPA tracking integrity; Tip Jar generates measurable revenue within first 30 days of active deployment.
- **Target users:** Users who are ready to make a purchase decision based on the options presented.

## Scope
- **In-scope:** Injecting context-aware calls to action (CTAs) into the SDUI schemas via the `ActionObject` contract (Schema Spec §4). Specifically supporting Affiliate Links, Grocery Swap Claims (including undo/revert), Escrow Funding, and Goodwill Tips. Moving the URL resolution for external links entirely to the backend. Implementing the 30% referral revenue share on **swap payouts only** (affiliate CPA, escrow take-rate, and tips are excluded from rev share — see PRD §6.2).
- **Out-of-scope:** Building the actual payment processing gateways (Stripe integration) or the receipt scanning OCR engine.

## User Flow
1. **Affiliate:** User clicks "Buy on Amazon" on an option. The server instantly resolves the current affiliate tracking tag and redirects them to Amazon.
2. **Coupon Swap:** User clicks "Claim $1.00 Swap". The UI instantly updates to show a "Pending Receipt" uploader block.
3. **Swap Undo:** User accidentally claims a swap. They tap "Undo" within the grace period. The claim status reverts and the UI shifts back from the receipt uploader to the comparison view.
4. **High-Ticket Escrow:** User agrees to a $15k vendor quote. The UI shifts to a timeline showing "Funds in Escrow".
5. **Escrow Bypass → Tip Jar Fallback:** A UHNW user bypasses escrow and wires money directly to the vendor. The system detects no escrow was funded and surfaces the Tip Jar as the fallback revenue capture. (See PRD §6.3 Reality Check.)
6. **Tip Jar:** After the system detects the user saved significant money (or bypassed escrow), a friendly "Tip Jar" appears at the top of the list (`Project.ui_schema`) allowing them to send $5–$100 to the platform.
7. **Referral Payout:** When a referred user's swap claim is verified, 30% of the payout is automatically credited to the referrer's wallet.

## Business Requirements

### Authentication & Authorization
- **Who needs access?** Any authenticated user viewing the list. Shared-list viewers (with a valid `ProjectInvite` link) can click affiliate links after signing up. Truly unauthenticated users cannot see list contents.
- **What actions are permitted?** Any list viewer can click affiliate links. Only list owners and members (not "viewer" role) can claim swaps or fund escrows.

### Monitoring & Visibility
- **What business metrics matter?** CPA revenue, Swap claim conversion rate, Escrow funding rate, Tip conversion rate.
- **What operational visibility is needed?** Broken affiliate link rates (404s after redirect), backend URL resolution latency.

### Billing & Entitlements
- **How is this monetized?** Directly captures the core revenue models: Affiliate CPA, Grocery Brand Bidding (Swaps), Concierge Take-Rate (Escrow), and Direct Goodwill (Tips).

### Data Requirements
- **What information must persist?** The exact `Bid ID` must be logged alongside every affiliate click to measure which providers/options perform best.
- **ActionObject contract:** Every `ActionRow` block in the `ui_schema` uses the `ActionObject` type (Schema Spec §4) which includes `bid_id`, `url`, `merchant_id`, `product_id`, `amount`, and `count` fields. The `bid_id` is required for `outbound_affiliate` intents to guarantee click attribution.
- **Swap undo:** `PopSwapClaim.status` must support a `"reverted"` state (or reuse `"canceled"`) for accidental claims. Reverting a claim triggers a schema rebuild, shifting the Row layout back from `ROW_TIMELINE` to the comparison view.
- **Referral payouts:** When a swap claim is verified (`receipt_verified`), the system must check `User.signup_source` for a referrer and credit 30% of the payout to the referrer's `wallet_balance_cents`.
- **Data security:** Tracking parameters (affiliate tags) must never be stored in the static JSON schemas, as they rotate and expire.

### Performance Expectations
- **What response times are acceptable?** The backend redirect (`/api/out`) must resolve the final affiliate URL and return a 302 in <100ms so the user doesn't notice a lag before reaching the retailer.

### UX & Accessibility
- **What user experience standards apply?** The transition from clicking an action to seeing the state change (e.g., claiming a swap -> seeing the receipt uploader) must feel instant and native, driven by real-time SSE pushes.

### Privacy, Security & Compliance
- **What data protection is required?** Escrow and Tip transactions must comply with PCI-DSS (handled via Stripe). Affiliate tracking must strip PII before handing off to third-party networks.

## Dependencies
- **Upstream:** `prd-sdui-comparison.md` (the SDUI blocks themselves must exist).
- **Downstream:** Existing payment processing and affiliate network integrations.

## Risks & Mitigations
- **Risk:** Affiliate tracking breaks because the UI schema uses a stale tag.
- **Mitigation:** The UI schema stores only an "intent" and the raw product ID. The backend constructs the final URL with the live tag at the exact moment of the click.

## Acceptance Criteria (Business Validation)
- [ ] 100% of affiliate clicks successfully log the source `Bid ID` in internal analytics before redirecting.
- [ ] Server-side URL resolution (`/api/out`) maintains a p99 latency of <100ms.
- [ ] Claiming a swap successfully updates the backend state machine and triggers a UI layout shift without requiring a page reload.
- [ ] Undoing a swap claim (within grace period) reverts the claim status and rebuilds the Row schema back to the comparison layout.
- [ ] Referral: When a referred user's swap is verified, 30% of the payout is credited to the referrer's wallet.
- [ ] Tip Jar appears in `Project.ui_schema` after a purchase is completed or when escrow bypass is detected.
- [ ] No affiliate link in any persisted `ui_schema` contains a tracking tag — all tags are appended at click time by `/api/out`.

## Traceability
- Parent PRD: `docs/active-dev/sdui-universal-list/parent.md`
