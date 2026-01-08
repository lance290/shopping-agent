---
allowed-tools: "*"
description: Update framework to latest version with guardrails
---
allowed-tools: "*"

# Framework Update Workflow

**Purpose**: Update existing installation with latest guardrail-enforced workflows and fixes.

## When to Use

- After pulling latest framework changes
- To get new guardrail enforcement
- To update workflows with bug fixes
- To add new workflows (verify, compact, checkpoint)

## Step 1: Backup Current State

```bash
# Create backup branch
git checkout -b backup-before-update-$(date +%Y%m%d)
git add .
git commit -m "backup: before framework update" || true
git push origin backup-before-update-$(date +%Y%m%d) || true
git checkout -
```

## Step 2: Check What Will Be Updated

```bash
# If framework is in Infra-As-Code subdirectory
cd Infra-As-Code
git pull origin main

# Show what files will change
./install.sh --help
```

## Step 3: Run Update

```bash
# From project root
cd /path/to/Infra-As-Code

# Run with --update flag (overwrites existing files)
./install.sh --update
```

This will:
- ✅ Update `.windsurf/workflows/` with new guardrails
- ✅ Update `.windsurf/macros.yaml` with enforced `/implement`
- ✅ Update `.githooks/` with latest checks
- ✅ Update `tools/` with new scripts
- ✅ Update `docs/` with strategy guides
- ⚠️ **Preserve** your `.windsurf/constitution.md` (asks before overwrite)

## Step 4: Review Changes

```bash
# See what changed
git status
git diff

# Key files to check:
git diff .windsurf/macros.yaml
git diff .windsurf/workflows/implement.md
git diff .windsurf/workflows/plan.md
git diff .windsurf/workflows/task.md
```

## Step 5: Migrate Existing Work

If you have existing `.cfoi/slices/[slice-name]/` directories, migrate to new structure:

```bash
# Get current branch
BRANCH=$(git branch --show-current)

# Create new branch directory
mkdir -p .cfoi/branches/$BRANCH

# If you have old slice directories, migrate them
if [ -d .cfoi/slices ]; then
  echo "Migrating .cfoi/slices/* to .cfoi/branches/$BRANCH/"
  
  # Find the active slice (most recent)
  ACTIVE_SLICE=$(ls -t .cfoi/slices | head -1)
  
  if [ -n "$ACTIVE_SLICE" ]; then
    # Copy files to new location
    cp .cfoi/slices/$ACTIVE_SLICE/plan.md .cfoi/branches/$BRANCH/plan.md 2>/dev/null || true
    cp .cfoi/slices/$ACTIVE_SLICE/tasks.md .cfoi/branches/$BRANCH/tasks.md 2>/dev/null || true
    cp .cfoi/slices/$ACTIVE_SLICE/implement-*.md .cfoi/branches/$BRANCH/ 2>/dev/null || true
    
    echo "✅ Migrated $ACTIVE_SLICE to .cfoi/branches/$BRANCH/"
    echo "⚠️ Old slices remain in .cfoi/slices/ - review before deleting"
  fi
fi

# Initialize new tracking files
cat > .cfoi/branches/$BRANCH/PROGRESS.md << 'EOF'
# Progress - Branch: $BRANCH

## Current Status
Work in progress - migrated from old structure

## Next Steps
- Continue with /implement workflow
EOF

touch .cfoi/branches/$BRANCH/ERRORS.md
touch .cfoi/branches/$BRANCH/DECISIONS.md

cat > .cfoi/branches/$BRANCH/metrics.json << 'EOF'
{
  "branch": "$BRANCH",
  "tasks": {
    "total": 0,
    "completed": 0,
    "inProgress": 0,
    "remaining": 0
  },
  "errors": {
    "totalEncountered": 0,
    "budget": {
      "perTask": 3,
      "perSession": 10,
      "exceeded": false
    }
  },
  "timeTracking": {
    "lastContextCompaction": null,
    "nextCompactionDue": null
  },
  "checkpoints": []
}
EOF

echo "✅ Initialized tracking files for branch: $BRANCH"
```

## Step 6: Test New Workflows

```bash
# In Windsurf, test the updated workflows
/plan      # Should show new guardrail steps
/task      # Should include E2E flows
/implement # Should enforce all 7 guardrails
/verify    # New workflow - dual-agent review
/compact   # New workflow - context compaction
/checkpoint # New workflow - save state
```

## Step 7: Update Team

If working in a team:

```bash
# Commit the framework updates
git add .windsurf .githooks .github tools docs
git commit -m "chore: update framework with guardrail enforcement

- Add error prevention guardrails to /implement
- Add /verify, /compact, /checkpoint workflows
- Update plan/task workflows with human checkpoints
- Migrate to branch-based .cfoi structure"

git push origin $(git branch --show-current)

# Notify team
echo "Framework updated! Team members should run:"
echo "  cd /path/to/Infra-As-Code"
echo "  git pull"
echo "  ./install.sh --update"
```

## Step 8: Clean Up (Optional)

After confirming everything works:

```bash
# Remove old slice structure (if migrated)
# ⚠️ Only do this after confirming new structure works!
# rm -rf .cfoi/slices

# Remove backup branch (after a few days)
# git branch -D backup-before-update-YYYYMMDD
# git push origin --delete backup-before-update-YYYYMMDD
```

---
allowed-tools: "*"

## What Gets Updated

### `.windsurf/workflows/`
- ✅ `plan.md` - Subagent exploration, human approval, tracking init
- ✅ `task.md` - E2E flows, manual verification, human review
- ✅ `implement.md` - Click-First CFOI, all 7 guardrails
- ✅ `verify.md` - NEW - Dual-agent code review
- ✅ `compact.md` - NEW - Context compaction
- ✅ `checkpoint.md` - NEW - Save working state

### `.windsurf/macros.yaml`
- ✅ `/implement` - Completely rewritten with guardrails
- ✅ `/verify` - NEW - Dual-agent verification
- ✅ `/compact` - NEW - Context reset
- ✅ `/checkpoint` - NEW - Rollback points

### `tools/`
- ✅ `verify-implementation.sh` - Latest checks
- ✅ `setup.sh` - Updated for new structure

### `docs/workflow-pack/`
- ✅ `QUICKSTART.md` - Getting started guide
- ✅ `KEEPING_AI_HONEST.md` - Guardrail enforcement playbook
- ✅ `EPHEMERAL_SETUP.md` - PR environment setup
- ✅ `BROWNFIELD_INTEGRATION.md` - Add framework to existing projects
- ✅ `CODE_REUSE_ENFORCEMENT.md` - DRY guidelines
- ✅ `ANTI_TEST_SKIPPING.md` - Test integrity guardrail
- ✅ `GREEN_BASELINE_ENFORCEMENT.md` - Pre-flight test enforcement

### `.githooks/`
- ✅ Latest pre-commit, pre-push checks
- ✅ Updated constitution enforcement

---
allowed-tools: "*"

## Breaking Changes

### Directory Structure Change
**Old**: `.cfoi/slices/[slice-name]/`
**New**: `.cfoi/branches/[branch-name]/`

**Why**: Plans/tasks are per-branch, not per-slice. More intuitive for long-running work.

**Migration**: Step 5 handles this automatically.

### New Tracking Files
- `PROGRESS.md` - Progress summaries (for compaction)
- `ERRORS.md` - Known issues (for compaction)
- `DECISIONS.md` - Architectural decisions (for compaction)
- `metrics.json` - Error budget, time tracking

**Migration**: Step 5 creates these automatically.

---
allowed-tools: "*"

## Rollback Procedure

If update causes issues:

```bash
# 1. Switch to backup branch
git checkout backup-before-update-YYYYMMDD

# 2. Create new branch from backup
git checkout -b restore-old-framework

# 3. Restore old framework
git reset --hard backup-before-update-YYYYMMDD

# 4. Continue work on this branch
# Or investigate what went wrong with the update
```

---
allowed-tools: "*"

## FAQ

**Q: Will this overwrite my constitution?**
A: The installer asks before overwriting. Say "skip" to keep yours.

**Q: What about my in-progress work?**
A: Step 1 creates a backup. Step 5 migrates your plans/tasks.

**Q: Do I need to update immediately?**
A: No, but new guardrails prevent error loops. Recommended before starting new features.

**Q: Will this work with old branches?**
A: Yes. Each branch gets its own `.cfoi/branches/[branch-name]/` directory.

**Q: What if I have customized workflows?**
A: Back up first (Step 1). After update, merge your customizations back in.

---
allowed-tools: "*"

## After Update

You now have:
- ✅ Guardrail-enforced `/implement` workflow
- ✅ Error prevention system (7 guardrails)
- ✅ Dual-agent verification (`/verify`)
- ✅ Automatic context compaction (`/compact`)
- ✅ Rollback points every 45 min (`/checkpoint`)
- ✅ Branch-based tracking structure
- ✅ Error budget system
- ✅ Human-in-the-loop checkpoints

**Ready to build MVPs without falling into error loops!** 🚀
