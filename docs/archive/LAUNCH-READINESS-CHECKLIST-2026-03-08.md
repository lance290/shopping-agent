# Launch Readiness Checklist

Date: 2026-03-08

Scope:
- BuyAnything
- PopSavings / Pop

## Executive Summary

Current recommendation:
- Do not open-launch the combined product as-is.
- BuyAnything can ship to a limited beta once the confirmed 0% platform fee policy is fully enforced in code, and the repository is split.
- PopSavings can ship to a closed pilot if wallet credits are clearly described as credits, not withdrawable cash, until payout, KYC, and policy work are complete.

Top-line judgment:
- We have locked the BuyAnything monetization policy: **strictly 0% platform fees**.
- The most critical architectural decision made is to **split the codebases**. Mixing an ultra-high-net-worth concierge with a budget grocery clipper in one repo creates unacceptable compliance and security blast radiuses.
- Pop has the stronger business concept, but its cashflow, payout, and compliance layers are incomplete.

## Go / No-Go By Product

### BuyAnything

Decision today:
- No-go for broad public launch.
- Conditional go for limited beta after the P0 items below (including the codebase split) are completed.

Reason:
- The zero-fee policy is now officially confirmed, but live code and tests still contain 5% fee-taking and payment-intermediary behavior that must be purged.
- The application must be structurally isolated from PopSavings to ensure data privacy for high-net-worth users.

### PopSavings

Decision today:
- No-go for broad public launch.
- Conditional go for invite-only pilot if credits are non-cash, brand-funded, and contractually explicit.

Reason:
- The demand loop is promising.
- The payout and margin logic are not mature enough for scaled consumer launch.
- The core promise is "save money and earn money back," but the repo does not yet support a complete, compliant cash-out flow.

## Launch Blockers

Owner labels are suggested roles, not named people.

