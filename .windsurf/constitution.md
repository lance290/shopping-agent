# Workspace Constitution (Build-First Delivery)

## Priorities

1. Build-first loop: scope → ship the end-user experience → harden with tests.
2. Keep vertical slices narrow; each `/task` should be <45 minutes.
3. Commit after every `/implement` task and compact Windsurf context to stay focused.
4. Harden only after the feature works: add contracts, seeds, unit/integration/E2E tests before merge.
5. Prefer pure functions and keep files under 450 lines; refactor once tests are green.

## Code Organization

- **Co-location**: Group related UI/API/domain code together; avoid horizontal scaffolding.
- **API structure**: Use routes/controllers → services → repositories/adapters.
- **Data access**: Repositories/adapters encapsulate persistence. No direct database calls from UI/services.
- **Contracts**: Any cross-service change updates contracts and regenerates typed clients.
- **Branch artifacts**: Store planning artifacts in `.cfoi/branches/[branch]/` for easy cleanup.
- **Function reuse**: Extract reusable functions when logic appears 3+ times. Prefer small, composable functions over large monolithic ones.

## Guardrails

- **⛔ GREEN BASELINE RULE**: ALL tests must pass before starting ANY new work (planning, tasks, checkpoints). No exceptions. This is a BLOCKER.
- Secrets never appear in code or logs. Use Secret Manager or equivalent.
- Every PR automatically provisions an ephemeral Cloud Run environment with synthetic data only.
- Hooks enforce formatting, file-length limits, and checkpoint discipline.
- Tests target: unit for domain, integration for data edges, E2E for golden paths.
- Default package manager: npm (override by updating this constitution if needed).

## Product Signals & Feedback Loops (App Development)

- How can I learn from what users are actually doing every day?
- Where are my signals coming from?
- How often do I look at them?
- What signal loops am I building?

## AI Accountability Rules

**Purpose**: Prevent AI from wandering, being lazy, or skipping critical work.

### REQUIRED When Implementing:

- ✅ **Verify ALL tests pass BEFORE starting** (green baseline - this is mandatory and blocking)
- ✅ Complete ALL code (no TODOs, FIXMEs, or placeholders)
- ✅ Add ALL imports at top of files (not scattered throughout)
- ✅ Implement error handling (not just happy path)
- ✅ Write actual tests (not empty test files with just imports)
- ✅ **Run ALL tests AFTER implementation** (must pass before commit)
- ✅ Update documentation as you go (not "I'll do it later")
- ✅ Verify against original `/plan` before completing
- ✅ Cite the active product/effort north star in build, manual, and automation proof artifacts
- ✅ Run `./tools/verify-implementation.sh` before claiming done
- ✅ Show proof of completion (code snippets, test output, working demo)

### FORBIDDEN Behaviors:

- ❌ **Starting ANY work with failing tests** (green baseline violation - this is a blocker)
- ❌ **Proceeding past test verification without human confirmation** (cannot be bypassed)
- ❌ **Skipping tests** (`.skip()`, `.todo()`, `xit()`, `xdescribe()`, `@skip`, etc.) - tests must RUN
- ❌ **Commenting out tests** to avoid running them - tests must RUN
- ❌ **Deleting test files** to avoid fixing them - SEVERE VIOLATION
- ❌ **Deleting test cases** from test files to make them pass - SEVERE VIOLATION
- ❌ **Reducing test count** without explicit human approval and documentation
- ❌ **Duplicating code** instead of extracting reusable functions (DRY principle)
- ❌ Saying "I'll do X" then not doing X
- ❌ Creating placeholder functions (`// TODO: implement this`)
- ❌ Leaving `pass`, `raise NotImplementedError`, or empty functions
- ❌ Fake data or hardcoded examples only (use realistic values)
- ❌ Claiming completion without showing actual code changes
- ❌ Wandering from original goal without explicit approval
- ❌ "This should work" without proving it works
- ❌ Large commits without showing what changed
- ❌ **Committing code with failing tests** (breaks rollback ability)
- ❌ Claiming completion without explicit north star alignment evidence

### Verification Process:

1. **Before implementation**: Review task, confirm scope, create checklist
2. **During implementation**: Update progress every 30 minutes; **commit at least every 30 minutes** (smaller, frequent commits are easier to review and roll back)
3. **After implementation**: Fill completion checklist with proof
4. **Pre-commit**: Run verification script, show passing tests
5. **Final check**: Human reviews checklist, confirms north star linkage, and approves

### Red Flags (Human Should Reject):

🚩 "I'll implement X later" → No. Implement now or explicitly defer with reason.
🚩 "Here's a basic version" → Define "basic". Show full implementation.
🚩 "TODO: Add error handling" → Not acceptable. Add it now.
🚩 "See the updated file" → Show actual code, don't just reference.
🚩 "Let me know if you want..." → Follow the plan, don't ask permission.

### Quality Enforcement:

Run before committing:

```bash
./tools/verify-implementation.sh
```

This checks for:

- TODO/FIXME comments in new code
- Placeholder implementations
- Imports not at top of files
- Empty or trivial test files
- Missing error handling
- Duplicate code blocks (DRY violations)

**Remember**: Trust but verify. AI is a tool, not a decision maker.
