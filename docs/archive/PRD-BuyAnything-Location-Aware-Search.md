# PRD: BuyAnything Location-Aware Search and Geocoding

## 1. Executive Summary

BuyAnything needs a consistent way to decide when location matters, what kind of location matters, and how that location should affect retrieval and ranking.

Today, location appears in several partial forms:

- the LLM may extract route or service constraints
- the vendor search path blends a clean vendor query with the full user query
- vendors may have text service areas and optional latitude/longitude
- some user flows already reverse-geocode GPS to ZIP code

What does not exist yet is a unified contract for:

1. deciding whether location matters for a request
2. distinguishing trip endpoints from vendor proximity
3. forward-geocoding user-mentioned places when needed
4. integrating geographic relevance into search without over-weighting it for the wrong categories

This PRD defines the implementation spec for location-aware search in BuyAnything.

---

## 2. Product Decisions Locked By This PRD

### 2.1 Location is not a single boolean

The system must not treat location as a simple yes/no flag.

Instead, each request should classify location into one of these modes:

- `none`
- `endpoint`
- `service_area`
- `vendor_proximity`

These modes drive both geocoding behavior and ranking behavior.

### 2.2 Trip endpoints and vendor proximity are different problems

For many categories, the user’s location context matters even when the vendor’s physical location does not.

Examples:

- private jet charter: route matters, vendor HQ proximity usually does not
- yacht charter: itinerary or port matters, vendor HQ proximity may be secondary
- real estate brokers: local market coverage matters strongly
- roofers or HVAC: local vendor proximity and service coverage matter strongly

The system must model these separately.

### 2.3 Forward geocoding is conditional, not universal

The platform should only forward-geocode user-mentioned locations when location meaningfully affects retrieval or scoring.

Examples:

- `endpoint`: geocode origin/destination/service location for constraint scoring, not vendor distance filtering
- `vendor_proximity`: geocode search target and use geo-aware vendor retrieval
- `none`: do not geocode at all

### 2.4 Geographic relevance is a ranking component, not the sole ranking mechanism

Vector relevance and full-text relevance remain core signals.

When location matters, geographic relevance should be added as another scoring signal, weighted according to the location mode and request category.

### 2.5 The LLM should emit explicit location semantics

The LLM must not only embed location terms into a free-form search query.

It should explicitly declare:

- whether location matters
- what kind of location matters
- which place fields were extracted
- how confident it is in that interpretation

### 2.6 Geo-aware behavior must degrade gracefully

If geocoding fails, the search must still run.

Fallback order:

1. structured text matching on extracted place names
2. existing vector + FTS search
3. current non-geo behavior

No request should fail solely because geocoding failed.

---

## 3. Current Problems

### 3.1 Location is implicit instead of contractual

The current system asks the LLM to put location-like data into constraints, but there is no first-class field that says what location means for ranking.

### 3.2 Endpoint and proximity use cases are currently conflated

A route such as `SAN -> EWR` and a local-service request such as `best broker in Nashville` are not the same retrieval problem.

The current search flow has no explicit mechanism to separate them.

### 3.3 Structured location is under-leveraged in vendor embeddings

The current vendor embedding concept builder expects `intent_payload["constraints"]`, while the persisted search intent schema stores extracted fields under `features`.

That means location and other structured specs may be under-weighted in semantic retrieval today.

### 3.4 GIS-capable infrastructure exists, but search does not use it

The stack already has:

- PostGIS available in database infra
- `vendor.latitude`
- `vendor.longitude`

But current vendor retrieval is still hybrid vector + full-text, not spatial.

### 3.5 Vendor location metadata varies in quality

Some vendors have:

- textual service areas only
- headquarters text only
- lat/lon populated from offline enrichment

The search strategy must support mixed data quality.

---

## 4. Desired Launch Behavior

### 4.1 Every request gets a location relevance decision

For every BuyAnything request, the system should determine:

- whether location matters
- what kind of location matters
- which locations were extracted

### 4.2 Jet charters and route-based services

For route-based services, the system should:

- extract origin and destination
- forward-geocode those locations when feasible
- use them for route and service-fit scoring
- avoid heavily penalizing vendors because their office is far away

### 4.3 Local brokers and local services

For local categories, the system should:

