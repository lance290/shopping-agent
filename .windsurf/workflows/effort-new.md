---
allowed-tools: "*"
description: Create a new effort (feature/bug/enhancement) within current branch
---
# New Effort Workflow

Use this when you need to work on multiple things in the same branch (e.g., original feature is done, now need to fix a bug and add an enhancement).

## Step 1: Identify Current Branch
// turbo
1. Get current branch name
2. Ensure `.cfoi/branches/[branch-name]/` directory exists (create if needed)
3. Create `efforts/` subdirectory if it doesn't exist

## Step 2: Create Effort
// turbo
1. Prompt user for effort details:
   - **Type**: feature | bug | enhancement | refactor | docs
   - **Name**: Short slug (e.g., "auth-timeout-fix", "add-caching")
   - **Description**: One-line summary
2. Create effort directory: `.cfoi/branches/[branch-name]/efforts/[type]-[name]/`
3. **Auto-assign priority**:
   - Scan all existing `effort.json` files in `.cfoi/branches/[branch-name]/efforts/*/`
   - Find the highest existing `priority` value (default 0 if none exist)
   - Assign `priority = max + 1` to the new effort
   - This ensures new efforts are added to the end of the queue by default
4. Initialize effort metadata file: `effort.json`
   ```json
   {
     "type": "bug",
     "name": "auth-timeout-fix",
     "description": "Fix authentication timeout issue",
     "created": "2025-10-12T23:00:00Z",
     "status": "planning",
     "priority": 3,
     "parent": null,
     "definition_of_done": {
       "version": 1,
       "status": "draft",
       "thresholds": [
         {
           "description": "Onboarding completes in < 3 minutes",
           "metric": "onboarding_time_seconds",
           "target": 180,
           "evidence_required": "measured",
           "type": "threshold"
         }
       ],
       "signals": [
         {
           "description": "Signup completion rate ≥ 85%",
           "metric": "signup_completion_rate",
           "target": 0.85,
           "weight": 0.4,
           "evidence_required": "measured",
           "type": "signal"
         }
       ],
       "approval": {
         "by": "[Name]",
         "timestamp": "2025-10-12T23:00:00Z",
         "change_reason": "initial definition",
         "change_type": "tighten|loosen|clarify"
       }
     }
   }
   ```
   > **Note**: `priority` is auto-assigned. Lower number = higher priority. Use `/effort-list` to view order, manually edit `effort.json` to reorder if needed.

## Step 3: Set as Current Effort & Initialize Progress Log
// turbo
1. Write effort name to `.cfoi/branches/[branch-name]/.current-effort`

2. Create `PROGRESS.md` at `.cfoi/branches/[branch-name]/efforts/[effort-name]/PROGRESS.md`:
   ```markdown
   # Progress Log - [effort-name]
   
   > **Purpose**: Quick context loading for fresh sessions. Read this FIRST.
   
   ## Current State
   - **Status**: 🟡 Planning
   - **Current task**: None (not yet decomposed)
   - **Last working commit**: N/A
   - **App status**: Unknown
   
   ## Quick Start
   ```bash
   # Run this to start development environment
   ./init.sh  # or: npm run dev
   ```
   
   ## Session History
   
   ### [YYYY-MM-DD HH:MM] - Session 1 (Initial Setup)
   - Created effort: [effort-name]
   - Type: [type]
   - Description: [description]
   - Next: Run /plan to create implementation plan
   
   ## How to Use This File
   
   **At session start:**
   1. Read "Current State" to understand where we are
   2. Check "Last working commit" - if app is broken, revert here
   3. Review recent session history for context
   
   **At session end:**
   1. Update "Current State" with latest status
   2. Add session entry with what was accomplished
   3. Note any blockers or next steps
   
   **⚠️ IMPORTANT**: Keep this file updated! Future sessions depend on it.
   ```

3. Display: "✅ Created effort: [type]-[name] (now active)"

## Step 4: Establish Effort North Star
**CRITICAL: Must complete before planning**

