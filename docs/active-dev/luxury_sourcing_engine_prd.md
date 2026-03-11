# Luxury Sourcing Engine PRD

## 1. Document Overview

**Product name:** Luxury Sourcing Engine (working title)  
**Primary users:** Executive assistants, chiefs of staff, family office staff, personal assistants, concierge teams  
**Core promise:** Convert ambiguous, high-expectation requests into trustworthy, actionable sourcing paths across almost any ethical category.

This product is not a normal search engine, shopping site, or directory. It is a sourcing intelligence system that helps an operator answer requests like:

- Find a real estate broker in Nashville to sell a $3MM mansion
- Find a luxury science camp for a 12-year-old this summer
- Find a Tennessee Walking Horse champion or champion-level trainer
- Find a $50k bottle of Scotch
- Find a private chef in Aspen for a four-day retreat
- Find a top concierge physician in London
- Find a private villa with high security and on-site staff in St. Barts

The system must work even when the category is unfamiliar, fragmented, not fully cataloged, partially off-market, or spread across specialist ecosystems.

The product’s main value is not simply returning links. Its value is:

1. Understanding what the user is actually asking for
2. Discovering what types of sources are most likely to know the answer
3. Ranking those sources and resulting candidates by trust, relevance, prestige, and actionability
4. Separating discovery from verification
5. Producing a clean next-step workflow for the assistant

---

## 2. Problem Statement

Executive assistants and chiefs of staff are often asked to source highly variable, high-stakes, prestige-sensitive requests with incomplete information and little time.

Today, these users often rely on:

- generic search engines
- scattered spreadsheets
- WhatsApp threads
- personal contacts
- niche directories
- repeated manual research
- inconsistent broker/vendor relationships

This leads to:

- slow response times
- inconsistent quality
- excessive dependence on tribal knowledge
- poor documentation of why a recommendation was made
- lack of reusable institutional memory
- false confidence from low-trust web results
- difficulty handing off work across assistants or teams

The product should provide a repeatable, transparent system for finding almost anything ethical, even when the product team does not have a custom category integration for that exact category.

---

## 3. Product Vision

Build a category-agnostic sourcing engine that can take messy natural-language requests and rapidly identify:

- the best source types for the niche
- the strongest candidate options
- the best contacts to approach
- the verification steps required before commitment
- the most likely next action to move the request forward

This should feel less like search and more like an intelligent operator that knows where excellence lives on the internet.

---

## 4. Product Thesis

The core thesis is:

**The hardest part of “find anything” is not understanding every category. It is identifying and ranking the right sources for each category quickly and consistently.**

Instead of hardcoding dozens or hundreds of luxury verticals, the system should learn to:

- normalize the request
- infer the request type
- generate multiple query families
- identify recurring domains, entities, organizations, brokers, directories, and prestige signals
- rank sources before ranking individual results
- store what worked for reuse later

This lets the system generalize across categories.

---

## 5. Goals

### 5.1 Primary goals

1. Allow users to submit ambiguous, freeform sourcing requests
2. Convert each request into a structured sourcing brief
3. Identify likely source archetypes for the request
4. Run multi-strategy discovery across the public web and internal memory
5. Rank and present the most actionable options
6. Clearly distinguish between likely matches and verified matches
7. Surface next actions and required verification
8. Learn from repeated successful sourcing activity

### 5.2 Secondary goals

1. Reduce dependence on one employee’s private contact network
2. Improve trust and repeatability of sourcing recommendations
3. Create reusable source maps for future similar requests
4. Produce clean internal briefs that can be forwarded to the principal
5. Support collaboration and handoff between assistants and teams

---

## 6. Non-Goals

1. Becoming a universal checkout marketplace
2. Guaranteeing purchase or booking directly inside the platform for all categories
3. Replacing specialist brokers in deeply relationship-driven markets
4. Fully verifying every item or service automatically in v1
5. Providing legal, tax, insurance, or compliance advice
6. Becoming a mass-market consumer shopping engine

---

## 7. Target Users

### 7.1 Primary persona: Executive Assistant

**Needs:**
- solve requests quickly
- avoid embarrassing misses
- present a few strong options fast
- make the principal feel taken care of
- keep a trail of what was researched and why

