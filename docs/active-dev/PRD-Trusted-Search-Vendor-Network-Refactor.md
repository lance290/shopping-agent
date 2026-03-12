# PRD: Trusted Search & Vendor Network Refactor

**Status:** Draft
**Author:** Engineering
**Date:** 2026-03-12
**Priority:** P0 — Trust, contact quality, and coverage determine product viability
**Depends on:** PRD-LLM-Tool-Calling-Search-Architecture (implemented, `USE_TOOL_CALLING_AGENT=true`)

---

## 1. Problem Statement

BuyAnything is not a generic search product. It is a transaction-intelligence product for executive assistants and other high-trust operators who need to **find, assess, and act on the best source for anything**.

Today, the system can sometimes find results, but it does not consistently answer the more important questions:

- Is this query location-sensitive?
- Is this a buy-now product, a quote-based service, or a brokered high-end deal?
- Is direct contact information required to make this result useful?
- Is this source trusted enough to show prominently?
- If we do not already know the right source, how do we find one fast and explain that clearly to the user?

The current search stack over-optimizes for returning results and under-optimizes for returning **the right kind of result with the right degree of trust and actionability**.

### Observed Failures

| Failure | Why it matters |
|--------|----------------|
| Articles, listicles, and aggregators appear for purchase-intent queries | Erodes trust and wastes time |
| Service queries show product-style CTAs | Misrepresents how the deal actually closes |
| Location-sensitive queries are treated too loosely | Results become irrelevant even if nominally related |
| Contact quality is not primary for high-end services and brokered deals | A result without a usable human path is often worthless |
| Vendor DB is inconsistent, under-verified, and hard to improve from the UI | The moat cannot compound |
| Misses feel like search failure instead of intelligent discovery | The user loses confidence quickly |

### Core Insight

For BuyAnything, **search is not “find links.”** Search is:

> Return the best contactable trusted source for this transaction type, in this geography, and make the next step obvious.

---

## 2. Product Principles

1. **Trust beats completeness.** A short list of contactable, high-confidence sources is better than a long list of scraped links.
2. **Query details must drive search behavior.** Location sensitivity, transaction mode, trust sensitivity, and urgency are first-class signals.
3. **High-end deals are human workflows.** For luxury services, brokered assets, and bespoke procurement, contact quality outranks raw volume.
4. **The vendor graph is the product.** Crawlers and APIs are acquisition layers; the differentiated asset is the trusted vendor network.
5. **Every miss should teach the system.** When we do not have enough trusted supply, discovery should run fast and persist useful new candidates.
6. **EAs must be able to curate the graph directly.** Saving, editing, rating, and trusting sources should be easy.

---

## 3. Goals

### Primary Goals

1. Refactor search so every query is interpreted through a structured decision layer before tool selection.
2. Make vendor trust, contactability, and provenance explicit ranking inputs.
3. Give EAs a fast workflow to add, edit, and rate trusted sources.
4. Detect coverage gaps in real time and run live discovery quickly when the DB is insufficient.
5. Communicate clearly to the EA when results come from trusted inventory vs newly discovered candidates.

### Non-Goals

1. Building a custom crawler platform from scratch.
2. Solving every category with one provider or one scraper.
3. Opening community ratings publicly without moderation.
4. Replacing all existing provider integrations immediately.

---

## 4. User Stories

### Executive Assistant

- As an EA, when I ask for a local or service-based source, I want the system to prioritize direct providers with real contact paths.
- As an EA, when I ask for a luxury or brokered asset, I want trusted brokers, dealers, or resellers first, not generic articles.
- As an EA, when BuyAnything does not already know the right source, I want it to tell me that and search live without feeling broken.
- As an EA, when I find a good source, I want to save it to my trusted network in seconds.
- As an EA, when a source changes, I want to edit it without needing engineering help.

### Team / Organization

- As a team, we want a clear path to shared trust over time, but Phase 3 ships with personal endorsements only until a Team/Organization model exists.
- As an admin, I want provenance and auditability so I know who added or changed a vendor and why.
- As an operator, I want search quality to improve because the system learns from saves, edits, trust signals, and misses.

---

## 5. Proposed Solution Overview

The refactor introduces four major product layers.

