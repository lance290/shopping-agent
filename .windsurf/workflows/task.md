---
allowed-tools: "*"
description: Decompose the plan into verified, testable tasks
---
allowed-tools: "*"

# Guardrail-Enhanced Task Decomposition

## Step 0: Validate Prerequisites & Load Context
// turbo
**⚠️ PREREQUISITE CHECK: Have you run /plan?**

1. Check if `.cfoi/branches/[branch-name]/.current-effort` exists
   - If **MISSING**: Display error and HALT:
     ```
     ❌ NO EFFORT FOUND!
     
     You must create an effort and plan before creating tasks.
     Run: /effort-new
     Then: /plan
     
     Cannot proceed with /task without a plan.
     ```

2. Load current effort name and use `.cfoi/branches/[branch-name]/efforts/[effort-name]/`
3. Display: "📋 Creating tasks for effort: [effort-name]"

## Step 1: Load Plan Context
// turbo
1. Read the approved plan from:
   - Path: `.cfoi/branches/[branch-name]/efforts/[effort-name]/plan.md`
2. If **plan.md does not exist**: Display error and HALT:
   ```
   ❌ NO PLAN FOUND!
   
   You must run /plan before creating tasks.
   Run: /plan
   
   Cannot break down tasks without a plan to work from.
   ```
3. Confirm plan was human-approved by checking for the approval marker in `plan.md`:
   - Required: `<!-- PLAN_APPROVAL: approved by <Name> at <ISO-8601 timestamp> -->`
4. If not approved: Display warning and request approval before proceeding

## Step 2: Generate Task Breakdown
// turbo
1. Run the `/task` macro; it will:
   - Break down plan into <45 minute tasks
   - For EACH task, specify:
     * **E2E flow to build** (Click-First approach)
     * **Manual verification steps** (how human will test it)
     * Files to create/modify
     * **Tests to write AFTER** (to lock in working behavior)
     * Dependencies on other tasks
     * Error budget allocation (max 3 errors)
     * **Evidence requirements**:
       - Manual artifact to capture (screenshot/log/demo URL) with target path `.cfoi/branches/[branch-name]/proof/[task-id]/manual.md`
       - Automated proof (test suite name, coverage target delta)
       - Human owner responsible for sign-off

2. **Save tasks in BOTH formats** (effort-specific path):
   - Base path: `.cfoi/branches/[branch-name]/efforts/[effort-name]/`

   **a) `tasks.md`** - Human-readable format for review
   
   **b) `tasks.json`** - Machine-readable format (less likely to be corrupted):
   ```json
   {
     "version": 1,
     "effort": "[effort-name]",
     "created": "[ISO timestamp]",
     "tasks": [
       {
         "id": "task-001",
         "description": "User can create account with email",
         "e2e_flow": "Navigate to /signup, fill form, submit, see success",
         "manual_verification": [
           "Open http://localhost:3000/signup",
           "Enter test@example.com and password",
           "Click Submit",
           "Verify redirect to dashboard"
         ],
         "files": ["src/pages/signup.tsx", "src/api/auth.ts"],
         "tests_to_write": ["signup.test.ts"],
         "dependencies": [],
         "estimated_minutes": 30,
         "error_budget": 3,
         "status": "pending",
         "proof_path": ".cfoi/branches/[branch-name]/proof/task-001/"
       }
     ]
   }
   ```

   **⚠️ TASK LIST PROTECTION RULES:**
   - Tasks in `tasks.json` may ONLY have their `status` field changed
   - Never delete, reorder, or modify task descriptions after approval
   - If a task is wrong, flag it in PROGRESS.md for human review
   - Use strongly-worded instruction: "It is unacceptable to remove or edit tasks"

## Step 3: Task Quality Verification
// turbo
1. Verify each task includes:
   - ✅ Clear E2E flow ("user can click X and see Y")
   - ✅ Manual test steps (how human verifies it works)
   - ✅ Specific files to change (not vague)
   - ✅ Success criteria (what "working" looks like)
   - ✅ Estimated time <45 minutes
   - ✅ Error handling requirements
   - ✅ Test requirements (to write AFTER feature works)
    - ✅ Evidence artifacts with destination paths in `.cfoi/branches/[branch-name]/proof/`
    - ✅ Named human approver for sign-off
