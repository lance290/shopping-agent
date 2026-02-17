# BuyAnything — Product Requirements Document (PRD)
**Product:** buy-anything.com  
**Doc owner:** Lance  
**Version:** 1.0  
**Date:** 2026-02-16  
**Status:** Draft for build

---

## 1) Summary

BuyAnything is a “buy anything” marketplace optimized for **HNWI + Executive Assistants (EAs)**. It must feel absurdly simple to use for both:
- **Everyday retail** (e.g., Roblox gift cards, AirPods, luggage) → monetized via **affiliate links**.
- **High-ticket, high-friction purchases** (e.g., jet charters, mega-yachts, custom jewelry) → monetized via **vendor referrals / concierge facilitation**, **without** BuyAnything acting as the merchant of record.

The core redesign goal is to **separate Public vs Private experiences** so we can:
- get approved quickly by affiliate networks (public, indexable, content-rich),
- while preserving a **login-required system of record** for real deals.

---

## 2) Goals

### Product goals
1. **One place to start:** a single entry point that lets a user request *anything* and routes them correctly.
2. **Zero shame UX:** buying a $25 gift card should feel as “premium” as requesting a $25M yacht.
3. **Fast approvals for affiliate networks:** a **public, reviewable surface** that is content-rich and compliant.
4. **Private deal rooms:** maintain an auditable system of record for EA-driven procurement workflows.
5. **Vendor quality + trust:** emphasize vetted vendors, clear process, and confidentiality.

### Business goals
- Activate affiliate revenue quickly while high-ticket supply ramps.
- Capture high-intent demand in a structured way to enable vendor fulfillment.
- Convert “curious browsing” into requests and qualified leads.

### Success metrics (KPIs)
**Activation**
- Time to first meaningful action (TTV): < 60 seconds to click out (affiliate) or submit request (concierge).
- % of new users completing a “Buy Request” flow: target 20–35% for warm traffic.

**Conversion**
- Affiliate click-through rate (CTR) from curated pages: target 8–15%.
- Concierge request completion rate: target 10–20% from homepage sessions.
- Vendor response SLA: median < 2 hours (business hours) for high-ticket categories.

**Quality**
- Request → qualified lead rate: > 50% (high-ticket).
- % deals with complete audit trail (requirements, offers, decision): > 95%.

**Compliance**
- Affiliate program approvals achieved (Amazon, eBay, Skimlinks, Impact): all accepted within 2–4 weeks of launch target.
- Affiliate link disclosure coverage on pages with outbound links: 100%.

---

## 3) Non-goals

- Becoming a payment processor, escrow provider, or merchant-of-record (initially).
- Building a full two-sided “self-serve” luxury marketplace on Day 1.
- Replacing the Executive Assistant as the human-in-the-loop decision maker and operator.
- Fully automating high-ticket procurement end-to-end on Day 1 (the system should assist and compress time, not remove judgment).
- Price tracking / alerts for Amazon-linked items (avoid policy pitfalls until explicitly approved).

---

## 4) Core product thesis

**A single “Intent Router”** sits behind the homepage search box / CTA:
- If the request is **commodity retail** → show curated results + affiliate links (fast path).
- If the request is **high-consideration / service / bespoke / regulated** → route to a concierge request with minimal friction (premium path).
- If uncertain → ask 2–4 short questions, then route.

**The user should never have to decide which mode they are in.**

---

## 5) Personas

### P1 — HNWI Principal
- Wants “done-for-me” and confidentiality.
- Low tolerance for forms and fluff.
- Values trust signals, responsiveness, and discretion.

### P2 — Executive Assistant (Primary operator)
- Needs speed, clarity, audit trail, and repeatability.
- Manages multiple principals and budgets.
- Wants vendor comparisons and approvals in one place.

### P3 — Vendor / Provider (Jet charter, yacht broker, jeweler, etc.)
- Wants qualified leads with requirements.
- Needs an easy way to respond with options, pricing ranges, and availability.
- Wants to protect sensitive details and avoid tire-kickers.

### P4 — Affiliate Shopper (could be EA or principal)
- Wants a clean curated experience and quick outbound purchase.
- Less need for account creation.

---

## 6) User journeys

