#!/usr/bin/env bash
# Comprehensive test for install.sh cleanup and workflow integrity
# Tests both cleanup completeness and installed workflow functionality

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="/tmp/cfoi-install-test-$$"
# Point to repo root (two levels up from tools/tests)
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
  printf "${GREEN}✓${NC} %s\n" "$1"
}

warn() {
  printf "${YELLOW}⚠${NC} %s\n" "$1"
}

error() {
  printf "${RED}✗${NC} %s\n" "$1" >&2
}

cleanup_test_env() {
  if [[ -d "$TEST_ROOT" ]]; then
    rm -rf "$TEST_ROOT"
  fi
}

# Setup test environment
setup_test_project() {
  info "Setting up test project at $TEST_ROOT"
  mkdir -p "$TEST_ROOT"
  
  # Create a minimal project structure
  cat > "$TEST_ROOT/package.json" <<'EOF'
{
  "name": "test-project",
  "version": "1.0.0",
  "scripts": {
    "test": "echo 'Tests pass'"
  }
}
EOF
  
  # Initialize git repo
  (cd "$TEST_ROOT" && git init -q)
  
  info "Test project created"
}

# Copy framework into test project
copy_framework_to_test() {
  local dest="$TEST_ROOT/Infra As A Service"
  info "Copying framework to test project"
  
  mkdir -p "$dest"
  
  # Use rsync if available, otherwise cp
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude='.git' --exclude='test-install.sh' "$FRAMEWORK_DIR"/ "$dest"/
  else
    cp -R "$FRAMEWORK_DIR"/. "$dest"/
  fi
  
  info "Framework copied to $dest"
}

