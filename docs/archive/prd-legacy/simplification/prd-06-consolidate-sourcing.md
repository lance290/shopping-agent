# PRD-06: Consolidate Sourcing System

## Business Outcome
- **Measurable impact:** Eliminate duplicate sourcing definitions by removing the shadow root module (`apps/backend/sourcing.py`) and keeping the package implementation as source of truth.
- **Success criteria:** Root `sourcing.py` deleted, package imports continue to resolve correctly, duplicate symbols removed/centralized, and no regression in sourcing metrics instrumentation.
- **Target users:** Developers (one code path to debug and maintain; bug fixes apply everywhere).

## Scope
- **In-scope:**
  - Delete `apps/backend/sourcing.py` (root, 778 LOC)
  - Verify package imports remain correct after deleting the shadow root module
  - Keep `sourcing/metrics.py` instrumentation intact
  - Evaluate collapsing `sourcing/service.py` + `sourcing/repository.py` if the separation isn't justified
  - Ensure `sourcing/` package exports all symbols that were previously imported from root `sourcing.py`
- **Out-of-scope:**
  - Rewriting the sourcing logic or search providers
  - Changing search result quality or ranking
  - Adding new search providers
  - Changing the sourcing API contract

## Current State (Evidence)

### Duplicate Symbols (defined in both files)

| Symbol | `sourcing.py` (root) | `sourcing/repository.py` | `sourcing/` (other) |
|--------|---------------------|--------------------------|---------------------|
| `SearchResult` | class (Pydantic model) | class (Pydantic model) | also in `sourcing/models.py`? |
| `SearchResultWithStatus` | class | class | — |
| `SourcingRepository` | class (778 LOC) | class (1,128 LOC) | — |
| `extract_merchant_domain()` | function | function | — |
| `normalize_url()` | function | function | — |
| `compute_match_score()` | function | function | — |
| `redact_secrets` | alias/function | alias/function | — |

### Import Resolution Clarification (second-pass)

`from sourcing import ...` currently resolves to `sourcing/__init__.py` (package), not the root `sourcing.py` file, because the package directory takes precedence.

Implication:
- Root `apps/backend/sourcing.py` is likely dead/shadow code.
- Deletion can proceed without the previously assumed 3-file import rewrite, but should still be validated with runtime import checks + tests.

### `sourcing/` Package Structure

```
sourcing/
  __init__.py
  adapters/
    __init__.py
    base.py
    google_cse.py
    rainforest.py
    ebay.py
  executors/
    __init__.py
    base.py
    google_cse.py
    rainforest.py
    ebay.py
  models.py
  repository.py          (1,128 LOC — the "real" implementation)
  service.py             (orchestrates search + persistence)
  normalizers.py
  metrics.py             (214 LOC — active)
  safety.py
  taxonomy.py
  material_filter.py
  choice_filter.py
  messaging.py
```

### `sourcing/metrics.py` — Confirmed Active

`sourcing/metrics.py` is imported by `sourcing/service.py` and `sourcing/repository.py` and has dedicated tests. Do not delete in this PRD.

### `sourcing/service.py` vs `sourcing/repository.py` — Evaluate Collapse

- `service.py` wraps `repository.py` with DB persistence logic
- If the separation is `repository = search execution` and `service = search + save to DB`, this is a valid separation
- If `service.py` is a thin wrapper that just calls `repository.py` and saves results, consider collapsing

## Target State

### After Deletion

```
apps/backend/
  sourcing.py              ← DELETED
  sourcing/
    __init__.py            ← Updated exports (ensure SearchResult, etc. are re-exported)
    repository.py          ← Single SourcingRepository
    service.py             ← Orchestration (keep if justified)
    models.py              ← SearchResult, SearchResultWithStatus, etc.
    adapters/              ← Provider-specific query adapters
    executors/             ← Provider-specific search executors
    normalizers.py
    safety.py
    taxonomy.py
    material_filter.py
    choice_filter.py
    messaging.py
    metrics.py             ← KEEP (active)
```

### Updated Imports (optional cleanup)

**`main.py`:**
```python
# BEFORE
from sourcing import SourcingRepository, SearchResult
# AFTER
from sourcing.repository import SourcingRepository
from sourcing.models import SearchResult  # or from sourcing import SearchResult via __init__.py
```

**`routes/clickout.py`:**
```python
# BEFORE
from sourcing import extract_merchant_domain
# AFTER
from sourcing.repository import extract_merchant_domain  # or move to sourcing/utils.py
```

