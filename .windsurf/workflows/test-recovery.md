---
allowed-tools: "*"
description: Recover from test failures and broken test suites
---
allowed-tools: "*"

# Test Recovery Workflow

Use this workflow when tests are failing, test suite is broken, or coverage has regressed.

---
allowed-tools: "*"

## When to Use

- Tests suddenly failing after working before
- Test suite won't run at all
- Coverage dropped significantly
- Pre-commit hook blocking all commits
- Tests passing locally but failing in CI
- Flaky tests causing intermittent failures

---
allowed-tools: "*"

## Step 0: Assess the Situation

**AI: Ask the user:**

1. What's the symptom?
   - All tests failing
   - Some tests failing
   - Tests won't run (error before tests start)
   - Coverage regression
   - Flaky tests (pass sometimes, fail sometimes)
   - Tests passing locally but failing in hook/CI

2. When did this start?
   - After specific commit
   - After dependency update
   - After environment change
   - Suddenly (no obvious cause)

3. Can you run tests manually?
   ```bash
   npm test  # or pytest, go test, etc.
   ```

**AI: Based on answers, guide to appropriate section below.**

---
allowed-tools: "*"

## Step 1: Quick Diagnostics

### Check Test Command

**AI: Verify test command works:**

```bash
# Try running tests manually
npm test

# Check exit code
echo $?
# 0 = success, non-zero = failure
```

**If tests won't run at all:**
- Missing dependencies → Go to Step 2A
- Configuration error → Go to Step 2B
- Test framework not installed → Go to Step 2C

**If tests run but fail:**
- All tests failing → Go to Step 3A
- Some tests failing → Go to Step 3B
- Flaky tests → Go to Step 3C

---
allowed-tools: "*"

## Step 2: Test Suite Won't Run

### 2A: Missing Dependencies

**Symptoms:**
```
Error: Cannot find module 'jest'
Error: No module named 'pytest'
```

**Fix:**

```bash
# Node.js
npm install

# Or clean install
rm -rf node_modules package-lock.json
npm install

# Python
pip install -r requirements.txt

# Or with virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Go
go mod download
```

**AI: After fix, verify:**
```bash
npm test
```

---
allowed-tools: "*"

### 2B: Configuration Error

**Symptoms:**
```
Error: Invalid configuration
Error: Cannot find config file
```

**Common Issues:**

1. **Missing config file:**
   ```bash
   # Check for config
   ls jest.config.js pytest.ini go.mod
   ```
   
   **Fix: Create minimal config:**
   ```javascript
   // jest.config.js
   module.exports = {
     testEnvironment: 'node',
     testMatch: ['**/*.test.js', '**/*.test.ts'],
     collectCoverageFrom: ['src/**/*.{js,ts}']
   };
   ```

2. **Invalid config syntax:**
   ```bash
   # Validate JSON config
   cat jest.config.json | jq .
   ```
   
   **Fix: Correct syntax errors**

3. **Wrong test pattern:**
   ```javascript
   // jest.config.js
   module.exports = {
     testMatch: [
       '**/__tests__/**/*.[jt]s?(x)',
       '**/?(*.)+(spec|test).[jt]s?(x)'
     ]
   };
   ```

**AI: After fix, verify:**
```bash
npm test
```

---
allowed-tools: "*"

### 2C: Test Framework Not Installed

**Symptoms:**
```
Command 'jest' not found
Command 'pytest' not found
```

**Fix:**

```bash
# Node.js - Jest
npm install --save-dev jest @types/jest

# Node.js - Vitest
npm install --save-dev vitest

# Python - pytest
pip install pytest pytest-cov

# Add test script to package.json
{
  "scripts": {
    "test": "jest",
    "coverage": "jest --coverage"
  }
}
```

**AI: After fix, verify:**
```bash
npm test
```

---
allowed-tools: "*"

## Step 3: Tests Run But Fail

### 3A: All Tests Failing

**Symptoms:**
- Every single test fails
- Usually same error across all tests

**Common Causes:**

1. **Environment Setup Failed**
   
   **Check:**
   ```bash
   # Look for setup errors in test output
   npm test 2>&1 | head -20
   ```
   
   **Common issues:**
   - Database not running
   - Environment variables missing
   - Test database not created
   
   **Fix:**
   ```bash
   # Set test environment variables
   export NODE_ENV=test
   export DATABASE_URL=postgresql://localhost/test_db
   
   # Or create .env.test
   cat > .env.test <<EOF
   NODE_ENV=test
   DATABASE_URL=postgresql://localhost/test_db
   EOF
   ```

2. **Global Setup/Teardown Broken**
   
   **Check:**
   ```javascript
   // jest.config.js
   module.exports = {
     globalSetup: './test/setup.js',
     globalTeardown: './test/teardown.js'
   };
   ```
   
   **Fix: Debug setup file:**
   ```javascript
   // test/setup.js
   module.exports = async () => {
     console.log('Global setup running...');
     // Add error handling
     try {
       // Your setup code
     } catch (error) {
       console.error('Setup failed:', error);
       throw error;
     }
   };
   ```