### Layer 1: Query Intelligence

Enrich the existing agent system prompt so the LLM classifies query shape **as part of its first tool-selection step** — not as a separate LLM call. The agent already decides which tools to call; we extend that decision with structured reasoning.

The agent prompt will instruct the LLM to identify these signals from the user's request and row context before selecting tools:

#### `QueryProfile` signals (embedded in agent reasoning)

- `location_sensitivity`: `required` | `preferred` | `irrelevant`
- `transaction_mode`: `buy_now` | `request_quote` | `brokered_deal`
- `contact_priority`: `primary` (people-driven deals) | `secondary` (commodity)
- `source_preference`: marketplace | direct_provider | broker | mixed

These signals are **not** generated by a separate LLM call. They are part of the agent's existing tool-selection reasoning, made explicit through prompt engineering and logged in the search event stream for debugging.

#### Impact

This layer determines:
- which tools to call and with what parameters
- how results should be ranked (contact quality weight, location weight)
- what CTA is shown on result cards
- whether insufficient coverage triggers live discovery messaging

### Layer 2: Trusted Vendor Graph

Refactor vendor data into a trust-first model.

#### Vendor identity
- canonical name
- canonical domain
- primary category
- secondary categories
- vendor type: retailer, reseller, broker, service_provider, advisor, marketplace, aggregator
- geography / service area
- tier affinity

#### Contact model

The Vendor model already has: `contact_name`, `email`, `phone`, `website`. Extend it with:
- `contact_title` — role at the company
- `contact_form_url` — web form for inquiries
- `booking_url` — direct booking/scheduling link

Do **not** create a separate `VendorContact` child table yet. Most vendors have one primary contact. If multi-contact becomes necessary, it can be added later without breaking the schema.

#### Trust model

The Vendor model already has: `is_verified`, `verification_level`, `reputation_score`, `tier_affinity`. Extend it with:
- `vendor_type` — enum: retailer, reseller, broker, service_provider, advisor, marketplace, aggregator
- `contact_quality_score` — computed from contact field completeness
- `trust_score` — blended score from verification + contact quality + reputation + freshness
- `source_provenance` — how this vendor was discovered (ea_submitted, google_maps, web_search, manual_research, marketplace)
- `last_verified_at` — when contact info was last confirmed valid
- `last_contact_validated_at` — when someone confirmed the phone/email works

The existing `AuditLog` table (already in production) handles edit tracking — no separate vendor edit history table needed.

### Layer 3: Miss Handling + Live Discovery

When the DB lacks enough good results, search should shift into a clear discovery workflow.

#### Miss definition
A miss is any search where trusted coverage is insufficient because:
- too few results are available
- results are weak on contact quality
- location fit is poor
- results are the wrong transaction type
- only aggregator / editorial results are available

#### Miss workflow (parallel, not sequential)

Run in two parallel waves to keep latency under 8 seconds:

**Wave 1 (parallel):**
- Search EA's saved/trusted vendors (if authenticated)
- Search full vendor DB (hybrid vector + FTS, already implemented)
- Search marketplaces (if commodity product)

**Wave 2 (parallel, triggered if Wave 1 coverage < threshold):**
- Run Google Maps scraper for local/service queries
- Run commercial web search with intent keywords
- Run marketplace search for product queries

**Post-search:**
- Enrich strong candidates (extract contact info, validate website)
- Persist newly discovered candidates in discovery storage with `status="discovered"` and only promote them into the main Vendor graph after review/enrichment
- Label results clearly: trusted vs newly discovered

### Layer 4: Transaction-Aware Presentation

Results should render based on how the deal closes.

#### Display types

| Result type | What to show | CTA |
|------------|--------------|-----|
| Direct-buy product | price, condition, merchant, shipping, trust badge | `View Deal` |
| Quote-based service | location, phone/email/contact path, trust badge | `Request Quote` |
| Brokered luxury asset | broker/dealer identity, specialization, trust notes, contact path | `Contact Source` |
| Newly discovered candidate | source type, directness, confidence, why surfaced | `Review Source` or `Request Quote` |

---

## 6. Detailed Requirements

### 6.1 Query Intelligence Requirements

