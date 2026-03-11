# PRD: BuyAnything Proactive Vendor Discovery and Demand-Building

## 1. Executive Summary

BuyAnything should not stop at telling the user that vendor coverage is thin.

If the platform already has strong enough results, it should show them. If it does not, it should proactively search outside the current vendor database in real time, ask clarifying questions when needed, stream discovered vendor results back into the row, and save strong candidates into the vendor database for offline enrichment.

This turns search gaps into an engine for building the vendor database based on actual demand instead of speculative manual seeding.

Messaging remains important, but it is a status signal. It is not the core feature.

---

## 2. Product Decisions Locked By This PRD

### 2.1 Commodity items are already well covered by marketplace search
For commodity and mainstream product requests, BuyAnything already has enough external product coverage through Amazon, Google, and eBay.

- Commodity/product search should continue to rely on those providers.
- This PRD is primarily about vendor discovery for services, high-value goods, advisory requests, brokerage, and niche supply.

### 2.2 Existing vendor DB should be used first, but with strict standards
BuyAnything already has a few thousand vendors in the database. Those should always be checked first.

- If the existing DB has strong enough relevant results, show them.
- The bar for "strong enough" should be strict.
- Weak, generic, geographically wrong, or semantically off-target vendors should not count as sufficient coverage.

### 2.3 Thin coverage should trigger proactive live discovery
When DB coverage is insufficient, the system should launch live vendor discovery outside the database.

- This is the core feature.
- It should happen during the user flow, not only as a later ops process.
- The user should see incoming discovered results as they are found.

### 2.4 Clarifying questions remain part of the discovery loop
The system should still ask clarifying questions when needed before or during discovery.

- Discovery should not blindly search broad web results when the request is under-specified.
- Clarifying questions should improve search precision, not delay the experience unnecessarily.

### 2.5 Discovered vendors should be normalized into the existing result model
External vendor discoveries should be converted into the same row/result shape used by current vendor results.

- The user should not care whether a vendor came from the DB or live discovery.
- The UI should present a unified result stream.

### 2.6 Strong discovered vendors should be saved for offline enrichment
Good vendor candidates discovered from real user demand should be added to the vendor database pipeline.

- This should create a demand-driven database growth loop.
- Newly discovered vendors may require offline enrichment before becoming fully trusted vendors.

### 2.7 Status messaging is secondary
If live discovery is underway or DB coverage is thin, the user may be told that BuyAnything is expanding the search or sourcing additional vendors.

- This is status communication.
- It is not the primary fallback behavior.

---

## 3. Problem Statement

### 3.1 Current behavior is too passive when DB coverage is weak
Today, the system may understand the request but still fail to satisfy it because the relevant vendor is not already in the vendor database.

That is the wrong stopping point.

### 3.2 Thin coverage should not end the search
For requests like:

- luxury corporate retreat planning
- rare or high-end whisky sourcing
- selling a luxury mansion in Nashville
- buying a Gulfstream

the platform should not assume the correct vendors are already in the DB.

### 3.3 We should build the vendor DB from demand, not guesses
Actual user searches are the best signal for what vendors matter.

Every meaningful thin-coverage search should be an opportunity to:

- find relevant vendors
- test whether they satisfy real user demand
- add them to the enrichment pipeline

### 3.4 Messaging-only solves the wrong problem
Telling the user "we have thin coverage" without actively trying to find vendors is insufficient.

The primary job is to find vendors. Messaging is supportive.

---

## 4. Goal

Build a proactive vendor discovery loop that:

1. Searches the internal vendor DB first with a strict relevance bar.
2. Detects when DB coverage is insufficient.
3. Launches live web/vendor discovery when needed.
4. Asks clarifying questions when the request is still too broad or ambiguous.
5. Extracts vendor website, contact information, thumbnails, and location/context from discovered results.
6. Streams discovered vendors into the row as results arrive.
7. Persists strong candidates for offline enrichment and future reuse.

