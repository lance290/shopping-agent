---
allowed-tools: "*"
description: Override or customize git hooks when needed
---
allowed-tools: "*"

# Git Hooks Override Workflow

Use this workflow when you need to customize, disable, or troubleshoot git hooks.

**⚠️ WARNING:** Disabling hooks defeats quality enforcement. Only do this when absolutely necessary.

---
allowed-tools: "*"

## When to Use

- Need to customize hook behavior for your project
- Hooks causing issues and blocking work
- Emergency situation requiring bypass
- Testing hook changes
- Understanding what hooks do

---
allowed-tools: "*"

## Step 0: Understand Current Hooks

**AI: Show user what hooks are active:**

```bash
# List installed hooks
ls -la .githooks/

# Show hook configuration
git config core.hooksPath

# View pre-commit hook
cat .githooks/pre-commit | head -50
```

**AI: Explain to user:**

The framework installs three hooks:

1. **pre-commit**: Runs before each commit
   - Test suite
   - Coverage check
   - TypeScript type checking
   - Lazy pattern detection
   - Test quality checks

2. **pre-push**: Runs before pushing to remote
   - Full test suite
   - Coverage regression check
   - Deleted test detection

3. **post-commit**: Runs after successful commit
   - Updates metrics
   - Records commit in proof artifacts

---
allowed-tools: "*"

## Step 1: Temporary Bypass (Single Commit)

**When to use:** Emergency situation, need to commit immediately

**AI: Guide user:**

```bash
# Bypass pre-commit hook for one commit
git commit --no-verify -m "emergency: description"

# Or bypass pre-push hook
git push --no-verify
```

**AI: Remind user:**

⚠️ **This is dangerous because:**
- Skips all quality checks
- Could commit broken code
- Could push failing tests
- Defeats framework's purpose

**AI: Create tracking issue:**

```bash
# Document why bypass was needed
cat > .cfoi/branches/$(git rev-parse --abbrev-ref HEAD)/hook-bypasses.md <<EOF
# Hook Bypass Log

## $(date -u +"%Y-%m-%d %H:%M:%S UTC")

**Commit:** $(git rev-parse HEAD)
**Reason:** [USER: explain why bypass was necessary]
**Issues to fix:**
- [ ] [what needs to be fixed]
- [ ] [what needs to be fixed]

**Target fix date:** [date]
EOF
```

---
allowed-tools: "*"

## Step 2: Disable Hooks Temporarily

**When to use:** Need to disable hooks for multiple commits (e.g., during major refactor)

**AI: Guide user:**

```bash
# Disable hooks
git config core.hooksPath /dev/null

# Or rename hooks directory
mv .githooks .githooks.disabled

# Work without hooks...
git commit -m "work in progress"
git commit -m "more work"

# Re-enable hooks when done
git config core.hooksPath .githooks

# Or restore directory
mv .githooks.disabled .githooks
```

**AI: Remind user:**

⚠️ **Remember to:**
- Re-enable hooks when done
- Run full verification before pushing:
  ```bash
  ./tools/verify-implementation.sh
  ```
- Fix any issues found

---
allowed-tools: "*"

## Step 3: Customize Hook Behavior

**When to use:** Need to adjust hooks for your project's needs

### 3A: Customize Test Command

**AI: Guide user:**

```bash
# Set custom test command
export CFOI_TEST_COMMAND="npm run test:ci"

# Or add to .env
echo 'CFOI_TEST_COMMAND="npm run test:ci"' >> .env

# Or set in shell profile
echo 'export CFOI_TEST_COMMAND="npm run test:ci"' >> ~/.zshrc
```

**Common customizations:**

```bash
# Run tests without watch mode
CFOI_TEST_COMMAND="npm test -- --watch=false"

# Run tests in CI mode
CFOI_TEST_COMMAND="npm run test:ci"

# Run specific test suite
CFOI_TEST_COMMAND="npm test -- --testPathPattern=unit"

# Python with pytest
CFOI_TEST_COMMAND="pytest tests/"

# Go tests
CFOI_TEST_COMMAND="go test ./..."
```

---
allowed-tools: "*"

### 3B: Customize Coverage Command

**AI: Guide user:**

```bash
# Set custom coverage command
export CFOI_COVERAGE_COMMAND="npm run coverage:ci"

# Or disable coverage in pre-commit
unset CFOI_COVERAGE_COMMAND
```

**Common customizations:**