3. **Breaking Change in Code**
   
   **Identify when it broke:**
   ```bash
   # Find last working commit
   git log --oneline -10
   
   # Checkout previous commit
   git checkout HEAD~1
   npm test
   
   # If tests pass, the issue is in HEAD
   git checkout -
   ```
   
   **Fix: Revert breaking change or update tests**

**AI: After identifying cause, apply fix and verify:**
```bash
npm test
```

---
allowed-tools: "*"

### 3B: Some Tests Failing

**Symptoms:**
- Specific tests fail consistently
- Other tests pass

**Diagnosis:**

```bash
# Run only failing tests
npm test -- --testNamePattern="failing test name"

# Or run specific file
npm test path/to/failing.test.js

# Get detailed output
npm test -- --verbose
```

**Common Causes:**

1. **Test Depends on External State**
   
   **Bad:**
   ```javascript
   let sharedState = {};
   
   test('test 1', () => {
     sharedState.value = 1;
     expect(sharedState.value).toBe(1);
   });
   
   test('test 2', () => {
     // Fails if test 1 didn't run first
     expect(sharedState.value).toBe(1);
   });
   ```
   
   **Fix: Make tests independent:**
   ```javascript
   test('test 1', () => {
     const state = { value: 1 };
     expect(state.value).toBe(1);
   });
   
   test('test 2', () => {
     const state = { value: 1 };
     expect(state.value).toBe(1);
   });
   ```

2. **Async Issues**
   
   **Bad:**
   ```javascript
   test('async test', () => {
     fetchData().then(data => {
       expect(data).toBe('result');
     });
     // Test finishes before promise resolves
   });
   ```
   
   **Fix: Properly handle async:**
   ```javascript
   test('async test', async () => {
     const data = await fetchData();
     expect(data).toBe('result');
   });
   ```

3. **Mock Not Reset**
   
   **Fix:**
   ```javascript
   afterEach(() => {
     jest.clearAllMocks();
   });
   ```

**AI: After fix, verify:**
```bash
npm test
```

---
allowed-tools: "*"

### 3C: Flaky Tests

**Symptoms:**
- Tests pass sometimes, fail sometimes
- Different results on different runs
- "Works on my machine"

**Diagnosis:**

```bash
# Run test multiple times
for i in {1..10}; do
  npm test -- --testNamePattern="flaky test"
  echo "Run $i: $?"
done
```

**Common Causes:**

1. **Race Conditions**
   
   **Bad:**
   ```javascript
   test('race condition', async () => {
     startAsyncOperation();
     // Doesn't wait for completion
     expect(result).toBe('done');
   });
   ```
   
   **Fix:**
   ```javascript
   test('no race condition', async () => {
     await startAsyncOperation();
     expect(result).toBe('done');
   });
   ```

2. **Time-Dependent Tests**
   
   **Bad:**
   ```javascript
   test('time dependent', () => {
     const now = new Date();
     expect(formatDate(now)).toBe('2025-01-15');
     // Fails at midnight
   });
   ```
   
   **Fix: Mock time:**
   ```javascript
   test('time mocked', () => {
     jest.useFakeTimers();
     jest.setSystemTime(new Date('2025-01-15'));
     const now = new Date();
     expect(formatDate(now)).toBe('2025-01-15');
     jest.useRealTimers();
   });
   ```

3. **Non-Deterministic Data**
   
   **Bad:**
   ```javascript
   test('random data', () => {
     const id = generateRandomId();
     expect(id).toBe('abc123'); // Fails randomly
   });
   ```
   
   **Fix: Mock random:**
   ```javascript
   test('mocked random', () => {
     jest.spyOn(Math, 'random').mockReturnValue(0.5);
     const id = generateRandomId();
     expect(id).toBe('predictable');
   });
   ```

**AI: After fix, verify stability:**
```bash
# Run 10 times to confirm
for i in {1..10}; do npm test; done
```

---
allowed-tools: "*"

## Step 4: Coverage Regression

**Symptoms:**
```
❌ Coverage regression detected
  lines: 85.5% → 82.3% (drop: 3.2%)
```

**Diagnosis:**

```bash
# Check coverage report
cat .cfoi/branches/main/coverage/latest-summary.json

# View detailed coverage
npm run coverage
open coverage/lcov-report/index.html
```

**Common Causes:**

1. **New Code Without Tests**
   
   **Identify uncovered code:**
   ```bash
   # Coverage report shows which files/lines
   npm run coverage
   ```
   
   **Fix: Add tests for new code:**
   ```javascript
   // New function added
   function newFeature() {
     // implementation
   }
   
   // Add test
   test('newFeature works', () => {
     expect(newFeature()).toBe(expected);
   });
   ```

