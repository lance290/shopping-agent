# Review Fixes - Iteration 3

## Resolved Issues

### M1 resolved: shared embedding builder now reused in the stream path
- Replaced the inline multi-concept embedding construction in `apps/backend/routes/rows_search.py`
- The stream path now calls `build_query_embedding(...)`
- The stream path now forwards `intent_payload` into `search_streaming(...)`

### M2 resolved: sync and stream paths now share the same query-embedding contract
- `apps/backend/sourcing/service.py` now computes `query_embedding` via `build_query_embedding(...)`
- The sync path passes `intent_payload` and `query_embedding` into `search_all_with_status(...)`
- Quantum reranking in the sync path now uses the same computed `query_embedding` instead of depending on a stored `row.search_intent.query_embedding`

### m1 resolved: current FTS semantics now have a focused regression test
- Added a regression assertion in `apps/backend/tests/test_vendor_search_intent.py`
- This locks in the current `" | "` FTS query join behavior unless intentionally changed later

## Verification
- Backend: `uv run pytest tests/test_embedding_and_quantum_regressions.py tests/test_vendor_search_intent.py tests/test_streaming_and_vendor_search.py`
  - Result: `52 passed`
- Frontend: `pnpm vitest run app/tests/tip-jar-copy.test.ts app/tests/sdui-scenario-contracts.test.ts`
  - Result: `27 passed`