This system should be understood as three connected loops:

- Fulfillment loop: satisfy the current user request now.
- Learning loop: detect what supply is missing.
- Asset-building loop: persist and enrich the right discovered vendors for future use.

---

## 5. Scope

### In scope

- strict DB-first vendor coverage evaluation
- live external vendor discovery when DB coverage is weak
- clarifying-question loop during discovery
- extraction of website, contact info, thumbnails, and vendor metadata
- streaming discovered results into the row
- unified display of DB vendors and discovered vendors
- saving discovered vendors into a persistence queue or vendor table for offline enrichment
- status messaging when discovery is underway or still weak

### Out of scope

- full autonomous outreach to newly discovered vendors from this PRD alone
- final trust scoring / compliance certification for all new vendors
- a full analyst dashboard for discovery review
- replacing commodity product search providers

---

## 6. Core User Stories

### 6.1 Strict DB-first search
As a user, if BuyAnything already has strong relevant vendors for my request, I want to see them immediately without unnecessary external discovery.

### 6.2 Real-time live discovery
As a user, if BuyAnything does not already have enough vendors in its DB, I want it to continue searching the web and directories instead of stalling or apologizing.

### 6.3 Clarification during discovery
As a user, if my request is under-specified, I want the assistant to ask the minimum clarifying questions needed to improve discovery quality.

### 6.4 Streaming discovered vendors
As a user, I want to see useful vendor results appear as they are found, not only after the whole discovery process finishes.

### 6.5 Demand-driven database growth
As the business, I want real user searches to create the next generation of vendor records so the DB improves from actual demand.

---

## 7. Desired Behavior

### 7.1 Step 1: Check internal coverage first
For every non-commodity vendor search:

- run internal vendor DB retrieval first
- apply strict relevance evaluation
- count only genuinely strong matches as sufficient coverage

Weak results should not qualify as "good enough" simply because they exist.

Examples of results that should fail the strict bar:

- wrong location for a location-sensitive request
- generic national brands when the user asked for local specialists
- semantically adjacent but wrong service type
- broad aggregators with little evidence of fit

Coverage sufficiency must be quality-weighted, not count-based.

- 3 excellent vendors may be sufficient.
- 20 mediocre vendors may still be insufficient.

### 7.2 Step 2: If coverage is weak, launch live discovery
When internal coverage is insufficient:

- start external discovery immediately
- search the web using request-shaped queries
- search niche/vendor-oriented sources appropriate to the request type
- continue discovery until:
  - enough strong results are found, or
  - the request remains under-specified and needs clarification, or
  - discovery confidence remains too weak and ops escalation is warranted

### 7.3 Step 3: Ask clarifying questions along the way
The system should ask clarifying questions when they materially improve vendor discovery.

Examples:

- "Do you want a local Nashville boutique luxury brokerage or a national luxury brand?"
- "Are you looking for a broker to buy a Gulfstream or charter a jet?"
- "Is the corporate retreat domestic or international?"
- "Are you looking for collectors' bottles, auction inventory, or retail purchase?"

The system should avoid unnecessary questions when the request is already specific enough.

### 7.3.1 Clarification guardrails

- ask at most 2 clarifying questions before beginning discovery
- ask at most 1 blocking clarification at a time
- if partial discovery can begin safely, start low-confidence discovery in parallel while waiting
- never block obvious discovery on perfection
- if the request is already actionable, begin discovery immediately and only ask follow-up questions that improve ranking or filtering

### 7.4 Step 4: Extract structured vendor data from discovered results
As live results arrive, the system should extract and normalize:

- vendor name
- website URL
- contact email when available
- phone when available
- thumbnail / favicon / image when available
- vendor description snippet
- location or service-area hint when available
- source URL(s)

### 7.5 Step 5: Display incoming results in the row
Discovered vendors should appear in the row as incoming results.