1. Every search must produce a `QueryProfile` before tool selection.
2. Location-sensitive queries must preserve geography across all eligible tool calls.
3. Human-driven deal types must require higher contact-quality thresholds.
4. Tool selection must be aware of transaction mode.
5. Result display must be derived from transaction mode plus result type.

### 6.2 Vendor Trust Requirements

1. Vendors must have structured provenance for major fields.
2. Vendors must support verification state semantics using the existing `status` and `verification_level` fields plus trust/provenance metadata.
3. Vendors must support explicit trust scoring and contact-quality scoring.
4. Aggregators must be identified and never outrank direct providers for equivalent intent.
5. Ratings and edits must be attributable to a user and timestamped.

### 6.3 EA Curation Requirements

1. EAs must be able to save a source from a result card into their trusted network.
2. EAs must be able to create a vendor manually with minimal fields and let enrichment fill in the rest.
3. EAs must be able to edit contacts, notes, categories, and service regions.
4. EAs must be able to rate a vendor privately with personal notes and personal-contact flags.
5. The system must prioritize personal-trusted sources before generic discovery results. Team trust is deferred until a Team model exists.

### 6.4 Miss Handling Requirements

1. The system must detect insufficient trusted coverage, not just zero-result states.
2. Misses must trigger live discovery fast.
3. The UI must tell the EA what is happening.
4. Strong newly discovered sources must be persisted for review.
5. Weak newly discovered sources may be shown only if clearly labeled as low-confidence.

### 6.5 Contact Quality Requirements

For high-end, service, and brokered transactions, ranking must strongly weight:
- direct phone
- direct email
- named human contact
- inquiry path
- official site
- location match
- freshness

If contactability is weak, the result should not rank highly regardless of semantic relevance.

---

## 7. Proposed Data Model Changes

### Vendor

Add or normalize support for:
- `vendor_type`
- `category`
- `secondary_categories`
- `service_regions`
- `contact_title`
- `contact_form_url`
- `booking_url`
- `trust_score`
- computed `contact_quality_score`
- `source_provenance`
- `last_verified_at`
- `last_contact_validated_at`

Do not add a dedicated `contact_quality_score` DB column in Phase 2. It is computed from field completeness at read/ranking time.

### VendorEndorsement (new table)

User-attributed trust and rating data:
- `id`
- `vendor_id` (FK → vendor)
- `user_id` (FK → user)
- `trust_rating` — 1-5 scale
- `recommended_for_categories` — JSON array of category slugs
- `recommended_for_regions` — JSON array of region strings
- `notes` — free text
- `is_personal_contact` — boolean, EA knows this vendor directly
- `created_at`
- `updated_at`

Endorsements are always user-scoped. There is no team model yet; "team trust" is deferred until a Team/Organization model exists.

### Edit Tracking

Use the existing `AuditLog` table with:
- `action = "vendor.update"`
- `resource_type = "vendor"`
- `resource_id = vendor.id`
- `details = JSON {field, old_value, new_value}`

No new table required.

---

## 8. Search Behavior by Category

### Commodity Products
- prioritize marketplace APIs
- price and availability dominate
- direct human contact is optional

### Luxury Goods / Rare Goods
- prioritize authenticated resellers, dealers, auction houses, brokers
- commercial intent mandatory
- trust and authenticity signals outrank breadth

### Services / Local Providers
- prioritize vendor DB and direct provider discovery
- location sensitivity usually required
- contact quality is primary

### Brokered Assets / High-End Deals
Examples: jets, yachts, islands, companies, skyscrapers

- prioritize brokers, specialists, and advisors
- named human contact is strongly preferred
- source directness matters more than product-style inventory volume

---

## 9. User Experience Requirements

### During Search

The UI should clearly differentiate between:
- checking trusted sources
- checking internal coverage
- running live discovery
- enriching new candidates
- final trusted results vs newly discovered candidates

### Example status messages

- `Checking your trusted sources first…`
- `We do not have enough trusted vendors for this request yet.`
- `Searching live for direct providers in San Diego…`
- `Found 6 candidates; 2 have strong contact info and trust signals.`
- `Saved 4 newly discovered sources for review.`

### On Result Cards