```bash
# Jest with specific reporters
CFOI_COVERAGE_COMMAND="npm test -- --coverage --coverageReporters=json-summary"

# Python with pytest-cov
CFOI_COVERAGE_COMMAND="pytest --cov --cov-report=xml"

# Disable coverage (faster commits)
unset CFOI_COVERAGE_COMMAND
```

---
allowed-tools: "*"

### 3C: Adjust Coverage Tolerance

**AI: Guide user:**

```bash
# Allow 0.5% coverage drop
export CFOI_COVERAGE_TOLERANCE=0.5

# Or more permissive (1% drop)
export CFOI_COVERAGE_TOLERANCE=1.0

# Or strict (no drop allowed)
export CFOI_COVERAGE_TOLERANCE=0
```

---
allowed-tools: "*"

### 3D: Skip Specific Checks

**AI: Show user how to modify hooks:**

```bash
# Edit pre-commit hook
nano .githooks/pre-commit
```

**Example: Skip TypeScript check:**

```bash
# Find this section in pre-commit:
if [ -f "$ROOT_DIR/tsconfig.json" ] && command -v npx >/dev/null 2>&1; then
  # TypeScript checking code...
fi

# Comment it out:
# if [ -f "$ROOT_DIR/tsconfig.json" ] && command -v npx >/dev/null 2>&1; then
#   # TypeScript checking code...
# fi
```

**AI: Warn user:**

⚠️ **Modifying hooks directly:**
- Changes will be lost on framework update
- Better to use environment variables when possible
- Document why modification was needed

---
allowed-tools: "*"

## Step 4: Create Project-Specific Hook

**When to use:** Need additional checks specific to your project

**AI: Guide user:**

```bash
# Create custom hook
cat > .githooks/pre-commit.local <<'EOF'
#!/usr/bin/env bash
# Project-specific pre-commit checks

# Example: Check for secrets
if git diff --cached | grep -i "api_key\|secret\|password"; then
  echo "❌ Potential secret detected in commit"
  exit 1
fi

# Example: Check for large files
if git diff --cached --name-only | xargs ls -l | awk '{if ($5 > 1000000) print $9}'; then
  echo "❌ Large file detected (>1MB)"
  exit 1
fi

echo "✅ Project-specific checks passed"
EOF

chmod +x .githooks/pre-commit.local
```

**AI: Integrate with main hook:**

```bash
# Add to end of .githooks/pre-commit
if [ -f .githooks/pre-commit.local ]; then
  .githooks/pre-commit.local
fi
```

---
allowed-tools: "*"

## Step 5: Debug Hook Failures

**When to use:** Hook fails but you don't understand why

**AI: Guide user through debugging:**

### 5A: Run Hook Manually

```bash
# Run pre-commit hook directly
.githooks/pre-commit

# Check exit code
echo $?
# 0 = success, non-zero = failure
```

### 5B: Add Debug Output

```bash
# Edit hook to add debug output
nano .githooks/pre-commit

# Add at top:
set -x  # Print each command before executing

# Or add specific debug points:
echo "DEBUG: Running tests..."
echo "DEBUG: Test command: $TEST_COMMAND"
```

### 5C: Check Hook Environment

```bash
# See what environment hook has
cat > .githooks/debug-env <<'EOF'
#!/usr/bin/env bash
echo "=== Environment ==="
env | sort
echo "=== Path ==="
echo $PATH
echo "=== Node Version ==="
node --version
echo "=== NPM Version ==="
npm --version
EOF

chmod +x .githooks/debug-env
.githooks/debug-env
```

### 5D: Compare with Terminal

```bash
# Run test in terminal
npm test
echo "Terminal exit code: $?"

# Run test in hook
.githooks/pre-commit
echo "Hook exit code: $?"

# If different, environment mismatch
```

---
allowed-tools: "*"

## Step 6: Disable Specific Hook

**When to use:** One hook is problematic, others are fine

**AI: Guide user:**

```bash
# Disable pre-commit (keep pre-push)
mv .githooks/pre-commit .githooks/pre-commit.disabled

# Or make it always succeed
echo '#!/bin/bash' > .githooks/pre-commit
echo 'exit 0' >> .githooks/pre-commit
chmod +x .githooks/pre-commit

# Commits will now skip pre-commit checks
# Pre-push will still run
```

**AI: Remind user to re-enable:**

```bash
# Re-enable later
mv .githooks/pre-commit.disabled .githooks/pre-commit
```

---
allowed-tools: "*"

## Step 7: Completely Remove Hooks

