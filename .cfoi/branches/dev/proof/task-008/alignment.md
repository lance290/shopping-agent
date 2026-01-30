# Alignment Check - task-008

## North Star Goals Supported
- **Product Mission**: Reliable multi-provider procurement search with transparent results.
- **Acceptance Checkpoint**: "Normalized results persisted as bids with canonical URL upserts."

## Task Scope Validation
- **In scope**:
  - Implementing `SourcingService` to orchestrate search and persistence.
  - Aggregating normalized results from `search_all_with_status`.
  - Upserting `Bid` records keyed by `canonical_url` (to prevent duplicates).
  - Creating/Linking `Seller` records based on merchant domain.
  - Updating `rows_search.py` to delegate logic to `SourcingService`.
- **Out of scope**:
  - UI changes (handled in task-009).
  - Cross-provider deduplication beyond exact canonical URL match.

## Acceptance Criteria
- [ ] `SourcingService.search_and_persist` executes search and saves bids.
- [ ] Bids are upserted: existing bids (by canonical URL) updated, new ones inserted.
- [ ] Sellers are created if they don't exist.
- [ ] Row provider_query_map and search_intent are preserved (already done, but verified).
- [ ] Response includes aggregated results and provider statuses.

## Approved by: Cascade
## Date: 2026-01-30
