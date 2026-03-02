# PRD Session Manager Module

**Version:** 1.0  
**Module Type:** Orchestration & State Management  
**Max Lines:** 400

## Module Overview

The Session Manager orchestrates the entire PRD workflow, maintains state across modules, and provides navigation between workflow phases. This is the entry point for all PRD generation activities.

---

## Entry Criteria

- [ ] User has requested PRD creation or workflow resumption
- [ ] Workspace access is available
- [ ] Required directories exist (`docs/PRDs/` and `docs/AIs/`)

---

## Module Objective

**Primary Goal:** Initialize, coordinate, and manage the PRD workflow session from start to completion, ensuring proper state persistence and module sequencing.

**Focus Anchor:**

1. "I am managing the PRD workflow session for [Task Name]"
2. "My objective is to orchestrate all 6 modules and maintain workflow state"
3. "I will not proceed without validating each module's completion criteria"

---

## Process Steps

### Step 1: Session Initialization [Progress: 16%]

#### 1.1 Check for Existing Session

```markdown
**Action:** Look for existing workflow state file
**Location:** `docs/PRDs/{sanitized-task-name}/workflow-state_{sanitized-task-name}.json`
**Decision Point:**

- If exists: → Go to Step 1.2 (Resume Session)
- If not exists: → Go to Step 1.3 (New Session)
```

#### 1.2 Resume Existing Session

```markdown
**Message to User:** "I found an existing PRD workflow for [Task Name]. Current progress: Stage [X] - [Stage Name]. Would you like to:"

- Resume from current stage
- Start over (will archive existing progress)
- Review current progress first

**Action:** Load state file and navigate to appropriate module
**Next Module:** Based on currentStage in state file
```

#### 1.3 New Session Setup

```markdown
**Message to User:** "Starting new PRD workflow. I'll guide you through 6 focused phases to create a comprehensive PRD."

**Initialize State File:**
{
"sessionId": "[timestamp-uuid]",
"taskName": "[To be determined]",
"sanitizedTaskName": "[auto-generated]",
"startTime": "[ISO timestamp]",
"currentStage": 1,
"stageCompleted": false,
"moduleProgress": {
"sessionManager": 16,
"taskDiscovery": 0,
"informationGathering": 0,
"corePrdGenerator": 0,
"technicalSpecification": 0,
"implementationBridge": 0
},
"workflowMode": "regular",
"completedModules": [],
"activeModule": "taskDiscovery"
}
```

### Step 2: Module Navigation [Progress: 33%]

#### 2.1 Module Sequence Definition

```markdown
**Standard Flow:**

1. Task Discovery → Information Gathering → Core PRD Generator → Technical Specification → Implementation Bridge → Completion
2. Each module must reach 100% completion before handoff
3. Rollback available to any previous module
```

#### 2.2 Module Handoff Protocol

```markdown
**Before Each Module:**

1. Validate entry criteria
2. Set module context
3. Update progress tracking
4. Confirm user readiness

**After Each Module:**

1. Validate exit criteria
2. Update state file
3. Prepare next module inputs
4. Confirm continuation
```

### Step 3: Progress Monitoring [Progress: 50%]

#### 3.1 Real-Time Progress Updates

```markdown
**Update Frequency:** After each major step within modules
**Progress Display:**

- Overall workflow: X% complete
- Current module: Y% complete
- Estimated time remaining: Z minutes

**Progress Validation:**

- Green: All criteria met, ready to proceed
- Yellow: Minor issues, user review recommended
- Red: Critical issues, intervention required
```

#### 3.2 Checkpoint Management

```markdown
**Automatic Checkpoints:** Every 25% module completion
**Manual Checkpoints:** User-triggered save points
**Recovery Points:** Before any destructive operations
**State Persistence:** All changes auto-saved to state file
```

### Step 4: Error Handling [Progress: 66%]

#### 4.1 Module Failure Recovery

