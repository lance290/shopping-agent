#!/bin/bash
set -e

# Migrate Existing Branches to New Framework Structure
# This script migrates .cfoi/slices/ to .cfoi/branches/ without losing work
# Usage: Copy framework into your project, cd into it, run: ./tools/migrate-existing-branches.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$FRAMEWORK_DIR"

# Detect if we're in a framework subdirectory
if [[ "$(basename "$FRAMEWORK_DIR")" == "Infra-As-Code" ]] || [[ "$(basename "$FRAMEWORK_DIR")" == "Infra As A Service" ]]; then
  PROJECT_ROOT="$(cd "$FRAMEWORK_DIR/.." && pwd)"
  echo "🔍 Detected framework in subdirectory"
  echo "   Framework: $FRAMEWORK_DIR"
  echo "   Project: $PROJECT_ROOT"
else
  echo "🔍 Running from project root"
  echo "   Project: $PROJECT_ROOT"
fi

echo ""
echo "🔄 Migrating Existing Branches to New Framework Structure"
echo "   Working directory: $PROJECT_ROOT"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Function to migrate a single branch
migrate_branch() {
  local BRANCH=$1
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📋 Migrating branch: $BRANCH"
  echo ""
  
  # Create new branch directory
  mkdir -p ".cfoi/branches/$BRANCH"
  
  # Check if old slices directory exists
  if [ -d ".cfoi/slices" ]; then
    # Find most recent slice (likely the active one)
    ACTIVE_SLICE=$(ls -t .cfoi/slices 2>/dev/null | head -1)
    
    if [ -n "$ACTIVE_SLICE" ]; then
      echo "  Found active slice: $ACTIVE_SLICE"
      
      # Migrate plan
      if [ -f ".cfoi/slices/$ACTIVE_SLICE/plan.md" ]; then
        cp ".cfoi/slices/$ACTIVE_SLICE/plan.md" ".cfoi/branches/$BRANCH/plan.md"
        echo "  ✅ Migrated plan.md"
      fi
      
      # Migrate tasks
      if [ -f ".cfoi/slices/$ACTIVE_SLICE/tasks.md" ]; then
        cp ".cfoi/slices/$ACTIVE_SLICE/tasks.md" ".cfoi/branches/$BRANCH/tasks.md"
        echo "  ✅ Migrated tasks.md"
      fi
      
      # Migrate implementation notes
      if ls .cfoi/slices/$ACTIVE_SLICE/implement-*.md 1> /dev/null 2>&1; then
        cp .cfoi/slices/$ACTIVE_SLICE/implement-*.md ".cfoi/branches/$BRANCH/" 2>/dev/null || true
        echo "  ✅ Migrated implement-*.md files"
      fi
      
      echo ""
      echo "  📝 Old slice: .cfoi/slices/$ACTIVE_SLICE/"
      echo "  📝 New location: .cfoi/branches/$BRANCH/"
    fi
  fi
  
  # Initialize PROGRESS.md
  if [ ! -f ".cfoi/branches/$BRANCH/PROGRESS.md" ]; then
    cat > ".cfoi/branches/$BRANCH/PROGRESS.md" << EOF
# Progress - Branch: $BRANCH

## Migration Status
Migrated from old .cfoi/slices/ structure on $(date '+%Y-%m-%d %H:%M:%S')

## Current Status
$(if [ -f ".cfoi/branches/$BRANCH/tasks.md" ]; then
  echo "Tasks defined, ready to continue implementation"
else
  echo "Ready to run /plan or /task"
fi)

## Next Steps
- Review migrated files
- Continue with /implement or start new planning with /plan
EOF
    echo "  ✅ Created PROGRESS.md"
  fi
  
  # Initialize ERRORS.md
  if [ ! -f ".cfoi/branches/$BRANCH/ERRORS.md" ]; then
    cat > ".cfoi/branches/$BRANCH/ERRORS.md" << EOF
# Known Issues - Branch: $BRANCH

No errors tracked yet.
EOF
    echo "  ✅ Created ERRORS.md"
  fi
  
  # Initialize DECISIONS.md
  if [ ! -f ".cfoi/branches/$BRANCH/DECISIONS.md" ]; then
    cat > ".cfoi/branches/$BRANCH/DECISIONS.md" << EOF
# Architectural Decisions - Branch: $BRANCH

## Migration Decision
Migrated from .cfoi/slices/ to .cfoi/branches/ structure for better long-running work support.
EOF
    echo "  ✅ Created DECISIONS.md"
  fi
  
  # Initialize metrics.json
  if [ ! -f ".cfoi/branches/$BRANCH/metrics.json" ]; then
    # Count tasks if tasks.md exists
    TASK_COUNT=0
    if [ -f ".cfoi/branches/$BRANCH/tasks.md" ]; then
      TASK_COUNT=$(grep -c "^- \[ \]" ".cfoi/branches/$BRANCH/tasks.md" 2>/dev/null || echo 0)
    fi
    
    cat > ".cfoi/branches/$BRANCH/metrics.json" << EOF
{
  "branch": "$BRANCH",
  "migrated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "tasks": {
    "total": $TASK_COUNT,
    "completed": 0,
    "inProgress": 0,
    "remaining": $TASK_COUNT
  },
  "errorBudget": {
    "perTask": 3,
    "perSession": 10,
    "currentTaskErrors": 0,
    "sessionErrors": 0
  },
  "timeTracking": {
    "lastContextCompaction": null,
    "nextCompactionDue": null
  },
  "checkpoints": []
}
EOF
    echo "  ✅ Created metrics.json"
  fi
  
  echo ""
  echo "✅ Branch $BRANCH migrated successfully!"
  echo ""
}