### Journey A — “I need Roblox gift cards”
1. User lands on public homepage.
2. Types: “Roblox gift card $100” into universal search.
3. Intent Router classifies as retail.
4. Results page shows curated options (Amazon/eBay/etc.) with clear disclosure.
5. User clicks out to merchant and buys.

**Success:** outbound click tracked; optional lightweight “save for later” prompt.

---

### Journey B — “Charter a jet from SAN to Aspen next week”
1. User types the request into homepage.
2. Intent Router classifies as high-ticket concierge.
3. Minimal form appears (3–6 fields) + “Upload itinerary” option.
4. User submits; optional login creation (EA-friendly) or “email-only” magic link.
5. A private deal room is created; **EA is the operator**. The system generates a clean brief and suggests vendors.
6. EA selects vendors to ping (or uses auto-suggest), invites them, and receives offers as cards.
7. EA compares, asks questions, gets approvals, and BuyAnything records the decision and “connected” outcome.

**Success:** response SLA met; deal moves to “Connected/Booked” with complete log.

---

### Journey C — “I don’t know what I want—just find me the best”
1. User lands on a public curated guide (e.g., “Best gifts for 12-year-old nephews”).
2. Browses; clicks affiliate links and/or hits “Concierge this”.
3. If they hit concierge, prefill request with page context.

---

## 7) Information Architecture (IA)

### Public surface (indexable, no login required)
- **/** Home (universal search + curated entry points)
- **/categories** (Retail, Travel, Gifts, Tech, Experiences, Home, Luxury, etc.)
- **/guides/** (editorial content, “vault” pages, checklists)
- **/vendors/** (public vendor directory / spotlights where appropriate)
- **/how-it-works**
- **/about**
- **/contact**
- **/privacy**
- **/terms**
- **/affiliate-disclosure** (also inline disclosures on relevant pages)

### Private surface (login required; system of record)
- **/app** (shell)
- **/app/inbox** (requests + messages)
- **/app/requests/new**
- **/app/requests/:id** (deal room)
- **/app/vendors** (vendor management)
- **/app/principals** (HNWI profiles / households)
- **/app/settings** (roles, security, preferences)

**Implementation requirement:** root domain must not force redirect to /login.  
Login should live at **/app/login** or **app.buy-anything.com**.

---

## 8) Functional requirements

### 8.1 Universal Search + Intent Router (Public)
**User story:** As a user, I can type anything I want to buy and be routed to the right path.

**Requirements**
- Single search input on homepage and persistent header.
- Supports free text (e.g., “mega yacht”, “Roblox gift cards”, “wedding gift for CEO”).
- Router outputs:
  1) **Retail results** page
  2) **Concierge request** wizard
  3) **Hybrid** (top retail results + “Need help?” concierge CTA)

**Routing signals (v1 heuristic)**
- Keywords: “charter”, “yacht”, “broker”, “bespoke”, “custom”, “availability”, “quote”, “private chef”, “security”
- Price/scale cues: “million”, “$50k”, “crew”, “itinerary”
- Category: services/experiences vs goods
- Confidence score:
  - High confidence retail → direct results
  - High confidence concierge → wizard
  - Low confidence → ask 2–3 questions

**Acceptance criteria**
- 95% of common retail queries route to retail.
- 90% of luxury/service queries route to concierge.
- Any user can override with a “Switch to concierge / Switch to retail” toggle.

---

### 8.2 Retail Results (Affiliate) (Public)
**User story:** As a user, I can quickly click out to buy a retail item from trusted merchants.

**Requirements**
- Result cards include:
  - product title, image, approximate price (if allowed), merchant logo
  - short reason (“Top pick”, “Best value”, “Fast shipping”)
  - “Buy” button (outbound affiliate link)
- Sorting: Top picks, price, rating (where available/allowed)
- Strong disclosure near the grid and in footer.
- Track outbound clicks, merchant, page, query.

**Nice-to-have**
- “Save” wishlist (requires login or email magic link)
- “Ask concierge to handle it” CTA on every retail page

---

### 8.3 Concierge Request Wizard (Public → Private)
**User story:** As an EA, I can submit a high-ticket request in under 2 minutes.

**Requirements**
- 3-step max wizard (with progressive disclosure)
  1) What are you buying? (prefilled from search)
  2) Key requirements (category-dependent)
  3) Contact + confidentiality preference
