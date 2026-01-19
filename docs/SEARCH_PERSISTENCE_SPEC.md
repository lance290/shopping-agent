Goal
Ensure sidebar cards, product panel, and chat refinements stay in sync per row, with the DB as source of truth and Zustand as a per-row cache.

Required Changes
Row as single source of truth
Row stores: title (human-readable query), request_spec.constraints (JSON), request_spec.last_query (string).
Every refinement updates the row in DB before rendering.
LLM tool flows (create & refine)
On refine (e.g., “under $50”, “blue”), LLM MUST:
Read current row constraints (from backend) for the active row.
Merge new constraint(s).
Build new title string reflecting ALL constraints.
Call updateRow with { title, request_spec.constraints }.
Call searchListings with row_id; searchListings reads constraints from backend, not from LLM memory.
Return row_id + results.
On new search:
createRow sets initial title/constraints.
Set activeRowId to new row.
Call searchListings(row_id) and store results under that row.
Zustand store: per-row data
Keep rows and activeRowId.
Keep rowResults: Record<rowId, Products[]>.
Optionally rowQueries: Record<rowId, string> if needed for display.
When activeRowId changes, product panel shows rowResults[activeRowId]; if missing, fetch from backend or trigger search.
Product panel behavior
Renders strictly from rowResults[activeRowId].
On card click: if no results cached, trigger fetch/re-run search for that row.
Do not display stale results from another row.
Sidebar/card titles
Always use row.title from DB.
Refinements must update the row title via updateRow so UI reflects the latest query/constraints.
Prevent constraint leakage
searchListings must read the row’s stored constraints; do not reuse constraints from previous rows or LLM memory.
When creating a new row, start with a clean constraint set.
Sync cycle
After any tool completes (create/refine/delete), frontend calls /api/rows and setRows() to refresh rows from DB.
When searchListings returns, write results to rowResults[rowId].
Success Criteria
Card title matches the last refined query/constraints.
Clicking any card shows that card’s results (no cross-row bleed).
New searches start with clean constraints; no leakage from prior rows.
Page reload preserves correct rows and per-row results (or refetches per-row cleanly).
Refinements update both DB and store before rendering.
Implementation Notes (no code here, just guidance)
Ensure searchListings ignores LLM conversation state and uses backend row constraints.
Make product panel selector depend on activeRowId + rowResults[activeRowId].
Add per-row result cache; avoid a single global searchResults.
Always call updateRow before running a refined search.
Use this as the blueprint to implement the fixes.

Keep repeating until source of truth is clear and synchronized, is persistent across sessions, is displayed properly in the UI, and is accessible to all components that need it, and all tests pass, and is isolated per user, and code is clean and maintainable.
