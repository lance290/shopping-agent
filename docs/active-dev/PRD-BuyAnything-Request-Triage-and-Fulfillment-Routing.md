# PRD: BuyAnything Request Triage and Fulfillment Routing

## 1. Executive Summary

BuyAnything now operates across two fundamentally different fulfillment modes:

- affiliate-driven commodity search across providers like Amazon, eBay, Kayak, Kroger, and Walmart
- source-first sourcing for high-touch, prestige-sensitive, specialist, or weakly cataloged requests

The system should not send every request directly into the same search pipeline.

Instead, BuyAnything needs a front-door triage and fulfillment routing layer that evaluates the request first, determines what kind of request it is, and chooses the cheapest and most appropriate execution path.

This layer should decide whether to:

- run affiliate adapters only
- run affiliate adapters and sourcing discovery in parallel
- skip affiliate adapters and go directly into source-first sourcing

This routing layer is the control point that makes the platform operationally efficient, cost-aware, and scalable across both commodity and high-touch procurement.

---

## 2. Product Decisions Locked By This PRD

### 2.1 Not every request should enter the luxury sourcing engine
The source-first sourcing engine is expensive and powerful, but it should not be the default execution path for simple catalog-searchable requests.

Commodity and mainstream requests should be handled through existing affiliate provider adapters whenever possible.

### 2.2 Existing affiliate adapters are first-class fulfillment channels
Amazon, eBay, Kayak, Kroger, and Walmart are not just sources among many. They are structured commerce and travel fulfillment channels with adapter logic already built for BuyAnything.

They should be treated separately from open-ended web discovery.

### 2.3 Commodity routing should optimize for speed and monetizable coverage
When a request is catalog-searchable and well-covered by affiliate providers, the system should favor those providers first.

This is both the fastest user experience and the most aligned with current affiliate revenue pathways.

### 2.4 High-touch sourcing remains necessary and should be selectively invoked
Requests involving services, brokers, specialists, places, access, prestige, discretion, or fragmented supply should continue into the source-first sourcing engine.

The routing layer is a gateway, not a replacement.

### 2.5 Some requests should run both paths in parallel
Mixed requests or partially catalogable luxury requests may benefit from both:

- affiliate provider fanout for fast structured offers
- source-first sourcing for deeper specialist discovery

This hybrid mode is a key product capability.

---

## 3. Problem Statement

### 3.1 The platform now has multiple retrieval regimes
BuyAnything no longer operates as one generic search system.

It has at least two distinct retrieval systems:

- provider-based affiliate commerce/travel retrieval
- source-first sourcing and discovery

Treating these as one undifferentiated pipeline creates cost, UX, and architecture problems.

### 3.2 Sending all requests into a sourcing-heavy path is wasteful
If a user asks for:

- paper towels
- carry-on luggage under $300
- groceries for the week
- a flight itinerary

there is no reason to invoke multi-stage query planning, open-web discovery, extraction, consolidation, and trust-ranking designed for brokers or rare goods.

### 3.3 Sending all requests into affiliate search is also wrong
If a user asks for:

- a luxury real estate broker in Nashville
- a private chef in Aspen
- a $50k bottle of Scotch
- a private villa with security in St. Barts

affiliate adapters alone will not satisfy the request.

### 3.4 We need a deliberate front-door control point
The system needs a clear decision layer that determines:

- what kind of request this is
- whether it is catalog-searchable
- whether it is affiliate-covered
- whether it requires sourcing
- whether both paths should run together

---

## 4. Goal

Build a front-door request triage and fulfillment routing layer that:

1. Classifies the request into fulfillment-relevant categories.
2. Chooses an execution mode before expensive downstream work begins.
3. Reuses affiliate provider adapters when appropriate.
4. Invokes source-first sourcing when necessary.
5. Supports hybrid execution for mixed requests.
6. Produces clear provenance so the UI can present unified results from different origins.

---

## 5. Scope

### In scope

- front-door request classification for fulfillment routing
- decisioning for affiliate-only, sourcing-only, and hybrid execution
- clear distinction between affiliate provider adapters and discovery/source adapters
- unified execution-mode metadata
- unified result provenance contract
- routing-aware metrics and observability

### Out of scope

- rewriting existing provider adapters
- replacing the luxury sourcing engine
- redesigning the entire chat or row UX in this PRD alone
- changing affiliate economics or commission logic
- building a full policy engine for every possible category

---

## 6. Core User Stories

### 6.1 Commodity speed path
As a user, if my request is a normal product, grocery, or travel request, I want BuyAnything to use fast provider integrations instead of overcomplicating the search.

### 6.2 High-touch sourcing path
As a user, if my request is specialist or high-touch, I want BuyAnything to recognize that and route into deeper sourcing automatically.

### 6.3 Hybrid path
As a user, if my request could benefit from both structured providers and specialist sourcing, I want BuyAnything to run both and show me the best combined result set.

### 6.4 Provenance clarity
As a user, I want to understand whether a result came from an affiliate provider, open-web discovery, or internal memory.

---

## 7. Desired Behavior

### 7.1 Step 1: Triage the request before execution
Every request should first pass through a lightweight routing layer.