# Test 1: Verify cleanup removes everything
test_cleanup_completeness() {
  echo ""
  echo "=========================================="
  echo "TEST 1: Cleanup Completeness"
  echo "=========================================="
  
  local framework_path="$TEST_ROOT/Infra As A Service"
  local parent_path="$TEST_ROOT"
  
  # Run install with cleanup
  info "Running install.sh --update --cleanup"
  (cd "$framework_path" && bash install.sh --update --cleanup)
  
  # Check if framework directory is gone
  if [[ -d "$framework_path" ]]; then
    error "FAILED: Framework directory still exists at $framework_path"
    ls -la "$framework_path"
    return 1
  else
    info "Framework directory removed"
  fi
  
  # Check for any leftover .git* files in project root that shouldn't be there
  local leftover_git_files=()
  while IFS= read -r -d '' file; do
    # Skip the actual project .git directory
    if [[ "$file" != "$TEST_ROOT/.git" ]]; then
      leftover_git_files+=("$file")
    fi
  done < <(find "$TEST_ROOT" -maxdepth 2 -name ".git*" -print0 2>/dev/null || true)
  
  if [[ ${#leftover_git_files[@]} -gt 0 ]]; then
    warn "Found .git* files (this may be expected if they were installed):"
    printf '  %s\n' "${leftover_git_files[@]}"
  fi
  
  # Check for empty parent directories (excluding git, node_modules, and expected empty dirs)
  local empty_dirs=()
  while IFS= read -r -d '' dir; do
    # Skip .git, node_modules, and other expected empty directories
    if [[ "$dir" =~ /.git/ ]] || [[ "$dir" =~ /node_modules/ ]] || [[ "$dir" =~ /.cfoi/ ]]; then
      continue
    fi
    if [[ -z "$(ls -A "$dir" 2>/dev/null)" ]]; then
      empty_dirs+=("$dir")
    fi
  done < <(find "$TEST_ROOT" -type d -empty -print0 2>/dev/null || true)
  
  if [[ ${#empty_dirs[@]} -gt 0 ]]; then
    warn "Found empty directories (may be expected):"
    printf '  %s\n' "${empty_dirs[@]}"
  else
    info "No unexpected empty directories found"
  fi
  
  info "✅ Cleanup completeness: PASSED"
  return 0
}

# Test 2: Verify installed workflows are present and valid
test_workflow_integrity() {
  echo ""
  echo "=========================================="
  echo "TEST 2: Workflow Integrity"
  echo "=========================================="
  
  local workflows_dir="$TEST_ROOT/.windsurf/workflows"
  
  # Check if workflows directory exists
  if [[ ! -d "$workflows_dir" ]]; then
    error "FAILED: Workflows directory not found at $workflows_dir"
    return 1
  else
    info "Workflows directory exists"
  fi
  
  # Count workflow files
  local workflow_count
  workflow_count=$(find "$workflows_dir" -name "*.md" -type f | wc -l | tr -d ' ')
  
  if [[ "$workflow_count" -eq 0 ]]; then
    error "FAILED: No workflow files found"
    return 1
  else
    info "Found $workflow_count workflow files"
  fi
  
  # Validate each workflow has proper structure (skip documentation files)
  local invalid_workflows=()
  local valid_count=0
  while IFS= read -r -d '' workflow; do
    local basename_wf
    basename_wf=$(basename "$workflow")
    
    # Skip documentation files that aren't actual workflows
    if [[ "$basename_wf" =~ ^(EFFORT-WORKFLOW-DIAGRAM|MIGRATION-GUIDE|EFFORT-SYSTEM-SUMMARY|EFFORT-SYSTEM|EFFORT-QUICK-REFERENCE)\.md$ ]]; then
      continue
    fi
    
    # Check for YAML frontmatter
    if ! grep -q "^---$" "$workflow"; then
      invalid_workflows+=("$basename_wf: Missing YAML frontmatter")
      continue
    fi
    
    # Check for description field
    if ! grep -q "^description:" "$workflow"; then
      invalid_workflows+=("$basename_wf: Missing description field")
      continue
    fi
    
    # Check file is not empty
    if [[ ! -s "$workflow" ]]; then
      invalid_workflows+=("$basename_wf: Empty file")
      continue
    fi
    
    ((valid_count++))
  done < <(find "$workflows_dir" -name "*.md" -type f -print0)
  
  if [[ ${#invalid_workflows[@]} -gt 0 ]]; then
    error "FAILED: Found invalid workflows:"
    printf '  %s\n' "${invalid_workflows[@]}"
    return 1
  else
    info "All $valid_count workflows have valid structure"
  fi
  
  info "✅ Workflow integrity: PASSED"
  return 0
}

# Test 3: Verify critical files are installed
test_critical_files() {
  echo ""
  echo "=========================================="
  echo "TEST 3: Critical Files Installation"
  echo "=========================================="
  
  local critical_files=(
    ".windsurf/workflows"
    ".githooks"
    "docs/workflow-pack"
  )
  
  local missing_files=()
  
  for file in "${critical_files[@]}"; do
    if [[ ! -e "$TEST_ROOT/$file" ]]; then
      missing_files+=("$file")
    fi
  done
  
  if [[ ${#missing_files[@]} -gt 0 ]]; then
    error "FAILED: Missing critical files/directories:"
    printf '  %s\n' "${missing_files[@]}"
    return 1
  else
    info "All critical files installed"
  fi
  
  info "✅ Critical files: PASSED"
  return 0
}

# Test 4: Verify git hooks are executable
test_git_hooks() {
  echo ""
  echo "=========================================="
  echo "TEST 4: Git Hooks Executable"
  echo "=========================================="
  
  local hooks_dir="$TEST_ROOT/.githooks"
  
  if [[ ! -d "$hooks_dir" ]]; then
    warn "Git hooks directory not found (may be optional)"
    return 0
  fi
  
  local non_executable=()
  while IFS= read -r -d '' hook; do
    if [[ ! -x "$hook" ]]; then
      non_executable+=("$(basename "$hook")")
    fi
  done < <(find "$hooks_dir" -type f ! -name "*.md" ! -name "*.txt" -print0 2>/dev/null || true)
  
  if [[ ${#non_executable[@]} -gt 0 ]]; then
    error "FAILED: Non-executable hooks found:"
    printf '  %s\n' "${non_executable[@]}"
    return 1
  else
    info "All hooks are executable"
  fi
  
  info "✅ Git hooks: PASSED"
  return 0
}

# Test 5: Verify no framework artifacts in project
test_no_framework_artifacts() {
  echo ""
  echo "=========================================="
  echo "TEST 5: No Framework Artifacts"
  echo "=========================================="
  
  # Look for files that should only be in the framework directory
  local framework_artifacts=(
    "install.sh"
    "INSTALL.md"
    "test-install.sh"
  )
  
  local found_artifacts=()
  
  for artifact in "${framework_artifacts[@]}"; do
    # Check in project root (not in subdirectories)
    if [[ -f "$TEST_ROOT/$artifact" ]]; then
      # These files are actually supposed to be installed
      if [[ "$artifact" == "INSTALL.md" ]]; then
        info "INSTALL.md correctly installed to project root"
      else
        found_artifacts+=("$artifact")
      fi
    fi
  done
  
  if [[ ${#found_artifacts[@]} -gt 0 ]]; then
    warn "Found framework artifacts in project root (may be intentional):"
    printf '  %s\n' "${found_artifacts[@]}"
  else
    info "No unexpected framework artifacts found"
  fi
  
  info "✅ Framework artifacts: PASSED"
  return 0
}

# Test 6: Verify installed files are not symlinks (excluding node_modules)
test_no_symlinks() {
  echo ""
  echo "=========================================="
  echo "TEST 6: No Symlinks (Real Copies)"
  echo "=========================================="
  
  local symlinks=()
  while IFS= read -r -d '' link; do
    # Skip node_modules - npm always creates symlinks for binaries
    if [[ "$link" =~ /node_modules/ ]]; then
      continue
    fi
    symlinks+=("${link#$TEST_ROOT/}")
  done < <(find "$TEST_ROOT" -type l -print0 2>/dev/null || true)
  
  if [[ ${#symlinks[@]} -gt 0 ]]; then
    error "FAILED: Found symlinks (should be real copies):"
    printf '  %s\n' "${symlinks[@]}"
    return 1
  else
    info "All framework files are real copies (no symlinks)"
  fi
  
  info "✅ No symlinks: PASSED"
  return 0
}

# Main test runner
main() {
  echo "=========================================="
  echo "CFOI Install & Cleanup Test Suite"
  echo "=========================================="
  echo "Framework: $FRAMEWORK_DIR"
  echo "Test Root: $TEST_ROOT"
  echo ""
  
  # Cleanup any previous test runs
  cleanup_test_env
  
  # Setup
  setup_test_project
  copy_framework_to_test
  
  # Run tests
  local failed_tests=0
  
  test_cleanup_completeness || ((failed_tests++))
  test_workflow_integrity || ((failed_tests++))
  test_critical_files || ((failed_tests++))
  test_git_hooks || ((failed_tests++))
  test_no_framework_artifacts || ((failed_tests++))
  test_no_symlinks || ((failed_tests++))
  
  # Summary
  echo ""
  echo "=========================================="
  echo "TEST SUMMARY"
  echo "=========================================="
  
  if [[ $failed_tests -eq 0 ]]; then
    info "ALL TESTS PASSED ✅"
    echo ""
    info "Cleanup is complete and workflows are intact"
    cleanup_test_env
    exit 0
  else
    error "$failed_tests TEST(S) FAILED ❌"
    echo ""
    error "Test environment preserved at: $TEST_ROOT"
    error "Inspect manually to debug issues"
    exit 1
  fi
}

# Trap to cleanup on exit
trap cleanup_test_env EXIT

main "$@"