1. Check if Product North Star exists at `.cfoi/branches/[branch-name]/product-north-star.md`
   - If missing: Halt and prompt user to run `/north-star` first to create Product North Star
   - Display: "⚠️ No Product North Star found. Run /north-star to create one before proceeding."

2. If Product North Star exists, create effort-level north star:
   - Path: `.cfoi/branches/[branch-name]/efforts/[effort-name]/product-north-star.md`
   - Template:
     ```markdown
     # Effort North Star (Effort: [effort-name], v[YYYY-MM-DD])
     
     ## Goal Statement
     [One sentence: What this effort achieves]
     
     ## Ties to Product North Star
     - **Product Mission**: [Reference specific section from product north star]
     - **Supports Metric**: [Which product metric does this move?]
     
     ## In Scope
     - [Specific deliverable 1]
     - [Specific deliverable 2]
     
     ## Out of Scope
     - [What we explicitly won't do]
     - [What's deferred to future efforts]
     
     ## Acceptance Checkpoints
     - [ ] [Checkpoint 1 mapped to product metric]
     - [ ] [Checkpoint 2 mapped to product metric]
     
     ## Dependencies & Risks
     - **Dependencies**: [What we need before starting]
     - **Risks**: [What could block us]
     
     ## Approver / Date
     - Approved by: [Name]
     - Date: [YYYY-MM-DD]
     ```

3. Prompt user to fill in north star sections
4. Save to effort directory
5. Display: "✅ Effort north star created. Review before planning."

## Step 4.5: Capture Definition of Done (DoD) **(REQUIRED)**
1. Prompt user for DoD inputs **before planning**:
   - Thresholds (binary gates tied to north star) with metric + target + evidence type (measured/sampled/self-reported)
   - Weighted signals (0–100 aggregate) with metric + target + weight + evidence type
   - Confidence level (measured vs. self-reported)
   - Approver name and timestamp
2. Update `effort.json.definition_of_done`:
   - Set `status` to `active` once thresholds/signals are filled
   - Bump `version` if user revises during creation
3. Add DoD summary to `PROGRESS.md` under a new section:
   ```markdown
   ## Definition of Done (DoD)
   - Status: Active
   - Thresholds:
     - [ ] [metric] target [value] (evidence: [type])
   - Signals (weighted):
     - [ ] [metric] target [value], weight [w], evidence [type]
   - Confidence: [measured/sampled/self-reported]
   - Approved by: [Name] on [Date]
   ```
4. **Gate**: Do not proceed to /plan until DoD is present and marked `active`.

## Step 5: Ready for Planning ✅

**🎉 Effort Created Successfully!**

```
✅ Effort: [effort-name]
✅ North star: Established
✅ Status: Ready for planning

📍 YOU ARE HERE: effort-new → [plan] → task → implement
```

**🚦 NEXT STEP (Required):**
```
/plan
```

**What happens next:**
1. AI will ask clarifying questions about your requirements
2. Research the codebase to understand existing patterns
3. Generate a detailed technical plan
4. Wait for your approval before proceeding

**⚠️ Do not skip to /task or /implement - they will fail without a plan!**

---
allowed-tools: "*"

**💡 Tip**: Use `/notes` anytime during development to capture:
- Quick ideas or improvements
- Technical debt you discover
- Questions or blockers
- Deferred work items

Notes are saved to `.cfoi/branches/[branch]/efforts/[effort]/NOTES.md`

---
allowed-tools: "*"

**Usage Example**:
```
User: /effort-new
AI: What type of effort? (feature/bug/enhancement/refactor/docs)
User: bug
AI: Short name (slug format)?
User: auth-timeout-fix
AI: One-line description?
User: Fix authentication timeout issue after 5 minutes
AI: ✅ Created effort: bug-auth-timeout-fix (now active)
    Ready to run /plan
```

**Key Features**:
- ✅ Multiple efforts per branch
- ✅ Each effort has its own plan/tasks
- ✅ Clear effort switching
- ✅ Effort type categorization
- ✅ Isolated tracking per effort
