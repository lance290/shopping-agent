---
allowed-tools: "*"
description: List all efforts in the current branch with their status
---
allowed-tools: "*"

# List Efforts Workflow

Quick overview of all efforts in the current branch.

## Step 1: Get Current Branch
// turbo
1. Get current branch name
2. Check if `.cfoi/branches/[branch-name]/efforts/` exists
3. If not exists: Display "No efforts found. Run /effort-new to create one."

## Step 2: Load All Efforts
// turbo
1. List all directories in `.cfoi/branches/[branch-name]/efforts/`
2. For each effort directory:
   - Read `effort.json` for metadata (including `priority` field)
   - Check if `plan.md` exists
   - Check if `tasks.md` exists
   - Count completed tasks (if tasks exist)
   - Check if it's the current effort (from `.current-effort`)
3. **Sort efforts by priority** (ascending: 1 = highest priority, runs first)

## Step 3: Display Summary
// turbo
Display formatted table (sorted by priority):
```
📋 Efforts in branch: [branch-name]

┌────┬─────────────────────────┬──────────┬────────────┬────────┬─────────┐
│ #  │ Effort                  │ Type     │ Status     │ Tasks  │ Current │
├────┼─────────────────────────┼──────────┼────────────┼────────┼─────────┤
│ 1  │ bug-auth-timeout        │ bug      │ in-progress│ 2/3    │ ✅      │
│ 2  │ feature-main            │ feature  │ completed  │ 8/8    │         │
│ 3  │ enhance-caching         │ enhance  │ planning   │ 0/0    │         │
└────┴─────────────────────────┴──────────┴────────────┴────────┴─────────┘

Current: bug-auth-timeout (priority #1)
Next action: Run /implement to continue task 3

💡 To reorder: Edit `priority` field in effort.json (lower = higher priority)
💡 To execute next: "execute next effort" will pick the highest-priority non-completed effort
```

## Step 4: Suggest Actions
// turbo
Based on current effort status, suggest:
- **planning**: "Run /plan to create plan"
- **planned**: "Run /task to break down into tasks"
- **in-progress**: "Run /implement to work on next task"
- **completed**: "Run /effort-switch to work on another effort"

**When user says "execute next effort"**:
1. Find the highest-priority (lowest `priority` number) effort with status NOT "completed"
2. If different from current effort, run `/effort-switch [effort-name]`
3. Then suggest the appropriate action based on that effort's status

---
allowed-tools: "*"

**Usage**:
```
You: /effort-list
AI: [Shows table of all efforts]
```

**Key Features**:
- ✅ Quick overview of all work in branch
- ✅ **Sorted by priority** (auto-assigned at creation)
- ✅ See which effort is active
- ✅ Track progress across efforts
- ✅ Get suggested next action
- ✅ "Execute next effort" picks highest-priority incomplete effort