**`routes/rows_search.py`:**
```python
# BEFORE
from sourcing import (
    SearchResult, SearchResultWithStatus, extract_merchant_domain,
    normalize_url, compute_match_score
)
# AFTER
from sourcing.models import SearchResult, SearchResultWithStatus
from sourcing.repository import extract_merchant_domain, normalize_url, compute_match_score
```

### `sourcing/__init__.py` — Clean Exports

Update `__init__.py` to re-export commonly used symbols so imports can be short:
```python
from sourcing.models import SearchResult, SearchResultWithStatus
from sourcing.repository import SourcingRepository, extract_merchant_domain, normalize_url, compute_match_score
```

This allows both `from sourcing import SearchResult` (short) and `from sourcing.models import SearchResult` (explicit).

## User Flow
No user flow change. Search works identically. Same providers, same results, same persistence.

## Business Requirements

### Authentication & Authorization
- No auth changes

### Monitoring & Visibility
- After deletion: verify search still works end-to-end
- Monitor for import errors in logs

### Performance Expectations
- No change — same code, just one copy instead of two

### Data Requirements
- No data changes

### UX & Accessibility
- No UI changes

### Privacy, Security & Compliance
- `redact_secrets` function must still work (used in logging)

## Implementation Steps

### Step 1: Verify `sourcing/` package has all needed symbols

Before deleting root `sourcing.py`, verify that every symbol imported from it exists in the `sourcing/` package:

```bash
# Symbols imported from root sourcing.py:
grep -rn "from sourcing import" apps/backend/ --include="*.py" | grep -v "from sourcing\." 
```

For each symbol, confirm it exists in `sourcing/repository.py`, `sourcing/models.py`, or another `sourcing/` submodule.

### Step 2: Optional import cleanup

If desired, make imports more explicit (`from sourcing.repository ...`, `from sourcing.models ...`) for readability. This is optional and not required for deleting root `sourcing.py`.

### Step 3: Update `sourcing/__init__.py`

Ensure it re-exports the commonly used symbols for backward compatibility.

### Step 4: Delete `sourcing.py` (root)

```bash
rm apps/backend/sourcing.py
```

### Step 5: Keep `sourcing/metrics.py`

Retain metrics module and ensure its instrumentation coverage stays green.

### Step 6: Evaluate `service.py` vs `repository.py` collapse

Read both files. If `service.py` is a thin wrapper:
- Move persistence logic into `repository.py`
- Delete `service.py`
- Update imports

If the separation is meaningful (e.g., service handles transactions, repository handles search execution):
- Keep both
- Document the boundary

### Step 7: Run tests

```bash
cd apps/backend && python -m pytest
```

## Dependencies
- **Upstream:** PRD-01 (dead backend code deleted) — ensures we're not updating imports for code that will be deleted
- **Downstream:** None — this is independent and can run in parallel with PRD-03/04/05

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing symbol in `sourcing/` package | High | Verify every imported symbol exists before deleting root file |
| `sourcing/__init__.py` circular import | Medium | Use explicit submodule imports in `__init__.py`; test with `python -c "from sourcing import SearchResult"` |
| Root `sourcing.py` has logic divergence from `sourcing/repository.py` | High | Diff the two implementations before deletion; if root has unique logic, port it to package first |
| `sourcing/metrics.py` is imported by a deploy script we don't see | Low | Check for any non-Python imports (shell scripts, Docker commands) |
| Collapsing service+repository introduces bugs | Medium | Only collapse if the separation is truly unjustified; keep both if in doubt |

## Acceptance Criteria (Business Validation)
- [ ] `apps/backend/sourcing.py` (root) deleted
- [ ] Runtime import check confirms `import sourcing` resolves to package module path
- [ ] `sourcing/__init__.py` re-exports remain consistent with package symbols used by routes/tests
- [ ] `sourcing/metrics.py` retained and active imports/tests still pass
- [ ] Backend starts cleanly: `python -c "from main import app"`
- [ ] Search works: submit chat intent → tiles appear with correct data
- [ ] All tests pass
- [ ] No duplicate symbol definitions across `sourcing/` submodules

## Traceability
- **Parent PRD:** `docs/prd/simplification/parent.md`
- **Analysis:** `SIMPLIFICATION_PLAN.md` — Problem 2: Duplicated Core Code, Phase 5: Simplify the Sourcing System

---
**Note:** Technical implementation decisions are made during /plan and /task.