- users should see results while discovery is still running
- discovered vendors should use the same row/result UI model as internal vendor results
- the system may label them as discovered or newly sourced in provenance, but the visual interaction should remain unified

### 7.6 Step 6: Save strong candidates for offline enrichment
Strong discovered vendors should be persisted for downstream enrichment.

This should support:

- later normalization
- geocoding
- contact cleanup
- categorization
- duplicate detection
- future reuse in internal vendor search

Weak or incomplete candidates should not be persisted automatically.

---

## 8. Functional Requirements

### 8.0 Coverage scoring model
The system must evaluate internal DB coverage using an explicit first-pass scoring model.

V1 scoring should default to deterministic heuristics where possible for debuggability, with model-assisted classification allowed for ambiguous signals such as luxury-tier fit, category specialization, and source credibility.

Each candidate vendor should be scored on a 0.0-1.0 scale across these dimensions:

- semantic fit
- geography fit
- luxury / exclusivity fit when relevant
- contactability
- evidence of category specialization
- freshness / active presence
- source credibility
- duplicate / aggregator penalty

Suggested v1 weighted model:

- semantic fit: 0.30
- geography fit: 0.20
- category specialization: 0.15
- source credibility: 0.15
- contactability: 0.10
- freshness / active presence: 0.05
- luxury / exclusivity fit: 0.10 when relevant, otherwise redistributed to semantic and specialization
- duplicate / aggregator penalty: subtractive penalty up to -0.20

Definitions:

- semantic fit: does this vendor clearly match the actual request
- geography fit: does the vendor match the location mode and target geography
- luxury / exclusivity fit: does the vendor show evidence of operating at the requested tier
- contactability: does the result have first-party contact info or a clear conversion path
- category specialization: does the site clearly focus on this service/asset class
- freshness / active presence: does the vendor appear active and current
- source credibility: is this an official or high-trust source
- duplicate / aggregator penalty: penalize generic directories, duplicate domains, and low-signal list pages

Coverage should be judged on quality-weighted sufficiency, not raw count.

Suggested v1 sufficiency thresholds:

- sufficient coverage:
  - at least 3 vendors with score >= 0.75
  - and at least 2 vendors with score >= 0.80 for location-sensitive or high-value requests
- borderline coverage:
  - 2 vendors with score >= 0.75
  - or 4 vendors with score >= 0.65
- insufficient coverage:
  - fewer than 2 vendors with score >= 0.75
  - or top results dominated by aggregators, duplicates, wrong geography, or weak specialization

The system should prefer fewer excellent vendors over many weak ones.

Borderline coverage behavior must be explicit:

- show strong internal results immediately
- start live external discovery in parallel
- merge discovered vendors into the same result stream as they arrive
- rank internal and discovered vendors against the same quality-weighted scoring policy
- suppress or merge obvious duplicates across internal and discovered results

### 8.1 Strict coverage detection
The system must determine whether internal DB coverage is actually sufficient, not merely whether any vendors matched. This decision should be made using the scoring model above and should remain stricter than simple semantic retrieval hit count.

### 8.2 Commodity exemption
Commodity and mainstream product searches should not trigger this workflow by default if standard marketplace providers already cover them adequately.

Examples:

- sneakers
- frozen pizza
- office supplies
- commodity electronics

### 8.3 External discovery trigger
If internal vendor coverage is weak, the system must be able to trigger live external discovery.

External discovery may use:

- general web search
- maps/business listing search
- vertical directories
- niche category sites
- curated vendor source lists

The exact provider implementation may evolve, but source strategy must vary by discovery mode.

### 8.4 Discovery-mode selection
The system should choose discovery behavior based on request type, not just category labels.

Examples of discovery modes:

- local service discovery
- destination service discovery
- luxury goods discovery
- brokerage discovery
- advisory discovery
- aircraft/yacht/asset market discovery

### 8.4.1 Discovery mode to source strategy
The system must not use one generic discovery stack for all request types.