- extract the search area or service location
- forward-geocode that area
- use geographic filtering and ranking to prefer vendors that serve or are near the target market

### 4.4 National or remote services

For categories where service-area coverage matters more than physical proximity, the system should:

- use location as a soft service-area relevance signal
- not hard-filter by distance unless the category explicitly requires it

### 4.5 Commodity product search

For ordinary product requests, location should usually be ignored except where provider-specific inventory or user ZIP-based pricing already requires it.

---

## 5. Scope

### In scope

- LLM contract for location relevance
- forward geocoding rules for request locations
- geo-aware retrieval strategy for vendor search
- location-aware ranking rules
- category-based weighting rules
- fallback behavior when geocoding or GIS data is missing
- observability and test expectations

### Out of scope

- rewriting the entire search stack
- mandatory real-time geocoding for all requests
- broad map UI or geospatial visualization
- automatic vendor data cleanup beyond the search-related fields needed here
- user-facing route planning or travel optimization

---

## 6. Core Concepts

### 6.1 Location relevance modes

#### `none`

Use when location should not meaningfully affect retrieval or ranking.

Examples:

- Roblox gift card
- coffee mugs
- headphones

#### `endpoint`

Use when one or more request locations define the service context, itinerary, or route, but vendor proximity is not the main decision factor.

Examples:

- private jet charter
- yacht charter itinerary
- relocation between cities

#### `service_area`

Use when the vendor must serve a place or market, but physical nearness to the user is less important than documented coverage in that place.

Examples:

- destination wedding planner
- luxury travel advisor for Aspen
- real estate broker covering a named market

#### `vendor_proximity`

Use when local presence or short travel distance materially affects vendor suitability.

Examples:

- roofing
- HVAC
- local photographers
- stagers
- home services

### 6.2 Place target types

The system should support these extracted place targets:

- `origin`
- `destination`
- `service_location`
- `search_area`
- `vendor_market`

Not every request needs all fields.

### 6.3 Geocoding types

#### Forward geocoding

Convert a user-mentioned place such as `Nashville, TN` into coordinates and normalized place metadata.

This is the primary geocoding problem addressed by this PRD.

#### Reverse geocoding

Convert GPS coordinates into a postal code or place label.

This already exists elsewhere in the product for user profile location and is not the main focus of this PRD.

---

## 7. LLM Contract

### 7.1 Required new intent fields

The LLM intent payload should be extended to include a `location_context` object.

Target shape:

```json
{
  "location_context": {
    "relevance": "none|endpoint|service_area|vendor_proximity",
    "confidence": 0.0,
    "targets": {
      "origin": "San Diego, CA",
      "destination": "Nashville, TN",
      "service_location": null,
      "search_area": null,
      "vendor_market": null
    },
    "notes": "Route matters more than vendor office location"
  }
}
```

The backend validation contract for v1 is:

- `relevance` is required
- `confidence` is required and must be `0.0-1.0`
- `targets` is required but may contain all null values when `relevance = none`
- `notes` is optional and not used for ranking

If `location_context` is missing entirely:

- the backend must apply the category-first heuristic fallback
- the request must remain valid

If `location_context` is present but malformed:

- the backend must discard only that object
- the rest of the search intent must remain usable

### 7.2 LLM decision rules

The LLM should determine location mode primarily from category and request shape, not merely from the presence of city names.

Examples:

- `private jet from SAN to EWR` -> `endpoint`
- `best real estate broker in Brentwood TN` -> `service_area` or `vendor_proximity`
- `roof repair in Nashville` -> `vendor_proximity`
- `custom emerald ring in New York` -> usually `none` unless the user explicitly wants local jeweler matching

### 7.3 Category-first heuristic backstop

If the LLM output is absent or low-confidence, the backend should apply a deterministic fallback by category.

Initial heuristic defaults:

- `private_aviation` -> `endpoint`
- `yacht_charter` -> `endpoint`
- `real_estate` -> `service_area`
- `roofing` -> `vendor_proximity`
- `hvac` -> `vendor_proximity`
- `photography` -> `vendor_proximity`
- `interior_design` -> `service_area`
- `jewelry` -> `none`
- commodity product search -> `none`

---

## 8. Search Intent Persistence Contract

