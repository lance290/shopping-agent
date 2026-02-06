# Review Scope - enhancement-bug-report-triage

## Files to Review

### Backend (modified)
- `apps/backend/models.py` (modified)
- `apps/backend/routes/bugs.py` (modified)
- `apps/backend/services/email.py` (modified)

### Backend (added)
- `apps/backend/scripts/migrate_triage_columns.py` (added)
- `apps/backend/scripts/verify_triage_models.py` (added)
- `apps/backend/scripts/manual_verify_triage.py` (added)
- `apps/backend/tests/test_bug_triage.py` (added)

### Effort Docs (added)
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/ASSUMPTIONS.md`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/DECISIONS.md`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/ERRORS.md`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/NOTES.md`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/PROGRESS.md`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/effort.json`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/metrics.json`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/plan.md`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/product-north-star.md`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/tasks.json`
- `.cfoi/branches/dev/efforts/enhancement-bug-report-triage/tasks.md`
- `.cfoi/branches/dev/proof/task-001/build-log.md`
- `.cfoi/branches/dev/proof/task-002/alignment.md`
- `.cfoi/branches/dev/proof/task-002/build-log.md`
- `.cfoi/branches/dev/proof/task-002/tests.md`
- `.cfoi/branches/dev/proof/task-003/alignment.md`
- `.cfoi/branches/dev/proof/task-003/build-log.md`
- `.cfoi/branches/dev/proof/task-004/alignment.md`
- `.cfoi/branches/dev/proof/task-004/build-log.md`

## Out of Scope (unchanged)
- `apps/backend/routes/rows_search.py`
- `apps/backend/sourcing/choice_filter.py`
- `apps/backend/tests/test_choice_filter.py`
- `apps/backend/tests/test_rows_search.py`
- `apps/backend/tests/test_rows_search_persistence.py`
- `apps/bff/src/llm.ts`
- `apps/frontend/app/components/Chat.tsx`
- `apps/frontend/app/components/ChoiceFactorPanel.tsx`
- `apps/frontend/app/components/RequestTile.tsx`
- `apps/frontend/app/components/RowStrip.tsx`
- `apps/frontend/app/store.ts`
- `apps/frontend/app/tests/board-display.test.ts`
- `apps/frontend/app/tests/row-strip-errors.test.tsx`
- `apps/frontend/app/utils/api.ts`

## Review Started: 2026-02-05T11:05:00-08:00
