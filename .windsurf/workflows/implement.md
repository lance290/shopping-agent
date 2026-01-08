---
allowed-tools: "*"
description: Execute a single task via the implement macro with verification
---
allowed-tools: "*"

# Click-First CFOI Implementation Workflow

**THE WORKFLOW**: Run tests → Commit → Build → Click-test → Tests → Repeat

> **🚀 AUTONOMOUS MODE**: This workflow runs Steps 0-4 automatically without stopping.
> The ONLY pause point is Step 5 (Click-Test) where human verification is required.
> After click-test approval, Steps 6 and Wrap Up also run automatically.

**🚀 TURBO MODE RULE (NON-NEGOTIABLE)**

Turbo mode may ONLY waive the human pause at Step 5 **when the human explicitly approves waiving the click-test**.
Turbo mode does NOT allow skipping any automated verification.
Automated tests/verification (Step 1 + Step 6 + Step 7) are always required, and the agent must record a command + log/output artifact before proceeding.

## Step 0: Validate Prerequisites & Load Context
// turbo
**⚠️ PREREQUISITE CHECK** (runs automatically)

1. Check `.cfoi/branches/[branch-name]/.current-effort` exists
   - If **MISSING**: Display error and HALT:
     ```
     ❌ NO EFFORT FOUND!
     
     You must complete the full workflow before implementing:
     1. /effort-new  (create effort)
     2. /plan        (create plan)
     3. /task        (break into tasks)
     4. /implement   (you are here)
     
     Cannot proceed without tasks to implement.
     ```

2. Load current effort name and use `.cfoi/branches/[branch-name]/efforts/[effort-name]/`

3. Check if `tasks.json` exists (preferred) or `tasks.md` (fallback)
   - If **BOTH MISSING**: Display error and HALT:
     ```
     ❌ NO TASKS FOUND!
     
     You must run /task before implementing.
     Run: /task
     
     Cannot implement without a task breakdown.
     ```

4. Load tasks from `tasks.json` (preferred) and determine which task to implement:
   - Find first task with `"status": "pending"`
   - If all tasks complete: Display completion message (see Wrap Up section)
   - Display: "🔨 Implementing [task-id]: [task-name]"

5. Resolve product north star path:
   - Primary: `.cfoi/branches/[branch-name]/efforts/[effort-name]/product-north-star.md`
   - Fallback: `.cfoi/branches/[branch-name]/product-north-star.md`
   - If neither exists, halt and request the human to author the north star before continuing

6. Display: "📍 North star loaded from: [path]" and cache the path for downstream steps

## Step 0B: Session Boot Sequence (Anthropic-Inspired)
// turbo
**Get bearings before starting work** - Critical for multi-session projects

1. **Orient**: Run `pwd` to confirm working directory

2. **Load context from PROGRESS.md**:
   ```bash
   cat .cfoi/branches/[branch-name]/efforts/[effort-name]/PROGRESS.md
   ```
   - Check "Current State" section
   - Note "Last working commit" (rollback point if needed)
   - Review recent session history

3. **Check git history**:
   ```bash
   git log --oneline -10
   ```
   - Understand what was recently changed
   - Identify last known-good commit

4. **Start development environment** (if not already running):
   - Check if dev server is already running (curl health endpoint)
   - If not running, prompt human: "Dev server not detected. Please start it."
   - If `init.sh` exists (optional), offer: "Run `./init.sh` to start automatically?"

5. **🚨 CRITICAL: Smoke test EXISTING functionality FIRST**:
   - If app should be running, verify it starts
   - Test basic functionality (health check, login, etc.)
   - **If app is BROKEN**: Fix it BEFORE starting new feature
   - Don't start new work on a broken foundation
   
   ```
   ⚠️ SMOKE TEST RESULTS:
   - App starts: [✅ Yes / ❌ No - FIX FIRST]
   - Health check: [✅ Pass / ❌ Fail - FIX FIRST]
   - Basic flow works: [✅ Pass / ❌ Fail - FIX FIRST]
   ```

6. **Display session start summary**:
   ```
   📍 SESSION BOOT COMPLETE
   
   Working directory: [pwd]
   Effort: [effort-name]
   Current task: [task-id] - [description]
   Last commit: [hash] - [message]
   App status: [✅ Running / ⚠️ Not started / ❌ Broken]
   
   Ready to implement [task-id]
   ```

