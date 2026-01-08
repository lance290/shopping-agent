# shellcheck shell=bash

ROOT_DIR=$(git rev-parse --show-toplevel)
cd "$ROOT_DIR" || exit 1

FAIL=0

PYTHON_BIN="python3"
if [ -d "$ROOT_DIR/.venv" ] && [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached-head")
if [ "$CURRENT_BRANCH" = "HEAD" ]; then
  CURRENT_BRANCH="detached-head"
fi

CFOI_BRANCH_DIR=".cfoi/branches/$CURRENT_BRANCH"
TEST_RESULTS_DIR="$CFOI_BRANCH_DIR/test-results"
COVERAGE_DIR="$CFOI_BRANCH_DIR/coverage"
PROOF_DIR="$CFOI_BRANCH_DIR/proof"

mkdir -p "$TEST_RESULTS_DIR" "$COVERAGE_DIR" "$PROOF_DIR"

METRICS_FILE="$CFOI_BRANCH_DIR/metrics.json"
METRICS_AVAILABLE=true

LAST_COVERAGE_COMMAND=""
LAST_COVERAGE_STATUS=0
LAST_COVERAGE_LOG=""

timestamp() {
  date -u +"%Y%m%dT%H%M%SZ"
}
