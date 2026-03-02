# Green Baseline Enforcement - Zero Tolerance for Failing Tests

## The Problem You Experienced

**Scenario**: Got halfway through a project, 42 failing tests suddenly discovered from tasks days ago.

**Root cause**: Framework didn't enforce "all tests pass" before starting new work.

**Result**: Compounding failures across multiple tasks, impossible to isolate new bugs from old ones.

---

## The Fix: ⛔ Mandatory Test Verification (4 Critical Gates)

### Gate 1: `/plan` - Cannot Plan on Broken Codebase

**Before**: No test verification before planning  
**After**: Step 0 blocks if ANY tests fail

```
⛔ PRE-PLANNING TEST VERIFICATION REQUIRED

Before creating a plan, verify ALL tests pass:
  npm run test:all

Expected: ✅ ALL TESTS PASS (0 failures)

If ANY tests fail:
  ❌ STOP - Cannot plan on broken codebase
  → Fix ALL failing tests first
  → Or run /checkpoint to rollback

⛔ THIS IS A BLOCKER - DO NOT PROCEED IF TESTS FAIL
```

**Enforcement**: Agent MUST wait for human confirmation before proceeding.

---

### Gate 2: `/implement` - Cannot Start Task on Broken Codebase

**Before**: Suggested running tests, but allowed proceeding if ignored  
**After**: Step 1 blocks if ANY tests fail

```
⛔ MANDATORY PRE-TASK TEST VERIFICATION

Before implementing this task, verify ALL tests pass:
  npm run test:all

Expected: ✅ ALL TESTS PASS (0 failures)

If ANY tests fail:
  ❌ STOP - Cannot start task on broken codebase
  → Fix ALL failing tests first
  → Or run /checkpoint to rollback

Why this matters:
  - Can't distinguish new bugs from old ones
  - Compounds problems across tasks
  - Breaks rollback ability

⛔ THIS IS A BLOCKER - DO NOT PROCEED IF TESTS FAIL
```

**Enforcement**: Agent MUST wait for human confirmation before proceeding.

---

### Gate 3: `/checkpoint` - Cannot Create Rollback Point with Failing Tests

**Before**: Warning but not blocking  
**After**: Step 1 blocks if ANY tests fail

```
⛔ MANDATORY CHECKPOINT TEST VERIFICATION

Before creating checkpoint, verify ALL tests pass:
  npm run test:all

Expected: ✅ ALL TESTS PASS (0 failures)

If ANY tests fail:
  ❌ STOP - Cannot checkpoint broken code
  → Fix ALL failing tests first
  → Or rollback to last working commit

Why this matters:
  - Checkpoints are rollback points
  - Cannot rollback to broken state
  - Must maintain "always green" history

⛔ THIS IS A BLOCKER - DO NOT PROCEED IF TESTS FAIL
```

**Enforcement**: Agent MUST wait for human confirmation before proceeding.

---

### Gate 4: Constitution - "Green Baseline Rule"

**Added to Guardrails section**:

```markdown
⛔ GREEN BASELINE RULE: ALL tests must pass before starting ANY new work 
   (planning, tasks, checkpoints). No exceptions. This is a BLOCKER.
```

**Added to REQUIRED When Implementing**:
- ✅ **Verify ALL tests pass BEFORE starting** (green baseline - mandatory and blocking)
- ✅ **Run ALL tests AFTER implementation** (must pass before commit)

**Added to FORBIDDEN Behaviors**:
- ❌ **Starting ANY work with failing tests** (green baseline violation - blocker)
- ❌ **Proceeding past test verification without human confirmation** (cannot be bypassed)
- ❌ **Committing code with failing tests** (breaks rollback ability)

---

## Why This Matters

### Before (Weak Enforcement)

```
Day 1: Task 1 → 2 tests fail (ignored, kept going)
Day 2: Task 2 → 5 tests fail (includes Day 1 failures + new ones)
Day 3: Task 3 → 12 tests fail (compounding)
Day 4: Task 4 → 42 tests fail (impossible to debug)

Result: Can't distinguish new bugs from old, can't rollback cleanly
```

### After (Zero Tolerance)

```
Day 1: Task 1 → 2 tests fail → STOP → Fix both → All tests pass ✅ → Proceed
Day 2: Task 2 → Try to start → Test 1 fails → STOP → Fix → All pass ✅ → Proceed
Day 3: Task 3 → Try to start → All tests pass ✅ → Proceed → New test fails → Fix → All pass ✅
Day 4: Task 4 → Try to start → All tests pass ✅ → Proceed → Clean, green baseline maintained

Result: Always know exactly what broke, can rollback to any commit safely
```

---

## The Enforcement Chain

### 1. At Planning (`/plan`)
```
Human: /plan
Agent: ⛔ Run tests first!
Human: npm run test:all → 3 failures
Agent: ❌ STOP - Fix those 3 tests before I create a plan
Human: (fixes tests) → all pass
Agent: ✅ OK, now I'll create the plan
```

### 2. At Each Task (`/implement`)
```
Human: /implement
Agent: ⛔ Run tests first!
Human: npm run test:all → 1 failure (from yesterday)
Agent: ❌ STOP - Fix that 1 test before starting new work
Human: (fixes test) → all pass
Agent: ✅ OK, now I'll implement this task
```

