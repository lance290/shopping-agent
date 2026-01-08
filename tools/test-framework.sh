#!/usr/bin/env bash
# Smoke test for the Windsurf workflow pack
# Usage: bash tools/test-framework.sh

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
TMP_ROOT="$(mktemp -d 2>/dev/null || mktemp -d -t framework-test)"
cleanup() { rm -rf "$TMP_ROOT"; }
trap cleanup EXIT

FRAMEWORK_SRC="$ROOT_DIR"
PACK_ARCHIVE="$TMP_ROOT/Infra-As-Code-pack"
HOST_ROOT="$TMP_ROOT/host-project"
DEST_PACK="$HOST_ROOT/Infra-As-Code"

mkdir -p "$HOST_ROOT" "$PACK_ARCHIVE"

copy_pack() {
  local src="$1"
  local dest="$2"
  mkdir -p "$dest"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude '.git' --exclude 'node_modules' "$src/" "$dest/"
  else
    (cd "$src" && tar --exclude='.git' --exclude='node_modules' -cf - .) | (cd "$dest" && tar -xf -)
  fi
}

copy_pack "$FRAMEWORK_SRC" "$PACK_ARCHIVE"

reset_framework_copy() {
  rm -rf "$DEST_PACK"
  copy_pack "$PACK_ARCHIVE" "$DEST_PACK"
}

run_install() {
  local extra_flags=("$@")
  reset_framework_copy
  pushd "$DEST_PACK" >/dev/null
  if [ ${#extra_flags[@]} -gt 0 ]; then
    ./install.sh --update --target "$HOST_ROOT" "${extra_flags[@]}" >/dev/null
  else
    ./install.sh --update --target "$HOST_ROOT" >/dev/null
  fi
  popd >/dev/null
}

echo "▶ Running install.sh smoke test (fresh install)…"
run_install
PROJECT_ROOT="$HOST_ROOT"

assert_dir() {
  local path="$1"
  if [ ! -d "$path" ]; then
    echo "❌ Expected directory missing: $path"
    exit 1
  fi
}

assert_file() {
  local path="$1"
  if [ ! -f "$path" ]; then
    echo "❌ Expected file missing: $path"
    exit 1
  fi
}

assert_grep() {
  local pattern="$1"
  local file="$2"
  if ! grep -qE "$pattern" "$file"; then
    echo "❌ Pattern '$pattern' not found in $file"
    exit 1
  fi
}

echo "✔ Fresh installation completed"

assert_dir "$PROJECT_ROOT/docs/setup"
assert_file "$PROJECT_ROOT/docs/setup/SERVICES_GCP.md"
assert_dir "$PROJECT_ROOT/.cfoi/branches"
assert_file "$PROJECT_ROOT/tools/verify-implementation.sh"
assert_grep ".cfoi/branches" "$PROJECT_ROOT/tools/slice-new.ts"
assert_grep ".venv detected but not active" "$PROJECT_ROOT/.githooks/pre-commit"

EXCLUDE_FILE="$PROJECT_ROOT/.git/info/exclude"
assert_file "$EXCLUDE_FILE"
while read -r pattern; do
  [ -z "$pattern" ] && continue
  if [[ "$pattern" == ";;" ]]; then
    continue
  fi
done <<'PATTERNS'
# CFOI work artifacts (per-developer, local only)
.cfoi/
# Optional local AI checklists
checklist-*.md
# Optional personal notes
*-notes.md
*-scratch.md
# Windsurf transient artifacts
.swarm/
.windsurf/cache/
.checkpoint
PATTERNS

echo "✔ Fresh install assets validated"

mkdir -p "$PROJECT_ROOT/.cfoi/branches/main/efforts/demo"
touch "$PROJECT_ROOT/.cfoi/branches/main/efforts/demo/plan.md"

run_install

if [ ! -d "$PROJECT_ROOT/.cfoi/branches/main/efforts/demo" ]; then
  echo "❌ Effort directory removed during update"
  exit 1
fi

echo "✔ Update preserved existing effort directories"

run_install --cleanup

if [ -d "$DEST_PACK" ]; then
  echo "❌ Framework directory still exists after cleanup"
  exit 1
fi

echo "✔ Cleanup removed framework copy"

echo "✅ Framework smoke test passed"

# Optionally run bats test suite if available
if command -v bats >/dev/null 2>&1; then
  echo "▶ Running bats test suite…"
  if [ -d "$ROOT_DIR/tests/bats" ]; then
    bats -r "$ROOT_DIR/tests/bats"
  else
    echo "ℹ️  No bats tests found at tests/bats — skipping"
  fi
else
  echo "ℹ️  bats not installed — skipping extended test suite"
fi
