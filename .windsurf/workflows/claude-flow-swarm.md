---
allowed-tools: "*"
description: Complex multi-agent orchestration using claude-flow
---
allowed-tools: "*"

# Claude Flow Swarm Workflow

**Invoke claude-flow's multi-agent system for complex tasks requiring coordination**

## When to Use
- Complex refactoring across multiple files
- Large-scale migrations or transformations
- Research + implementation cycles
- Tasks that exceed single-agent context limits
- When you need parallel agent execution

## Prerequisites

// turbo
```bash
# Check if claude-flow is installed
npx claude-flow@alpha --version || echo "❌ claude-flow not found"
```

If missing, install:
```bash
npm install -g claude-flow@alpha
npx claude-flow@alpha init
```

## Step 0: Determine Effort Context

// turbo
1. Check if `.cfoi/branches/[branch-name]/.current-effort` exists
2. If exists: Load current effort name and use `.cfoi/branches/[branch-name]/efforts/[effort-name]/`
3. If not exists: Use legacy path `.cfoi/branches/[branch-name]/` (backward compatible)
4. Display: "🐝 Swarm for effort: [effort-name]" or "🐝 Swarm for branch: [branch-name]"

## Step 1: Prepare Swarm Context

// turbo
1. **Gather CFOI artifacts** (from effort-specific path):
   - Read current `plan.md` (goals, constraints)
   - Read current `tasks.md` (active task details)
   - Read `PROGRESS.md` (what's been done)
   - Read `DECISIONS.md` (constraints and choices)
   - Read `product-north-star.md` (if exists)

2. **Create swarm session directory**:
   ```bash
   TIMESTAMP=$(date +%Y%m%d-%H%M%S)
   SWARM_DIR=".cfoi/branches/$(git branch --show-current)/swarm/$TIMESTAMP"
   mkdir -p "$SWARM_DIR/context"
   mkdir -p "$SWARM_DIR/output"
   ```

3. **Snapshot context**:
   ```bash
   cp plan.md "$SWARM_DIR/context/" 2>/dev/null || true
   cp tasks.md "$SWARM_DIR/context/" 2>/dev/null || true
   cp PROGRESS.md "$SWARM_DIR/context/" 2>/dev/null || true
   cp DECISIONS.md "$SWARM_DIR/context/" 2>/dev/null || true
   ```

## Step 2: Format Swarm Objective

Build a clear objective for claude-flow from CFOI context:

**Template:**
```
Objective: [Current task from tasks.md]

Context:
- Goal: [From plan.md]
- Current Progress: [From PROGRESS.md]
- Constraints: [From DECISIONS.md and plan.md]
- Success Criteria: [From plan.md or tasks.md]

Files to Consider:
[List relevant file paths from task context]

Requirements:
- Follow existing code patterns
- Maintain test coverage
- Document decisions
```

Save to `$SWARM_DIR/context/objective.txt`

## Step 3: Execute Swarm

// turbo
Choose swarm mode based on task complexity:

**For Research + Implementation:**
```bash
cd "$SWARM_DIR"
npx claude-flow@alpha swarm "$(cat context/objective.txt)" \
  --output "./output" \
  2>&1 | tee swarm-execution.log
```

**For Hive Mind (More Intelligent):**
```bash
cd "$SWARM_DIR"
npx claude-flow@alpha hive-mind spawn "$(cat context/objective.txt)" \
  --output "./output" \
  2>&1 | tee swarm-execution.log
```

**Monitor execution:**
- Watch `swarm-execution.log` for progress
- Check `.claude/agents/` for agent activity
- Use `npx claude-flow@alpha hive-mind status` to monitor

## Step 4: Sync Results Back to CFOI

// turbo
After swarm completes:

1. **Copy outputs**:
   ```bash
   # Copy claude-flow outputs to swarm session
   cp -r .claude/agents/* "$SWARM_DIR/output/agents/" 2>/dev/null || true
   
   # Copy any generated files
   if [ -d "$SWARM_DIR/output" ]; then
     echo "✅ Swarm outputs saved to $SWARM_DIR/output"
   fi
   ```

2. **Extract key decisions**:
   ```bash
   # Parse swarm outputs for decisions
   echo "## Swarm Run: $TIMESTAMP" >> DECISIONS.md
   echo "" >> DECISIONS.md
   grep -h "Decision:" "$SWARM_DIR/output/"*.md 2>/dev/null >> DECISIONS.md || true
   echo "" >> DECISIONS.md
   ```

3. **Update PROGRESS.md**:
   ```bash
   echo "## Swarm Execution: $TIMESTAMP" >> PROGRESS.md
   echo "" >> PROGRESS.md
   echo "**Objective:** $(head -1 $SWARM_DIR/context/objective.txt)" >> PROGRESS.md
   echo "**Status:** $(tail -1 $SWARM_DIR/swarm-execution.log)" >> PROGRESS.md
   echo "**Outputs:** $SWARM_DIR/output/" >> PROGRESS.md
   echo "" >> PROGRESS.md
   ```

4. **Create summary**:
   ```bash
   cat > "$SWARM_DIR/SUMMARY.md" << 'EOF'
# Swarm Session Summary

**Started:** $TIMESTAMP
**Objective:** [from objective.txt]
**Status:** [SUCCESS/PARTIAL/FAILED]

## Agents Involved
[List from .claude/agents/]

## Key Outputs
[List generated files]

## Decisions Made
[Extract from agent logs]

## Next Steps
[What human needs to review/approve]
EOF
   ```

## Step 5: Review and Integrate

1. **Review swarm outputs**:
   - Check `$SWARM_DIR/SUMMARY.md`
   - Review agent transcripts in `$SWARM_DIR/output/agents/`
   - Examine any code changes or generated files

2. **Integrate changes**:
   - Copy approved code changes to working directory
   - Update tests if needed
   - Run verification: `./tools/verify-implementation.sh`

3. **Document in proof/**:
   ```bash
   TASK_ID="[current-task-id]"
   mkdir -p "proof/$TASK_ID"
   echo "Swarm session: $SWARM_DIR" >> "proof/$TASK_ID/implementation.md"
   ```

## Step 6: Cleanup

// turbo
```bash
# Archive completed swarm session
if [ -d "$SWARM_DIR" ]; then
  echo "📦 Swarm session archived at: $SWARM_DIR"
  echo "   View summary: cat $SWARM_DIR/SUMMARY.md"
fi

# Optional: Clean up claude-flow transient files
# npx claude-flow@alpha cleanup
```

## Error Handling

**If swarm fails:**
1. Check `$SWARM_DIR/swarm-execution.log` for errors
2. Review `.claude/agents/` for agent failures
3. Verify claude-flow has valid API keys configured
4. Try with smaller, more focused objective
5. Fall back to manual `/implement` workflow

**Common Issues:**
- **"No API key"** → Run `npx claude-flow@alpha config` to set keys
- **"Agent timeout"** → Objective too complex, break it down
- **"Context limit"** → Reduce files in scope

## Success Criteria

- [ ] Swarm completed without errors
- [ ] Outputs documented in `$SWARM_DIR/`
- [ ] Key decisions captured in `DECISIONS.md`
- [ ] Progress updated in `PROGRESS.md`
- [ ] Code changes reviewed and integrated
- [ ] Tests passing after integration

**Final Output:** "🎉 Swarm complete! Summary: $SWARM_DIR/SUMMARY.md"

---
allowed-tools: "*"

## Quick Reference

```bash
# Start swarm
npx claude-flow@alpha swarm "objective"

# Monitor status
npx claude-flow@alpha hive-mind status

# View metrics
npx claude-flow@alpha hive-mind metrics

# Check agent activity
ls .claude/agents/
```

**See also:**
- claude-flow docs: https://github.com/ruvnet/claude-flow
- `/implement` - Standard single-agent implementation
- `/verify` - Post-swarm verification workflow
