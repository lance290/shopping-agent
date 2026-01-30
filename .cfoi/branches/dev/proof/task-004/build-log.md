# Build Log - task-004

## Summary
Implemented BFF intent extraction (LLM + heuristic fallback) and wired `/api/search` to forward structured `search_intent` payloads to the backend.

## Files Touched
- apps/bff/src/intent/index.ts
- apps/bff/src/types.ts
- apps/bff/src/index.ts
- apps/bff/test/intent.test.ts

## Root Cause Addressed
Legacy `/api/search` forwarded only raw query strings, causing inconsistent intent handling and price parsing downstream. Added structured intent extraction with fallback to stabilize provider queries and ensure consistent metadata.

## North Star Alignment
Supports effort north star by introducing structured intent extraction with versioned taxonomy, improving search success rate and price filter accuracy.
Reference: .cfoi/branches/dev/efforts/refactor-search-architecture-v2/product-north-star.md

## Manual Test Instructions
1. Start backend and BFF.
2. POST to `http://localhost:8080/api/search` with `rowId` and price constraints.
3. Verify backend request payload includes `search_intent`.
