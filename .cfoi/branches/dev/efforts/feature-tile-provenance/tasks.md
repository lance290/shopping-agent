# Tasks - feature-tile-provenance

## task-001: Add provenance to NormalizedResult + build in normalizer (25 min)
**Files**: `sourcing/models.py`, `sourcing/normalizers/__init__.py`, `tests/test_provenance_pipeline.py`
**Dependencies**: None

**E2E Flow**: When a search returns results, each NormalizedResult carries a provenance dict with product_info and matched_features built from structured provider data (rating, shipping, reviews, match_score).

**Manual Verification**:
1. Run: `uv run python -m pytest tests/test_provenance_pipeline.py -v`
2. Verify NormalizedResult includes provenance with product_info and matched_features

**Tests**: `TestNormalizerProvenance` class in `test_provenance_pipeline.py`

---

## task-002: Enrich provenance with search intent + chat in _persist_results() (35 min)
**Files**: `sourcing/service.py`, `tests/test_provenance_pipeline.py`
**Dependencies**: task-001

**E2E Flow**: When _persist_results() creates or updates a Bid, it merges NormalizedResult provenance with search intent keywords/features from Row.search_intent and extracts last 2 user messages from Row.chat_history. The merged JSON is set on Bid.provenance.

**Manual Verification**:
1. Run: `uv run python -m pytest tests/test_provenance_pipeline.py -v`
2. Verify Bid.provenance is non-null with merged search intent and chat excerpts

**Tests**: `TestPersistProvenance` class in `test_provenance_pipeline.py`

---

## task-003: Improve TileDetailPanel fallback + accessibility (25 min)
**Files**: `TileDetailPanel.tsx`, `tests/tile-detail-panel.test.ts`
**Dependencies**: None (parallel with task-001/002)

**E2E Flow**: Detail panel shows "Based on your search" for null provenance. Tab navigates sections. ARIA labels present.

**Manual Verification**:
1. Run: `cd apps/frontend && npx vitest run app/tests/tile-detail-panel.test.ts`
2. Verify fallback message and Tab navigation

**Tests**: `tile-detail-panel.test.ts`

---

## task-004: End-to-end integration tests + regression check (30 min)
**Files**: `tests/test_provenance_pipeline.py`, `tests/tile-detail-panel.test.ts`
**Dependencies**: task-001, task-002, task-003

**E2E Flow**: Full search_and_persist creates Bids with provenance. GET /bids/{id}?include_provenance=true returns populated computed fields. All existing tests pass.

**Manual Verification**:
1. Run all backend tests: `uv run python -m pytest tests/ -v`
2. Run all frontend tests: `cd apps/frontend && npx vitest run`
3. Verify zero regressions

**Tests**: `TestEndToEndProvenance` class