### 8.1 Persist location semantics explicitly

The persisted `search_intent` payload should include:

- `location_context`
- extracted place targets
- normalized geocode output once resolved

For v1, both `location_context` and `location_resolution` should live inside the existing `search_intent` JSON payload rather than in new top-level row columns.

This keeps the rollout additive and avoids widening the row schema before the behavior is proven.

### 8.2 Persist geocoded results separately from raw LLM text

The system should keep both:

- raw extracted place strings from the LLM
- normalized geocode objects produced by the backend

This avoids re-prompting the LLM and preserves auditability.

Suggested shape:

```json
{
  "location_context": {
    "relevance": "endpoint",
    "confidence": 0.92,
    "targets": {
      "origin": "San Diego, CA",
      "destination": "Nashville, TN"
    }
  },
  "location_resolution": {
    "origin": {
      "normalized_label": "San Diego, California, United States",
      "lat": 32.7157,
      "lon": -117.1611,
      "precision": "city"
    },
    "destination": {
      "normalized_label": "Nashville, Tennessee, United States",
      "lat": 36.1627,
      "lon": -86.7816,
      "precision": "city"
    }
  }
}
```

### 8.3 Backward compatibility

Existing `features` and current structured constraints must continue to work during rollout.

The new fields should be additive.

For v1, the implementation must also normalize location-bearing keys from existing `features` and legacy structured constraints into the new `location_context.targets` shape when possible.

---

## 9. Retrieval Strategy

### 9.1 Retrieval layers

Vendor search should operate as a merge of up to three candidate-generation layers:

1. vector search
2. full-text search
3. geo candidate search

Geo candidate search runs only when the resolved location mode requires it.

### 9.2 Retrieval by location mode

#### `none`

Use:

- vector search
- FTS

Do not invoke forward geocoding or geo candidate expansion.

#### `endpoint`

Use:

- vector search
- FTS
- optional route/service-area candidate expansion if the vendor corpus supports route metadata

Do not rank primarily by vendor office distance.

#### `service_area`

Use:

- vector search
- FTS
- service-area candidate search

Service-area candidate search may use:

- structured service area polygons if available later
- vendor coverage metadata
- textual service area matching as fallback

For v1, the service-area candidate search order is locked to:

1. `vendor.store_geo_location` text match
2. vendor category match
3. vector + FTS merge

No polygon or geometry coverage model is required for v1.

#### `vendor_proximity`

Use:

- vector search
- FTS
- geo radius or nearest-neighbor candidate search around the target place

For v1, `vendor_proximity` uses these vendor fields only:

- `vendor.latitude`
- `vendor.longitude`
- `vendor.store_geo_location`
- `vendor.category`

If `latitude` and `longitude` are missing for a vendor, fall back to `store_geo_location` text matching and neutral geo scoring.

### 9.3 Candidate merge behavior

Results from geo candidate search should be merged with vector and FTS candidates, not replace them.

This avoids dropping semantically strong vendors just because their geo data is incomplete.

### 9.4 Hard filters vs soft filters

Default policy:

- `vendor_proximity`: soft filter by default, optional hard radius for categories where locality is mandatory
- `service_area`: soft filter unless business rules require hard inclusion
- `endpoint`: no hard distance filter on vendor HQ

For v1, this is locked more specifically:

- `vendor_proximity`: fetch geo candidates within radius, but do not hard-exclude non-geo vendors before final ranking
- `service_area`: no hard radius filter
- `endpoint`: no HQ-distance filter at all

This prevents the rollout from suppressing strong vendors simply because the geo corpus is incomplete.

---

## 10. Ranking Strategy

### 10.1 Scoring components

The final vendor ranking should blend:

- `semantic_score`
- `fts_score`
- `geo_score`
- `constraint_score`
- optional category-specific bonuses

Illustrative formula:

`final_score = a * semantic_score + b * fts_score + c * geo_score + d * constraint_score`

### 10.2 Weight profiles by location mode

#### `none`

- semantic: high
- FTS: medium
- geo: zero
- constraint: normal

Locked default weights for v1:

- semantic: `0.55`
- FTS: `0.25`
- geo: `0.00`
- constraint: `0.20`

#### `endpoint`

