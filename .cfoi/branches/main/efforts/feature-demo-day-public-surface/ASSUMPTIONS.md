# Assumptions - feature-demo-day-public-surface

> Document all assumptions made during planning. Verify during implementation.

## Assumptions

### Backend
1. **`SourcingRepository.search_all_with_status()` works without row_id** — it just needs a query string and optional kwargs (desire_tier, providers). Needs verification during Task 3.
2. **`triage_provider_query()` and `extract_search_intent()` accept None** for `row_title` and `project_title` parameters. Verified: both have `Optional[str] = None` signatures.
3. **Scoring pipeline can run without Bid persistence** — `score_results()`, quantum reranker, and constraint scorer operate on `NormalizedResult` objects, not Bids. Needs verification during Task 3.
4. **`VendorDirectoryProvider` can be called independently** for the vendor search endpoint. Verified: it has a standalone `search()` method.

### Frontend
5. **Next.js route groups** `(public)` and `(workspace)` work with the existing root layout. Standard Next.js App Router feature — low risk.
6. **Moving `page.tsx` to `(workspace)/page.tsx`** preserves all existing functionality — the workspace route still resolves to `/` for logged-in users.
7. **Skimlinks script in root layout** handles universal affiliate link conversion for non-Amazon/eBay links on public pages too.

### Data
8. **Vendor slugs can be derived from vendor name** via slugification, or we add a `slug` column to the vendor table. Need to check if slugs are unique.
9. **Vendor database is being populated in parallel** by user — we work with whatever vendors exist at demo time.
10. **Guide content generation via LLM** happens during development (Task 6), not at runtime. Guides are static files.

### Scoring
11. **Vendor directory tier_fit of 0.85 for commodity** is the right balance — not 1.0 (gives slight preference to retail APIs which have prices/ratings) but not penalizing vendors who sell commodities.