**Pain points:**
- vague asks
- constant interruption
- lack of niche expertise
- fear of low-quality or fake results
- limited time

### 7.2 Secondary persona: Chief of Staff

**Needs:**
- handle strategic or lifestyle requests
- coordinate across vendors and advisors
- maintain quality and discretion
- preserve institutional knowledge

### 7.3 Tertiary persona: Family Office / Concierge Team

**Needs:**
- repeatable sourcing workflows
- quality control across staff
- centralized memory of trusted sources and contacts

### 7.4 Admin / Team Lead

**Needs:**
- see which sources lead to successful outcomes
- identify high-performing researchers, brokers, and vendors
- standardize workflow and quality across the team

---

## 8. Core Use Cases

### 8.1 Use case archetypes

The system should support requests that fall into five broad classes:

1. **Thing**
   - Birkin bag
   - rare Scotch
   - diamond necklace
   - vintage car
   - art piece

2. **Person**
   - broker
   - trainer
   - physician
   - private chef
   - tutor

3. **Place**
   - science camp
   - resort
   - school
   - clinic
   - ranch

4. **Experience**
   - expedition
   - private performance
   - concierge travel package
   - charter itinerary

5. **Access**
   - membership
   - reservation
   - ticket
   - waitlist
   - invitation-only event

### 8.2 Concrete example: Nashville real estate broker for a $3MM mansion

**User request:**  
“Find the best real estate brokers in Nashville, TN to sell my client’s $3MM mansion.”

This request looks simple but contains multiple hidden dimensions:

- local geography matters
- price band matters
- broker prestige matters
- luxury market specialization matters
- current listing activity may matter
- brokerage brand may matter
- discreet seller representation may matter
- the user may prefer a small shortlist rather than a list of everyone

The system should infer and structure the brief as:

- request type: person/service provider
- category: real estate broker
- transaction type: seller representation
- market: Nashville, TN
- property value: ~$3MM
- segment: luxury residential
- probable desired traits: strong local luxury experience, listing volume, branding quality, seller fit, responsiveness

Then the system should search source archetypes such as:

- brokerage sites
- luxury home specialists
- ranking/editorial lists
- local MLS-adjacent or directory ecosystems
- luxury neighborhood market content
- professional profiles
- recent notable listings

Then it should output:

- top broker candidates
- why each surfaced
- what signals make them credible
- what still needs verification
- suggested next outreach sequence

This is the exact pattern the product should generalize to other categories.

---

## 9. User Stories

### 9.1 Intake and understanding

- As an EA, I want to type a request naturally so I do not need to know the right sourcing jargon.
- As an EA, I want the system to infer missing constraints when possible so I can move fast.
- As a chief of staff, I want the system to clarify the likely interpretations of an ambiguous request so I do not miss the real intent.

### 9.2 Discovery

- As a user, I want the system to search in multiple intelligent ways rather than rely on one literal query.
- As a user, I want the system to identify the right ecosystems for the request, not just random pages.
- As a user, I want the system to remember useful sources from prior work.

### 9.3 Evaluation

- As a user, I want to see why a result is recommended.
- As a user, I want to know whether the result is official, specialist, editorial, or community-based.
- As a user, I want clear trust and verification signals.

### 9.4 Action

- As a user, I want direct contact paths when available.
- As a user, I want a short, principal-ready summary.
- As a user, I want to save the request and revisit it later.

### 9.5 Team / memory

- As a team lead, I want successful sources and contacts to become reusable team knowledge.
- As an operator, I want to see past results for similar requests.

---

## 10. Core Product Principles

1. **Source-first, not category-first**  
   Prioritize identifying the right source archetypes rather than trying to pre-model every niche.

2. **Rank sources before items**  
   A result from a trusted specialist ecosystem should generally outrank a superficially similar result from a low-trust page.

3. **Multiple interpretations beat one literal interpretation**  
   Many sourcing requests are underspecified.

4. **Discovery is not verification**  
   The system must clearly label what has and has not been confirmed.

5. **Explainability matters**  
   Every surfaced result should have a reason.

6. **Institutional memory compounds**  
   The system should get better as teams use it.

7. **Fast shortlist > exhaustive dump**  
   The product should optimize for confident next actions.

---

## 11. Functional Requirements

### 11.1 Request intake

