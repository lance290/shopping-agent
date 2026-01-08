---
allowed-tools: "*"
description: Dual-agent code review and verification
---
allowed-tools: "*"

# Dual-Agent Verification Workflow

**Purpose**: Independent AI agent reviews implementation to catch issues before human review.

## Step 0: Determine Effort Context
// turbo
1. Check if `.cfoi/branches/[branch-name]/.current-effort` exists
2. If exists: Load current effort name and use `.cfoi/branches/[branch-name]/efforts/[effort-name]/`
3. If not exists: Use legacy path `.cfoi/branches/[branch-name]/` (backward compatible)
4. Display: "🔍 Verifying task for effort: [effort-name]"

## Step 1: Load Context & Evidence Bundle
// turbo
1. Read the plan from effort-specific path (determined in Step 0)
2. Read the current task from effort-specific `tasks.md`
3. Read implementation notes from effort-specific `implement-[task-id].md`
4. Identify files that were changed (from implementation notes)
5. Load proof artifacts from effort-specific `proof/[task-id]/`:
   - `build-log.md`
   - `manual.md`
   - `automation.md`
   - `acceptance.md`

## Step 2: Review Implementation
// turbo
1. Read each changed file
2. Verify against plan requirements:
   - ✅ Does code solve the problem in the plan?
   - ✅ Are test requirements met?
   - ✅ Is success criteria achieved?
3. Check constitution compliance:
   - ✅ Routes/controllers/repositories pattern followed?
   - ✅ No duplicate code?
   - ✅ Files under 450 lines?
   - ✅ Pure functions preferred?
   - ✅ Co-location principles followed?
4. Identify anti-patterns:
   - ❌ TODOs or FIXMEs?
   - ❌ Placeholder implementations?
   - ❌ Missing error handling?
   - ❌ Hardcoded values that should be config?
   - ❌ Direct database calls outside repositories?
   - ❌ Imports scattered throughout file?

## Step 3: Test & Coverage Analysis
// turbo
1. Read test files
2. Verify tests are meaningful:
   - ✅ Tests actually assert something?
   - ✅ Cover happy path?
   - ✅ Cover error cases?
   - ✅ Cover edge cases?
   - ❌ Tests are trivial or just imports?
3. Parse `automation.md` to confirm:
   - Test command matches repo expectations
   - Test log path exists
   - Coverage summary path exists and matches `coverage/latest-summary.json`
   - No coverage regressions recorded (if `coverage-regressions.json` exists, flag)
4. Cross-check effort-specific `coverage/` and `test-results/` directories for latest artifacts referenced in `automation.md`

## Step 4: Validate Manual Evidence
// turbo
1. Review `manual.md` for human click-test notes, timestamp, and approver name
2. Ensure acceptance checklist at `acceptance.md` has required boxes filled (manual evidence, automation proofs, human sign-off)
3. If any checklist items unchecked → mark as HIGH severity issue

## Step 5: Generate Review Report
// turbo
1. Create review report with:
   ```markdown
   # Code Review - Task [task-id]
   
   ## Summary
   - Overall Assessment: [APPROVE / REQUEST_CHANGES / REJECT]
   - Code Quality: [HIGH / MEDIUM / LOW]
   - Test Coverage: [GOOD / ADEQUATE / INSUFFICIENT]
   - Constitution Compliance: [X/10]
   
   ## Strengths
   - [What was done well]
   
   ## Issues Found
   - **[HIGH/MEDIUM/LOW]**: [Issue description]
     - Location: [file:line]
     - Recommendation: [How to fix]
   
   ## Plan Alignment
   - [x] Solves problem from plan
   - [x] Meets acceptance criteria
   - [ ] Missing: [what's missing]
   
   ## Test Quality
   - [x] Tests are meaningful
   - [x] Happy path covered
   - [ ] Missing: [what tests are missing]
   
   ## Constitution Compliance
   - [x] Routes/controllers pattern
   - [x] No code duplication
   - [ ] Violation: [what's wrong]
   
   ## Recommendation
   [APPROVE and proceed] OR [REQUEST_CHANGES: list changes needed]
   ```

2. Save report to effort-specific `review-[task-id].md`

## Step 6: Check for Blockers
// turbo
1. If HIGH severity issues found:
   - Mark as REQUEST_CHANGES
   - Stop implementation pipeline
   - Require fixes before proceeding
2. If MEDIUM severity issues:
   - Mark as REQUEST_CHANGES
   - List as recommended fixes
3. If only LOW severity:
   - Mark as APPROVE with suggestions

## Step 7: Report to Human
1. Display summary in chat:
   ```
   🔍 Code Review Complete
   
   Assessment: [APPROVE / REQUEST_CHANGES / REJECT]
   Issues: [count] high, [count] medium, [count] low
   
   Full report: [effort-specific]/review-[task-id].md
   ```

2. If REQUEST_CHANGES:
   - List top 3 issues to fix
   - Suggest running `/fix-review` to address issues

## Step 8: Update Metrics & Evidence Status
// turbo
1. Add review outcome to metrics.json:
   ```json
   {
     "reviews": [
       {
         "taskId": "task-1",
         "timestamp": "2024-10-05T15:30:00Z",
         "outcome": "APPROVE",
         "issuesFound": 2,
         "severity": "LOW"
       }
     ]
   }
   ```
2. Append entry to `metrics.json` under `evidence.manual[task-id]` noting reviewer outcome and whether manual proof validated
3. If coverage regressions flagged, ensure they are referenced in the review report and metrics

---
allowed-tools: "*"

## When to Use

- **After every `/implement`** - Catch issues early
- **Before human review** - Save human time
- **When stuck** - Fresh eyes might spot the problem
- **Before commits** - Extra safety net

---
allowed-tools: "*"

**Benefits**:
- ✅ Fresh perspective catches mistakes
- ✅ Prevents single-agent drift
- ✅ Catches constitution violations
- ✅ Verifies test quality
- ✅ Reduces human review burden

---
allowed-tools: "*"

## Before Merge Checklist

Before merging this effort, ensure:
- ✅ All tasks completed and verified
- ✅ Tests passing (green baseline)
- ✅ Code review approved
- ✅ **Review NOTES.md** - Address or defer technical debt
- ✅ **Convert ideas to tasks** - Don't lose good ideas
- ✅ Constitution compliance verified

**📝 Check your notes**: `.cfoi/branches/[branch]/efforts/[effort]/NOTES.md`  
Any unresolved items? Address them or create follow-up tasks.