### 3. At Checkpoint (`/checkpoint`)
```
Human: /checkpoint
Agent: ⛔ Run tests first!
Human: npm run test:all → 2 failures (introduced this task)
Agent: ❌ STOP - Cannot checkpoint with failing tests
Human: (fixes tests) → all pass
Agent: ✅ OK, creating checkpoint/rollback point
```

### 4. At Constitution Check
```
Agent: (about to implement)
Agent: (checks constitution)
Agent: ⛔ GREEN BASELINE RULE says I must verify tests
Agent: (displays test verification message)
Agent: (WAITS for human confirmation)
```

---

## Implementation Details

### `/plan` Changes
- **Line 39-70**: Added Step 0 before exploration
- **Blocker**: Cannot proceed to Step 1 (exploration) until tests pass
- **Message**: Clear "⛔ BLOCKER" language

### `/implement` Changes
- **Line 323-363**: Changed Step 1 to mandatory verification
- **Blocker**: Cannot proceed to Step 2 (commit/push) until tests pass
- **Message**: Explains why it matters (can't distinguish bugs)

### `/checkpoint` Changes
- **Line 782-817**: Changed Step 1 to mandatory verification
- **Blocker**: Cannot proceed to Step 2 (verification script) until tests pass
- **Message**: Explains checkpoints are rollback points

### Constitution Changes
- **Line 21**: Added ⛔ GREEN BASELINE RULE to Guardrails
- **Line 34**: Added test verification to REQUIRED list
- **Line 39**: Added test verification AFTER implementation
- **Line 47-48**: Added test verification to FORBIDDEN list
- **Line 57**: Added committing failing tests to FORBIDDEN list

---

## How to Use This

### Starting a New Plan
```bash
# Step 1: Run tests FIRST
npm run test:all

# If tests fail:
#   → Fix them or rollback
#   → Do NOT proceed to /plan

# If tests pass:
#   → Run /plan
#   → Agent will still verify (double-check)
```

### Starting a New Task
```bash
# Step 1: Run tests FIRST
npm run test:all

# If tests fail:
#   → This is from a previous task
#   → Fix it NOW before starting new work
#   → Do NOT proceed to /implement

# If tests pass:
#   → Run /implement
#   → Agent will still verify (double-check)
```

### Creating a Checkpoint
```bash
# Step 1: Run tests FIRST
npm run test:all

# If tests fail:
#   → Your task broke something
#   → Fix it NOW before checkpointing
#   → Do NOT proceed to /checkpoint

# If tests pass:
#   → Run /checkpoint
#   → Agent will still verify (double-check)
#   → Clean rollback point created
```

---

## Emergency Recovery

If you're already in the situation (42 failing tests):

### Option 1: Fix Forward
```bash
# 1. Document current state
echo "42 tests failing as of $(date)" >> ERRORS.md

# 2. Run tests with verbose output
npm run test:all -- --verbose > test-failures.log

# 3. Categorize failures
#    - Which task introduced each failure?
#    - Can you group similar failures?

# 4. Fix in batches
#    - Start with earliest task's failures
#    - Fix one task's failures at a time
#    - Commit after each batch passes

# 5. Once ALL pass, create checkpoint
git commit -m "fix: resolve 42 accumulated test failures"
/checkpoint
```

### Option 2: Rollback to Last Green
```bash
# 1. Find last commit where tests passed
git log --all --grep="checkpoint"

# 2. Checkout that commit
git checkout [commit-sha]

# 3. Create new branch from clean state
git checkout -b recovery-$(date +%Y%m%d)

# 4. Cherry-pick working commits
git cherry-pick [good-commit-sha]

# 5. Skip commits that introduced failures
#    (or fix them as you cherry-pick)

# 6. Once clean, resume with /implement
```

---

## Metrics to Track

### Before Enforcement
- ⏱️ **Time to discover failures**: Days (compounding)
- 🐛 **Debugging difficulty**: Impossible (can't isolate)
- 💾 **Rollback ability**: Broken (no clean points)
- 😤 **Developer frustration**: High

### After Enforcement
- ⏱️ **Time to discover failures**: Immediate (same task)
- 🐛 **Debugging difficulty**: Easy (know exactly what broke)
- 💾 **Rollback ability**: Perfect (every commit is green)
- 😊 **Developer confidence**: High

---

## Summary of Changes

| Component | Before | After |
|-----------|--------|-------|
| `/plan` | No test check | ⛔ Step 0: Mandatory verification (blocker) |
| `/implement` | Suggested | ⛔ Step 1: Mandatory verification (blocker) |
| `/checkpoint` | Warning | ⛔ Step 1: Mandatory verification (blocker) |
| Constitution | Not mentioned | ⛔ GREEN BASELINE RULE in Guardrails |
| Enforcement | Weak | **Zero tolerance** |

---

## The Core Principle

**NEVER start new work on a broken codebase.**

This isn't a suggestion. It's not optional. It's a **blocker**.

- ⛔ Cannot plan with failing tests
- ⛔ Cannot implement with failing tests  
- ⛔ Cannot checkpoint with failing tests
- ⛔ Cannot commit with failing tests

**Green baseline = deployable baseline**

Every commit should be shippable. Every checkpoint should be a safe rollback point.

**Zero tolerance. No exceptions. Always green.** ✅