The system shall allow the user to submit a freeform request in natural language.

The system shall extract or infer:
- request object
- request type (thing, person, place, experience, access)
- desired action (buy, book, hire, locate, compare, verify, shortlist)
- location/geography
- budget band
- time sensitivity
- prestige sensitivity
- hard constraints
- soft preferences
- likely missing variables

The system shall create a structured sourcing brief from the request.

### 11.2 Interpretation engine

The system shall generate one or more plausible interpretations when a request is ambiguous.

Example:
“Find a Tennessee Walking Horse champion” may mean:
- horse for sale
- notable champion horse
- champion bloodline breeder
- trainer associated with champions
- someone who can broker access into that world

The system shall retain multiple interpretations and allow the search layer to explore them in parallel.

### 11.3 Source archetype inference

The system shall infer likely source types based on the request.

Possible source archetypes include:
- official bodies
- associations and registries
- curated marketplaces
- auction houses
- brokerages and specialist advisors
- ranking/editorial lists
- event ecosystems
- local directories
- social proof ecosystems
- prior trusted internal sources

### 11.4 Query family generation

The system shall generate multiple query families instead of one query.

Families should include:
- direct intent queries
- official body queries
- prestige-oriented queries
- specialist/broker queries
- alternative terminology queries
- local and regional queries
- verification-oriented queries

### 11.5 Discovery engine

The system shall collect candidate results across source types.

The system shall identify recurring:
- domains
- organizations
- listings
- people
- locations
- credentials
- awards
- events
- brokerages
- associations

### 11.6 Extraction layer

To manage token costs and limits, the system shall first pass candidate pages through a lightweight heuristic or traditional NLP filter to determine relevance before utilizing an LLM.

For each qualified candidate result, the system shall attempt to extract:
- title/name
- entity type
- organization
- location
- contact details
- pricing or budget clues
- credentials or awards
- notable claims
- listing or availability clues
- source type
- freshness clues
- verification requirements

### 11.7 Ranking engine

The system shall rank candidates using a hybrid approach (not solely LLM-based):
1. source quality (deterministic scoring based on domain authority, source type, and memory)
2. entity/result quality (LLM-assisted semantic match)
3. overall recommendation strength (combined weighted score)

### 11.8 Output generation

The system shall return:
- structured brief summary
- top sources
- top candidate results
- explanation of why each surfaced
- what still needs verification
- recommended next actions

The system should support:
- quick shortlist view
- detailed research view
- exportable summary for the principal

### 11.9 Memory and reuse

The system shall store successful sources, contacts, domains, and query strategies.

The system shall use prior success signals to boost future similar searches.

### 11.10 Collaboration

The system should allow users to:
- save searches
- annotate results
- mark sources as trusted/untrusted
- hand off a request to another teammate
- preserve research history

---

## 12. Non-Functional Requirements

1. Search results should appear quickly enough to support live operational use. Given the multi-strategy discovery, full resolution may take 30–90 seconds. The system must support asynchronous streaming updates so the user is not blocked by a static loading screen.
2. The system should degrade gracefully when a niche has sparse public web data.
3. The system should preserve user trust by labeling uncertainty clearly.
4. The system should support auditability of why recommendations were made.
5. The system should be designed for extensibility across new source types.
6. The system should avoid hard dependency on one third-party search provider.
7. The system should support privacy-conscious handling of sensitive user requests.

---

## 13. System Design Overview

### 13.1 High-level architecture

1. Request Intake Layer
2. Brief Structuring Layer
3. Interpretation Layer
4. Query Generation Layer
5. Discovery Layer
6. Extraction Layer
7. Source Ranking Layer
8. Result Ranking Layer
9. Verification Layer
10. Memory Layer
11. Presentation Layer

### 13.2 Conceptual flow

User request → Structured brief → Query families + source archetypes → Discovery → Entity extraction → Ranking → Verification prompts → Output shortlist → Save memory

---

## 14. Data Model

### 14.1 Core entities

#### Request
- request_id
- raw_text
- created_by
- created_at
- status
- urgency
- budget_low
- budget_high
- geography
- request_type
- action_type
- prestige_level
- sensitivity_level

#### StructuredBrief
- brief_id
- request_id
- normalized_object
- normalized_category
- normalized_action
- constraints_json
- assumptions_json
- interpretations_json
- source_archetypes_json

