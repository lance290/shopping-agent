#!/usr/bin/env bash
# Setup git hooks for the repository

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HOOKS_DIR="$ROOT_DIR/.githooks"

echo "🔧 Setting up git hooks..."
echo ""

# Check if .githooks directory exists
if [[ ! -d "$HOOKS_DIR" ]]; then
  echo "❌ Error: .githooks/ directory not found"
  echo "This script expects hooks to be in .githooks/"
  exit 1
fi

# Make all hooks executable
echo "📝 Making hooks executable..."
find "$HOOKS_DIR" -type f -exec chmod +x {} \;
echo "✅ Hooks are executable"
echo ""

# Configure git to use .githooks
echo "🔗 Configuring git to use .githooks/..."
if ! command -v git >/dev/null 2>&1; then
  echo "❌ Error: git not found"
  exit 1
fi

git config core.hooksPath .githooks
echo "✅ Git configured: core.hooksPath = .githooks"
echo ""

# Verify configuration
CONFIGURED_PATH=$(git config core.hooksPath)
if [[ "$CONFIGURED_PATH" == ".githooks" ]]; then
  echo "🎉 Success! Git hooks are now active"
  echo ""
  echo "Available hooks:"
  ls -1 "$HOOKS_DIR" | grep -v '\.sample$' | grep -v '\.md$' | sed 's/^/  • /'
  echo ""
  echo "These hooks will run automatically on git operations."
else
  echo "⚠️  Warning: Configuration may not have applied correctly"
  echo "Current value: $CONFIGURED_PATH"
  exit 1
fi