Every card should make confidence legible:
- trusted by you
- verified by BuyAnything
- newly discovered
- low-confidence fallback

---

## 10. Phased Rollout

### Phase 1: Query Intelligence + Display Correctness
- introduce `QueryProfile`
- make tool selection aware of location sensitivity, transaction mode, and contact priority
- fix result display by transaction type
- add explicit miss messaging

**Success metric:** high-end and service searches stop showing product-style results and low-value editorial noise.

### Phase 2: Vendor Trust Model
- add verification states, contact quality, provenance, and trust scores
- rank trusted and contactable vendors above generic matches
- separate direct providers from aggregators

**Success metric:** trusted/contactable results consistently outrank weak results.

### Phase 3: EA Curation Workflows
- save vendor to trusted network (VendorEndorsement)
- edit vendor contact/category/region fields
- personal ratings and notes
- all edits tracked via existing AuditLog
- requires authentication (anonymous users see results but cannot curate)

**Success metric:** EAs can improve the graph without engineering help.

### Phase 4: Fast-Miss Discovery + Persistence
- detect insufficient trusted coverage (not just zero results)
- trigger parallel live discovery (Wave 2)
- enrich and persist strong candidates
- surface newly discovered candidates with clear "newly discovered" labels
- use existing streaming UX (SearchProgressBar, SSE events) for status messaging

**Success metric:** misses feel fast, intelligent, and compounding rather than broken.

---

## 11. Success Metrics

| Metric | Current Problem | Target |
|--------|-----------------|--------|
| High-end/service queries with 3+ contactable sources | inconsistent | >85% |
| Location-sensitive queries returning location-fit results | unreliable | >90% |
| Searches with clear trusted vs discovered labeling | low | 100% |
| Vendor records with structured contactability | incomplete | >80% |
| Verified or personally trusted vendors in top 5 | inconsistent | >70% |
| Time to first credible source on a miss | slow/unclear | <8s |
| EA save/edit/rate workflow completion | manual/off-platform | <30s per action |

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Too much complexity introduced too quickly | Deliver in phases; keep acquisition layer mostly intact initially |
| Ratings become noisy or low-trust | Start with private/team scopes and audit trails |
| Low-confidence discovery pollutes trust graph | Persist with review states, not immediate full trust |
| Contact enrichment is incomplete | Score contact quality explicitly rather than assuming it |
| Query intelligence misclassifies requests | Log profiles, review errors, and iterate prompts/rules |

---

## 13. Resolved Design Decisions

1. **Team trust is deferred.** No Team/Organization model exists. Phase 3 ships with personal endorsements only. Team trust requires a Team model first.
2. **BuyAnything-verified = admin only.** `is_admin=True` users can set `verification_level="staff_verified"`. Manual process initially.
3. **Low-confidence sources are always shown but clearly labeled.** Never hide results — just rank them lower and badge them as "newly discovered."
4. **No per-category trust thresholds initially.** A single contact-quality + trust score is sufficient for Phase 2.
5. **Saved trusted sources influence ranking for that EA only.** Global ranking influence requires moderation and is deferred.

## 14. Compatibility Notes

- **Anonymous sessions:** Search works without authentication. EA curation features (save, edit, rate) require auth. The frontend already handles the auth/anonymous split.
- **Existing streaming UX:** Phase 4 miss messaging uses the existing `SearchProgressBar` component and SSE event stream (`agent_message` events). No new streaming infrastructure needed.
- **Existing scoring:** Bid records already have `combined_score`, `relevance_score`, `quality_score`, `source_tier`. The trust refactor extends these — it does not replace them.
- **Existing search_web bug:** The `search_web` tool description currently says "Use when you need editorial content, 'best of' lists" — this contradicts commercial intent. Phase 1 fixes this description.

---

## 15. Recommendation

This refactor should be treated as the next foundational search effort.

The crawler layer can remain mostly intact for now. The major product gap is not “find more URLs.” It is:
- understand the exact transaction shape of the query
- prioritize the right source type
- rank by trust and contactability
- let EAs directly improve the vendor graph
- turn misses into fast, clearly explained discovery events

If executed correctly, BuyAnything shifts from a search assistant that sometimes finds things to a trusted procurement network that compounds with every search.
