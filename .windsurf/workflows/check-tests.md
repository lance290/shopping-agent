---
allowed-tools: "*"
description: Verify and generate missing unit, integration, e2e, and scenario tests after /build-all
---

# Check-Tests Workflow

**Purpose**: Run this workflow immediately after `/build-all` to guarantee the current session has complete test coverage across **unit**, **integration**, **e2e**, and **scenario** levels for both **frontend** and **backend** (when either side was changed). If any required level is missing, create those tests before `/push`.

> **When to use**: After `/build-all` completes, before `/push`.
> **Primary outcome**: Every changed frontend/backend behavior from the session is protected by all required test layers (or explicitly documented as blocked).

---
## Step 0: Preconditions
// turbo

1. Detect current branch and set:
   - `branch = git branch --show-current`
   - `build-all dir = .cfoi/branches/[branch]/build-all/`
2. Confirm `/build-all` artifacts exist:
   - Required: `.cfoi/branches/[branch]/build-all/BUILD-ALL-REPORT.md`
3. If missing, HALT with:
   ```
   ❌ BUILD-ALL REPORT NOT FOUND

   Run /build-all first, then re-run /check-tests.
   ```

---
## Step 1: Determine Current Session Scope
// turbo

1. Gather changed files for this session:
   ```bash
   # Prefer current working tree (staged + unstaged)
   git diff --name-only --diff-filter=ACMRT HEAD

   # If empty, use last commit as session scope
   git diff --name-only --diff-filter=ACMRT HEAD~1..HEAD
   ```
2. Remove non-code files from scope (docs, lockfiles, snapshots, generated files, media).
3. Exclude existing test files from this list (we only want changed implementation targets).
4. Classify changed implementation files into:
   - `frontend scope`: files under `apps/frontend/`
   - `backend scope`: files under `apps/backend/`
5. If both scopes are present, enforce test creation + verification for both scopes. One side cannot substitute for the other.
6. If no implementation files changed, output:
   ```
   ℹ️ No implementation changes detected.
   No additional tests required.
   ```
   Then proceed to Step 6 and write a no-op report.

---
## Step 2: Build Test Obligation Matrix

For each changed implementation file, create a matrix row with required test layers:

- **Unit**: Pure logic, helpers, deterministic transformations.
- **Integration**: DB, API, routing, adapters, persistence, or service boundaries.
- **E2E**: User-visible click/flow coverage across real interfaces.
- **Scenario**: Multi-step business path spanning components/services (happy + key edge path).

Required format:

```markdown
| Surface | Changed File | Behavior | Unit | Integration | E2E | Scenario | Notes |
|---|---|---|---|---|---|---|---|
| backend | apps/backend/routes/foo.py | adds quote status transition | required | required | required | required | - |
```

Rules:
1. Default to **required** unless there is a concrete technical reason.
2. `n/a` is allowed only with a short written justification.
3. Every changed behavior must map to at least one test per required layer.
4. If both frontend and backend changed, both must appear in the matrix.

---
## Step 3: Discover Existing Tests and Identify Gaps
// turbo

1. Search for tests already covering each behavior.
2. Mark each layer per behavior as one of:
   - `covered`
   - `partial`
   - `missing`
3. Do **not** count any of these as valid coverage:
   - skipped tests
   - TODO placeholders
   - empty assertions
4. Produce a gap list ordered by severity:
   1. missing unit
   2. missing integration
   3. missing e2e
   4. missing scenario

---
## Step 4: Create Missing Tests

For every `missing` or `partial` row, write/expand tests in existing test locations.

Preferred locations:
- Backend unit/integration/scenario: `apps/backend/tests/` (or existing backend scenario directories)
- Frontend unit/integration/scenario: existing frontend test directories already used by the repo
- Frontend e2e: `apps/frontend/e2e/` (or existing repo e2e directories)

Rules:
1. Follow existing naming/style conventions in the nearest existing tests.
2. Keep tests behavior-focused (assert the user/system outcome, not implementation trivia).
3. Add regression assertions for the exact changed behavior.
4. Keep edits atomic; do not mix unrelated refactors.

---
## Step 5: Run Verification Suites

1. Discover repo test commands in this order:
   1) `package.json` scripts (`test`, `test:unit`, `test:integration`, `e2e`, `scenario`, `ci`)
   2) `docker compose` strategy
   3) `Makefile` targets
   4) language fallback commands
2. Determine verification scope from Step 1:
   - `backend_changed`: at least one changed implementation file in `apps/backend/`
   - `frontend_changed`: at least one changed implementation file in `apps/frontend/`
3. Run targeted suites for newly created tests first.
4. Run full required suites for each changed scope:
   - If `backend_changed`: run backend unit + integration + scenario suites (and backend e2e if present in repo).
   - If `frontend_changed`: run frontend unit + integration + e2e + scenario suites.
5. If both scopes changed, PASS requires both backend and frontend suites to pass.
6. If failures occur, fix root cause and rerun until green or explicitly blocked.
7. Never bypass verification with `--no-verify`.

---
## Step 6: Write Test Completeness Report

Create/update:
`/Volumes/PivotNorth/Shopping Agent/.cfoi/branches/[branch]/build-all/TEST-COMPLETENESS-REPORT.md`

Template:

```markdown
# Test Completeness Report - [timestamp]

## Session Scope
- Branch: [branch]
- Changed implementation files: [count]
- Frontend changed: [yes/no]
- Backend changed: [yes/no]

## Obligation Matrix
[table from Step 2 + Step 3 status]

## Tests Created/Updated
- Unit: [files]
- Integration: [files]
- E2E: [files]
- Scenario: [files]

## Verification Commands
### Backend
- [command]

### Frontend
- [command]

## Results
### Backend
- Unit: [pass/fail/n/a]
- Integration: [pass/fail/n/a]
- E2E: [pass/fail/n/a]
- Scenario: [pass/fail/n/a]

### Frontend
- Unit: [pass/fail/n/a]
- Integration: [pass/fail/n/a]
- E2E: [pass/fail/n/a]
- Scenario: [pass/fail/n/a]

## Open Blockers
- [none or explicit blocker with owner + next action]

## Verdict
- PASS (all required layers covered + passing)
- BLOCKED (include reason)
```

---
## Step 7: Completion Gate

Only declare completion when one of the following is true:

1. **PASS**
   - All required layers exist for session behaviors
   - All required suites pass for each changed scope (frontend and/or backend)
2. **BLOCKED**
   - Missing layers/tests or failing suites have explicit blocker entries with owner + next action

Final output:

```
🧪 CHECK-TESTS COMPLETE

- Backend: [status]
- Frontend: [status]
- Report: .cfoi/branches/[branch]/build-all/TEST-COMPLETENESS-REPORT.md

Next: /push (only if PASS)
```

---
## Key Rules

1. This workflow is mandatory after `/build-all` and before `/push`.
2. All four test layers are required unless explicitly justified as `n/a`.
3. If backend changed, backend verification is mandatory; if frontend changed, frontend verification is mandatory.
4. If both changed, both must be green before PASS.
5. Prefer extending existing test files over creating parallel duplicate structures.
6. Never mark complete if any required layer is missing.
7. Never use `--no-verify`.
