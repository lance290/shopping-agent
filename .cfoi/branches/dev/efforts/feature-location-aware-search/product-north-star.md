# Effort North Star (Effort: feature-location-aware-search, v2026-03-09)

## Goal Statement
Implement a clean, explicit location-aware search pipeline for BuyAnything so route-based services, local services, and market-coverage searches rank vendors appropriately without regressing commodity search.

## Ties to Product North Star
- **Product Mission**: Enable users to buy anything through reliable AI-assisted search and vendor matching.
- **Supports Metrics**: search success rate, provider coverage quality, intent extraction quality, and persistence-first search behavior.

## In Scope
- Explicit `location_context` and `location_resolution` contracts inside `search_intent`
- Category-aware location mode defaults and LLM override handling
- Conditional forward geocoding with durable caching
- Geo/service-area candidate generation for vendor directory search
- Mode-specific ranking weights and graceful fallback behavior
- Test coverage for route-based, local-service, and non-location-sensitive flows

## Out of Scope
- Map UI or visual geospatial interfaces
- Polygon coverage modeling
- Rebuilding grocery ZIP/provider logic
- Broad vendor data cleanup outside fields required for v1

## Acceptance Checkpoints
- [ ] Supported categories persist valid `location_context` and normalized geocode results.
- [ ] `private_aviation` searches use endpoints without over-weighting vendor HQ distance.
- [ ] `roofing`, `hvac`, and `photography` searches can apply geo-aware local relevance.
- [ ] `real_estate` defaults to service-area relevance with moderate proximity bonus.
- [ ] Commodity product search remains functionally unchanged when location mode is `none`.

## Dependencies & Risks
- **Dependencies**: Existing chat intent pipeline, vendor directory search pipeline, vendor lat/lon enrichment, pgvector + PostGIS-capable database.
- **Risks**: Incomplete vendor geo data, geocoding latency, schema drift between LLM output and persisted `SearchIntent`, ranking regressions from over-weighting geo.

## Approver / Date
- **Approver**: User request via /build-all
- **Date**: 2026-03-09