- semantic: high
- FTS: medium
- geo: near zero for vendor proximity
- constraint: high

In this mode, location should mostly influence `constraint_score`, not `geo_score`.

Locked default weights for v1:

- semantic: `0.50`
- FTS: `0.20`
- geo: `0.05`
- constraint: `0.25`

#### `service_area`

- semantic: medium-high
- FTS: medium
- geo: medium
- constraint: medium-high

Locked default weights for v1:

- semantic: `0.40`
- FTS: `0.20`
- geo: `0.20`
- constraint: `0.20`

#### `vendor_proximity`

- semantic: medium
- FTS: medium
- geo: high
- constraint: medium

Locked default weights for v1:

- semantic: `0.30`
- FTS: `0.15`
- geo: `0.40`
- constraint: `0.15`

All weights must sum to `1.00`.

### 10.2a Geo score normalization

For v1, `geo_score` must be normalized to `0.0-1.0` before blending.

Default normalization rules:

- exact or strong text service-area match: `0.7-1.0`
- city-level proximity match inside target radius: distance-normalized score from `1.0` down to `0.2`
- unresolved vendor geo data: `0.5` neutral only when other matching signals exist
- non-match with known coordinates far outside radius: `0.0-0.2`

The implementation should avoid hidden score inflation from raw distance units.

### 10.3 Category examples

#### Private jet charter

- heavily weight semantic fit to charter specialists
- heavily weight route and service-fit constraints
- do not heavily weight vendor HQ distance

#### Real estate brokers

- heavily weight coverage of the target market
- moderately weight proximity or local office presence
- keep semantic category fit strong

#### Roofing / HVAC

- heavily weight vendor proximity and service area
- semantic fit remains necessary but secondary to local coverage

#### Jewelry / bespoke national luxury vendor

- location usually low or zero
- semantic fit dominates

### 10.4 Missing geo data handling

If vendor coordinates are missing:

- do not drop the result automatically
- assign a neutral geo score
- allow semantic and FTS signals to carry the result

If request geocoding fails:

- set geo score neutral
- continue with text and semantic matching

For v1, neutral geo score is locked to `0.5` only when the mode is `service_area` or `vendor_proximity` and the vendor has some non-geo evidence of relevance.

Otherwise, missing geo data should not manufacture positive relevance.

---

## 11. Geocoding Rules

### 11.1 When to forward-geocode

Forward-geocode only if all of the following are true:

1. `location_context.relevance != none`
2. a location target string exists
3. the target affects retrieval or ranking for the current mode

### 11.2 What to geocode by mode

#### `endpoint`

Geocode:

- `origin`
- `destination`
- `service_location` when relevant

#### `service_area`

Geocode:

- `search_area`
- `service_location`

#### `vendor_proximity`

Geocode:

- `search_area`
- `service_location`

### 11.3 Confidence and precision

Geocode results should carry precision metadata:

- exact address
- ZIP/postal code
- neighborhood
- city
- metro
- state/region

This precision should influence how aggressively the geo score is used.

Examples:

- exact address -> strong local weighting
- city-level only -> moderate weighting
- state-level only -> weak weighting

### 11.4 Caching

Forward geocode results should be cached by normalized query string to reduce latency and cost.

For v1, the cache contract is locked as follows:

- cache key: normalized place string plus country hint if present
- cache scope: global reusable cache, not row-scoped
- TTL: `30 days`
- negative-result TTL: `24 hours`
- persistence location: application database table or equivalent durable store, not in-memory only

This ensures the cache survives restarts and benefits repeated searches.

### 11.5 Failure behavior

If geocoding fails:

- store the raw target string
- mark the resolution status as unresolved
- continue with non-geo retrieval and text-based location signals

For v1, geocoding should run synchronously only once per unresolved target during the active search flow.

If it times out or fails:

- the search must proceed immediately
- the unresolved result may be retried asynchronously later, but retry is not required for initial launch

---

## 12. Vendor Data Requirements

### 12.1 Minimum vendor location fields

The vendor data model should support:

- `store_geo_location` or service area text
- `latitude`
- `longitude`

### 12.2 Recommended future fields

To improve quality over time, the vendor profile should also support:

- `service_area_type` (`local`, `regional`, `national`, `global`)
- `service_area_labels`
- `headquarters_label`
- `coverage_confidence`

