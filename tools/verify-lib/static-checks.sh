# shellcheck shell=bash

check_git_hooks_configured() {
  if [ -d "$ROOT_DIR/.githooks" ]; then
    echo "🔍 Checking git hooks configuration..."
    
    if ! command -v git >/dev/null 2>&1; then
      echo "  ℹ️  Git not found, skipping hooks check"
      echo ""
      return
    fi
    
    HOOKS_PATH=$(git config core.hooksPath 2>/dev/null || echo "")
    
    if [ "$HOOKS_PATH" = ".githooks" ]; then
      echo "  ✅ Git hooks configured correctly (core.hooksPath = .githooks)"
    else
      echo "  ⚠️  Git hooks not configured!"
      echo "  Expected: core.hooksPath = .githooks"
      echo "  Current: ${HOOKS_PATH:-<not set>}"
      echo ""
      echo "  Fix: Run ./tools/setup-hooks.sh"
      echo "  Or: git config core.hooksPath .githooks"
      echo ""
      echo "  Without this, git hooks won't run automatically!"
      # Don't fail, just warn - this is a setup issue, not a code quality issue
    fi
    echo ""
  fi
}

check_typescript() {
  if [ -f "$ROOT_DIR/tsconfig.json" ] && command -v npx >/dev/null 2>&1; then
    echo "🔍 Running TypeScript type checker..."
    
    TS_FILES=$(find "$ROOT_DIR" -name "*.ts" -o -name "*.tsx" 2>/dev/null | grep -v node_modules | grep -v dist | grep -v build | grep -v "\.cfoi/" | head -1)
    
    if [ -n "$TS_FILES" ]; then
      TSC_LOG="$TEST_RESULTS_DIR/tsc-$(timestamp).log"
      set +e
      npx tsc --noEmit > "$TSC_LOG" 2>&1
      TSC_STATUS=$?
      set -e
      
      if [ $TSC_STATUS -ne 0 ]; then
        REAL_ERRORS=$(grep -v "Unsafe use of any" "$TSC_LOG" | grep -E '^.*\([0-9]+,[0-9]+\): error TS[0-9]+:' | grep -v "\.cfoi/" || true)
        ANY_WARNINGS=$(grep "Unsafe use of any" "$TSC_LOG" | grep -v "\.cfoi/" || true)
        
        ERROR_COUNT=$(echo "$REAL_ERRORS" | grep -c "error TS" || echo 0)
        WARNING_COUNT=$(echo "$ANY_WARNINGS" | wc -l | tr -d ' ')
        
        if [ -n "$ANY_WARNINGS" ] && [ "$WARNING_COUNT" -gt 0 ]; then
          echo "  ⚠️  TypeScript 'any' type warnings: $WARNING_COUNT (non-blocking)"
          echo "$ANY_WARNINGS" | head -5
          if [ "$WARNING_COUNT" -gt 5 ]; then
            echo "     ... and $((WARNING_COUNT - 5)) more 'any' warnings"
          fi
          echo ""
        fi
        
        if [ -n "$REAL_ERRORS" ] && [ "$ERROR_COUNT" -gt 0 ]; then
          echo "  ❌ TypeScript type errors: $ERROR_COUNT"
          echo "$REAL_ERRORS" | head -20
          if [ "$ERROR_COUNT" -gt 20 ]; then
            echo "     ... and $((ERROR_COUNT - 20)) more errors"
          fi
          echo "  📋 Full log: $TSC_LOG"
          FAIL=$((FAIL+10))
        fi
      else
        echo "  ✅ TypeScript type checking passed"
      fi
      
      cp "$TSC_LOG" "$TEST_RESULTS_DIR/tsc-latest.log"
    else
      echo "  ℹ️  No TypeScript files detected, skipping type check"
    fi
    echo ""
  fi
}