Suggested v1 source strategy:

- local service discovery
  - maps/business listings
  - official local business sites
  - local directories and neighborhood/regional listings
- destination / travel / experience sourcing
  - official venue / resort / operator sites
  - destination management companies
  - specialty travel/luxury experience directories
- luxury brokerage
  - official brokerage sites
  - agent/team sites
  - high-end real estate brand sites
  - allowed luxury property directories when used as lead sources, not final trust anchors
- UHNW goods / assets
  - official dealer or broker sites
  - auction houses
  - specialty marketplaces
  - manufacturer-authorized or recognized distributors where applicable
- advisory / professional services
  - official firm sites
  - professional directories
  - credential/membership sources
- aircraft / yacht / high-value transport
  - official broker/dealer sites
  - recognized market platforms
  - manufacturer-adjacent or operator-adjacent sources

Source strategy should be explicit in implementation and test coverage.

### 8.5 Clarification gating
If the system lacks enough specificity to perform good discovery, it must ask targeted clarifying questions before or during discovery.

Clarification must obey the guardrails in section 7.3.1.

### 8.6 Result extraction
The system must convert discovered results into the existing row/result format.

At minimum, extracted fields should include:

- title / vendor display name
- merchant / vendor company
- URL
- image / thumbnail when possible
- email when possible
- phone when possible
- merchant domain
- source / provenance
- source credibility metadata
- official-site flag when available

### 8.6.1 Trust and provenance heuristics
Discovered vendors should carry enough trust/provenance metadata to support early ranking and later enrichment.

Suggested v1 trust signals:

- official site vs directory/listing page
- first-party contact info present
- recognized brand / franchise / affiliate network
- luxury-tier signal when relevant
- brokerage license / industry membership when relevant
- awards / press / reputation evidence
- whether the result is a generic aggregator

This is not full certification, but it is required for early ranking quality.

### 8.7 Result streaming
Discovered vendors should be streamable to the frontend as they are found.

### 8.8 Persistence for enrichment
Discovered vendor candidates that meet a minimum quality bar must be saved for offline enrichment.

The saved record should preserve enough raw provenance for later processing.

### 8.8.1 Persistence thresholds
The system must not persist every discovered candidate.

Minimum v1 persistence guardrails:

- valid canonical domain
- minimum completeness:
  - vendor name
  - URL
  - at least one of email, phone, location hint, or strong first-party website evidence
- minimum confidence:
  - candidate score >= 0.65
- not obviously duplicate
- not a low-signal generic directory page unless explicitly allowed by source policy
- not obviously irrelevant to the request category

Candidates below threshold may still be shown transiently in discovery mode, but should not be added to the enrichment queue automatically.

### 8.9 Status messaging
If the system has moved from DB search into discovery mode, it may inform the user that:

- BuyAnything is expanding the search
- additional vendors are being sourced live
- more relevant matches may appear as they are found

This message must not replace the actual discovery behavior.

### 8.10 Escalation if discovery is still weak
If external discovery also fails to find enough relevant vendors, the system may still log/report a coverage gap to ops.

Minimum escalation outputs should include:

- create a manual sourcing task for the request
- flag the missing supply pattern as a category or geography gap
- store the failed or weak search archetype for future supply-building prioritization

That is the backup workflow, not the first response.

---

## 9. UX Requirements

### 9.1 If we have strong results, show them immediately
No unnecessary messaging. No discovery splash screen if not needed.

### 9.2 If we do not have strong results, keep working visibly
The user should feel that the system is actively sourcing vendors, not giving up.

### 9.3 Clarifying questions should feel useful
Questions should improve precision, not feel bureaucratic.

### 9.4 Incoming results should feel native
Discovered vendors should appear in the same row/result experience the user already understands.

### 9.5 Status copy should be supportive, not apologetic
Examples of allowed meaning:

- "I’m expanding the search beyond our current vendor database."
- "I’m sourcing additional vendors for this request now."
- "I have a few candidates already and I’m still searching for stronger matches."

---

## 10. Data Requirements

### 10.1 Discovered vendor candidate record
The system should persist a discovered vendor candidate with fields such as:

- discovered name
- normalized website
- merchant domain
- email
- phone
- thumbnail / image URL
- text snippet
- detected category / service type
- location hint
- source URL
- source query
- row/request ID that triggered discovery
- discovery timestamp
- raw extraction payload

### 10.2 Offline enrichment queue
Discovered vendors should be written to a queue or table that supports offline enrichment.

Enrichment may later add:

- clean category mapping
- geocodes
- contact normalization
- deduplication against existing vendors
- embedding generation
- search-vector generation

The normalization pipeline must explicitly deduplicate across existing DB vendors and newly discovered candidates so the user does not see obvious repeated vendors under separate result records.

---

## 11. Acceptance Criteria

### AC-1 Strong internal results short-circuit discovery
If internal DB results are strong enough, the user sees those results without unnecessary live discovery.

### AC-2 Weak internal coverage triggers live discovery
If internal DB coverage is insufficient, the system launches external vendor discovery automatically.

### AC-3 Clarifying questions improve discovery
If the request is not specific enough, the system asks targeted clarifying questions that materially improve search quality.

### AC-4 Discovered vendors stream into the row
As live discovery finds vendors, the user sees incoming results in the row UI.

### AC-5 Discovered vendors are normalized
Discovered vendors are converted into the same result structure used by existing vendor results.

### AC-6 Strong discovered vendors are persisted
High-quality discovered vendors are saved into a persistence path for later enrichment and future reuse.

### AC-7 Status messaging does not replace discovery
User-facing coverage/discovery messaging may appear, but the system still actively searches outside the DB.

### AC-8 Commodity searches remain efficient
Commodity product searches continue using marketplace providers and do not unnecessarily trigger vendor discovery workflows.

---

## 12. Success Metrics

Primary MVP metrics:

- percentage of thin-coverage searches that produce at least one strong discovered vendor candidate
- increase in successful vendor-assisted requests after discovery mode triggers
- percentage of previously dead-end categories that now produce at least one usable vendor match

Secondary MVP metrics:

- percentage of discovered vendors successfully persisted for enrichment
- reduction in search dead-ends for service / brokerage / high-value requests
- percentage of future successful searches satisfied by vendors originally discovered from real user demand
- conversion lift for requests that enter discovery mode
- repeat-use rate of vendors first found through live discovery
- operator confidence that the discovery pipeline is building the right vendor DB

---

## 13. Risks

### 13.1 Over-broad discovery
If external discovery is too loose, the user will see generic or low-quality vendors.

### 13.2 Under-triggering discovery
If internal coverage evaluation is too forgiving, the system will stop too early and miss better live results.

### 13.3 Clarification fatigue
If the system asks too many questions, the experience will slow down unnecessarily.

### 13.4 Bad candidate persistence
If low-quality discovered vendors are saved without proper screening, the database will fill with junk.

### 13.5 Source instability
External discovery sources may be noisy, rate-limited, or inconsistent, so normalization quality matters.

---

## 14. Implementation Notes

This PRD assumes the current BuyAnything architecture can support:

- internal DB search
- provider-based external search
- result normalization
- row-based streaming updates
- later enrichment pipelines

The MVP should be implemented as an extension of the current retrieval -> normalization -> streaming pipeline, with live discovery inserted as a conditional branch after strict internal sufficiency evaluation.

The implementation should preserve that architecture and extend it with:

- stricter internal vendor sufficiency evaluation
- real-time external vendor discovery
- discovered-vendor normalization
- discovered-vendor persistence for enrichment

---

## 15. Final Principle

BuyAnything should not merely tell the user that the right vendor is missing.

It should go find the vendor.

The message is status.
The search is the product.