2. Flag any tasks that are too vague or too large

## Step 4: ⚠️ HUMAN CHECKPOINT - Task Review (REQUIRED)
1. Review the task breakdown at effort-specific path
2. Verify:
   - Each task is <45 minutes
   - E2E flows are clear and testable
   - Manual verification steps make sense
   - Task order makes sense
   - No "implement everything" mega-tasks
   - Error budget is reasonable
3. **DECISION**: Approve, revise, or re-plan
   - If approved → Proceed to step 5
   - If revisions needed → Adjust specific tasks
   - If major issues → Return to `/plan`

## Step 5: Initialize Task Tracking
// turbo
1. Add task tracking to `metrics.json`:
   ```json
   {
     "tasks": {
       "total": 8,
       "completed": 0,
       "inProgress": 0,
     },
     "currentTask": null,
     "errorBudget": {
       "perTask": 3,
       "currentTaskErrors": 0
     },
     "evidence": {}
   }
   ```

2. **Update `PROGRESS.md`** (in the effort directory) with task summary and session entry:
   - Path: `.cfoi/branches/[branch-name]/efforts/[effort-name]/PROGRESS.md`
   ```markdown
   ## Current State
   - **Status**: 🟢 Ready for Implementation
   - **Current task**: task-001 (pending)
   - **Last working commit**: [current HEAD]
   - **App status**: Not started
   
   ## Task Summary
   | ID | Description | Status |
   |---
allowed-tools: "*"-|-------------|--------|
   | task-001 | [description] | ⬜ pending |
   | task-002 | [description] | ⬜ pending |
   ...
   
   ## Session History
   ### [YYYY-MM-DD HH:MM] - Session N (Task Breakdown)
   - Decomposed plan into [X] tasks
   - Estimated total time: ~[X * 45] minutes
   - Next: Run /implement to start task-001
   ```

3. Update effort status in `effort.json` to "in-progress"
4. For each task, create stub checklist at:
   - Path: `.cfoi/branches/[branch-name]/proof/[task-id]/acceptance.md`
   ```markdown
   # Task [task-id] Acceptance Proof

   ## Manual Evidence
   - [ ] Click-test performed by: ______
   - [ ] Artifact stored at: .cfoi/branches/[branch-name]/proof/[task-id]/manual.md

   ## Automated Evidence
   - [ ] Tests run (command): ______
   - [ ] Coverage summary captured (>= target %)

   ## Human Sign-Off
   - Owner: ______
   - [ ] Approved (name / timestamp)
   ```

## Step 6: Ready for Implementation ✅

**🎉 Tasks Approved and Ready!**

```
✅ Tasks: [X] tasks defined
✅ Task 1: Ready to implement
✅ Proof tracking: Initialized

📍 YOU ARE HERE: effort-new → plan → task → [implement] → implement → implement...
```

**🚦 NEXT STEP (Required):**
```
/implement
```

**What happens next:**
1. AI will build task 1 (make it work end-to-end)
2. **YOU must click-test it** to verify it works
3. AI will write tests to lock in the working behavior
4. Commit and save the working state

**After task 1 completes:**
- Run `/implement` again for task 2
- Repeat `/implement` until all [X] tasks are complete
- You'll see a completion message when done

**⚠️ Important:** Each `/implement` takes ~45 minutes. Take breaks between tasks!

---
allowed-tools: "*"

---
allowed-tools: "*"

**Key Changes from Old Workflow**:
- ✅ E2E flows specified for each task (Click-First)
- ✅ Manual verification steps defined upfront
- ✅ Test requirements (to write AFTER feature works)
- ✅ **MANDATORY human review** checkpoint
- ✅ Error budget per task
- ✅ Branch-specific directory structure
- ✅ Task tracking in metrics.json
