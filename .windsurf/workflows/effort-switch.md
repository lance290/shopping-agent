---
allowed-tools: "*"
description: Switch between efforts in the current branch
---
allowed-tools: "*"

# Switch Effort Workflow

Use this to switch between different efforts (features, bugs, enhancements) in the same branch.

## Step 1: List Available Efforts
// turbo
1. Get current branch name
2. List all efforts in `.cfoi/branches/[branch-name]/efforts/`
3. Read `.current-effort` to show which is active
4. Display efforts with status:
   ```
   Available efforts in branch [branch-name]:
   * feature-main (completed) ✅
     bug-auth-timeout (in-progress) 🔄 [CURRENT]
     enhance-caching (planning) 📋
   ```

## Step 2: Select Effort
// turbo
1. Prompt user: "Which effort to switch to?"
2. Validate effort exists
3. Show effort details from `effort.json`:
   - Type, name, description
   - Status, created date
   - Task progress (if tasks exist)

## Step 3: Switch Context
// turbo
1. Write new effort name to `.cfoi/branches/[branch-name]/.current-effort`
2. Display summary:
   ```
   ✅ Switched to effort: [effort-name]
   
   Status: [status]
   Plan: [exists/missing]
   Tasks: [X/Y completed]
   
   Next steps:
   - Run /plan (if no plan exists)
   - Run /task (if plan exists but no tasks)
   - Run /implement (if tasks exist)
   ```

## Step 4: Load Context
// turbo
1. If `PROGRESS.md` exists, display last 10 lines
2. If `tasks.md` exists, show current task status
3. Ready for work on this effort

---
allowed-tools: "*"

**Usage Example**:
```
User: /effort-switch
AI: Available efforts:
    1. feature-main (completed)
    2. bug-auth-timeout (in-progress) [CURRENT]
    3. enhance-caching (planning)
    
    Which effort? (1-3)
User: 3
AI: ✅ Switched to: enhance-caching
    Status: planning
    Plan: exists
    Tasks: not created yet
    
    Next: Run /task to create tasks
```

**Key Features**:
- ✅ Easy switching between efforts
- ✅ Shows status of each effort
- ✅ Suggests next action
- ✅ Loads relevant context
