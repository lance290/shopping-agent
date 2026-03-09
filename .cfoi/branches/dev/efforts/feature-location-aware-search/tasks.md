# Task Breakdown — feature-location-aware-search

## Summary
- Total tasks: 6
- Estimated total time: ~240 minutes
- Current status: Ready for implementation

## Tasks

### task-001
- Description: Add typed location intent/resolution contracts and persistence normalization
- E2E flow: A location-sensitive request persists `location_context` and normalized targets inside `row.search_intent`.
- Manual verification:
  - Run backend tests for search intent parsing/persistence.
  - Inspect persisted `search_intent` JSON for a location-sensitive row.
  - Record JSON sample in proof artifact.

### task-002
- Description: Implement category-default location mode selection and LLM override handling
- E2E flow: Search requests in supported categories resolve to the locked v1 location mode table, with high-confidence LLM overrides only.
- Manual verification:
  - Exercise classification on `private_aviation`, `real_estate`, `roofing`, and a commodity request.
  - Verify resulting mode matches expectations.
  - Record outputs in proof artifact.

### task-003
- Description: Build durable forward geocode cache and target resolver
- E2E flow: A request location is forward-geocoded once, stored in cache, then reused on subsequent searches.
- Manual verification:
  - Resolve the same location twice and verify second request is a cache hit.
  - Verify unresolved location produces a negative-cache entry.
  - Record timing/log output.

### task-004
- Description: Extend vendor retrieval with service-area and geo candidate generation
- E2E flow: Local-service or service-area searches merge geo/text candidates with the existing vector + FTS vendor set.
- Manual verification:
  - Run a local-service search and inspect candidate source composition.
  - Confirm vendors without coordinates are still eligible through text fallback.
  - Record sample ranked candidates.

### task-005
- Description: Implement locked v1 ranking weights and geo score normalization
- E2E flow: Vendor results blend semantic, FTS, geo, and constraint signals according to the location mode.
- Manual verification:
  - Verify `private_aviation` does not over-weight office distance.
  - Verify `roofing`/`hvac`/`photography` can benefit from local relevance.
  - Verify commodity search geo weight remains zero.

### task-006
- Description: Add integration/regression tests and validate graceful fallback behavior
- E2E flow: Search remains functional across geocode failures, missing vendor geo data, and location-irrelevant categories.
- Manual verification:
  - Run targeted backend tests for all supported category cases.
  - Confirm no failure path aborts search.
  - Attach test output summary.