**When to use:** Framework hooks incompatible with your workflow

**AI: Guide user:**

```bash
# Remove hook configuration
git config --unset core.hooksPath

# Or use default git hooks location
git config core.hooksPath .git/hooks

# Framework hooks will no longer run
```

**AI: Explain consequences:**

⚠️ **Without hooks, you lose:**
- Automatic test running
- Coverage regression detection
- TypeScript error prevention
- Lazy pattern detection
- Test deletion prevention
- Quality enforcement

**AI: Suggest alternative:**

Instead of removing hooks, consider:
1. Running verification manually before commits:
   ```bash
   ./tools/verify-implementation.sh && git commit
   ```

2. Setting up CI to catch issues:
   ```yaml
   # .github/workflows/test.yml
   name: Tests
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-node@v3
         - run: npm ci
         - run: ./tools/verify-implementation.sh
   ```

---
allowed-tools: "*"

## Step 8: Restore Default Hooks

**When to use:** Want to go back to framework defaults

**AI: Guide user:**

```bash
# Re-enable hooks
git config core.hooksPath .githooks

# Restore original hooks from framework
cp -r /path/to/framework/.githooks/* .githooks/

# Or reinstall framework
./install.sh --update

# Make executable
chmod +x .githooks/*

# Test hooks work
.githooks/pre-commit
```

---
allowed-tools: "*"

## Common Scenarios

### Scenario 1: "Hooks are too slow"

**Solution:**

```bash
# Disable coverage in pre-commit (run only in pre-push)
unset CFOI_COVERAGE_COMMAND

# Run only changed tests
CFOI_TEST_COMMAND="npm test -- --onlyChanged"

# Or disable pre-commit, rely on pre-push
mv .githooks/pre-commit .githooks/pre-commit.disabled
```

---
allowed-tools: "*"

### Scenario 2: "Hooks fail in CI but work locally"

**Solution:**

```bash
# Check CI environment
# Add to CI config:
- run: node --version
- run: npm --version
- run: git config core.hooksPath

# Match CI environment locally
nvm use 18  # or whatever CI uses
npm ci      # clean install like CI
```

---
allowed-tools: "*"

### Scenario 3: "Need to commit work-in-progress"

**Solution:**

```bash
# Use WIP commit (bypass hooks)
git commit --no-verify -m "WIP: work in progress"

# Later, fix and amend
# ... fix issues ...
git add .
git commit --amend --no-edit
# This runs hooks on the amended commit
```

---
allowed-tools: "*"

### Scenario 4: "Hooks conflict with other tools"

**Solution:**

```bash
# Check what's using hooks
git config core.hooksPath

# Use hook chaining
# Edit .githooks/pre-commit to call other hooks:
if [ -f .git/hooks/pre-commit ]; then
  .git/hooks/pre-commit
fi

# Or use tool like husky alongside
```

---
allowed-tools: "*"

## Best Practices

**AI: Remind user:**

1. **Document customizations:**
   ```bash
   # Create docs/HOOKS.md
   cat > docs/HOOKS.md <<EOF
   # Git Hooks Customization
   
   ## Custom Test Command
   \`\`\`bash
   CFOI_TEST_COMMAND="npm run test:ci"
   \`\`\`
   
   ## Reason
   [explain why customization was needed]
   EOF
   ```

2. **Test hook changes:**
   ```bash
   # After modifying hooks
   .githooks/pre-commit
   .githooks/pre-push
   ```

3. **Keep bypasses temporary:**
   - Document why bypass was needed
   - Create issue to fix properly
   - Set target date to re-enable

4. **Use environment variables over editing hooks:**
   - Easier to maintain
   - Survives framework updates
   - Documented in one place

5. **Consider CI as backup:**
   - Even if hooks disabled, CI can catch issues
   - Set up GitHub Actions or similar

---
allowed-tools: "*"

## Resources

### Documentation
- [REFERENCE.md](../../docs/REFERENCE.md#git-hooks) - Complete hook reference
- [TROUBLESHOOTING.md](../../docs/TROUBLESHOOTING.md#git-hook-problems) - Common issues

### Hook Files
- `.githooks/pre-commit` - Pre-commit hook
- `.githooks/pre-push` - Pre-push hook
- `.githooks/post-commit` - Post-commit hook
- `tools/verify-implementation.sh` - Verification script

---
allowed-tools: "*"

**Hooks customized!** Remember: hooks exist to maintain quality. Use overrides sparingly. 🔒