## Step 1: Verify Green Baseline (auto-continues)
// turbo
Run automated verification to confirm a green baseline before making changes.

**Preferred**: run the repo-standard verification command:

```bash
./tools/verify-implementation.sh
```

If that script does not exist in this repo, run your project's test command for the relevant service/workspace:

```bash
# Examples (pick the one that matches your stack or customize):

# Node.js / frontend
npm run test:all

# Go
go test ./...

# Rust
cargo test

# Python
pytest

# C++ (CMake/CTest)
cmake -S . -B build && cd build && ctest --output-on-failure
```

Log the command and output/log path in effort-specific `proof/[task-id]/tests.md`.

**NON-NEGOTIABLE**: Do not proceed to Step 2 unless you actually ran automated verification and captured evidence.
If tests fail, fix them before continuing.

> **Note:** Your git hooks are multi-language and monorepo-aware. Pre-push hooks will automatically run the right build/test commands for all detected project types (Node.js, Go, Rust, Python, C/C++/CMake, Makefile) across the repo.

## Step 2: Alignment Check (auto-continues)
// turbo
1. Load and review north star context:
   - Read `product-north-star.md` (product or effort-level)
   - Review task requirements from `tasks.md`
   - Identify relevant acceptance criteria and metrics

2. Verify conceptual alignment:
   - Does this task support north star goals?
   - Are acceptance criteria clear and measurable?
   - Are there any scope concerns or risks?

3. Document alignment reasoning in `proof/[task-id]/alignment.md`:
   ```markdown
   # Alignment Check - [task-id]
   
   ## North Star Goals Supported
   - [Reference specific north star section]
   - [Metric or checkpoint this moves]
   
   ## Task Scope Validation
   - In scope: [What we're implementing]
   - Out of scope: [What we're explicitly not doing]
   
   ## Acceptance Criteria
   - [ ] [Criterion 1]
   - [ ] [Criterion 2]
   
   ## Approved by: [Your initials]
   ## Date: [YYYY-MM-DD]
   ```

4. **Complexity Assessment** (informational only, do not stop):
   - If task involves **5+ files, cross-cutting concerns, or architectural changes**:
     - Note: "ℹ️ Complex task detected. Consider `/claude-flow-swarm` if you get stuck."
   - Continue with implementation regardless

## Step 3: Commit & Push Previous Work (auto-continues)
// turbo
If you have uncommitted changes from the last task:
```bash
git add .
git commit -m "feat: [previous task description]"
git push
```

Log result and **continue immediately to Step 4** (do not wait for user).

## Step 4: Build the Experience (auto-continues)
// turbo
Agent will:
1. Quote the exact task from effort-specific `tasks.md` (determined in Step 0)
2. **Build the UI/API/feature so it works end to end**, following:
   - Follow `.windsurf/constitution.md`
   - No TODO/FIXME comments
   - No placeholder implementations
   - Include error handling
   - Keep files < 450 lines
   - **Extract reusable functions** when logic appears 3+ times (DRY principle)
   - Prefer small, composable functions over large monolithic ones
   - Diagnose underlying causes before patching symptoms (log root-cause notes in `proof/[task-id]/build-log.md`)
3. Apply code changes
4. Summarize what changed
5. Update effort-specific `proof/[task-id]/build-log.md` with files touched, manual test instructions, and any setup commands
6. Explicitly document how the change advances the product north star, citing the cached path in `proof/[task-id]/build-log.md`, and show the root issue being addressed

**CFOI Principle**: Build working experience before writing tests

**DRY Reminder**: Before moving to Step 5, scan your changes for duplicate code:
- If you see the same logic 3+ times → extract a reusable function
- If functions are >100 lines → break into smaller, composable pieces
- If you copy-pasted code → refactor into shared utilities

## Step 5: Human Click-Test ⛔ STOP HERE
<!-- NO turbo annotation - this is the ONLY step that requires human interaction -->

**⛔ MANDATORY STOP** - Agent MUST display a **specific, actionable** click-test prompt:

```
👆 CLICK-TEST: [task-id] - [task name]

📋 WHAT TO TEST:
[List the SPECIFIC actions the user should take, e.g.:]
1. Run: npm run dev
2. Open http://localhost:3000/[specific-page]
3. Click [specific button] 
4. Enter [specific test data]
5. Verify [specific expected result]

🎯 EXPECTED BEHAVIOR:
- [Concrete outcome 1]
- [Concrete outcome 2]

⚠️ WATCH FOR:
- [Potential issue to check]
- [Edge case to verify]

Does it work?
- ✅ "yes" or "works" → I'll write tests
- ❌ "no [what's wrong]" → I'll fix it
- 🚀 "turbo: waive click-test" → I'll skip the pause and proceed to automated tests (Step 6) anyway
```

**CRITICAL**: The agent MUST fill in the specific details above based on:
- The task being implemented
- Files that were changed
- The `build-log.md` manual test instructions written in Step 4
- The acceptance criteria from `tasks.md`

**DO NOT** give generic instructions like "test the feature" or "verify it works".
**DO** give exact commands, URLs, clicks, inputs, and expected outputs.

**Human must click-test and confirm it works.** Log the outcome in effort-specific `proof/[task-id]/manual.md` with timestamp and approver.
If the human explicitly waives the click-test (turbo), log that waiver in `proof/[task-id]/manual.md` with timestamp and approver.
Include explicit confirmation that the observed behavior matches the product north star checkpoints and that the observed symptoms tie back to the diagnosed root cause, referencing the same `product-north-star.md` path.

## Step 5b: Commit Working Build (auto-continues after ✅)
// turbo
**After click-test approval**, immediately commit the working build:
```bash
git add .
git commit -m "feat([task-id]): [task description] - click-tested ✅"
```
This preserves the working state before adding tests. If tests cause issues, you can always revert to this commit.

## Step 6: Lock It In With Tests (auto-continues)
// turbo
**Only after a ✅ confirmation from Step 5**, agent writes tests:
- Unit tests for business logic / pure functions
- Integration tests for data flows
- E2E tests for the flow that was just click-tested
- Key error paths and edge cases

Then run `./tools/verify-implementation.sh` and copy test/coverage summary paths into:
```markdown
[effort-specific]/proof/[task-id]/automation.md
- Tests command: <cmd>
- Test log: <path>
- Coverage command: <cmd>
- Coverage summary: <path>
- Coverage regressions: <path or "none">
- North star reference: <resolved product-north-star.md path>
- Root cause closed: <explain how tests prove the underlying issue is resolved>
- Trust alignment score / notes: <summary from verification>
```

**NON-NEGOTIABLE**: Do not claim tests passed without an output artifact (log path or pasted summary).

If verification reveals drift from the product north star, treat it as a failure, address gaps, and rerun this step.

**CFOI Principle**: Tests capture proven-working behavior, not theoretical behavior

## Step 7: Quick Review Gate ⛔ BLOCKS IF ISSUES
// turbo

**Before marking task complete**, run a focused review on files changed in THIS task only.

### 7.1: Type & Signature Check
```bash
# Run TypeScript check (if tsconfig.json exists)
npx tsc --noEmit 2>&1 | head -50
```
**BLOCK if any errors.** These catch:
- Variables that should be set but aren't
- Function calls out of sync with signatures
- Missing imports
- Type mismatches

### 7.2: Cross-File DRY Scan ⛔ BLOCKS
**This is not optional. DRY violations BLOCK task completion.**

#### 7.2.1: Scan Files Changed in This Effort
Get the list of ALL files changed in this effort (not just this task):
```bash
# Files changed in this effort
git diff main...HEAD --name-only | grep -E '\.(ts|tsx|js|jsx|py|go|rs)$'
```

#### 7.2.2: For Each New/Modified Function in This Task
Ask these questions:

1. **Does similar logic exist in another file in this effort?**
   - Search for similar function names, patterns, or logic
   - If yes → Extract to shared utility NOW

2. **Does this duplicate something from a previous task?**
   - Review the functions/components added in earlier tasks
   - If yes → Refactor to reuse, not duplicate

3. **Are we building something that already exists in the codebase?**
   - Search project for similar utilities, helpers, hooks
   - If yes → Use existing, don't reinvent

4. **Is this pattern going to be needed again?**
   - If implementing for entity A, will entities B, C need the same?
   - If yes → Make it generic NOW, not "later"

#### 7.2.3: Specific Patterns to Hunt

