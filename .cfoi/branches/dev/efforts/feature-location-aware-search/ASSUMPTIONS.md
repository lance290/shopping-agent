# Assumptions — feature-location-aware-search

1. Existing vendor lat/lon coverage is incomplete, so text service-area fallback is mandatory.
2. Backend-only implementation is sufficient for v1 because the current frontend consumes search results from persisted row/bid data without needing a dedicated geo UI.
3. Durable geocode cache can be introduced without changing the public API contract.
4. The current test suite can absorb new location-aware tests without requiring separate frontend E2E coverage for v1.
