---
allowed-tools: "*"
description: Generate the CFOI plan with error prevention guardrails
---
allowed-tools: "*"

# Guardrail-Enhanced Planning Workflow

## Step 0: Validate Prerequisites & Load Context
// turbo
**⚠️ PREREQUISITE CHECK: Have you run /effort-new?**

1. Check if `.cfoi/branches/[branch-name]/.current-effort` exists
   - If **MISSING**: Display error and HALT:
     ```
     ❌ NO EFFORT FOUND!
     
     You must create an effort before planning.
     Run: /effort-new
     
     Cannot proceed with /plan without an active effort.
     ```

2. Load current effort name and use `.cfoi/branches/[branch-name]/efforts/[effort-name]/`
3. Check if `effort.json` exists - if missing, halt with same error above
4. Display: "📋 Planning for effort: [effort-name]"

**CRITICAL: North Star Validation**

5. Check Product North Star exists:
   - Path: `.cfoi/branches/[branch-name]/product-north-star.md`
   - If missing: **HALT** and display:
     ```
     ⛔ No Product North Star found!
     
     You must establish a Product North Star before planning.
     Run: /north-star
     
     Cannot proceed with planning without strategic direction.
     ```

6. Check Effort North Star exists (if in effort mode):
   - Path: `.cfoi/branches/[branch-name]/efforts/[effort-name]/product-north-star.md`
   - If missing: **HALT** and display:
     ```
     ⛔ No Effort North Star found for: [effort-name]
     
     Effort north star should have been created during /effort-new.
     Something went wrong. Please:
     1. Review Product North Star: .cfoi/branches/[branch]/product-north-star.md
     2. Create effort north star manually or re-run /effort-new
     
     Cannot proceed with planning without effort-level strategic direction.
     ```

7. Load and display north star context:
   - Show relevant sections from Product North Star
   - Show effort north star goal statement and acceptance checkpoints
   - Confirm: "✅ North stars validated. Proceeding with planning aligned to strategic goals."

**CRITICAL: Definition of Done (DoD) Validation**

8. Check DoD exists and is **active** in `effort.json.definition_of_done`
   - If missing or not `active`: **HALT** and display:
     ```
     ⛔ No Definition of Done found for: [effort-name]
     
     DoD must be captured during /effort-new (Step 4.5).
     Ensure thresholds + signals are filled and status is active, then re-run /plan.
     ```
9. Display current DoD summary (version, status, thresholds, signals, confidence, approval)
10. If user requests a change during planning:
    - Require `change_reason`, `change_type` (tighten|loosen|clarify), `changed_by`, `timestamp`
    - **Loosening** requires explicit approval (owner/admin) before proceeding
    - Bump `definition_of_done.version` and keep `status=active`
    - Append revision note to `PROGRESS.md` DoD section
11. Reminder: **Thresholds are binary gates**; **signals are weighted** toward the north star. All thresholds must pass; signals roll up to `north_star_score` only if thresholds pass.

## Step 1: CLARIFY (Gather Requirements)
// turbo
**CRITICAL: Always ask clarifying questions BEFORE planning**

1. **Assess Confidence**: Evaluate if you have enough information (0-100%)
2. **If confidence < 80%, ask AT LEAST 3 clarifying questions**:

   **Essential Questions (Always Ask)**:
   - **Problem & Users**: What specific problem are we solving? Who are the primary users?
   - **Business Context**: What business goals does this support? What metrics define success?
   - **Scope & Constraints**: What's in scope? What's explicitly out of scope? Technical constraints?

   **Additional Questions (When Relevant)**:
   - What similar features exist in the codebase?
   - What's the timeline and urgency?
   - Are there specific UX requirements or patterns to follow?
   - What systems need to integrate? Any API requirements?
   - What data will we collect/use? Privacy considerations?
   - How will this be rolled out? Beta testing plans?

3. **Wait for user responses** before proceeding
4. **Re-assess confidence** after gathering answers
5. **Document assumptions** if any information is still missing

## Step 2: EXPLORE (Subagent Research)
// turbo
1. Use a subagent to research the codebase WITHOUT writing any code yet
2. Ask Claude to investigate:
   - Existing similar features or patterns
   - Relevant files and their current structure
   - Dependencies and imports that will be needed
   - Potential conflicts or integration points
3. Subagent returns findings summary (preserves main context)

## Step 3: THINK HARD (Extended Thinking)
// turbo
1. Run the `/plan` macro with "think hard" mode
2. Claude will:
   - Analyze the clarified requirements
   - Analyze the research findings
   - Consider multiple approaches
   - Identify risks and dependencies
   - Generate a detailed plan with success criteria
   - **Document all assumptions** made during planning
   - Save to effort-specific path (determined in Step 0)

## Step 4: ⚠️ HUMAN CHECKPOINT - Plan Approval (REQUIRED)
1. Review the generated plan at effort-specific path
2. Verify:
   - **All clarifying questions were answered** (not skipped)
   - **Assumptions are documented** and acceptable
   - User story is clear and achievable
   - E2E test steps are realistic
   - API contracts fit existing architecture
   - Success criteria are objective and testable
   - No major risks or blockers
3. **DECISION**: Approve, revise, or cancel
   - If approved → Proceed to step 5
   - If revisions needed → Return to step 1 with feedback
   - If cancelled → Document why and pivot

## Step 5: Initialize Tracking Files
// turbo
1. Use effort-specific directory (determined in Step 0)
2. Initialize tracking files:
   - `PROGRESS.md` - What's done, what's next
   - `ERRORS.md` - Known issues and attempted fixes
   - `DECISIONS.md` - Why we chose X over Y
   - `ASSUMPTIONS.md` - **NEW**: Document all assumptions made during planning
   - `metrics.json` - Error budget, time tracking
3. Update effort status in `effort.json` to "planned"
4. Confirm initialization: "✅ Tracking initialized for effort: [effort-name]"

## Step 6: Set Error Budget
// turbo
1. Configure error budget in `metrics.json`:
   ```json
   {
     "maxErrorsPerTask": 3,
     "maxErrorsPerSession": 10,
     "contextCompactionInterval": 30,
     "confidenceThreshold": 80
   }
   ```

## Step 7: Ready for Tasks ✅

**🎉 Plan Approved and Saved!**

```
✅ Plan: Approved
✅ Tracking: Initialized
✅ Error budget: Set

📍 YOU ARE HERE: effort-new → plan → [task] → implement
```

**🚦 NEXT STEP (Required):**
```
/task
```

**What happens next:**
1. AI will break your plan into <45 minute tasks
2. Each task will have clear success criteria
3. Manual verification steps will be defined
4. Wait for your approval of the task breakdown

**⚠️ Do not skip to /implement - it needs tasks to work with!**

---
allowed-tools: "*"

---
allowed-tools: "*"

**Key Changes from Old Workflow**:
- ✅ **CLARIFYING QUESTIONS FIRST** - Never plan without understanding requirements
- ✅ **Confidence-based questioning** - Ask more questions if <80% confident
- ✅ **Document assumptions** - Track what we don't know
- ✅ Subagent exploration BEFORE planning
- ✅ Extended thinking mode for better plans
- ✅ **MANDATORY human approval** checkpoint
- ✅ Branch-specific directory structure
- ✅ Error budget initialization
- ✅ Tracking files for long-horizon tasks

**Inspired by**: CEO's PRD workflow (DunhamPRD.md) - clarifying questions approach prevents wasted planning effort
