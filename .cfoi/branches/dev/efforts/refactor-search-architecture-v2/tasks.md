# Task Breakdown — refactor-search-architecture-v2
_Generated: 2026-01-30T05:05:27Z_

## task-001: Scaffold sourcing models and dataclasses for SearchIntent pipeline
- **E2E Flow**: Run backend unit tests that instantiate SearchIntent/ProviderQuery/NormalizedResult and confirm JSON serialization succeeds.
- **Estimated Time**: 35 minutes
- **Error Budget**: 3
- **Dependencies**: None
- **Files**: apps/backend/sourcing/__init__.py, apps/backend/sourcing/models.py, apps/backend/tests/test_sourcing_models.py
- **Tests to Write**: apps/backend/tests/test_sourcing_models.py
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-001/manual.md
- **Automated Proof Command**: `pytest apps/backend/tests/test_sourcing_models.py`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Run: cd apps/backend && pytest tests/test_sourcing_models.py
  1. Verify tests pass and dataclasses serialize with required fields
  1. Document sample SearchIntent JSON in proof manual

## task-002: Implement canonical URL + currency normalization utilities
- **E2E Flow**: Execute unit tests that canonicalize sample URLs and convert foreign currency prices; verify outputs stored for aggregator.
- **Estimated Time**: 40 minutes
- **Error Budget**: 3
- **Dependencies**: task-001
- **Files**: apps/backend/sourcing/utils/__init__.py, apps/backend/sourcing/utils/url.py, apps/backend/sourcing/utils/currency.py, apps/backend/tests/test_sourcing_utils.py
- **Tests to Write**: apps/backend/tests/test_sourcing_utils.py
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-002/manual.md
- **Automated Proof Command**: `pytest apps/backend/tests/test_sourcing_utils.py`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Run: cd apps/backend && pytest tests/test_sourcing_utils.py
  1. Inspect test log to confirm canonical URLs strip tracking params and FX conversion works
  1. Capture CLI output in manual proof