check_lazy_patterns() {
  echo "📋 Checking for lazy patterns (TODO, FIXME, placeholders)..."
  STAGED=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.(js|ts|tsx|jsx|py|go|rs|java|cs)$' || true)

  if [ -n "$STAGED" ]; then
    for file in $STAGED; do
      [ -f "$file" ] || continue
      
      TODO_COUNT=$(grep -n 'TODO:' "$file" | wc -l | tr -d ' ')
      if [ "$TODO_COUNT" -gt 0 ]; then
        echo "  ❌ $file: Found $TODO_COUNT TODO comments"
        grep -n 'TODO:' "$file" | head -3
        FAIL=$((FAIL+1))
      fi
      
      FIXME_COUNT=$(grep -n 'FIXME:' "$file" | wc -l | tr -d ' ')
      if [ "$FIXME_COUNT" -gt 0 ]; then
        echo "  ❌ $file: Found $FIXME_COUNT FIXME comments"
        grep -n 'FIXME:' "$file" | head -3
        FAIL=$((FAIL+1))
      fi
      
      if grep -qE '(placeholder|implement.*this|coming soon|not implemented|raise NotImplementedError|^[[:space:]]*pass[[:space:]]*$)' "$file"; then
        echo "  ❌ $file: Contains placeholder implementation"
        grep -nE '(placeholder|implement.*this|coming soon)' "$file" | head -3
        FAIL=$((FAIL+1))
      fi
    done
    
    if [ "$FAIL" -eq 0 ]; then
      echo "  ✅ No lazy patterns found"
    fi
  else
    echo "  ℹ️  No code files staged"
  fi

  echo ""
}

check_duplicate_code() {
  echo "🔄 Checking for duplicate code (DRY principle)..."
  STAGED=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.(js|ts|tsx|jsx|py|go|rs|java|cs)$' || true)
  
  if [ -n "$STAGED" ]; then
    for file in $STAGED; do
      [ -f "$file" ] || continue
      
      TEMP_FILE=$(mktemp)
      awk 'NF > 0' "$file" > "$TEMP_FILE"
      
      DUPLICATES=0
      LINE_COUNT=$(wc -l < "$TEMP_FILE" | tr -d ' ')
      
      if [ "$LINE_COUNT" -gt 10 ]; then
        for i in $(seq 1 $((LINE_COUNT - 4))); do
          COUNT=$(awk "NR >= $i && NR <= $LINE_COUNT" "$TEMP_FILE" | \
                  grep -F "$(sed -n "${i}p" "$TEMP_FILE")" | wc -l | tr -d ' ')
          
          if [ "$COUNT" -ge 3 ]; then
            DUPLICATES=$((DUPLICATES + 1))
            break
          fi
        done
      fi
      
      rm -f "$TEMP_FILE"
      
      if [ "$DUPLICATES" -gt 0 ]; then
        echo "  ⚠️  $file: Potential duplicate code detected"
        echo "     Consider extracting repeated logic into reusable functions (DRY principle)"
        echo "     Run a code duplication tool (jscpd, PMD, SonarQube) for detailed analysis"
      fi
    done
    
    echo "  ℹ️  For better duplicate detection, consider adding:"
    echo "     - JavaScript/TypeScript: jscpd, ESLint with sonarjs plugin"
    echo "     - Python: pylint with duplicate-code check"
    echo "     - Multi-language: SonarQube, PMD Copy/Paste Detector"
    echo ""
  else
    echo "  ℹ️  No code files staged"
  fi

  echo ""
}

check_north_star_alignment() {
  echo "🌟 Ensuring proof artifacts cite the active north star..."
  if [ -d "$PROOF_DIR" ]; then
    RECENT_PROOF_FILES=$(find "$PROOF_DIR" -maxdepth 3 -type f -name '*.md' -mmin 720 2>/dev/null | sort)
    if [ -z "$RECENT_PROOF_FILES" ]; then
      echo "  ℹ️  No recent proof markdown files detected under $PROOF_DIR (last 12h)"
      echo "     This is normal early in an effort. Check will enforce once proof artifacts exist."
    else
      local alignment_issues=0
      for proof_file in $RECENT_PROOF_FILES; do
        base_name=$(basename "$proof_file")
        case "$base_name" in
          build-log.md|manual.md|automation.md|alignment.md)
            if ! grep -qi 'product-north-star' "$proof_file"; then
              echo "  ⚠️  $proof_file: Missing explicit product/effort north star reference"
              alignment_issues=$((alignment_issues+1))
            fi
            ;;
          *)
            :
            ;;
        esac
      done

      if [ "$alignment_issues" -eq 0 ]; then
        echo "  ✅ Recent proof artifacts reference the product/effort north star"
      else
        echo "  ⚠️  $alignment_issues proof file(s) missing north star references (non-blocking)"
        echo "     Add references to product-north-star.md or effort north star in proof artifacts"
      fi
    fi
  else
    echo "  ℹ️  Proof directory $PROOF_DIR not found yet"
    echo "     This is normal for new efforts. Directory will be created during /implement"
  fi

  echo ""
}