#### QuerySet
- query_set_id
- brief_id
- family_type
- query_text
- priority
- status

#### Source
- source_id
- domain
- source_name
- source_type
- source_subtype
- trust_score
- prestige_score
- coverage_score
- freshness_score
- notes

#### CandidateEntity
- entity_id
- brief_id
- name
- entity_type
- organization
- source_id
- url
- location
- contact_json
- pricing_json
- prestige_signals_json
- credentials_json
- claims_json
- extraction_confidence

#### Recommendation
- recommendation_id
- brief_id
- entity_id
- rank
- overall_score
- why_selected_json
- verification_needed_json
- next_action

#### SourceMemory
- memory_id
- source_id
- category_hint
- geography_hint
- success_count
- failure_count
- avg_response_quality
- last_success_at
- notes

### 14.2 Category-specific extension fields

The model should support optional extension tables or flexible JSON fields for category-specific attributes.

Examples:

**Real estate broker**
- brokerage
- neighborhoods_served
- luxury_focus
- recent_listing_band
- seller_representation_focus

**Rare goods**
- provenance
- certificate
- serial number
- condition
- auction history

**Camp/program**
- age_range
- season
- boarding
- admissions_selectivity
- academic_focus

**Horse / equestrian**
- breed
- trainer
- champion titles
- pedigree
- stable location

---

## 15. Search Strategy Framework

The system should not rely on one universal search mode. It should choose one or more strategies.

### 15.1 Strategy A: Official-first
Use when the request likely relates to:
- credentials
- registries
- rankings tied to institutions
- championships
- licensing
- associations
- accreditation

### 15.2 Strategy B: Market-first
Use when the request is a buyable object with active inventory.

### 15.3 Strategy C: Specialist-first
Use when the best supply is controlled by brokers, agents, advisors, or niche professionals.

### 15.4 Strategy D: Prestige-first
Use when status, curation, taste, and social proof matter more than broad availability.

### 15.5 Strategy E: Local-network-first
Use when geography and local reputation dominate.

### 15.6 Strategy F: Hybrid
Most real requests should use more than one strategy.

**Example: Nashville $3MM mansion broker**
- specialist-first
- prestige-first
- local-network-first

---

## 16. Ranking Model

### 16.1 Source-level ranking criteria

Each source should be scored on:
- trustworthiness
- category fit
- prestige relevance
- geographic relevance
- freshness
- actionability
- historical success in memory

### 16.2 Result-level ranking criteria

Each candidate entity should be scored on:
- match to brief
- source trust
- prestige signals
- evidence density
- direct contactability
- local relevance
- apparent availability
- uniqueness/non-redundancy

### 16.3 Recommendation score

Overall score should combine:
- source score
- result score
- memory boost
- verification burden penalty
- duplication penalty

### 16.4 Explainability

Every recommendation should have a machine-readable and human-readable reason stack such as:
- local luxury specialist
- repeated across multiple trusted domains
- clear contact path
- relevant price band
- recent activity signals
- strong prestige markers

---

## 17. Prestige and Trust Signals

The system should learn cross-category signals that often indicate higher-quality results.

### 17.1 For people / service providers
- award-winning
- championship-associated
- board-certified
- licensed
- represented by premium firm
- featured in respected press
- speaks at notable events
- official membership in elite organizations
- repeated mentions across trusted sources

### 17.2 For places / programs
- accredited
- selective admissions
- invitation-only
- established history
- premium clientele
- notable alumni
- editorial recognition

### 17.3 For objects
- provenance
- certification
- serial number
- limited edition
- historical auction comps
- specialist venue
- detailed condition documentation

### 17.4 For source pages
- official domain
- transparent business identity
- current contact information
- detailed service descriptions
- evidence of real activity rather than pure marketing copy

---

## 18. Verification Framework

A critical system behavior is clearly separating discovery from verification.

### 18.1 Verification states
- not yet verified
- partially verified
- verified by source evidence
- verified by external confirmation

### 18.2 Common verification categories
- authenticity
- current availability
- licensing or credential status
- title/ownership
- age fit
- geographic fit
- budget alignment
- insurance/compliance requirements
- response timeliness

