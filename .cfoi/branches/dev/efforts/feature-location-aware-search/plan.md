<!-- PLAN_APPROVAL: approved by User request via /build-all at 2026-03-09T12:00:00Z -->

# Implementation Plan — BuyAnything Location-Aware Search

## 0. Alignment Snapshot
- **Product North Star**: Reliable AI-assisted multi-provider procurement search with transparent results and durable persistence.
- **Effort North Star**: Add explicit location semantics, conditional forward geocoding, and category-aware geo ranking without regressing existing commodity search.
- **Definition of Done (active, v1)**:
  - **Thresholds**: location context persists; geocode failures degrade gracefully; commodity search remains regression-free.
  - **Signals**: location mode classification integrity; hybrid geo retrieval; ranking weight integrity; durable geocode cache.

## 1. Clarified Requirements
| Topic | Details |
| --- | --- |
| Primary problem | The current search stack mixes route context, local-service relevance, and vendor proximity implicitly instead of explicitly. |
| Users impacted | Buyers requesting route-based services, local services, and market-based experts; operators who need predictable search behavior. |
| Business goal | Improve vendor relevance for location-sensitive categories while preserving existing search quality for categories where location should not matter. |
| Scope | Backend-heavy feature spanning chat intent persistence, vendor retrieval, ranking, and tests. Minimal frontend impact because search results are already rendered from persisted row/bid data. |
| Constraints | Must reuse current FastAPI + SQLModel + pgvector stack; must not require map UI; must degrade gracefully with incomplete vendor geo data. |

## 2. Assumptions
1. The existing `search_intent` JSON field is the right v1 storage location for `location_context` and `location_resolution`.
2. Forward geocoding can use the same general pattern as existing reverse geocoding flows, but with a durable cache and category-aware gating.
3. `vendor.latitude` and `vendor.longitude` are populated for only part of the corpus, so text service-area fallback remains mandatory.
4. The user’s `/build-all` request is sufficient approval to generate effort, plan, and tasks artifacts without a separate review cycle.

## 3. Architecture Discovery Relevant to This Effort
- The LLM chat contract currently emits generic `constraints`, but row persistence converts them into `SearchIntent.features`.
- Vendor directory retrieval currently blends semantic vector search with FTS, but not spatial SQL.
- Vendor records already include `store_geo_location`, `latitude`, and `longitude`.
- PostGIS is available in infrastructure, though the current search path does not use it.
- User profile location already supports reverse geocoding of GPS coordinates to ZIP; this effort is about forward geocoding request locations.

## 4. Implementation Strategy

### Phase 1: Intent Contract and Persistence Repair
1. Extend the LLM/shared search intent contract to support `location_context` and `location_resolution`.
2. Normalize legacy location-bearing fields from `constraints`/`features` into the new target shape.
3. Fix the current mismatch where vendor embedding concepts look for `constraints` while persisted `SearchIntent` stores `features`.
4. Add tests for parsing and persistence of the new contract.

### Phase 2: Category Defaults and Location Resolution Gate
1. Encode the locked v1 category table in backend logic.
2. Apply LLM override only when confidence >= 0.75; otherwise use backend defaults.
3. Add a resolver that decides whether to forward-geocode and which targets to geocode based on location mode.
4. Persist unresolved/ambiguous outcomes without breaking search.

### Phase 3: Durable Forward Geocode Cache
1. Add a durable cache model/table or equivalent persistence for forward geocode lookups.
2. Implement normalized keying, positive TTL (30 days), and negative TTL (24 hours).
3. Add a thin service wrapper to resolve targets and reuse cache entries across users and rows.
4. Add tests for cache hit/miss behavior and TTL classification.

### Phase 4: Geo-Aware Candidate Generation
1. Keep current vector + FTS behavior as the base candidate set.
2. Add service-area candidate generation using `store_geo_location` text matching for `service_area`.
3. Add geo candidate generation using `latitude`/`longitude` where available for `vendor_proximity`.
4. Merge and dedupe candidate sets without dropping strong semantic matches when geo data is missing.

### Phase 5: Ranking and Fallback Behavior
1. Implement the locked v1 weight table by location mode.
2. Normalize `geo_score` to 0-1 before blending.
3. Apply neutral geo score only in the narrow cases allowed by the PRD.
4. Add tests covering `private_aviation`, `real_estate`, `roofing`, `hvac`, `photography`, and commodity search.

### Phase 6: Verification and Regression Coverage
1. Add focused unit tests for contract parsing, geocode gating, and score blending.
2. Add integration tests for vendor retrieval and ranking behavior.
3. Run targeted backend test suites to validate no regression in existing rows search.
4. Update build-all artifacts and report any deferred items if uncovered.

## 5. Shared Components / Reuse Plan
- Reuse the current `SearchIntent` machinery rather than creating a new request-intent model.
- Reuse existing vendor directory provider path instead of replacing it; extend candidate generation and ranking.
- Reuse current auth/profile geocoding patterns for HTTP client conventions and error handling, but not the ZIP-specific output contract.
- Extract forward geocode and cache behavior into a dedicated service module so rows search and any future public vendor search can reuse it.

## 6. Testing Strategy
1. **Unit tests**
   - `location_context` parsing and defaulting
   - category table fallback and override rules
   - forward geocode gating
   - cache hit/miss and TTL behavior
   - `geo_score` normalization and weight blending
2. **Integration tests**
   - rows search persists location context and resolution
   - `private_aviation` ranks by endpoint-aware fit without HQ bias
   - `roofing`/`hvac`/`photography` can apply local relevance
   - `real_estate` uses service-area default with soft proximity bonus
   - commodity search behavior remains unaffected
3. **Regression checks**
   - existing vendor vector + FTS path still works with no geo data
   - geocoding failure does not abort search

## 7. Risks & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Incomplete vendor coordinates | Geo ranking may be noisy | Keep text service-area fallback and avoid hard exclusion |
| LLM output drift | Malformed location context | Validate and fall back to locked category defaults |
| Geocoding latency | Slower search | Durable cache + conditional gating + graceful fallback |
| Over-weighted geo scoring | Ranking regressions | Locked weight table + regression tests by category |
| Scope creep into map/search redesign | Delays implementation | Hold v1 to backend search behavior only |

## 8. Deliverables
- Updated backend intent contract and persistence helpers
- Forward geocode service + durable cache
- Vendor retrieval extensions for service-area and geo candidates
- Ranking updates with locked weights
- Test coverage for category-specific behavior
- Updated build-all artifacts for this PRD

## 9. Next Step
Proceed to task decomposition, then implement in small backend-first slices.