That layer should determine:

- request domain
- request type
- likely execution mode
- best initial providers or sourcing strategies

### 7.2 Step 2: Select one of three execution modes
The system should choose one of these modes:

- affiliate-only
- sourcing-only
- affiliate-plus-sourcing

### 7.3 Step 3: Execute the selected mode

#### Affiliate-only
Use when the request is well-covered by structured providers.

Examples:

- groceries
- flights
- commodity household goods
- mainstream consumer products

#### Sourcing-only
Use when the request is not meaningfully catalog-searchable or is relationship/trust-driven.

Examples:

- brokers
- private chefs
- physicians
- camps
- villas
- specialist services

#### Affiliate-plus-sourcing
Use when fast provider results may help, but deeper sourcing may still be necessary.

Examples:

- luxury goods with partial marketplace coverage
- rare products with possible resale inventory plus specialist dealer ecosystem
- travel with both structured booking and concierge-style options

### 7.4 Step 4: Preserve provenance in the result stream
All results returned downstream should include origin metadata such as:

- amazon
- ebay
- kayak
- kroger
- walmart
- web_discovery
- source_memory

The user should see a unified experience, but the system must preserve this distinction internally.

---

## 8. Functional Requirements

### 8.1 Request classification
The system must classify requests into fulfillment-relevant buckets such as:

- commodity_product
- grocery
- travel
- marketplace_product
- service_or_specialist
- luxury_or_high_touch
- mixed_or_ambiguous

### 8.2 Execution-mode decisioning
The system must choose one of:

- affiliate_only
- sourcing_only
- affiliate_plus_sourcing

### 8.3 Provider routing
The system must be able to route affiliate-eligible requests to one or more provider adapters such as:

- Amazon
- eBay
- Kayak
- Kroger
- Walmart

### 8.4 Sourcing invocation
The system must be able to invoke the source-first sourcing engine when routing deems it necessary.

### 8.5 Hybrid execution
The system must support running provider-based affiliate retrieval and source-first sourcing in parallel for mixed requests.

### 8.6 Unified provenance contract
All downstream results must carry provenance fields sufficient for ranking, analytics, and UI display.

### 8.7 Cost-aware routing
The routing layer should minimize unnecessary invocation of expensive discovery and extraction pipelines.

### 8.8 Routing explainability
The system should persist or emit lightweight reason codes explaining why a route was chosen.

Example reason codes:

- grocery_terms_detected
- travel_intent_detected
- service_request_detected
- prestige_sensitive_request
- low_catalog_confidence
- specialist_discovery_required

---

## 9. UX Requirements

### 9.1 Fast requests should feel fast
Commodity and affiliate-covered requests should not incur visible delay from sourcing-oriented orchestration.

### 9.2 Complex requests should feel intelligent, not slow by accident
When the system chooses sourcing, the user should understand that BuyAnything is performing deeper work rather than simply lagging.

### 9.3 Hybrid requests should not feel fragmented
When both paths are used, the UI should still feel unified, even if the system tracks different result origins internally.

---

## 10. Data Requirements

### 10.1 Fulfillment plan object
The system should persist or emit a fulfillment plan containing:

- request_id
- classified_domain
- execution_mode
- affiliate_providers
- invoke_sourcing_engine
- reason_codes

### 10.2 Unified result metadata
Every downstream result should include:

- result_kind
- origin
- execution_mode
- verification_state when applicable
- ranking inputs or provenance references

---

## 11. Acceptance Criteria

### AC-1 Commodity requests route to affiliate providers
A grocery or mainstream product request routes to affiliate adapters without unnecessary sourcing work.

### AC-2 Specialist requests route to sourcing
A service or specialist request routes into the source-first sourcing engine.

### AC-3 Mixed requests can invoke both paths
A partially catalogable but high-touch request can run affiliate providers and sourcing together.

### AC-4 Routing reasons are inspectable
The system stores or emits reason codes explaining the selected execution path.

### AC-5 Result provenance is preserved
All returned results carry origin metadata suitable for UI, ranking, and analytics.

---

## 12. Success Metrics

Primary metrics:

- percent of commodity requests routed to affiliate-only mode
- percent of high-touch requests routed to sourcing-only mode
- percent of hybrid requests producing useful mixed results
- reduction in unnecessary sourcing-engine invocation for commodity requests

Secondary metrics:

- latency by execution mode
- affiliate click/conversion by route type
- user usefulness rating by route type
- routing misclassification rate

---

## 13. Risks

### 13.1 Over-routing to affiliate-only
If the system routes too aggressively to affiliate-only mode, it may miss better specialist outcomes.

### 13.2 Over-routing to sourcing
If the system routes too aggressively to sourcing, it will burn cost and slow down obvious commodity flows.

### 13.3 Hybrid overuse
If hybrid mode is invoked too often, the system may become expensive and operationally noisy.

### 13.4 Provenance confusion
If provenance is not modeled clearly, ranking and UX may degrade when multiple result origins mix.

---

## 14. Final Principle

BuyAnything should not treat all requests as the same kind of search.

It should first decide what kind of fulfillment problem it is solving.

Routing is the front door.
Execution is what follows.
