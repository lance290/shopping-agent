# Code Reuse Enforcement Guide

**Purpose**: Enforce DRY (Don't Repeat Yourself) principle and function reuse across the codebase.

---

## Framework Enforcement

The framework now enforces function reuse through:

### 1. **Constitution Rule** (`.windsurf/constitution.md`)
- Extract reusable functions when logic appears 3+ times
- Prefer small, composable functions over large monolithic ones
- Forbidden: Duplicating code instead of extracting reusable functions

### 2. **Verification Script** (`tools/verify-implementation.sh`)
- Detects duplicate code blocks (5+ identical lines)
- Warns about potential DRY violations
- Suggests code duplication tools for detailed analysis

### 3. **Implement Workflow** (`.windsurf/workflows/implement.md`)
- Explicit DRY reminder before click-testing
- Checklist for refactoring duplicate code
- Guidelines for breaking down large functions

### 4. **Git Hooks** (`.githooks/pre-commit`)
- Runs verification script before commit
- Blocks commits with detected violations (unless using checkpoint)

---

## Recommended Linting Tools

### JavaScript/TypeScript

#### Option 1: jscpd (Copy/Paste Detector)
```bash
# Install
npm install -D jscpd

# Add to package.json
{
  "scripts": {
    "check:duplication": "jscpd src/"
  }
}

# Create .jscpd.json
{
  "threshold": 5,
  "reporters": ["html", "console"],
  "ignore": ["**/__tests__/**", "**/node_modules/**"],
  "format": ["typescript", "javascript"],
  "minLines": 5,
  "minTokens": 50
}
```

#### Option 2: ESLint with SonarJS
```bash
# Install
npm install -D eslint eslint-plugin-sonarjs

# Add to .eslintrc.js
module.exports = {
  plugins: ['sonarjs'],
  extends: ['plugin:sonarjs/recommended'],
  rules: {
    'sonarjs/no-duplicate-string': ['error', 3],
    'sonarjs/no-identical-functions': 'error',
    'sonarjs/cognitive-complexity': ['warn', 15]
  }
};
```

### Python

#### Option 1: pylint
```bash
# Install
pip install pylint

# Add to .pylintrc or pyproject.toml
[MESSAGES CONTROL]
enable=duplicate-code

[SIMILARITIES]
min-similarity-lines=5
ignore-comments=yes
ignore-docstrings=yes
```

#### Option 2: flake8 with plugins
```bash
# Install
pip install flake8 flake8-bugbear

# Add to .flake8
[flake8]
max-line-length = 100
select = C,E,F,W,B,B950
ignore = E203,E501,W503
```

### Multi-Language

#### SonarQube / SonarCloud
```yaml
# sonar-project.properties
sonar.projectKey=your-project
sonar.sources=src
sonar.exclusions=**/node_modules/**,**/__tests__/**
sonar.cpd.exclusions=**/*.test.ts,**/*.spec.ts

# Duplication thresholds
sonar.cpd.minimumLines=5
sonar.cpd.minimumTokens=50
```

#### PMD Copy/Paste Detector (CPD)
```bash
# Install (Java required)
brew install pmd  # macOS
# or download from https://pmd.github.io/

# Run
pmd cpd --minimum-tokens 50 --files src/ --language javascript
```

---

## Integration with Framework

### Update package.json
```json
{
  "scripts": {
    "test:all": "npm run test && npm run check:duplication",
    "check:duplication": "jscpd src/",
    "lint": "eslint . --ext .ts,.tsx,.js,.jsx",
    "lint:fix": "eslint . --ext .ts,.tsx,.js,.jsx --fix"
  }
}
```

### Update verify-implementation.sh
Add after the basic duplicate check:

```bash
# Run jscpd if available
if command -v jscpd >/dev/null 2>&1; then
  echo "🔍 Running jscpd (detailed duplicate detection)..."
  if ! jscpd src/ --threshold 5 --min-lines 5; then
    echo "  ❌ Code duplication detected by jscpd"
    FAIL=$((FAIL+1))
  fi
fi
```

### Update pre-commit hook
Add to `.githooks/pre-commit`:

```bash
# Check for code duplication with jscpd
if command -v jscpd >/dev/null 2>&1 && [ -f "package.json" ]; then
  echo "[pre-commit] 🔄 Checking for duplicate code..."
  if ! jscpd src/ --threshold 5 --min-lines 5 --silent; then
    echo "[pre-commit] ⚠️  Code duplication detected"
    FAIL=$((FAIL+1))
  fi
fi
```

---

## Configuration Examples

### Strict Configuration (Recommended for New Projects)
```json
// .jscpd.json
{
  "threshold": 3,          // Fail if >3% duplication
  "minLines": 5,           // 5+ duplicate lines
  "minTokens": 50,         // 50+ duplicate tokens
  "reporters": ["console", "html"],
  "ignore": [
    "**/__tests__/**",
    "**/node_modules/**",
    "**/*.test.ts",
    "**/*.spec.ts"
  ],
  "format": ["typescript", "javascript", "jsx", "tsx"]
}
```

### Lenient Configuration (For Legacy Codebases)
```json
// .jscpd.json
{
  "threshold": 10,         // Fail if >10% duplication
  "minLines": 10,          // 10+ duplicate lines
  "minTokens": 100,        // 100+ duplicate tokens
  "reporters": ["console"],
  "ignore": [
    "**/__tests__/**",
    "**/node_modules/**",
    "**/legacy/**"
  ]
}
```

---

## CI/CD Integration

### GitHub Actions
```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  duplication-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run check:duplication
      - name: Upload duplication report
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: duplication-report
          path: ./jscpd-report/
```

### Pre-push Hook
```bash
#!/usr/bin/env bash
# .githooks/pre-push

echo "[pre-push] 🔄 Checking for code duplication..."
if command -v jscpd >/dev/null 2>&1; then
  if ! npm run check:duplication; then
    echo "[pre-push] ❌ Code duplication detected"
    echo "Fix duplications or use [checkpoint] to bypass"
    exit 1
  fi
fi
```

---

## Best Practices

### When to Extract Functions

✅ **DO extract** when:
- Logic appears 3+ times
- Function is >100 lines
- You copy-pasted code
- Similar patterns with minor variations

❌ **DON'T extract** when:
- Only 2 occurrences (wait for 3rd)
- Code is configuration/data (not logic)
- Abstraction makes code harder to understand
- Premature optimization

### Refactoring Patterns

#### Before (Duplicate Code)
```typescript
// user-service.ts
async function createUser(data) {
  if (!data.email) throw new Error('Email required');
  if (!data.name) throw new Error('Name required');
  const user = await db.users.create(data);
  await sendEmail(user.email, 'Welcome!');
  return user;
}

// product-service.ts
async function createProduct(data) {
  if (!data.name) throw new Error('Name required');
  if (!data.price) throw new Error('Price required');
  const product = await db.products.create(data);
  await sendEmail(admin.email, 'New product created');
  return product;
}
```

#### After (Extracted Functions)
```typescript
// utils/validation.ts
export function validateRequired(obj: Record<string, any>, fields: string[]) {
  for (const field of fields) {
    if (!obj[field]) {
      throw new Error(`${field} is required`);
    }
  }
}

// utils/notifications.ts
export async function notifyByEmail(to: string, subject: string) {
  await sendEmail(to, subject);
}

// user-service.ts
async function createUser(data) {
  validateRequired(data, ['email', 'name']);
  const user = await db.users.create(data);
  await notifyByEmail(user.email, 'Welcome!');
  return user;
}

// product-service.ts
async function createProduct(data) {
  validateRequired(data, ['name', 'price']);
  const product = await db.products.create(data);
  await notifyByEmail(admin.email, 'New product created');
  return product;
}
```

---

## Metrics & Monitoring

### Track Duplication Over Time
```bash
# Generate duplication report
jscpd src/ --reporters json --output ./metrics/

# Store in metrics
echo "{ \"duplication\": $(jq '.statistics.total.percentage' ./metrics/jscpd-report.json) }" \
  >> .cfoi/branches/$(git branch --show-current)/metrics.json
```

### Set Quality Gates
```json
// package.json
{
  "scripts": {
    "quality:gate": "node scripts/quality-gate.js"
  }
}
```

```javascript
// scripts/quality-gate.js
const report = require('../jscpd-report.json');
const MAX_DUPLICATION = 5; // 5% max

if (report.statistics.total.percentage > MAX_DUPLICATION) {
  console.error(`❌ Duplication ${report.statistics.total.percentage}% exceeds ${MAX_DUPLICATION}%`);
  process.exit(1);
}
```

---

## Troubleshooting

### False Positives
```json
// .jscpd.json - Ignore specific patterns
{
  "ignore": [
    "**/generated/**",
    "**/*.config.js",
    "**/migrations/**"
  ],
  "skipComments": true
}
```

### Performance Issues
```json
// .jscpd.json - Optimize for large codebases
{
  "maxSize": "100kb",      // Skip large files
  "maxLines": 1000,        // Skip long files
  "format": ["typescript"] // Only check specific languages
}
```

---

## Summary

The framework now enforces function reuse through:

1. ✅ **Constitution rule** - Extract functions when logic appears 3+ times
2. ✅ **Verification script** - Basic duplicate detection
3. ✅ **Implement workflow** - DRY reminder before click-testing
4. ✅ **Recommended tools** - jscpd, ESLint, pylint, SonarQube

**Next Steps**:
1. Install jscpd: `npm install -D jscpd`
2. Create `.jscpd.json` configuration
3. Add `check:duplication` script to package.json
4. Run `npm run check:duplication` before commits
5. Monitor duplication metrics over time

**Goal**: Keep code duplication <5% across the codebase.