| ID | Severity | Owner | Product | Blocker | Required Action | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| P0-0 | P0 | CTO + Backend | Both | **Codebase Entanglement**. BuyAnything and PopSavings share the same repo, DB models, and services. | Execute a hard split of the codebase into two distinct repositories/microservices to prevent domain leakage and limit liability blast radius. | `apps/backend/models/auth.py`, `apps/backend/models/bids.py` |
| P0-1 | P0 | Founder + Backend + Legal/Ops | BuyAnything | **Fee Logic Remains**. Monetization policy is locked to zero fees, but code/tests still enforce fees. | Enforce the confirmed 0% fee policy. Remove the contradictory 5% fee-taking paths and logic from code, tests, and copy. | `apps/frontend/app/disclosure/page.tsx`, `apps/backend/routes/checkout.py`, `apps/backend/tests/test_zero_fee_policy.py` |
| P0-2 | P0 | Backend + Ops/Security | Both | Admin operation secrets are hardcoded in source. | Move all admin keys to environment variables, rotate the existing values, and audit any deployed use of those endpoints. | `apps/backend/routes/admin_ops.py` |
| P0-3 | P0 | Backend + Ops/Security | Both | Stripe webhooks accept unsigned payloads when secrets are missing. | Fail closed in non-local environments. Add an explicit environment gate so unsigned webhooks are impossible in staging/production. | `apps/backend/routes/checkout.py`, `apps/backend/routes/stripe_connect.py` |
| P0-4 | P0 | Backend + Legal/Ops | BuyAnything | Privacy policy says anonymous search queries are not stored, but guest rows persist search titles/specs. | Either stop persisting guest query content or update the privacy policy to reflect what is actually stored. | `apps/frontend/app/(public)/privacy/page.tsx`, `apps/backend/routes/rows.py` |
| P0-5 | P0 | Backend | BuyAnything | Seller Stripe onboarding path is internally broken or brittle because it references `merchant.business_name` on the unified Vendor model. | Fix the field mapping, add tests around onboarding, and verify the full merchant setup flow end-to-end. | `apps/backend/routes/stripe_connect.py`, `apps/backend/routes/merchants.py` |
| P1-1 | P1 | Founder + Product + Finance | Pop | Pop unit economics are not coherent yet. Sales docs assume `rebate + Pop fee`, but live ledger logic only clearly credits the shopper and referrer. | Define a real live margin model per redemption: brand spend, user reward, referral reward, OCR/fraud cost, payout cost, Pop margin. Reflect it in models and contracts. | `docs/sales/POP_CPG_OUTREACH_PLAYBOOK (1).md`, `apps/backend/models/coupons.py` |
| P1-2 | P1 | Product + Legal/Ops + Backend | Pop | Pop promises money-back behavior without a finished cash-out, KYC, or payout rail. | Decide launch language: either `wallet credits only` for pilot, or implement real cash-out, KYC, and payout rails before public launch. | `docs/active-dev/PRD-PopSwaps-Rebate-Flow.md`, `apps/backend/routes/pop_wallet.py` |
| P1-3 | P1 | Growth + Product | Pop | Viral loop is present but not yet strong enough to guarantee organic growth. | Instrument the loop before scaling spend: invite sent, invite opened, signup conversion, first receipt scan, second receipt scan, wallet accumulation, referral conversion. | `apps/backend/routes/pop_referral.py`, `apps/frontend/app/pop-site/list/[id]/components/PopListFooterActions.tsx` |
| P1-4 | P1 | Product + Growth | BuyAnything | BuyAnything viral loop is weak. | Treat virality as secondary. Lead with repeat usage, concierge value, enterprise referrals, and affiliate monetization until a stronger loop exists. | `apps/backend/services/deal_pipeline.py`, `apps/frontend/app/share/[token]/page.tsx` |
| P1-5 | P1 | Backend + Partnerships | Pop | Supply-side scale is still partly manual; Ibotta is still a stub. | Launch with manual/challenger-brand supply only, and do not plan growth assumptions around aggregator scale until it is real. | `apps/backend/services/coupon_provider.py` |
| P1-6 | P1 | QA + Backend + Frontend | Both | Current launch confidence is low while the broader suite is not green. | Re-run and fix the failing frontend/backend suites before any public launch decision. | Prior audit found failing `pnpm test` and `uv run pytest -q`. |

## Recommended Owner Map

- Founder / Product:
  - Oversee the codebase split strategy.
  - Decide whether Pop launches as `credits-only pilot` or `cash-out product`.
- Backend:
  - Execute the physical codebase split between BuyAnything and PopSavings.
  - Rip out all >0% fee logic for BuyAnything.
  - Fix Stripe onboarding.
  - Lock down webhooks and admin ops.
  - Align data flow with privacy promises.
- Frontend:
  - Align marketing and disclosure copy with the strictly 0% fee reality.
  - Make Pop wallet language explicit if cash-out is not available.
- Legal / Ops:
  - Draft Terms of Service (currently missing entirely).
  - Review privacy, campaign funding language, and payout language to ensure regulatory compliance.
  - Rotate secrets and define environment requirements for payment endpoints.

## Recommended Execution Order

### Phase 1: Architecture Split & Policy Enforcement

Goal:
- Enforce the 0% fee decision and split the domains to resolve liability leakage.

Actions:
1. Initialize the physical codebase split (separate repositories or strictly isolated services/DBs for BuyAnything and Pop).
2. Strip all >0% platform fee logic, escrow-intermediary behaviors, and related tests from BuyAnything.
3. Freeze launch copy around the zero-fee decision.

Exit criteria:
- Two distinct deployment paths/repos exist for the two products.
- BuyAnything checkout and tests reflect exactly 0 fees.

### Phase 2: Security And Legal Floor

Goal:
- Remove avoidable liability and compliance blockers.

Actions:
1. Draft and publish Terms of Service.
2. Rotate and externalize admin keys.
3. Fail closed on Stripe webhooks outside local dev.
4. Align privacy policy with actual guest-search storage behavior.
5. Re-review payments language to avoid accidental escrow/intermediary claims.

