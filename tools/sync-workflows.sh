#!/usr/bin/env bash
# Sync workflows between:
# - .windsurf/workflows (Windsurf)
# - .agent/workflows (Antigravity)
# - .claude/commands (Claude Code)
# - .codex/commands (GPT-5.2 Codex)
# - .gemini/commands (Gemini CLI)

set -euo pipefail

# Get the project root (directory where this script's parent 'tools' directory lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WINDSURF_DIR="$ROOT_DIR/.windsurf/workflows"

# Target directories
AGENT_DIR="$ROOT_DIR/.agent/workflows"
CLAUDE_DIR="$ROOT_DIR/.claude/commands"
CODEX_DIR="$ROOT_DIR/.codex/commands"
GEMINI_DIR="$ROOT_DIR/.gemini/commands"

echo "🔄 Syncing workflows across AI platforms..."
echo ""

if [ ! -d "$WINDSURF_DIR" ]; then
  echo "❌ Error: $WINDSURF_DIR not found"
  exit 1
fi

# Create target directories
mkdir -p "$AGENT_DIR" "$CLAUDE_DIR" "$CODEX_DIR" "$GEMINI_DIR"

# Clean target directories
rm -rf "${AGENT_DIR}"/* "${CLAUDE_DIR}"/* "${CODEX_DIR}"/* "${GEMINI_DIR}"/*

# Create symlinks for each workflow
for workflow in "$WINDSURF_DIR"/*.md; do
  if [ -f "$workflow" ]; then
    filename=$(basename "$workflow")
    
    # Create absolute path for symlink target
    abs_workflow_path="$(cd "$(dirname "$workflow")" && pwd)/$filename"
    
    # Antigravity (Markdown)
    ln -sf "$abs_workflow_path" "$AGENT_DIR/$filename"
    
    # Claude Code (Markdown)
    ln -sf "$abs_workflow_path" "$CLAUDE_DIR/$filename"
    
    # Codex (Markdown)
    ln -sf "$abs_workflow_path" "$CODEX_DIR/$filename"
    
    # Gemini (Markdown)
    ln -sf "$abs_workflow_path" "$GEMINI_DIR/$filename"
    
    echo "  ✅ Linked: $filename"
  fi
done

echo ""
echo "🎉 Workflows synced across all platforms!"
echo ""
echo "📁 Source (Windsurf): .windsurf/workflows/"
echo "📁 Antigravity:       .agent/workflows/"
echo "📁 Claude Code:       .claude/commands/"
echo "📁 GPT-5.2 Codex:     .codex/commands/"
echo "📁 Gemini CLI:        .gemini/commands/"
echo ""
echo "Changes to source workflows will affect all platforms automatically."