### 18.3 Example: Nashville broker verification
For a broker shortlist, verification may include:
- currently active in Nashville luxury market
- actual seller-side representation experience in similar price band
- responsiveness
- reputation quality
- fit for client’s neighborhood and property type

---

## 19. Memory and Learning System

### 19.1 Why memory matters
The product becomes more valuable when it remembers:
- which domains repeatedly produced useful results
- which brokers or specialists actually responded
- which query styles worked best
- which sources were stale or misleading
- which results converted into successful outcomes

### 19.2 Memory types

1. **Source memory**  
   Trusted domains, organizations, directories, brokerages

2. **Contact memory**  
   Specific people, responsiveness, quality notes

3. **Pattern memory**  
   Which query families worked for a niche

4. **Outcome memory**  
   Which recommendations led to successful bookings, purchases, hires, or introductions

### 19.3 Team value
This transforms individual assistant knowledge into organizational knowledge.

---

## 20. UX / UI Requirements

### 20.1 Primary screens

#### A. New Request Screen
- freeform request box
- optional structured fields for budget, location, timing, discretion, preferences
- examples of request styles

#### B. Brief Review Screen
- normalized brief
- inferred assumptions
- alternate interpretations
- editable constraints

#### C. Results Screen
- asynchronous "research in progress" indicator / streaming state
- top recommendations
- source-type tags
- trust and prestige indicators
- why surfaced
- verification needed
- contact actions

#### D. Research Graph / Source View
- recurring domains
- recurring organizations
- related entities
- previous successful sources

#### E. Saved Requests / Memory Screen
- past similar requests
- trusted sources by category/geography
- reusable source maps

### 20.2 Output modes

1. **Quick shortlist mode**
   - 3–5 top options
   - one-line explanation
   - next action

2. **Operator mode**
   - deeper research details
   - source breakdown
   - evidence details
   - verification checklist

3. **Principal-ready memo mode**
   - concise summary
   - clean options
   - no research clutter

---

## 21. End-to-End Workflow Example: Nashville Broker Search

### 21.1 Request
“Find the best real estate brokers in Nashville, TN to sell my client’s $3MM mansion.”

### 21.2 Brief structuring
The system infers:
- person/service provider request
- seller representation
- luxury residential
- Nashville geography
- ~$3MM band
- likely need for prestige + local strength + responsiveness

### 21.3 Strategy selection
Chosen strategies:
- local-network-first
- specialist-first
- prestige-first

### 21.4 Query family generation
The system generates query families such as:
- Nashville luxury real estate broker 3 million seller
- Nashville luxury listing agent estate homes
- best luxury real estate brokers Nashville
- Nashville mansion listing specialist
- Nashville luxury brokerage seller representation
- local editorial / awards / ranking queries
- broker profile / active listing clues

### 21.5 Source discovery
The system identifies likely high-value source types:
- luxury brokerage websites
- broker profile pages
- editorial “top agents” pages
- local luxury market sites
- neighborhood-focused luxury pages
- team memory from prior Nashville sourcing

### 21.6 Extraction
For each candidate broker, extract:
- name
- brokerage
- contact information
- Nashville area focus
- luxury positioning
- seller-side language
- relevant listing band clues
- awards or press mentions

### 21.7 Recommendation output
Return a shortlist such as:
- Candidate A — local luxury specialist, strong seller positioning, direct contact path
- Candidate B — large-brand prestige, strong Nashville luxury footprint
- Candidate C — boutique high-touch broker with local neighborhood focus

Each with:
- why selected
- what to verify
- suggested order of outreach

### 21.8 Save memory
Store:
- which domains were useful
- which candidate was contacted
- which candidate responded
- whether the source ultimately led to a listing relationship

---

## 22. Admin and Team Features

### 22.1 Team settings
- default trust rules
- approved domains list
- blocked or low-trust domains list
- team-wide notes on vendors and brokers

### 22.2 Analytics
- request volume by category
- average time to shortlist
- source success rate
- contact response rate
- recommendation acceptance rate
- repeat-source effectiveness

### 22.3 Feedback loop
Users should be able to mark:
- useful
- irrelevant
- stale
- high trust
- low trust
- responded quickly
- did not respond
- great fit
- poor fit

---

## 23. Safety, Ethics, and Policy Constraints

