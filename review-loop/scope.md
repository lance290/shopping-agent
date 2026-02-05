# Review Scope - Cherry-picked Upstream Commits

## Files to Review

### Backend (modified)
- `apps/backend/routes/rows_search.py` (modified)
- `apps/backend/sourcing/choice_filter.py` (added)
- `apps/backend/tests/test_choice_filter.py` (added)
- `apps/backend/tests/test_rows_search.py` (modified)

### BFF (modified)
- `apps/bff/src/llm.ts` (modified)

### Frontend (modified)
- `apps/frontend/app/components/Chat.tsx` (modified)
- `apps/frontend/app/components/ChoiceFactorPanel.tsx` (modified)
- `apps/frontend/app/components/RequestTile.tsx` (modified)
- `apps/frontend/app/components/RowStrip.tsx` (modified)
- `apps/frontend/app/store.ts` (modified)
- `apps/frontend/app/tests/board-display.test.ts` (modified)
- `apps/frontend/app/tests/row-strip-errors.test.tsx` (modified)
- `apps/frontend/app/utils/api.ts` (modified)

## Commits in Scope
1. `4bd89c4` - wheels up time + trip type fields for private jet charter
2. `9a350f9` - prevent product search when modifying service row parameters
3. `15ee4b9` - multi-select support for choice factors
4. `075f5e5` - clear chat stream when clicking "New Request"
5. `1698a15` - choice factor filtering for search results
6. `b539fb0` - progressive disclosure for choice factor questions
7. `5315ab6` - improved loading state for service rows
8. `6572366` - enable vendor search for service rows

## Review Started: 2026-02-05T08:22:00-08:00
