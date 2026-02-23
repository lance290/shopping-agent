# PRD: Demo Preparation & Polish

## Business Outcome
- Measurable impact: Investor demo on Thursday runs flawlessly — all three scenarios execute without errors, crashes, or awkward pauses
- Success criteria: Demo tells a coherent story: commodity retail → vendor introduction → viral loop, with real working software at every step
- Target users: Investor audience (Thursday demo), internal team (QA verification)

## Scope
- In-scope:
  - Pre-test all demo queries to ensure they return results (avoid API quota surprises)
  - Polish social features UX: likes, comments, shares all function end-to-end
  - Verify affiliate system is ready to activate (env vars documented, handlers tested)
  - Prepare demo script with three scenarios
  - Ensure the entire public surface is coherent (no broken links, no placeholder content)
- Out-of-scope:
  - Building new features (everything needed is in PRDs 00-05)
  - Affiliate network applications (post-demo)
  - Vendor commission negotiations (aspirational)

## User Flow (Demo Script)

### Scenario A: "Roblox gift cards" (Commodity retail — affiliate path)
1. Open public homepage (anonymous) → type "Roblox gift cards $100"
2. Search results page shows Amazon/eBay/Google Shopping results
3. Click "Buy" → affiliate redirect to retailer with tracking params
4. Show `ClickoutEvent` logged in system (handler_name, affiliate_tag)
5. **Story**: "This click earns us affiliate commission. No login required."

### Scenario B: "I need a caterer for a 50-person corporate event" (Vendor directory path)
1. Switch to workspace (logged in) → type the request
2. System searches ALL providers in parallel — three-stage re-ranker scores by intent fit, vendor directory caterers score high, Amazon results sink naturally
3. Show 3-5 caterer vendor tiles matched by embedding similarity
4. Click "Request Quote" → one-click outreach (no form filling — identity auto-populated)
5. Show the outreach email draft + tracking status
6. **Story**: "One click, 5 vendors contacted. The EA's job went from 45 minutes to 2."

### Scenario B-alt: "Charter a jet from SAN to Aspen" (High-end variant if audience warrants)
- Same flow, charter operators instead of caterers. Shows range.

### Scenario C: "The viral loop" (Tell the growth story)
1. Show the caterer who received our outreach
2. "This caterer needs to buy things too — serving equipment, linens, a van, marketing materials."
3. "When they search for those, we connect them with OTHER vendors — or route to Amazon for commodity items."
4. Show the indie bookstore angle: "The bookstore owner needs shelving, a POS, shipping supplies."
5. Show referral attribution code (share page → localStorage → verifyAuth → User.referral_share_token)
6. **Key insight**: "The flywheel spins fastest at the small/mid tier — a local bakery buys more often than a Gulfstream operator."

## Business Requirements

### Authentication & Authorization
- Demo Scenario A: must work fully anonymous (tests the public surface)
- Demo Scenario B: must work logged in (tests the workspace)
- Demo Scenario C: storytelling — no live auth required, just code walkthrough

### Monitoring & Visibility
- Pre-demo: verify all search providers are responding (check API quotas)
- Pre-demo: verify clickout tracking is logging events
- Pre-demo: verify outreach email sending works (or have mock mode ready)

### Billing & Entitlements
- Affiliate env vars documented but not necessarily active for demo (affiliate accounts pending)
- Demo can show the `LinkResolver` handler list and explain activation is env-var-only

### Data Requirements
- Pre-seed demo data if needed: known vendors for "caterer" and "charter" queries
- Ensure vendor embeddings are fresh for demo queries
- Have a clean user account for demo (no stale rows cluttering the workspace)

### Performance Expectations
- All demo scenarios complete within 30 seconds each (no waiting for slow APIs)
- If a provider is slow, the demo should show partial results (streaming) rather than blank screen

### UX & Accessibility
- Likes: heart icon toggles visually with count badge
- Comments: comment count visible on OfferTile, comments panel accessible
- Share links: produces working URLs, public share page renders correctly
- No visual bugs, no console errors during demo

### Privacy, Security & Compliance
- Demo account should not contain real customer data
- If showing database/admin views, redact any PII

## Dependencies
- Upstream: ALL other PRDs (00-05) must be complete
- Downstream: Affiliate network applications (post-demo, separate effort)

## Risks & Mitigations
- API quotas exhausted during demo → Pre-test all demo queries day-of; have cached/mock fallback
- Search returns unexpected results → Pre-run demo queries, note which ones work reliably
- Demo account has stale data → Create fresh account or clear rows before demo
- Internet connectivity issues → Have screenshots/video backup of each scenario

## Pre-Demo Checklist
- [ ] All demo queries tested and returning good results
- [ ] Clickout tracking verified (check DB for ClickoutEvent records)
- [ ] Outreach pipeline verified (send test email, check tracking)
- [ ] Public homepage, search, guides, vendor directory all loading correctly
- [ ] No broken links in navigation
- [ ] No console errors on any page
- [ ] Social features (like/comment/share) working end-to-end
- [ ] Demo script rehearsed with timing

## Acceptance Criteria (Business Validation)
- [ ] Demo Scenario A runs end-to-end without errors (< 30 seconds)
- [ ] Demo Scenario B runs end-to-end without errors (< 30 seconds)
- [ ] Demo Scenario C story is coherent with working code evidence
- [ ] No broken links, no placeholder content, no "Coming soon" pages on any public page
- [ ] Social features (likes, comments, shares) all function visually during demo
- [ ] Affiliate system documentation ready: "set these 3 env vars and it's live"

## Traceability
- Parent PRD: `docs/active-dev/demo-day/parent.md`
- Product North Star: `.cfoi/branches/dev/product-north-star.md`

---
**Note:** Technical implementation decisions (mock data strategy, demo account setup, rehearsal logistics) are made during /plan and /task phases, not in this PRD.