## task-003: Add DB migrations for search_intent, provider_query_map, and bid metadata
- **E2E Flow**: Apply Alembic upgrade and confirm new columns exist in rows/bids tables.
- **Estimated Time**: 40 minutes
- **Error Budget**: 3
- **Dependencies**: task-001, task-002
- **Files**: apps/backend/alembic/versions/*_search_architecture_v2.py, apps/backend/models.py, apps/backend/database.py, apps/backend/tests/test_migrations_search_architecture_v2.py
- **Tests to Write**: apps/backend/tests/test_migrations_search_architecture_v2.py
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-003/manual.md
- **Automated Proof Command**: `pytest apps/backend/tests/test_migrations_search_architecture_v2.py`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Run: cd apps/backend && alembic upgrade head
  1. Connect to Postgres and \d rows; ensure search_intent/provider_query_map columns exist
  1. Document schema diff screenshot in manual proof

## task-004: Implement BFF intent extraction service (LLM + fallback) and pass search_intent to backend
- **E2E Flow**: POST /api/search with a row containing price constraints and confirm payload includes structured search_intent JSON.
- **Estimated Time**: 45 minutes
- **Error Budget**: 3
- **Dependencies**: task-001, task-002, task-003
- **Files**: apps/bff/src/intent/index.ts, apps/bff/src/index.ts, apps/bff/src/types.ts, apps/bff/test/intent.test.ts
- **Tests to Write**: apps/bff/test/intent.test.ts
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-004/manual.md
- **Automated Proof Command**: `pnpm --filter apps/bff test intent`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Start BFF (pnpm dev) and backend
  1. Run curl POST http://localhost:8080/api/search with sample row; capture network request body
  1. Verify response echoes search_intent and attach screenshot

## task-005: Persist search_intent and provider_query_map on backend rows
- **E2E Flow**: Run /rows/{id}/search and confirm DB row stores search_intent JSON plus provider_query_map with adapters output.
- **Estimated Time**: 40 minutes
- **Error Budget**: 3
- **Dependencies**: task-003, task-004
- **Files**: apps/backend/routes/rows.py, apps/backend/routes/rows_search.py, apps/backend/tests/test_rows_search_intent.py
- **Tests to Write**: apps/backend/tests/test_rows_search_intent.py
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-005/manual.md
- **Automated Proof Command**: `pytest apps/backend/tests/test_rows_search_intent.py`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Run curl POST http://localhost:8000/rows/1/search
  1. Query Postgres: SELECT search_intent, provider_query_map FROM rows WHERE id=1
  1. Capture DB output screenshot

## task-006: Implement provider query adapters and taxonomy mapping
- **E2E Flow**: Trigger search with category-specific input and confirm provider_query_map stores adapter outputs per provider.
- **Estimated Time**: 45 minutes
- **Error Budget**: 3
- **Dependencies**: task-005
- **Files**: apps/backend/sourcing/adapters/__init__.py, apps/backend/sourcing/adapters/base.py, apps/backend/sourcing/adapters/rainforest.py, apps/backend/sourcing/adapters/google_cse.py, apps/backend/sourcing/taxonomy.py, apps/backend/tests/test_provider_adapters.py
- **Tests to Write**: apps/backend/tests/test_provider_adapters.py
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-006/manual.md
- **Automated Proof Command**: `pytest apps/backend/tests/test_provider_adapters.py`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Invoke POST /rows/{id}/search with category + price constraints
  1. Inspect provider_query_map JSON for rainforest/google entries
  1. Attach log snippet to manual proof

## task-007: Split provider executors and normalizers with status instrumentation
- **E2E Flow**: Run search hitting mock + rainforest providers and confirm response includes provider_status entries with latencies and normalized fields.
- **Estimated Time**: 45 minutes
- **Error Budget**: 3
- **Dependencies**: task-006
- **Files**: apps/backend/sourcing/executors/__init__.py, apps/backend/sourcing/executors/rainforest.py, apps/backend/sourcing/executors/google_cse.py, apps/backend/sourcing/normalizers/__init__.py, apps/backend/sourcing/normalizers/rainforest.py, apps/backend/tests/test_executors_normalizers.py
- **Tests to Write**: apps/backend/tests/test_executors_normalizers.py
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-007/manual.md
- **Automated Proof Command**: `pytest apps/backend/tests/test_executors_normalizers.py`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Set USE_MOCK_SEARCH=true and run search
  1. Inspect JSON response provider_status list for ok/timeout cases
  1. Record response snippet in manual proof

## task-008: Implement result aggregator + canonical bid persistence
- **E2E Flow**: Run search twice and verify bids table upserts by canonical_url while response returns ranked scores + provider_stats.
- **Estimated Time**: 45 minutes
- **Error Budget**: 3
- **Dependencies**: task-007
- **Files**: apps/backend/sourcing/service.py, apps/backend/routes/rows_search.py, apps/backend/tests/test_rows_search_persistence.py
- **Tests to Write**: apps/backend/tests/test_rows_search_persistence.py
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-008/manual.md
- **Automated Proof Command**: `pytest apps/backend/tests/test_rows_search_persistence.py`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Run curl POST /rows/{id}/search twice
  1. Check bids table count remains stable and existing rows updated
  1. Capture before/after screenshot of bids rows

## task-009: Wire provider stats and scores through BFF + minimal frontend UI
- **E2E Flow**: Search from UI and verify provider status badges render with partial/failure messaging.
- **Estimated Time**: 45 minutes
- **Error Budget**: 3
- **Dependencies**: task-008
- **Files**: apps/bff/src/index.ts, apps/frontend/app/store.ts, apps/frontend/app/components/ResultsList.tsx, apps/frontend/app/components/ProviderStatusBadge.tsx, apps/frontend/tests/results-provider-status.test.tsx
- **Tests to Write**: apps/frontend/tests/results-provider-status.test.tsx
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-009/manual.md
- **Automated Proof Command**: `pnpm --filter apps/frontend test provider-status`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Start frontend + BFF
  1. Perform search in UI; verify provider stats appear in results list
  1. Capture screenshot of UI for manual proof

## task-010: Add observability, regression tests, and feature flag rollout
- **E2E Flow**: Toggle USE_NEW_SOURCING_ARCHITECTURE flag and verify metrics dashboard captures DoD KPIs while old path remains fallback.
- **Estimated Time**: 45 minutes
- **Error Budget**: 3
- **Dependencies**: task-009
- **Files**: apps/backend/config/feature_flags.py, apps/backend/metrics/search_architecture.py, apps/backend/tests/test_feature_flag_search_arch.py, docs/prd/search-architecture-v2/PRD.md
- **Tests to Write**: apps/backend/tests/test_feature_flag_search_arch.py
- **Manual Evidence**: /Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/proof/task-010/manual.md
- **Automated Proof Command**: `pytest apps/backend/tests/test_feature_flag_search_arch.py`
- **Sign-off**: Lance
- **Manual Verification Steps:**
  1. Export Prometheus metrics and verify new counters exist
  1. Flip feature flag off/on and ensure searches route accordingly
  1. Attach metrics screenshot