2. **Tests Deleted**
   
   **Check git history:**
   ```bash
   git log --all --full-history -- "*.test.*"
   ```
   
   **Fix: Restore deleted tests:**
   ```bash
   git checkout HEAD~1 -- path/to/deleted.test.js
   ```

3. **False Regression (Tolerance Too Strict)**
   
   **Adjust tolerance:**
   ```bash
   # Allow 1% drop
   export CFOI_COVERAGE_TOLERANCE=1.0
   ```

**AI: After fix, verify:**
```bash
npm run coverage
./tools/verify-implementation.sh
```

---
allowed-tools: "*"

## Step 5: Tests Pass Locally But Fail in Hook/CI

**Symptoms:**
- `npm test` succeeds
- Pre-commit hook fails
- CI pipeline fails

**Common Causes:**

1. **Different Environment**
   
   **Check:**
   ```bash
   # Compare environments
   node --version
   npm --version
   
   # Check in hook
   .githooks/pre-commit
   ```
   
   **Fix: Ensure consistent environment:**
   ```bash
   # Use same Node version
   nvm use 18
   
   # Clean install
   rm -rf node_modules
   npm ci
   ```

2. **Unstaged Changes**
   
   **Check:**
   ```bash
   git status
   ```
   
   **Fix:**
   ```bash
   # Stage all changes
   git add .
   
   # Or stage specific files
   git add path/to/file
   ```

3. **Different Test Command**
   
   **Check what hook runs:**
   ```bash
   cat .githooks/pre-commit | grep -A5 "test"
   ```
   
   **Fix: Set consistent command:**
   ```bash
   export CFOI_TEST_COMMAND="npm test -- --watch=false"
   ```

**AI: After fix, test hook:**
```bash
.githooks/pre-commit
echo $?  # Should be 0
```

---
allowed-tools: "*"

## Step 6: Emergency Bypass (Last Resort)

**⚠️ WARNING: Only use if absolutely necessary**

If you need to commit urgently and tests are broken:

```bash
# Bypass pre-commit hook
git commit --no-verify -m "emergency: bypass tests"

# Create issue to fix tests
cat > .cfoi/branches/$(git rev-parse --abbrev-ref HEAD)/test-issues.md <<EOF
# Test Issues to Fix

**Created:** $(date)
**Reason for bypass:** [explain emergency]

## Failing Tests
- [ ] Test 1: [description]
- [ ] Test 2: [description]

## Action Plan
1. [step 1]
2. [step 2]

**Target fix date:** [date]
EOF
```

**AI: Remind user:**
- This defeats quality enforcement
- Must fix tests ASAP
- Document why bypass was necessary
- Create plan to fix

---
allowed-tools: "*"

## Step 7: Prevention

**AI: Help user prevent future test failures:**

1. **Run tests before committing:**
   ```bash
   # Add to workflow
   npm test && git commit
   ```

2. **Keep dependencies updated:**
   ```bash
   npm outdated
   npm update
   ```

3. **Monitor test health:**
   ```bash
   # Check test metrics
   cat .cfoi/branches/main/metrics.json
   ```

4. **Document test patterns:**
   ```markdown
   # Test Guidelines
   
   - All tests must be independent
   - Mock external dependencies
   - Use fake timers for time-dependent code
   - Clean up after each test
   - No shared mutable state
   ```

5. **Set up CI:**
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
         - run: npm test
   ```

---
allowed-tools: "*"

## Step 8: Recovery Checklist

**AI: Guide user through checklist:**

- [ ] Tests run successfully
- [ ] All tests passing
- [ ] Coverage at acceptable level (>80%)
- [ ] No flaky tests
- [ ] Pre-commit hook works
- [ ] Tests documented if complex
- [ ] Root cause identified
- [ ] Prevention measures in place

**AI: Create summary:**

```markdown
## Test Recovery Summary

**Issue:** [brief description]
**Root Cause:** [what caused it]
**Resolution:** [what fixed it]
**Time to Resolve:** [duration]

**Tests Status:**
- Total: [count]
- Passing: [count]
- Failing: 0
- Coverage: [percentage]%

**Lessons Learned:**
1. [lesson 1]
2. [lesson 2]

**Prevention:**
1. [ ] [preventive measure 1]
2. [ ] [preventive measure 2]
```

---
allowed-tools: "*"

## Resources

### Documentation
- [TROUBLESHOOTING.md](../../docs/TROUBLESHOOTING.md#test--coverage-issues)
- [REFERENCE.md](../../docs/REFERENCE.md#verification-tools)
- [ANTI_TEST_SKIPPING.md](../../docs/workflow-pack/ANTI_TEST_SKIPPING.md)

### Test Framework Docs
- Jest: https://jestjs.io/docs/getting-started
- Vitest: https://vitest.dev/guide/
- pytest: https://docs.pytest.org/

---
allowed-tools: "*"

**Tests recovered!** Remember: tests are your safety net. Keep them healthy! ✅
