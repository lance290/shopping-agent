---
allowed-tools: "*"
description: Save working state with tests passing
---
allowed-tools: "*"

# Checkpoint Workflow

**Purpose**: Commit working code and create rollback point.

## When to Use

- **After each task** - Create rollback points every 45 minutes
- **After major feature** - Lock in working state
- **Before risky changes** - Safe point to return to
- **End of session** - Save progress for next time

## Step 1: Verify Tests Pass
// turbo
1. Run full test suite:
   ```bash
   npm run test:all
   ```
2. **CRITICAL**: All tests must pass
3. If any test fails:
   - **Stop immediately**
   - Fix failing tests
   - Do NOT proceed until green
4. Cannot checkpoint broken code

## Step 2: Run Verification Script
// turbo
1. Run quality checks:
   ```bash
   ./tools/verify-implementation.sh
   ```
2. Must pass checks for:
   - No TODOs/FIXMEs
   - No placeholders
   - Imports at top
   - Meaningful tests
   - Error handling
3. If fails → Fix issues first

## Step 3: Review Changes
1. Show diff:
   ```bash
   git diff
   ```
2. Verify changes are:
   - Complete (no half-done work)
   - Correct (matches plan)
   - Clean (no debug code)

## Step 4: ⚠️ HUMAN CHECKPOINT - Quick Review
1. Quick verification:
   - Does the feature work? (you already click-tested it)
   - Are tests passing?
   - Any obvious issues?
2. **DECISION**: Commit or fix
   - ✅ Looks good → Proceed
   - ❌ Issues → Fix first

## Step 5: Commit Working Code
// turbo
1. Stage all changes:
   ```bash
   git add .
   ```

2. Commit with descriptive message:
   ```bash
   git commit -m "feat(task-X): [clear description]"
   ```
   
   Examples:
   - `feat(task-1): add user authentication UI`
   - `feat(task-2): implement login API endpoint`
   - `fix(task-3): handle invalid credentials`

3. Commit message should:
   - Reference task number
   - Describe what was added/changed
   - Be clear enough for code review

## Step 6: Update Tracking
// turbo
1. Mark task complete in `tasks.md`:
   ```markdown
   - [x] Task 1: User login UI
   - [x] Task 2: Login API
   - [x] Task 3: Error handling
   - [ ] Task 4: Next task...
   ```

2. Update PROGRESS.md:
   ```markdown
   ## Latest Checkpoint - [timestamp]
   
   Completed Task 3: Error handling
   - Commit: abc1234
   - Tests: All passing
   - Manual test: ✅ Works correctly
   
   Next: Task 4 - Password reset flow
   ```

3. Update metrics.json:
   ```json
   {
     "tasks": {
       "completed": 3,
       "inProgress": 0,
       "remaining": 5
     },
     "lastCheckpoint": {
       "timestamp": "2024-10-05T15:45:00Z",
       "commit": "abc1234",
       "taskId": "task-3"
     },
     "errorBudget": {
       "currentTaskErrors": 0  // Reset for next task
     }
   }
   ```

## Step 7: Consider Pushing
// turbo
1. Check commit count since last push
2. If ≥3 commits → Consider pushing:
   ```bash
   git push origin [branch-name]
   ```
3. Benefits of pushing:
   - Remote backup
   - Can't lose work
   - Others can see progress
   - Triggers CI/CD checks

## Step 8: Reset for Next Task
// turbo
1. Error budget reset to 0/3
2. Ready for next task
3. If >30 min since compaction → Suggest `/compact`

## Step 9: Confirm Checkpoint
1. Display confirmation:
   ```
   ✅ Checkpoint Complete
   
   Committed: feat(task-3): error handling
   SHA: abc1234
   
   📊 Progress:
   - Tasks: 3/8 complete
   - Tests: All passing ✅
   - Last error budget: 1/3 used
   
   🎯 Next: Task 4 - Password reset flow
   
   💾 Rollback point created
   ```

---
allowed-tools: "*"

## Emergency Rollback

If next task goes wrong, rollback to last checkpoint:

```bash
# See recent commits
git log --oneline -5

# Rollback to last checkpoint
git reset --hard HEAD~1

# Or rollback to specific commit
git reset --hard abc1234
```

---
allowed-tools: "*"

## Benefits

- ✅ Working code always committed
- ✅ Can rollback to any checkpoint
- ✅ Never lose more than 45 min of work
- ✅ Clear progress tracking
- ✅ Tests always passing at checkpoints
- ✅ Reduces fear of experimentation

---
allowed-tools: "*"

## Checkpoint vs [checkpoint] Commit

**Regular Checkpoint** (this workflow):
- Tests must pass
- Code must be complete
- Quality checks pass
- Creates safe rollback point

**[checkpoint] Commit** (emergency WIP):
- Used for work-in-progress
- Tests may fail
- Bypasses quality checks
- Only when explicitly needed
- Still requires human approval
