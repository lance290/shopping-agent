# shellcheck shell=bash

detect_test_command() {
  if [ -n "${CFOI_TEST_COMMAND:-}" ]; then
    echo "$CFOI_TEST_COMMAND"
    return 0
  fi

  if [ -f "package.json" ] && command -v npm >/dev/null 2>&1; then
    echo "npm run test -- --watch=false"
    return 0
  fi

  if command -v pnpm >/dev/null 2>&1 && [ -f "package.json" ]; then
    echo "pnpm test -- --watch=false"
    return 0
  fi

  if command -v yarn >/dev/null 2>&1 && [ -f "package.json" ]; then
    echo "yarn test --watch=false"
    return 0
  fi

  if command -v pytest >/dev/null 2>&1; then
    echo "pytest"
    return 0
  fi

  if command -v go >/dev/null 2>&1 && [ -f "go.mod" ]; then
    echo "go test ./..."
    return 0
  fi

  return 1
}

detect_coverage_command() {
  if [ -n "${CFOI_COVERAGE_COMMAND:-}" ]; then
    echo "$CFOI_COVERAGE_COMMAND"
    return 0
  fi

  if [ -f "package.json" ] && command -v npm >/dev/null 2>&1 && npm run -s | grep -q "coverage"; then
    echo "npm run coverage"
    return 0
  fi

  if command -v pnpm >/dev/null 2>&1 && [ -f "package.json" ] && pnpm run | grep -q "coverage"; then
    echo "pnpm coverage"
    return 0
  fi

  if command -v yarn >/dev/null 2>&1 && [ -f "package.json" ] && yarn run | grep -q "coverage"; then
    echo "yarn coverage"
    return 0
  fi

  if command -v pytest >/dev/null 2>&1; then
    echo "pytest --cov"
    return 0
  fi

  return 1
}

run_and_capture() {
  local label=$1
  local command=$2
  local output_dir=$3

  mkdir -p "$output_dir"
  local logfile="$output_dir/${label}-$(timestamp).log"

  echo "🧪 Running $label: $command"

  set +e
  eval "$command" 2>&1 | tee "$logfile"
  local status=$?
  set -e

  cp "$logfile" "$output_dir/latest.log"

  if [ $status -ne 0 ]; then
    echo "  ❌ $label failed (exit $status). See $logfile"
    FAIL=$((FAIL+1))
  else
    echo "  ✅ $label completed. Evidence stored at $logfile"
  fi

  echo ""

  if [ "$label" = "tests" ]; then
    local result="fail"
    [ $status -eq 0 ] && result="pass"
    record_test_evidence "$result" "$command" "$logfile"
  fi

  if [ "$label" = "coverage" ]; then
    LAST_COVERAGE_COMMAND="$command"
    LAST_COVERAGE_STATUS=$status
    LAST_COVERAGE_LOG="$logfile"
  fi

  return $status
}