| Pattern | How to Detect | Action |
|---
allowed-tools: "*"------|---------------|--------|
| Copy-paste functions | Same function body, different names | Extract shared utility |
| Almost-same functions | 90% identical, small variations | Parameterize the difference |
| Repeated fetch patterns | Same API call structure in multiple places | Create API client method |
| Duplicate validation | Same checks in multiple files | Create validation utility |
| Repeated transformations | Same map/filter/reduce logic | Create transform utility |
| Config duplication | Same constants in multiple files | Move to shared config |

#### 7.2.4: DRY Scan Output
```
🔍 CROSS-FILE DRY SCAN - Task [task-id]

Files in effort scope: [N]
Functions added this task: [list]

DRY Check Results:
- [ ] No similar logic in other effort files
- [ ] No duplication from previous tasks  
- [ ] No reinventing existing utilities
- [ ] Patterns made generic where needed

[If ANY unchecked]: ❌ BLOCKED - Extract/refactor before proceeding
[If ALL checked]: ✅ PASS
```

**BLOCK on DRY violations.** Do NOT proceed with duplicated code. Extract NOW.

### 7.3: Logic Sanity Check
Read through changed code and verify:
- [ ] All variables used are defined or passed in
- [ ] All function calls match their signatures (args count, types)
- [ ] No obvious logic inversions (checking wrong condition)
- [ ] Async/await used correctly (no missing awaits)
- [ ] No mutation of inputs or shared state without intent
- [ ] Error paths return/throw appropriately

### 7.4: Integration Check
- [ ] New functions are actually called from somewhere
- [ ] New components are actually rendered/used
- [ ] New API routes are actually hit by frontend
- [ ] Database schema changes have corresponding code changes

### 7.5: Observability Check (if observability configured)

**Skip if:** No observability stack configured (check `.cfoi/branches/<branch>/observability-config.json` or `bootstrap.json`)

**For new endpoints/services added in this task:**

#### 7.5.1: Health Checks
- [ ] New services have `/health` endpoint (liveness)
- [ ] New services have `/health/ready` endpoint (readiness with dependency checks)
- [ ] Health endpoints return proper status codes (200 OK, 503 unhealthy)

#### 7.5.2: Logging
- [ ] Uses structured logging (not `console.log`)
- [ ] Includes context (requestId, userId, traceId)
- [ ] Error logs include stack traces
- [ ] No sensitive data in logs (passwords, tokens, PII)

#### 7.5.3: Metrics
- [ ] New endpoints increment request counter
- [ ] New endpoints record latency histogram
- [ ] Business-critical operations have custom metrics
- [ ] Metric names follow conventions (`service_operation_unit`)

#### 7.5.4: Error Tracking
- [ ] Errors are captured to Sentry/error tracker
- [ ] Error context includes relevant metadata
- [ ] Expected errors (404, validation) are NOT sent to error tracker

#### 7.5.5: Tracing
- [ ] New external calls have spans
- [ ] Database queries are traced
- [ ] Span names are descriptive

**Observability Gate Output:**
```
🔭 OBSERVABILITY CHECK - Task [task-id]

Health Checks:  [✅ PASS / ⚠️ Missing / N/A]
Logging:        [✅ PASS / ⚠️ console.log found]
Metrics:        [✅ PASS / ⚠️ No metrics]
Error Tracking: [✅ PASS / ⚠️ Not configured]
Tracing:        [✅ PASS / ⚠️ Missing spans]

[If any ⚠️]: WARNING - Recommend adding instrumentation
[If all ✅ or N/A]: PASS
```

**Note:** Observability issues are WARNINGs, not blockers. But for production services, strongly recommend fixing before merge.

### Gate Decision
```
🚦 QUICK REVIEW GATE - Task [task-id]

Type Check:     [✅ PASS / ❌ X errors]      ← BLOCKS
DRY Check:      [✅ PASS / ❌ X violations]  ← BLOCKS (cross-file)
Logic Check:    [✅ PASS / ❌ X issues]      ← BLOCKS
Integration:    [✅ PASS / ⚠️ X orphans]    ← WARNING
Observability:  [✅ PASS / ⚠️ X gaps / N/A] ← WARNING (if configured)

[If ANY ❌]: BLOCKED - Fix before proceeding
[If only ⚠️]: WARNING - Strongly recommend fixing now
[If all ✅]: APPROVED - Continue to wrap up
```

**If BLOCKED**: Fix issues, re-run gate. Do NOT skip. This is non-negotiable.
**If WARNING**: User can say "fix" or "proceed anyway" (integration orphans only).

Log gate results to `proof/[task-id]/quick-review.md`.