Exit criteria:
- Terms of Service are live.
- No hardcoded live ops secrets.
- No unsigned payment webhooks in non-local environments.
- Privacy copy matches system behavior.

### Phase 3: Revenue Path Hardening

Goal:
- Make sure the chosen business models actually work.

Actions:
1. For BuyAnything, ensure affiliate clickout paths are intact and working alongside the zero-fee checkout.
2. Fix merchant Stripe onboarding.
3. For Pop, define the real redemption margin and referral-share math.
4. Confirm the first brand-funded pilot structure in contract form, not just PRD form.

Exit criteria:
- BuyAnything revenue path is strictly affiliate-driven and coherent.
- Pop per-redemption unit economics are explicit and defensible.

### Phase 4: Growth Instrumentation

Goal:
- Measure whether the loops are working before scaling.

Actions:
1. Instrument BuyAnything share-view to project-start conversion.
2. Instrument Pop invite-to-signup, signup-to-first-list, first-list-to-first-receipt, and receipt-to-repeat usage.
3. Add weekly funnel reporting.

Exit criteria:
- You can answer where acquisition, activation, and repeat usage are breaking.

### Phase 5: Launch Readiness Verification

Goal:
- Replace intuition with a clean launch gate.

Actions:
1. Get frontend and backend test suites green on BOTH new repositories.
2. Run a manual payments checklist.
3. Run a guest-flow/privacy checklist.
4. Run a disclosure/terms consistency review.

Exit criteria:
- A launch go/no-go can be made from evidence rather than hope.

## Product-Specific Recommendations

### BuyAnything: What To Do Now

Recommended near-term strategy:
- Launch as an affiliate-powered search and vendor-introduction platform with **0% fees**.
- Focus on repeat high-intent use cases where affiliate and referral value can be proven.

What not to do:
- Do not publicly imply a marketplace-with-protection model.
- Do not leave any 5% fee logic inside the codebase.
- Do not build growth expectations around viral sharing alone.

### PopSavings: What To Do Now

Recommended near-term strategy:
- Run a closed pilot with manual challenger-brand campaigns.
- Keep the messaging around "wallet credits" unless cash-out is real.
- Treat referral as an amplifier, not the primary engine, until savings are consistently meaningful.

What not to do:
- Do not promise withdrawable cash before payout rails exist.
- Do not assume Ibotta or large-scale coupon supply is imminent.
- Do not scale referral economics until margin is explicit.

## Business Gaps To Close

### BuyAnything
- The physical code split from PopSavings.
- Complete removal of legacy escrow and fee-taking logic.

### PopSavings
- A signed pilot structure with explicit brand economics.
- A finished payout/compliance plan.
- A measured activation and retention funnel.
- A defensible margin after OCR, fraud review, referral incentives, and payout costs.

## Liability Watchlist

This is not legal advice. It is an engineering/business risk list that needs counsel review.

- **Data Leakage:** Running a UHNW concierge alongside a grocery app exposes high-value profiles to mass-consumer attack vectors.
- **Missing ToS:** The platform operates without basic Terms of Service.
- **Privacy mismatch:** Public policy appears narrower than real guest data persistence.
- **Security posture:** Hardcoded ops secrets and webhook fail-open behavior are avoidable operational risks.

## Minimal Launch Gate

Do not move to open launch until all of the following are true:

- **Codebases are fully split.**
- BuyAnything monetization policy (0% fees) is explicitly enforced in code.
- Terms of Service are drafted and live.
- Admin secrets are rotated and no longer committed.
- Stripe webhooks fail closed in non-local environments.
- Seller Stripe onboarding works end-to-end.
- Privacy copy matches actual guest-search behavior.
- Pop launch language matches actual wallet/payout behavior.
- Test suites are green.

## My Recommendation

If you want momentum without creating unnecessary liability:

1. **Execute the codebase split.**
2. Launch BuyAnything as a narrow beta with **0% fees** and affiliate monetization only.
3. Launch Pop as a closed pilot with funded brands and credits-only wallet language.
