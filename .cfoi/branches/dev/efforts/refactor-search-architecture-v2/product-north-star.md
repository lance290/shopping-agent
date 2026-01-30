# Effort North Star (Effort: refactor-search-architecture-v2, v2026-01-29)

## Goal Statement
Implement Search Architecture v2 to reliably produce, persist, and rank results across multiple search providers while preserving negotiation options.

## Ties to Product North Star
- **Product Mission**: Reliable multi-provider procurement search with transparent results.
- **Supports Metrics**: search success rate (>90%), price filter accuracy (>95%), persistence reliability (100%).

## In Scope
- Structured intent extraction (LLM + fallback) with versioned taxonomy.
- Provider query adapters, executors, and normalizers.
- Result aggregation with scoring and post-filtering.
- Persistence rules: canonical URL + bid upserts + provider query audit trail.
- Backend response contract updates + logging/metrics.

## Out of Scope
- Cross-provider deduplication (explicitly excluded).
- Real-time price updates or live inventory checks.
- UI redesign beyond minimal wiring for new response fields.

## Acceptance Checkpoints
- [ ] Search returns results from all configured providers with provider status visibility.
- [ ] Price filters correctly applied and persisted across refreshes.
- [ ] Provider-specific query adapters active (verified via stored provider_query_map).
- [ ] Normalized results persisted as bids with canonical URL upserts.
- [ ] p95 end-to-end search latency <= 12s with partial results.

## Dependencies & Risks
- **Dependencies**: Provider API keys, DB migration approval, LLM availability.
- **Risks**: Provider API changes, LLM extraction failures, latency regressions.

## Approver / Date
- **Approver**: Pending
- **Date**: Pending