- Category templates (examples):
  - Jet charter: route, dates, pax, luggage, preferences, budget band
  - Yacht: destination, dates, guests, style, budget band, must-haves
  - Jewelry: type, occasion, materials, timeline, budget band
- Budget captured as **ranges** (avoid forcing exact numbers)
- File upload: itinerary/spec sheet
- Create request with:
  - request id
  - summary
  - requirement fields
  - contact identity (principal or EA)
- After submit: show “Deal Room created” + invite to sign in / magic link.

**Acceptance criteria**
- Median time to submit request < 120 seconds for a templated category.
- Works without account creation; account creation prompted after submit.

---

### 8.4 Deal Room (Private)
**User story:** As an EA, I can run the full lifecycle end-to-end: brief → vendor outreach → offers → compare → approval → connect → outcome.

**Requirements**
- Timeline/activity log (immutable events)
- Messaging thread (EA ↔ vendors, with optional internal concierge/support)
- Requirements panel with structured fields + free notes
- Vendor offer cards:
  - price range, availability, terms, highlights, attachments
  - compare view (2–4 offers side-by-side)
- Status workflow:
  - Draft → Submitted → EA outreach → Offers received → Shortlist → Approved → Connected/Booked → Closed (won/lost)
- Approvals:
  - “Needs principal approval” toggle
  - “Approved by” event logging
- Confidentiality:
  - vendor sees only what’s necessary until NDA stage (toggle)

**Acceptance criteria**
- 100% of key events logged (submit, vendor invited, offer received, decision, close).
- EA can export a summary PDF (v2).

---

### 8.5 Vendor Directory + Onboarding (Hybrid)
**User story:** As BuyAnything, we can manage and showcase vetted vendors.

**Requirements**
- Vendor records:
  - category, service areas, minimums, response SLA, contact method
  - verification status (vetted / pending / paused)
- Two modes:
  - **Private vendors only** (default for luxury)
  - **Public vendor spotlights** (optional marketing content)
- Vendor portal (v2):
  - accept invitations
  - submit offers via form
  - attach PDFs/images

---

### 8.6 Household / Principal Management (Private)
**User story:** As an EA, I can represent multiple principals/households with separate preferences.

**Requirements**
- Household entity with principals + assistants
- Role-based access:
  - Principal, EA, concierge, admin
- Preferences:
  - travel prefs, dietary, brands, “do not use vendors”, budget style

---

### 8.7 Trust & Safety / Compliance (Public + Private)
**Requirements**
- Clear disclaimers:
  - BuyAnything connects buyers and sellers; not the seller; no warranties on vendor performance (subject to final legal).
- Affiliate disclosures:
  - sitewide disclosure blocks for pages with affiliate links
  - merchant-specific required text where applicable
- Privacy:
  - track clicks with consent as required
  - clear cookie banner if used

**Acceptance criteria**
- Every page that contains affiliate links has an inline disclosure above first link/grid.
- Public pages are crawlable and not blocked by auth.
- No “coming soon” / placeholder content in navigation.

---

## 9) Content strategy (for approvals + conversion)

### Minimum viable public content (first 2 weeks)
Create 20–40 pages total, mix of:
- 10–15 “Guides” (EA playbooks, gift vaults, travel essentials, etc.)
- 5–10 category landing pages (retail + luxury)
- 5–15 vendor spotlights (if allowed; otherwise anonymized “how we source”)

**Each page should:**
- contain unique copy (no thin AI sludge)
- include curated outbound links (affiliate where applicable)
- include “Concierge this” CTA

### Content templates
- “BuyAnything Vault: Gifts for ___”
- “Executive Assistant Checklist: ___”
- “The BuyAnything Standard: How we vet ___ vendors”
- “The Concierge Brief: What we need to source ___ fast”

---

## 10) UX principles

1. **One box. One answer.** Everything starts from one input.
2. **Two clicks to value** (affiliate click or concierge submit).
3. **Always premium**: minimal UI, high trust, no clutter.
4. **Confidential by default** for luxury/service.
5. **EA-first** workflow: principals can approve, but EAs operate.

### EA-as-Operator by default
- Assume an EA is running the workflow: gathering requirements, comparing options, getting approvals, and recording outcomes.
- AI + tooling must reduce the EA’s work to: **2-minute brief → curated options → one-click approval packet → vendor connection**.