check_imports_position() {
  echo "📦 Checking imports are at top of files..."
  STAGED=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.(js|ts|tsx|jsx|py|go|rs|java|cs)$' || true)
  
  if [ -n "$STAGED" ]; then
    for file in $STAGED; do
      [ -f "$file" ] || continue
      
      if ! grep -qE '(^import |^from .* import|^require\()' "$file"; then
        continue
      fi
      
      FIRST_IMPORT=$(grep -nE '(^import |^from .* import|^require\()' "$file" | head -1 | cut -d: -f1)
      LINES_BEFORE=$(head -n "$FIRST_IMPORT" "$file" | grep -vE '(^[[:space:]]*$|^[[:space:]]*#|^[[:space:]]*/\*|^[[:space:]]*\*|^[[:space:]]*//|^[[:space:]]*"""|\047\047\047)' | wc -l | tr -d ' ')
      
      if [ "$LINES_BEFORE" -gt 5 ]; then
        echo "  ⚠️  $file: Imports not near top (line $FIRST_IMPORT, $LINES_BEFORE code lines before)"
        FAIL=$((FAIL+1))
      fi
    done
    
    if [ "$FAIL" -eq 0 ]; then
      echo "  ✅ Imports are properly positioned"
    fi
  else
    echo "  ℹ️  No code files staged"
  fi

  echo ""
}

check_test_quality() {
  echo "🧪 Checking test file quality..."
  TEST_FILES=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.(test|spec)\.(js|ts|tsx|jsx|py)$' || true)

  if [ -n "$TEST_FILES" ]; then
    for file in $TEST_FILES; do
      [ -f "$file" ] || continue
      
      LINES=$(wc -l < "$file" | tr -d ' ')
      if [ "$LINES" -lt 10 ]; then
        echo "  ❌ $file: Test file is suspiciously short ($LINES lines)"
        echo "     Tests should actually test something, not just import files"
        FAIL=$((FAIL+1))
      fi
      
      CODE_LINES=$(grep -vE '(^[[:space:]]*$|^[[:space:]]*#|^[[:space:]]*//|^import |^from .* import)' "$file" | wc -l | tr -d ' ')
      if [ "$CODE_LINES" -lt 5 ]; then
        echo "  ❌ $file: Test file has only imports, no actual tests ($CODE_LINES code lines)"
        FAIL=$((FAIL+1))
      fi
      
      SKIPPED_TESTS=$(grep -nE '(\.skip\(|\.todo\(|xit\(|xdescribe\(|xtest\(|@skip|@unittest.skip)' "$file" | wc -l | tr -d ' ')
      if [ "$SKIPPED_TESTS" -gt 0 ]; then
        echo "  ❌ $file: Found $SKIPPED_TESTS skipped test(s)"
        echo "     Tests must run, not be skipped!"
        grep -nE '(\.skip\(|\.todo\(|xit\(|xdescribe\(|xtest\(|@skip|@unittest.skip)' "$file" | head -3
        FAIL=$((FAIL+1))
      fi
      
      COMMENTED_TESTS=$(grep -nE '^\s*/+\s*(it\(|test\(|describe\(|def test_)' "$file" | wc -l | tr -d ' ')
      if [ "$COMMENTED_TESTS" -gt 0 ]; then
        echo "  ❌ $file: Found $COMMENTED_TESTS commented out test(s)"
        echo "     Uncommenting tests to avoid running them is not allowed!"
        grep -nE '^\s*/+\s*(it\(|test\(|describe\(|def test_)' "$file" | head -3
        FAIL=$((FAIL+1))
      fi
      
      TEST_COUNT=$(grep -cE '(^\s*it\(|^\s*test\(|^\s*def test_)' "$file" || echo 0)
      if [ "$TEST_COUNT" -eq 0 ]; then
        echo "  ❌ $file: No actual test cases found (no it(), test(), or def test_*)"
        echo "     Test files must contain actual tests!"
        FAIL=$((FAIL+1))
      fi
    done
    
    if [ "$FAIL" -eq 0 ]; then
      echo "  ✅ Test files look substantial and all tests will run"
    fi
  else
    echo "  ⚠️  No test files staged (did you write tests?)"
  fi

  echo ""
}

