# Review Loop Issues - Iteration 1

## Summary
Most files are clean and structural boundaries are good. The previous commit resolved the circular import issues and test setup failures. However, there are a few minor things to clean up, primarily related to file size and minor code organization since `rows_search.py` is still above the 500-line threshold.

## 🟠 Major Issues

### 1. `rows_search.py` is 530 lines (violates 500 LOC max)
- **File:** `apps/backend/routes/rows_search.py`
- **Description:** The file is 530 lines long. We tried to split it previously and hit a circular import issue with `SearchResponse`. However, `SearchResponse` only needs to be defined in one place (or an isolated models file), and the helper functions `_build_base_query`, `_sanitize_query`, and `_extract_filters` could be moved to a clean helper module (e.g. `routes/rows_search_helpers.py` or `sourcing/search_helpers.py`) to reduce file length.
- **Fix:** Move `_build_base_query`, `_sanitize_query`, and `_extract_filters` (lines 58-132) to `sourcing/search_helpers.py`.

## 🟡 Minor Issues / Nits

### 2. Repeated unused imports
- **File:** `apps/backend/routes/rows_search.py`
- **Description:** The `SearchIntent` and `build_provider_query_map` imports are no longer used locally.
- **Fix:** Remove unused imports.

### 3. Extra newlines at end of test files
- **File:** `apps/backend/tests/test_rows_authorization_behavior.py`
- **Description:** Lines 205-208 have multiple trailing blank lines.
- **Fix:** Remove extra trailing blank lines.

---