# Main migration logic
main() {
  # Check if we're in a git repository
  if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
  fi
  
  # Get current branch
  CURRENT_BRANCH=$(git branch --show-current)
  
  echo "Current branch: $CURRENT_BRANCH"
  echo ""
  
  # Ask user what to migrate
  echo "Options:"
  echo "  1) Migrate current branch only ($CURRENT_BRANCH)"
  echo "  2) Migrate all local branches"
  echo "  3) Migrate specific branch (you choose)"
  echo ""
  read -p "Choose option (1/2/3): " CHOICE
  
  case $CHOICE in
    1)
      migrate_branch "$CURRENT_BRANCH"
      ;;
    2)
      echo ""
      echo "Migrating all local branches..."
      echo ""
      
      # Get all local branches
      BRANCHES=$(git branch | sed 's/^[* ]*//')
      
      for BRANCH in $BRANCHES; do
        migrate_branch "$BRANCH"
      done
      ;;
    3)
      echo ""
      read -p "Enter branch name: " BRANCH_NAME
      migrate_branch "$BRANCH_NAME"
      ;;
    *)
      echo "❌ Invalid choice"
      exit 1
      ;;
  esac
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "✅ Migration Complete!"
  echo ""
  echo "📋 Summary:"
  echo "  - New structure: .cfoi/branches/[branch-name]/"
  echo "  - Tracking files: PROGRESS.md, ERRORS.md, DECISIONS.md, metrics.json"
  echo "  - Old slices preserved in: .cfoi/slices/ (can delete after verification)"
  echo ""
  echo "🎯 Next Steps:"
  echo "  1. Review migrated files in .cfoi/branches/[branch]/"
  echo "  2. Verify plan.md and tasks.md are correct"
  echo "  3. Continue with /implement or /plan in Windsurf"
  echo "  4. After confirming migration worked: rm -rf .cfoi/slices"
  echo ""
  echo "🔄 To update framework files (macros, workflows):"
  echo "  Run: /update in Windsurf"
  echo "  Or: ./install.sh --update"
  echo ""
}

# Run main function
main