check_error_handling() {
  echo "🛡️  Checking for error handling..."
  STAGED=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.(js|ts|tsx|jsx|py|go|rs|java|cs)$' || true)
  
  if [ -n "$STAGED" ]; then
    for file in $STAGED; do
      [ -f "$file" ] || continue
      
      HAS_FUNCTIONS=$(grep -cE '(^function |^async function |^def |^func |class.*{)' "$file" || echo 0)
      
      if [ "$HAS_FUNCTIONS" -gt 0 ]; then
        HAS_ERROR_HANDLING=$(grep -cE '(try|catch|except|if err|error|Error\()' "$file" || echo 0)
        
        if [ "$HAS_ERROR_HANDLING" -eq 0 ]; then
          echo "  ⚠️  $file: No error handling found (functions but no try/catch or error checks)"
        fi
      fi
    done
    
    echo "  ✅ Error handling check complete"
  else
    echo "  ℹ️  No code files staged"
  fi

  echo ""
}

check_deleted_tests() {
  echo "🔒 Checking for deleted tests..."
  DELETED_TESTS=$(git diff --cached --name-only --diff-filter=D | grep -E '\.(test|spec)\.(js|ts|tsx|jsx|py)$' || true)

  if [ -n "$DELETED_TESTS" ]; then
    echo "  ⛔ CRITICAL: Detected deleted test files!"
    echo ""
    for file in $DELETED_TESTS; do
      echo "    ❌ DELETED: $file"
    done
    echo ""
    echo "  🚨 DELETING TESTS IS FORBIDDEN"
    echo ""
    echo "  If tests are failing:"
    echo "    ✅ Fix the tests or the code"
    echo "    ❌ Don't delete tests to make them 'pass'"
    echo ""
    echo "  If tests are truly obsolete:"
    echo "    1. Get explicit human approval"
    echo "    2. Document why in commit message"
    echo "    3. Update test count in metrics.json"
    echo ""
    FAIL=$((FAIL+100))
  fi

  echo "🔍 Checking for deleted test cases in modified files..."
  MODIFIED_TESTS=$(git diff --cached --name-only --diff-filter=M | grep -E '\.(test|spec)\.(js|ts|tsx|jsx|py)$' || true)

  if [ -n "$MODIFIED_TESTS" ]; then
    for file in $MODIFIED_TESTS; do
      STAGED_COUNT=$(git show ":$file" | grep -cE '(^\s*it\(|^\s*test\(|^\s*def test_)' || echo 0)
      HEAD_COUNT=$(git show "HEAD:$file" 2>/dev/null | grep -cE '(^\s*it\(|^\s*test\(|^\s*def test_)' || echo 0)
      
      if [ "$STAGED_COUNT" -lt "$HEAD_COUNT" ]; then
        DELETED_COUNT=$((HEAD_COUNT - STAGED_COUNT))
        echo "  ⛔ CRITICAL: $file lost $DELETED_COUNT test case(s)!"
        echo "     Was: $HEAD_COUNT tests, Now: $STAGED_COUNT tests"
        echo ""
        echo "  🚨 DELETING TEST CASES IS FORBIDDEN"
        echo ""
        echo "  Test count must not decrease without explicit approval!"
        echo "  If refactoring, tests should be moved, not deleted."
        echo ""
        FAIL=$((FAIL+50))
      elif [ "$STAGED_COUNT" -gt "$HEAD_COUNT" ]; then
        ADDED_COUNT=$((STAGED_COUNT - HEAD_COUNT))
        echo "  ✅ $file: Added $ADDED_COUNT test case(s) (was: $HEAD_COUNT, now: $STAGED_COUNT)"
      fi
    done
  fi

  echo ""
}
