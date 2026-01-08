---
allowed-tools: "*"
description: Reset context while preserving critical state
---
allowed-tools: "*"

# Context Compaction Workflow

**Purpose**: Prevent context pollution by resetting every 30 minutes while preserving progress.

## When to Use

- **Automatically**: Every 30 minutes of active work
- **Manually**: When context feels cluttered with errors/dead-ends
- **Between major tasks**: After completing 3-4 tasks
- **When stuck**: Fresh context might reveal the solution

## Step 1: Check If Compaction Needed
// turbo
1. Read metrics.json
2. Check `lastContextCompaction` timestamp
3. If >30 minutes ago → Proceed with compaction
4. If recently compacted → Skip (unless manual override)

## Step 2: Summarize Progress
// turbo
1. Generate progress summary:
   ```markdown
   # Progress Summary - [timestamp]
   
   ## Completed
   - Task 1: [description] ✅
   - Task 2: [description] ✅
   
   ## Current Task
   - Task 3: [description] - In progress
   - Status: [what's done, what's next]
   
   ## Key Decisions Made
   - [Architectural choice]: Why we did X not Y
   - [Technical decision]: Reasoning
   
   ## What's Working
   - [Feature X] is fully functional
   - [API Y] tested and working
   
   ## Next Steps
   - [ ] Complete task 3
   - [ ] Start task 4
   ```

2. Append to `.cfoi/branches/[branch-name]/PROGRESS.md`

## Step 3: Document Known Errors
// turbo
1. Summarize any open issues:
   ```markdown
   # Known Issues - [timestamp]
   
   ## Active Errors
   - **Error**: [description]
     - Attempted fixes: [what we tried]
     - Current status: [blocked / investigating / workaround]
   
   ## Resolved Errors  
   - [Error that was fixed]: Solution was [X]
   
   ## Warnings to Remember
   - [Thing to watch out for]
   ```

2. Append to `.cfoi/branches/[branch-name]/ERRORS.md`

## Step 4: Capture Architectural Decisions
// turbo
1. Document any decisions made:
   ```markdown
   # Decisions - [timestamp]
   
   ## Why We Chose X Over Y
   - **Decision**: Use Redis for session storage
   - **Reason**: Need cross-instance session sharing
   - **Alternatives considered**: Memory store (doesn't scale)
   
   ## Pattern Decisions
   - Following repository pattern for data access
   - Using controller-service-repository layers
   ```

2. Append to `.cfoi/branches/[branch-name]/DECISIONS.md`

## Step 5: Update Metrics
// turbo
1. Update metrics.json:
   ```json
   {
     "lastContextCompaction": "2024-10-05T15:30:00Z",
     "compactionCount": 3,
     "totalMinutesSinceStart": 95
   }
   ```

## Step 6: Clear Context
1. Run `/clear` command in Windsurf
2. Context window is now empty
3. No message history clutter

## Step 7: Reload Essential Context
// turbo
1. Load in priority order:
   - Constitution: `.windsurf/constitution.md`
   - Plan: `.cfoi/branches/[branch-name]/plan.md`
   - Progress: `.cfoi/branches/[branch-name]/PROGRESS.md` (latest summary)
   - Current task: From `.cfoi/branches/[branch-name]/tasks.md`
   - Recent errors: Last 3 entries from `ERRORS.md`
   - Key decisions: From `DECISIONS.md`

2. **Do NOT reload**:
   - Old error messages
   - Dead-end explorations
   - Redundant file reads
   - Failed attempts

## Step 8: Confirm Ready
1. Display context reload summary:
   ```
   🔄 Context Compacted Successfully
   
   ✅ Loaded:
   - Constitution
   - Plan
   - Progress summary (last 30 min)
   - Current task: Task 3
   - Known errors: 1 active
   
   📊 Stats:
   - Context tokens saved: ~40,000
   - Fresh start with essential state preserved
   
   Ready to continue from Task 3
   ```

---
allowed-tools: "*"

## What Gets Preserved

✅ **Keep**:
- Plan and tasks
- Progress summaries
- Architectural decisions
- Known errors (active)
- Current task context

❌ **Discard**:
- Old error messages
- Dead-end explorations
- Redundant tool outputs
- Failed code attempts
- Resolved errors (keep summary only)

---
allowed-tools: "*"

## Benefits

- ✅ Prevents context pollution
- ✅ Can't get stuck in error loops >30 min
- ✅ Fresh perspective on problems
- ✅ Persistent memory across sessions
- ✅ Efficient token usage
- ✅ Better long-horizon performance

---
allowed-tools: "*"

## Emergency Compaction

If stuck in error loop:
```bash
# Force immediate compaction
/compact --force

# Reload and try different approach
```