### 12.3 Mixed-quality vendor records

The ranking system must support vendors that have:

- coordinates only
- text service area only
- both
- neither

This must not create hard regressions during rollout.

---

## 13. Implementation Phases

### Phase 1: Intent and scoring contract

Deliver:

- new `location_context` intent contract
- category fallback heuristics
- persisted raw location targets
- fixed bridge between persisted structured fields and embedding builder

Goal:

- location meaning is explicit in the request pipeline

### Phase 2: Forward geocoding integration

Deliver:

- conditional forward geocoding for location targets
- geocode result persistence
- caching
- unresolved fallback behavior

Goal:

- normalized location data is available for ranking

### Phase 3: Geo-aware retrieval

Deliver:

- geo candidate search for `vendor_proximity`
- service-area aware candidate expansion for `service_area`
- merged candidate generation with vector + FTS

Goal:

- location materially improves candidate quality where it should

### Phase 4: Weight tuning and observability

Deliver:

- category weight tables
- metrics on geocode usage, failure rate, and geo impact
- search-quality review for affected categories

Goal:

- tune relevance without regressions

---

## 14. Observability

### 14.1 Metrics to capture

- percent of requests classified into each `location_relevance` mode
- forward geocode success rate
- forward geocode latency
- percent of geo-aware searches using cached geocodes
- percent of ranked vendors with coordinates
- geo candidate contribution rate
- selection rate uplift for local-service categories

### 14.2 Debug fields

For each search, log:

- location mode
- extracted targets
- geocode resolution status
- whether geo candidate search ran
- effective weight profile

### 14.3 Quality review slices

Review search quality separately for:

- route-based services
- local services
- market-based experts
- non-location-sensitive product searches

---

## 15. Acceptance Criteria

### 15.1 LLM contract

- every new request gets a valid location relevance classification
- route-based requests consistently return `endpoint`
- local services consistently return `vendor_proximity` or `service_area`

### 15.2 Search behavior

- jet charter searches do not over-penalize remote vendors
- roofing and HVAC searches prefer nearby or covering vendors
- real estate broker searches materially improve local-market relevance
- commodity product search behavior does not regress

For v1 signoff, “materially improve” means offline evaluation or operator review shows location-aware ranking is directionally better on a fixed regression set for:

- `private_aviation`
- `real_estate`
- `roofing`
- `hvac`
- `photography`

### 15.3 Failure handling

- geocoding failure does not break search
- missing vendor coordinates do not zero out otherwise strong vendors

### 15.4 Ranking integrity

- geo weight is zero or near-zero for `none`
- geo weight is high only for `vendor_proximity`
- endpoint logic influences constraint fit more than office distance

---

## 16. Test Plan Requirements

### Unit tests

- location mode classification fallback logic
- forward geocode gating rules
- geocode precision weighting
- ranking weight profiles by mode

### Integration tests

- private jet charter: route extracted, vendor HQ distance not over-weighted
- real estate broker: local market relevance boosts appropriate vendors
- roofing: nearby/service-area vendors outrank distant generic ones
- jewelry: location ignored unless explicitly requested

### Regression tests

- existing vector + FTS search still runs when geo is absent
- current ZIP-based grocery/provider behavior remains intact
- malformed or low-confidence location output falls back safely

---

## 17A. Locked V1 Category Table

This table is implementation-binding for v1.

| Category / Request Type | Default Location Mode | Forward Geocode Targets | HQ Distance Used? | Hard Radius Filter? | Notes |
| --- | --- | --- | --- | --- | --- |
| `private_aviation` | `endpoint` | `origin`, `destination` | No | No | Route fit matters, not office location |
| `yacht_charter` | `endpoint` | `origin`, `destination`, `service_location` | No | No | Port / itinerary context matters |
| `real_estate` | `service_area` | `search_area`, `vendor_market` | Moderate soft bonus only | No | Coverage of target market dominates |
| `roofing` | `vendor_proximity` | `service_location`, `search_area` | Yes | No | Local presence matters strongly |
| `hvac` | `vendor_proximity` | `service_location`, `search_area` | Yes | No | Local service density matters |
| `photography` | `vendor_proximity` | `service_location`, `search_area` | Yes | No | Especially for event shoots |
| `interior_design` | `service_area` | `service_location`, `search_area` | Soft only | No | Regional coverage over strict nearness |
| `jewelry` | `none` | none | No | No | Ignore place unless explicitly local |
| commodity product search | `none` | none | No | No | Keep existing behavior |