## Wrap Up (auto-continues)
// turbo
**Task completion steps** (runs automatically after Step 7 passes):

1. **Update `tasks.json`**: Change task status from `"pending"` to `"passed"`
   ```json
   // ONLY change the status field - never modify other fields
   { "id": "task-001", "status": "passed", ... }
   ```
   
   **⚠️ TASK LIST PROTECTION**: It is unacceptable to remove or edit task descriptions.
   You may ONLY change the `status` field. If a task is wrong, note it in PROGRESS.md.

2. **Update `tasks.md`**: Mark current task as complete `[x]`

3. **Update `PROGRESS.md`** with session summary:
   ```markdown
   ## Current State
   - **Status**: 🟢 In Progress
   - **Current task**: [next-task-id] (pending)
   - **Last working commit**: [new commit hash]
   - **App status**: ✅ Running
   
   ## Task Summary
   | ID | Description | Status |
   |---
allowed-tools: "*"-|-------------|--------|
   | task-001 | [description] | ✅ passed |
   | task-002 | [description] | ⬜ pending |
   ...
   
   ## Session History
   ### [YYYY-MM-DD HH:MM] - Session N
   - Completed: [task-id] - [description]
   - Commit: [hash]
   - Tests: All passing
   - Notes: [any issues or observations]
   - Next: [next-task-id]
   ```

4. **Git commit** with descriptive message:
   ```bash
   git add .
   git commit -m "feat([task-id]): [task description] - verified ✅"
   ```

5. Update `metrics.json`: Increment completed count, reset error budget

6. Parse remaining tasks to determine next action

**Then display completion status:**

### If MORE tasks remain:
// turbo
```
🎉 TASK [task-id] COMPLETE!

✅ Manual proof recorded
✅ Tests passing and coverage captured
✅ North star alignment verified

📊 PROGRESS: [X] of [Y] tasks complete
📍 Next: [task-id+1]: [task-name]

🔄 AUTO-CONTINUING to next task...
```

**Immediately loop back to Step 0** and begin the next task.
The workflow only stops again at Step 5 (Click-Test) for the next task.

### If ALL tasks complete:
```
🎊 🎉 EFFORT COMPLETE! 🎉 🎊

✅ All [Y] tasks implemented
✅ All tests passing
✅ All proof artifacts captured
✅ North star alignment verified

📊 FINAL STATS:
- Tasks completed: [Y] of [Y]
- Time invested: ~[Y × 45] minutes
- Error budget used: [X] of [max]

📍 YOU ARE HERE: effort-new → plan → task → implement ✓

🚦 NEXT STEPS:

1. Run comprehensive validation:
   /validation
   (Analyzes codebase, discovers edge cases, runs all tests end-to-end)

2. Deep code review loop:
   /review-loop
   (Iterative review until code passes human-level scrutiny)

3. Quick verification:
   /verify

4. Commit and push:
   /checkpoint
   /push

5. Create PR or deploy:
   - Create pull request for review
   - Or run /deploy to ship it

🎓 What you accomplished:
[List completed tasks with brief descriptions]

Need to add more features? Start a new effort:
/effort-new
```

**💡 Quick Note?** If you discovered anything during implementation:
- Technical debt to address later
- Ideas for improvements
- Questions or blockers

Type `/notes` to capture it before you forget!

## CFOI Guardrails Enforced

- ✅ Green baseline verified before starting
- ✅ Commit/push cycle for each task
- ✅ **Build experience FIRST** (Click-First CFOI)
- ✅ **Human click-tests** before tests written (CFOI verification)
- ✅ **Tests written AFTER** click-test passes (lock in working behavior)
- ✅ No TODOs or placeholders
- ✅ Constitution compliance
- ✅ Write to files, not chat
- ✅ Proof artifacts written to effort-specific `proof/[task-id]/`
- ✅ Product north star captured upfront, validated via swarm preflight, and cited in proof artifacts
- ✅ **Quick Review Gate** blocks task completion until:
  - Type/signature errors fixed (BLOCKS)
  - **Cross-file DRY violations resolved** (BLOCKS - checks ALL effort files)
  - Logic sanity verified (BLOCKS)
  - Integration orphans addressed (WARNING)
  - **Observability gaps flagged** (WARNING - if stack configured)

**Click-First CFOI** - Prove it works by using it, THEN write tests, THEN pass review gate!