The product must only support ethical sourcing.

It must not support:
- illegal goods
- evasion of laws or regulations
- trafficking or exploitative services
- banned/restricted contraband markets
- unsafe or clearly harmful procurement categories

The system should include guardrails that:
- classify risky requests
- refuse disallowed categories
- avoid presenting unsafe or unlawful sourcing paths

---

## 24. MVP Scope

### 24.1 MVP capabilities

1. Freeform request intake
2. Structured brief generation
3. Multiple interpretation support
4. Source archetype inference
5. Query family generation
6. Public-web discovery
7. Candidate extraction
8. Simple source/result ranking
9. Quick shortlist generation
10. Save request and results
11. Team notes on sources

### 24.2 Explicitly out of MVP

1. Full transactional checkout
2. Deep category-specific parsers for every niche
3. Automated external verification for every vertical
4. Universal CRM or procurement suite
5. Heavy workflow automation beyond search and shortlist

---

## 25. Phase 2 and Phase 3 Roadmap

### Phase 2
- source graph visualization
- better memory-based ranking
- category-specific enrichments for top repeated niches
- outreach templates
- principal-ready memo generation
- vendor/broker response tracking

### Phase 3
- semi-automated verification workflows
- broker/vendor relationship graph
- proactive source discovery by geography/category
- premium source integrations
- recommendation personalization by principal taste profile

---

## 26. Technical Design Notes

### 26.1 Core services
- request parsing service
- LLM normalization service
- search orchestration service
- pre-extraction content filter (heuristic/lightweight NLP)
- extraction/enrichment service
- ranking service
- memory service
- UI API service

### 26.2 Storage needs
- relational data for requests/results/workflows
- document storage for extracted page data and summaries
- search index for past requests and source memory
- optional graph storage for relationship mapping between sources, entities, and outcomes

### 26.3 Search provider abstraction
The system should not depend fully on one search provider. It should support a provider abstraction that can combine:
- web search APIs
- direct site search modules
- cached prior source maps
- internal memory retrieval

### 26.4 LLM responsibilities
Use the LLM for:
- request normalization
- interpretation generation
- query family generation
- extraction cleanup
- explanation generation
- memo generation

Do not rely on the LLM alone to determine factual trust or perform final source ranking. Use deterministic heuristics (domain authority, team memory) as the primary driver for source ranking to prevent hallucinated prestige.

---

## 27. Success Metrics

### 27.1 Product metrics
- time to first useful shortlist
- percentage of requests yielding at least one high-confidence path
- percentage of shortlisted options marked useful
- average user edits to the structured brief
- repeat usage rate

### 27.2 Outcome metrics
- shortlist-to-contact rate
- contact response rate
- successful sourcing completion rate
- source reuse rate
- memory-assisted search success improvement

### 27.3 Trust metrics
- percentage of surfaced results later marked stale or poor
- user confidence rating
- ratio of high-trust vs low-trust sources in final outputs

---

## 28. Open Questions

1. How much user control should exist over strategy selection?
2. Should the product default to broad discovery or narrow trusted-source discovery?
3. How much internal memory should be organization-specific versus globally learned?
4. When should the system ask clarifying questions versus infer silently?
5. What level of result freshness is required by category?
6. Which premium data sources are worth integrating once usage patterns are known?
7. How should discretion and privacy preferences affect source selection?

---

## 29. Recommended Product Positioning

This product should be positioned as:

**An intelligent sourcing operator for executive assistants and chiefs of staff**

Not as:
- a shopping engine
- a standard concierge app
- a generic business search tool

The value proposition is:

- handle almost any ethical request
- find strong options fast
- know where to look
- show why it matters
- preserve team knowledge

---

## 30. Summary

The Luxury Sourcing Engine should solve a hard but common operational problem: finding excellent options across highly variable categories without requiring the user to be a domain expert in every niche.

The product’s key insight is that most sourcing problems are best solved by discovering and ranking the right source ecosystems, not by prebuilding exhaustive category coverage.

If implemented well, the system becomes a trusted operator for assistants and chiefs of staff by providing:
- fast structured understanding of the ask
- source-aware search strategies
- trust-ranked recommendations
- clear verification needs
- reusable institutional memory

That combination is what makes “find almost anything ethical” operationally realistic.