If the LLM returns a conflicting mode with confidence below `0.75`, the backend must use this table.

If the LLM returns a conflicting mode with confidence `>= 0.75`, the backend may accept the override but must log it for review.

---

## 17B. Locked V1 Retrieval Contract

The implementation order for vendor search is:

1. Build the semantic/vector candidate set.
2. Build the FTS candidate set.
3. If mode requires it, build the geo or service-area candidate set.
4. Merge and deduplicate all candidates.
5. Apply scoring using the locked weights in Section 10.

For v1:

- `service_area` candidate set must rely on `store_geo_location` text matching and category compatibility
- `vendor_proximity` candidate set must rely on `latitude`/`longitude` when available, otherwise `store_geo_location`
- there is no requirement to introduce polygon coverage models, travel-time models, or map APIs

---

## 17C. Locked V1 Data Contract

The backend typed contract for v1 should behave as if the following structures exist:

```json
{
  "location_context": {
    "relevance": "none|endpoint|service_area|vendor_proximity",
    "confidence": 0.0,
    "targets": {
      "origin": null,
      "destination": null,
      "service_location": null,
      "search_area": null,
      "vendor_market": null
    },
    "notes": null
  },
  "location_resolution": {
    "origin": null,
    "destination": null,
    "service_location": null,
    "search_area": null,
    "vendor_market": null
  }
}
```

Each non-null entry inside `location_resolution` must support:

- `normalized_label`
- `lat`
- `lon`
- `precision`
- `resolved_by`
- `resolved_at`
- `status`

Where:

- `precision` is one of `address|postal_code|neighborhood|city|metro|region`
- `status` is one of `resolved|unresolved|ambiguous`

---

## 17D. Locked V1 Cache Rules

Forward geocode caching is implementation-binding for v1:

- durable cache required
- `30 day` positive TTL
- `24 hour` negative TTL
- keyed by normalized place string
- cache reused across users and rows

The implementation must not rely on per-process memory cache alone.

---

## 18. Implementation Notes

### 17.1 Important existing mismatch to fix early

The current embedding concept builder expects structured fields under `constraints`, but the persisted `SearchIntent` schema stores them under `features`.

This should be corrected early in implementation so structured location and other specs actually influence semantic retrieval.

### 17.2 Recommended weighting principle

Use geo as a category-aware relevance signal, not a universal ranking override.

If the business question is:

- “Can this vendor serve this route?” -> endpoint and constraint fit
- “Does this vendor cover this market?” -> service-area relevance
- “Is this vendor local enough to matter?” -> vendor proximity

### 17.3 Recommended default policy

- travel and charter requests: endpoints yes, vendor proximity no
- local professional services: service area and proximity yes
- market-based experts: service area yes, proximity moderate
- products: location off unless provider-specific inventory needs it

---

## 19. Open Questions

### 18.1 Real estate mode default

Real estate brokers may sit between `service_area` and `vendor_proximity`.

Initial recommendation:

- default to `service_area`
- add a moderate local proximity bonus where coordinates exist

This is now locked for v1 by the category table in Section 17A.

### 18.2 Route-aware vendor metadata

Some route-based categories may eventually need richer vendor metadata than office coordinates alone.

Examples:

- operating regions
- port access
- airport coverage
- licensed states

This PRD does not require that enrichment for first rollout, but the design should leave room for it.

### 18.3 Geo radius by category

The exact default search radius for `vendor_proximity` categories should be tuned empirically by category and data density.

---

## 20. Summary

This PRD standardizes location-aware search around one core rule:

BuyAnything must first decide what location means for the request, then apply geocoding and geo weighting accordingly.

That means:

- route-based requests use forward-geocoded endpoints without over-valuing vendor office distance
- local services use geographic relevance heavily
- market-coverage requests use service-area relevance
- commodity product search stays mostly untouched

The result should be better vendor relevance without polluting every query with unnecessary geospatial logic.