```markdown
**Detection:** Module reports critical error or user intervention
**Response:**

1. Save current state
2. Identify failure point
3. Offer recovery options:
   - Restart current module
   - Roll back to previous checkpoint
   - Skip to manual override mode

**Fallback:** Always preserve completed work
```

#### 4.2 AI Confusion Detection

```markdown
**Triggers:**

- AI discusses topics outside current module scope
- Multiple failed validation attempts
- User reports AI going "off-track"

**Recovery Protocol:**

1. Display: "🔄 REFOCUS ALERT: Returning to [Module] objective"
2. Reload module context and objectives
3. Resume from last valid checkpoint
4. Confirm user understanding before proceeding
```

### Step 5: Workflow Completion [Progress: 83%]

#### 5.1 Final Validation

```markdown
**Completeness Check:**

- [ ] All 6 modules completed with 100% progress
- [ ] PRD document generated and validated
- [ ] Implementation tasks created (if applicable)
- [ ] All required files present in project structure

**Quality Gates:**

- [ ] PRD passes template compliance check
- [ ] Technical specifications are implementation-ready
- [ ] User stories have clear acceptance criteria
- [ ] No critical gaps or TBDs remain
```

#### 5.2 Session Closure

```markdown
**Final State Update:**
{
"status": "completed",
"endTime": "[ISO timestamp]",
"totalDuration": "[minutes]",
"finalDeliverables": [
"prd*[task-name].md",
"workflow-state*[task-name].json",
"changelog\_[task-name].md"
]
}

**User Summary:**
"✅ PRD Workflow Complete! Generated deliverables:

- Comprehensive PRD: [link]
- Implementation tasks: [count] tasks ready
- Total time: [duration]"
```

### Step 6: Maintenance Operations [Progress: 100%]

#### 6.1 Cleanup and Archival

```markdown
**Archive Completed Sessions:**

- Move state files to archive folder after 30 days
- Maintain quick access to recent sessions
- Clean up temporary files and states

**Session Analytics:**

- Track completion rates by module
- Identify common failure points
- Monitor average completion times
```

---

## Exit Criteria

- [ ] Session properly initialized or resumed
- [ ] Appropriate next module identified and prepared
- [ ] State file created/updated with current progress
- [ ] User confirmed and ready to proceed
- [ ] All session management functions operational

---

## Data Structures

### Workflow State Schema

```json
{
  "sessionId": "string",
  "taskName": "string",
  "sanitizedTaskName": "string",
  "startTime": "ISO string",
  "endTime": "ISO string | null",
  "currentStage": "number",
  "stageCompleted": "boolean",
  "status": "active | completed | failed | paused",
  "moduleProgress": {
    "sessionManager": "number (0-100)",
    "taskDiscovery": "number (0-100)",
    "informationGathering": "number (0-100)",
    "corePrdGenerator": "number (0-100)",
    "technicalSpecification": "number (0-100)",
    "implementationBridge": "number (0-100)"
  },
  "workflowMode": "express | regular | deep-dive | dev",
  "completedModules": "array of strings",
  "activeModule": "string",
  "checkpoints": "array of checkpoint objects",
  "errors": "array of error objects"
}
```

---

## Troubleshooting

### Common Issues

1. **State file corruption**: Auto-backup and recovery procedures
2. **Module handoff failures**: Fallback to manual navigation
3. **User confusion**: Context reset and objective restatement
4. **Progress tracking errors**: Manual override capabilities

### Recovery Commands

- `RESET SESSION` - Start completely fresh
- `ROLLBACK [stage]` - Return to specific stage
- `SKIP TO [module]` - Advanced navigation (with warnings)
- `EXPORT STATE` - Generate debugging information

---

## Next Module: Task Discovery

**Module File:** `prd-task-discovery.md`
**Entry Requirements:** Session initialized, user ready to proceed
**Expected Duration:** 5-10 minutes
