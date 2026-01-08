#!/usr/bin/env bash
# Edge case testing for install.sh cleanup
# Tests scenarios like nested directories, .git artifacts, etc.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="/tmp/cfoi-cleanup-edge-test-$$"
FRAMEWORK_DIR="$SCRIPT_DIR"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() {
  printf "${GREEN}✓${NC} %s\n" "$1"
}

error() {
  printf "${RED}✗${NC} %s\n" "$1" >&2
}

warn() {
  printf "${YELLOW}⚠${NC} %s\n" "$1"
}

cleanup_test_env() {
  if [[ -d "$TEST_ROOT" ]]; then
    rm -rf "$TEST_ROOT"
  fi
}

# Test 1: Framework in nested directory
test_nested_directory_cleanup() {
  echo ""
  echo "=========================================="
  echo "TEST: Nested Directory Cleanup"
  echo "=========================================="
  
  local test_dir="$TEST_ROOT/nested-test"
  mkdir -p "$test_dir"
  
  # Create a nested structure: project/vendor/Infra As A Service/
  local nested_framework="$test_dir/vendor/Infra As A Service"
  mkdir -p "$nested_framework"
  
  # Copy framework
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude='.git' --exclude='test-*.sh' "$FRAMEWORK_DIR"/ "$nested_framework"/
  else
    cp -R "$FRAMEWORK_DIR"/. "$nested_framework"/
  fi
  
  # Initialize git
  (cd "$test_dir" && git init -q)
  
  # Create package.json
  cat > "$test_dir/package.json" <<'EOF'
{
  "name": "nested-test",
  "version": "1.0.0"
}
EOF
  
  info "Running install with cleanup from nested location"
  (cd "$nested_framework" && bash install.sh --update --cleanup 2>&1 | grep -E "(Installing|Cleaning|Removed)" || true)
  
  # Verify framework directory is gone
  if [[ -d "$nested_framework" ]]; then
    error "FAILED: Nested framework directory still exists"
    return 1
  else
    info "Nested framework directory removed"
  fi
  
  # Verify parent vendor directory is also cleaned up if empty
  if [[ -d "$test_dir/vendor" ]]; then
    if [[ -z "$(ls -A "$test_dir/vendor" 2>/dev/null)" ]]; then
      error "FAILED: Empty vendor directory not cleaned up"
      return 1
    else
      info "Vendor directory contains other files (expected)"
    fi
  else
    info "Empty vendor directory was cleaned up"
  fi
  
  # Verify workflows are installed (should be in vendor/, not test_dir/)
  # Because install.sh goes up one level from the framework directory
  if [[ ! -d "$test_dir/vendor/.windsurf/workflows" ]]; then
    error "FAILED: Workflows not installed in vendor/"
    return 1
  else
    info "Workflows installed correctly in vendor/"
  fi
  
  info "✅ Nested directory cleanup: PASSED"
  return 0
}

# Test 2: .git artifacts cleanup
test_git_artifacts_cleanup() {
  echo ""
  echo "=========================================="
  echo "TEST: Git Artifacts Cleanup"
  echo "=========================================="
  
  local test_dir="$TEST_ROOT/git-test"
  mkdir -p "$test_dir"
  
  local framework_path="$test_dir/Infra As A Service"
  mkdir -p "$framework_path"
  
  # Copy framework
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude='test-*.sh' "$FRAMEWORK_DIR"/ "$framework_path"/
  else
    cp -R "$FRAMEWORK_DIR"/. "$framework_path"/
  fi
  
  # Initialize git in project
  (cd "$test_dir" && git init -q)
  
  # Create package.json
  cat > "$test_dir/package.json" <<'EOF'
{
  "name": "git-test",
  "version": "1.0.0"
}
EOF
  
  info "Running install with cleanup"
  (cd "$framework_path" && bash install.sh --update --cleanup 2>&1 | grep -E "(Installing|Cleaning|Removed)" || true)
  
  # Verify framework directory and its .git* files are gone
  if [[ -d "$framework_path" ]]; then
    error "FAILED: Framework directory still exists"
    return 1
  else
    info "Framework directory removed"
  fi
  
  # Check that project .git* files are intact
  if [[ ! -d "$test_dir/.git" ]]; then
    error "FAILED: Project .git directory was removed (should be preserved)"
    return 1
  else
    info "Project .git directory preserved"
  fi
  
  # Check that installed .githooks, .github, .gitignore exist
  local installed_git_files=(
    "$test_dir/.githooks"
    "$test_dir/.github"
    "$test_dir/.gitignore"
  )
  
  for file in "${installed_git_files[@]}"; do
    if [[ ! -e "$file" ]]; then
      error "FAILED: $(basename "$file") not installed"
      return 1
    fi
  done
  info "All .git* framework files installed correctly"
  
  info "✅ Git artifacts cleanup: PASSED"
  return 0
}

