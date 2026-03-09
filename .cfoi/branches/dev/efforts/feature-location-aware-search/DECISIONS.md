# Decisions — feature-location-aware-search

## 2026-03-09
- **Decision**: Treat this PRD as a single backend-first effort rather than slicing it into multiple child PRDs.
- **Why**: The scope is coherent around one cross-cutting search concern: explicit location semantics flowing from chat intent through vendor retrieval and ranking.
- **Confidence**: High

## 2026-03-09
- **Decision**: Keep `location_context` and `location_resolution` inside `row.search_intent` for v1 instead of introducing new row columns.
- **Why**: The PRD explicitly locks that behavior, and the current architecture already persists search intent as JSON.
- **Confidence**: High

## 2026-03-09
- **Decision**: Produce build-all artifacts now and defer implementation to the effort task loop.
- **Why**: The user asked to run `/build-all` for a single PRD; the clean output is the scoped plan/task set. No code was changed under this effort yet.
- **Confidence**: High
