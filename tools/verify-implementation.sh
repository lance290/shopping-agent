#!/usr/bin/env bash
# Verify AI hasn't cut corners during implementation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/verify-lib"

for lib in env metrics commands coverage static-checks; do
  LIB_PATH="$LIB_DIR/$lib.sh"
  if [[ ! -f "$LIB_PATH" ]]; then
    echo "Missing verifier library: $LIB_PATH" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$LIB_PATH"
done

echo "🔍 Verifying implementation quality..."
echo ""

if detect_test_command >/dev/null 2>&1; then
  TEST_COMMAND=$(detect_test_command)
  run_and_capture "tests" "$TEST_COMMAND" "$TEST_RESULTS_DIR" || true
else
  echo "⚠️  No automatic test command detected. Set CFOI_TEST_COMMAND to capture test evidence."
  echo ""
fi

if detect_coverage_command >/dev/null 2>&1; then
  COVERAGE_COMMAND=$(detect_coverage_command)
  if run_and_capture "coverage" "$COVERAGE_COMMAND" "$COVERAGE_DIR"; then
    capture_coverage_summary
    local cov_status="pass"
    [ "$LAST_COVERAGE_STATUS" -ne 0 ] && cov_status="fail"
    local summary_path="$COVERAGE_DIR/latest-summary.json"
    local regressions_path="$COVERAGE_DIR/coverage-regressions.json"
    record_coverage_evidence "$summary_path" "$cov_status" "$COVERAGE_COMMAND" "$regressions_path"
  else
    echo "⚠️  Coverage command failed; skipping summary capture."
    local summary_path="$COVERAGE_DIR/latest-summary.json"
    local regressions_path="$COVERAGE_DIR/coverage-regressions.json"
    record_coverage_evidence "$summary_path" "fail" "$COVERAGE_COMMAND" "$regressions_path"
  fi
else
  echo "⚠️  No automatic coverage command detected. Set CFOI_COVERAGE_COMMAND to capture coverage evidence."
  echo ""
fi

check_git_hooks_configured
check_typescript
check_lazy_patterns
check_duplicate_code
check_north_star_alignment
check_imports_position
check_test_quality
check_error_handling
check_deleted_tests

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAIL" -eq 0 ]; then
  echo "✅ Implementation verification PASSED"
  echo ""
  echo "All quality checks passed. Ready to commit!"
  exit 0
else
  echo "❌ Implementation verification FAILED"
  echo ""
  echo "Found $FAIL issue(s) that need to be fixed before committing."
  echo ""
  echo "Common fixes:"
  echo "  - Remove TODO/FIXME comments (implement the code instead)"
  echo "  - Replace placeholder functions with real implementations"
  echo "  - Move imports to top of file"
  echo "  - Write substantial tests (not just imports)"
  echo "  - Add error handling"
  echo ""
  echo "Run this script again after fixing issues."
  exit 1
fi