---

## 11)
---

## 11) Design requirements

### Public
- Homepage hero: universal search + 6–9 “jump” categories
- Persistent header search
- Curated collections with large cards (not dense grids)
- “Concierge this” button as a first-class action

### Private
- Inbox-centric layout
- Deal room with 3-column layout:
  - Left: timeline/messages
  - Center: offers + compare
  - Right: requirements + status

---

## 12) Technical requirements (implementation-agnostic)

### Separation of concerns
- Public site must be **accessible without auth**, indexable, and fast.
- Private app must enforce auth, RBAC, and audit logging.

### Security
- SOC2-aligned logging practices (event logs, access logs) even pre-SOC2
- Encrypt sensitive fields at rest where possible
- Vendor access scoped per request (least privilege)

### Performance
- Public pages: LCP < 2.5s on 4G for key pages
- Search results: < 500ms backend response (excluding third-party calls)

### Observability
- Track:
  - search queries + routing outcomes
  - affiliate outbound clicks
  - concierge funnel drop-offs
  - vendor response times

---

## 13) Data model (v1 conceptual)

- **User**
  - id, email, role(s), households[]
- **Household**
  - id, name, principals[], assistants[], preferences
- **Request**
  - id, created_by, household_id, category, summary, requirements{}, status
- **Offer**
  - id, request_id, vendor_id, price_range, availability, terms, attachments
- **Vendor**
  - id, categories[], regions[], status, sla_target
- **AffiliateClick**
  - id, user/session, merchant, url, page, timestamp, query

---

## 14) Integrations

### Affiliate networks (phased)
- Phase 1: simple outbound affiliate links + tracking
- Phase 2: merchant feeds / deep links (where available/allowed)
- Phase 3: personalization + recommendations

### Vendor comms
- Email + secure link to offer form (v1)
- Vendor portal (v2)

---

## 15) Rollout plan

### Phase 0 — “Approval-ready public surface” (1–2 weeks)
- Remove root redirect to /login
- Launch public IA pages + 20–40 content pages
- Implement disclosures + compliance pages
- Basic universal search + router (heuristic)
- Basic retail results pages with affiliate links

**Exit criteria**
- Public site passes internal review: no auth wall, no placeholders
- Ready to apply/submit for affiliate networks

---

### Phase 1 — “Concierge v1 + Deal Rooms” (2–4 weeks)
- Concierge request wizard → creates Request + Deal Room
- Inbox + deal room core workflow
- Vendor outreach via email with offer submission form

**Exit criteria**
- EAs can run real deals end-to-end with audit trail

---

### Phase 2 — “Vendor onboarding + compare + approvals” (4–8 weeks)
- Offer compare view
- Principal approval events
- Vendor directory + vetting workflow

---

### Phase 3 — “Scale + automation” (8–16 weeks)
- Smarter intent router (ML/LLM optional)
- Request auto-brief generation
- Vendor matching + SLA monitoring
- Saved preferences / repeat buys

---

## 16) Open questions / decisions to lock

1. **Brand positioning:** “Marketplace” vs “Concierge + marketplace” (affects copy + compliance).
2. **Account model:** magic link vs SSO; minimum friction for EAs.
3. **Confidentiality defaults:** what info is hidden from vendors until shortlist?
4. **Monetization:** referral fees vs subscription vs both (later).
5. **Category scope day-1:** which high-ticket verticals first?

---

## 17) Appendix — MVP page list (suggested)

**Homepage + core**
- / (public)
- /categories
- /how-it-works
- /about
- /contact
- /privacy
- /terms
- /affiliate-disclosure

**Category landers (10)**
- /categories/gifts
- /categories/travel
- /categories/tech
- /categories/home
- /categories/experiences
- /categories/fashion
- /categories/luxury (gateway)
- /categories/private-aviation
- /categories/yachts
- /categories/custom-jewelry

**Guides (10–15)**
- /guides/executive-assistant-playbook
- /guides/gift-vault-nephews
- /guides/private-flight-essentials
- /guides/best-luggage-for-private-travel
- /guides/how-to-brief-a-yacht-charter
- /guides/how-to-buy-a-rare-watch
- … etc.

**App**
- /app/login
- /app/inbox
- /app/requests/new
- /app/requests/:id
