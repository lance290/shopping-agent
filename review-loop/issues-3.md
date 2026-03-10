# Code Review Issues - Iteration 3

## Summary
- **Total Issues**: 3
- **Critical**: 0
- **Major**: 2
- **Minor**: 1
- **Nits**: 0

## Critical Issues 🔴
These BLOCK approval. Must be fixed.

- None.

## Major Issues 🟠
These require attention. Should be fixed.

### M1: Stream path duplicates the new embedding-builder logic instead of reusing the shared helper
- **File**: `apps/backend/routes/rows_search.py:531-599`
- **Category**: DRY / Integration / Future-proofing
- **Problem**: `rows_search.py` still hand-builds the multi-concept query embedding inline, while `apps/backend/sourcing/vendor_provider.py` now has `_build_embedding_concepts(...)` and `build_query_embedding(...)` as the intended shared implementation. That means the sync path and stream path can drift again on concept parsing, weights, batching behavior, and fallback semantics.
- **Risk**: A future tweak to the shared vendor embedding logic will silently change one path but not the other. You end up with different query embeddings, different vendor retrieval, and hard-to-explain ranking differences between sync and streaming search for the same row.
- **Fix**: Replace the inline concept-building block in `rows_search.py` with a call to `build_query_embedding(...)`, passing the same `vendor_query`, `sanitized_query`, and parsed `intent_payload` used elsewhere.

### M2: Sync and streaming quantum paths still compute query embeddings differently
- **File**: `apps/backend/sourcing/service.py:259-307`, `apps/backend/routes/rows_search.py:531-622`
- **Category**: Logic / Cross-file contract
- **Problem**: The streaming path computes `query_embedding` on demand from the row intent/context and uses it for quantum reranking. The sync `search_and_persist(...)` path still only quantum-reranks when `row.search_intent` already contains `query_embedding`. The current changes improved vendor-query forwarding, but they did not unify the quantum-reranker input contract across these two paths.
- **Risk**: The same search request can produce different quantum behavior depending on whether it runs through the sync route or the SSE route. That makes evaluation noisy and makes shadow-vs-live comparisons less trustworthy.
- **Fix**: Move query-embedding construction behind one shared helper and use it in both sync and stream flows. The sync path should not depend on pre-stored `query_embedding` if the stream path already knows how to derive it safely.

## Minor Issues 🟡
These improve quality. Nice to fix.

### m1: The provider FTS semantic change is not protected by a focused regression test
- **File**: `apps/backend/sourcing/vendor_provider.py:210-219`
- **Category**: Test Coverage / Search quality risk
- **Problem**: The FTS query changed from `&` to `|`, which materially changes recall/precision tradeoffs, but the new tests added in this session do not assert that this behavior is intentional or guarded. The nearby explanatory text also no longer clearly matches the implementation intent.
- **Suggestion**: Add one focused regression test around FTS query construction or hybrid-search behavior so future edits do not unknowingly toggle between AND/OR semantics.

---
## Verdict: FAIL

Fix all Major issues, then re-run /review-loop.
