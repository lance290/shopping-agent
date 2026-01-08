#!/bin/bash
set -e

# Cleanup Project - Remove AI Tool Clutter
# Usage: Copy framework into your project, cd into it, run: ./tools/cleanup-project.sh

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
echo "🧹 Cleaning up AI tool directories in: $PROJECT_ROOT"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# List of AI tool directories to remove
AI_TOOL_DIRS=(
  ".claude"
  ".claude-flow"
  ".cursor"
  ".hive-mind"
  ".husky"
  ".kombai"
  ".roo"
  ".swarm"
  ".taskmaster"
  ".vscode"
)

# Config files to remove
AI_TOOL_FILES=(
  ".roomodes"
  ".taskmasterconfig"
  ".windsurfrules"
  "claude-flow"
)

REMOVED_COUNT=0
KEPT_COUNT=0

# Remove directories
for DIR in "${AI_TOOL_DIRS[@]}"; do
  if [ -d "$DIR" ]; then
    # Check if directory is empty
    if [ -z "$(ls -A "$DIR")" ]; then
      echo "  🗑️  Removing empty directory: $DIR"
      rm -rf "$DIR"
      ((REMOVED_COUNT++))
    else
      echo "  ⚠️  Skipping non-empty directory: $DIR (review manually)"
      ((KEPT_COUNT++))
    fi
  fi
done

# Remove config files
for FILE in "${AI_TOOL_FILES[@]}"; do
  if [ -f "$FILE" ]; then
    echo "  🗑️  Removing config file: $FILE"
    rm -f "$FILE"
    ((REMOVED_COUNT++))
  fi
done

echo ""
echo "✅ Cleanup complete!"
echo "  Removed: $REMOVED_COUNT items"
if [ $KEPT_COUNT -gt 0 ]; then
  echo "  ⚠️  Kept: $KEPT_COUNT non-empty directories (review manually)"
fi
echo ""
echo "Note: .windsurf/ kept - will be populated with workflow pack"
echo "      .cfoi/ kept - will be migrated to new structure"