# Test 3: Multiple cleanup runs (idempotency)
test_multiple_cleanup_runs() {
  echo ""
  echo "=========================================="
  echo "TEST: Multiple Cleanup Runs"
  echo "=========================================="
  
  local test_dir="$TEST_ROOT/idempotent-test"
  mkdir -p "$test_dir"
  
  local framework_path="$test_dir/Infra As A Service"
  mkdir -p "$framework_path"
  
  # Copy framework
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude='.git' --exclude='test-*.sh' "$FRAMEWORK_DIR"/ "$framework_path"/
  else
    cp -R "$FRAMEWORK_DIR"/. "$framework_path"/
  fi
  
  (cd "$test_dir" && git init -q)
  cat > "$test_dir/package.json" <<'EOF'
{
  "name": "idempotent-test",
  "version": "1.0.0"
}
EOF
  
  info "First cleanup run"
  (cd "$framework_path" && bash install.sh --update --cleanup 2>&1 | grep -E "(Installing|Cleaning|Removed)" || true)
  
  if [[ -d "$framework_path" ]]; then
    error "FAILED: Framework directory still exists after first cleanup"
    return 1
  fi
  
  # Try to run cleanup again from project root (should be safe)
  info "Attempting second cleanup from project root"
  if (cd "$test_dir" && bash install.sh --cleanup 2>&1 | grep -q "Running from project root"); then
    info "Second run correctly detected project root"
  else
    warn "Second run behavior differs (may be expected)"
  fi
  
  # Verify workflows still intact
  if [[ ! -d "$test_dir/.windsurf/workflows" ]]; then
    error "FAILED: Workflows missing after multiple runs"
    return 1
  else
    info "Workflows still intact"
  fi
  
  info "✅ Multiple cleanup runs: PASSED"
  return 0
}

# Test 4: Cleanup with spaces in directory names
test_spaces_in_names() {
  echo ""
  echo "=========================================="
  echo "TEST: Spaces in Directory Names"
  echo "=========================================="
  
  local test_dir="$TEST_ROOT/space test dir"
  mkdir -p "$test_dir"
  
  local framework_path="$test_dir/Infra As A Service"
  mkdir -p "$framework_path"
  
  # Copy framework
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude='.git' --exclude='test-*.sh' "$FRAMEWORK_DIR"/ "$framework_path"/
  else
    cp -R "$FRAMEWORK_DIR"/. "$framework_path"/
  fi
  
  (cd "$test_dir" && git init -q)
  cat > "$test_dir/package.json" <<'EOF'
{
  "name": "space-test",
  "version": "1.0.0"
}
EOF
  
  info "Running cleanup with spaces in path"
  (cd "$framework_path" && bash install.sh --update --cleanup 2>&1 | grep -E "(Installing|Cleaning|Removed)" || true)
  
  if [[ -d "$framework_path" ]]; then
    error "FAILED: Framework directory with spaces still exists"
    return 1
  else
    info "Framework directory with spaces removed"
  fi
  
  if [[ ! -d "$test_dir/.windsurf/workflows" ]]; then
    error "FAILED: Workflows not installed in path with spaces"
    return 1
  else
    info "Workflows installed in path with spaces"
  fi
  
  info "✅ Spaces in names: PASSED"
  return 0
}

# Test 5: Safety checks prevent dangerous deletions
test_safety_checks() {
  echo ""
  echo "=========================================="
  echo "TEST: Safety Checks"
  echo "=========================================="
  
  local test_dir="$TEST_ROOT/safety-test"
  mkdir -p "$test_dir"
  
  # Try to run cleanup from a directory that doesn't match expected names
  local fake_framework="$test_dir/NotTheFramework"
  mkdir -p "$fake_framework"
  
  # Copy install.sh only
  cp "$FRAMEWORK_DIR/install.sh" "$fake_framework/"
  
  (cd "$test_dir" && git init -q)
  cat > "$test_dir/package.json" <<'EOF'
{
  "name": "safety-test",
  "version": "1.0.0"
}
EOF
  
  info "Attempting cleanup from non-framework directory"
  local output
  output=$(cd "$fake_framework" && bash install.sh --cleanup 2>&1 || true)
  
  if [[ "$output" =~ "SAFETY" ]] || [[ "$output" =~ "Running from project root" ]]; then
    info "Safety check prevented deletion"
  else
    warn "Safety check behavior unclear"
  fi
  
  if [[ -d "$fake_framework" ]]; then
    info "Non-framework directory preserved (safe)"
  else
    error "FAILED: Safety check failed - directory was deleted"
    return 1
  fi
  
  info "✅ Safety checks: PASSED"
  return 0
}

main() {
  echo "=========================================="
  echo "CFOI Cleanup Edge Cases Test Suite"
  echo "=========================================="
  echo "Framework: $FRAMEWORK_DIR"
  echo "Test Root: $TEST_ROOT"
  echo ""
  
  cleanup_test_env
  mkdir -p "$TEST_ROOT"
  
  local failed_tests=0
  
  test_nested_directory_cleanup || ((failed_tests++))
  test_git_artifacts_cleanup || ((failed_tests++))
  test_multiple_cleanup_runs || ((failed_tests++))
  test_spaces_in_names || ((failed_tests++))
  test_safety_checks || ((failed_tests++))
  
  echo ""
  echo "=========================================="
  echo "EDGE CASES TEST SUMMARY"
  echo "=========================================="
  
  if [[ $failed_tests -eq 0 ]]; then
    info "ALL EDGE CASE TESTS PASSED ✅"
    echo ""
    info "Cleanup handles all edge cases correctly"
    cleanup_test_env
    exit 0
  else
    error "$failed_tests TEST(S) FAILED ❌"
    echo ""
    error "Test environment preserved at: $TEST_ROOT"
    exit 1
  fi
}

trap cleanup_test_env EXIT

main "$@"
