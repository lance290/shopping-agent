# Build Log - task-005

## Summary
Persisted `search_intent` and `provider_query_map` in row search requests so the backend stores structured intent metadata on rows.

## Files Touched
- apps/backend/routes/rows_search.py
- apps/backend/tests/test_rows_search_intent.py

## Root Cause Addressed
Row searches previously ignored structured intent payloads, causing intent metadata to be dropped before persistence. Added explicit serialization and storage during `/rows/{id}/search`.

## North Star Alignment
Supports the effort north star’s persistence rules and audit trail for provider queries, improving persistence reliability.
Reference: .cfoi/branches/dev/efforts/refactor-search-architecture-v2/product-north-star.md

## Manual Test Instructions
1. POST `http://localhost:8000/rows/{id}/search` with `search_intent` and `provider_query_map` in the body.
2. Query DB: `SELECT search_intent, provider_query_map FROM rows WHERE id={id}`.
3. Capture output for manual proof.
