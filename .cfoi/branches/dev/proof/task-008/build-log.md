# Build Log - task-008

## Summary
Implemented `SourcingService` to orchestrate search execution, result normalization, and canonical bid persistence. Refactored `rows_search.py` to delegate to this service, ensuring centralized logic for upserting bids based on canonical URLs.

## Files Touched
- `apps/backend/sourcing/service.py`: New service class for search orchestration and persistence.
- `apps/backend/routes/rows_search.py`: Refactored to use `SourcingService` and removed inline persistence logic.
- `apps/backend/tests/test_rows_search_persistence.py`: New unit tests for persistence logic (deduplication, updates, creation).

## Root Cause Addressed
Previously, persistence logic was coupled to the route handler and lacked robust deduplication based on canonical URLs, leading to potential duplicates and scattered logic.

## North Star Alignment
Directly supports "Normalized results persisted as bids with canonical URL upserts" by enforcing canonical URL checks during bid creation/update.

## Manual Test Instructions
1. Run search on a row twice.
2. Verify in DB that bids are upserted (count stable for same results) and updated_at changes.
3. Check that provider statuses are returned in the API response.
