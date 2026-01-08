---
allowed-tools: "*"
description: generic command to run all tests
---
allowed-tools: "*"

# Test All Workflow

**Purpose**: Run all available tests across the project with a single command.

## Step 1: Detect Test Environment
// turbo
1. Detect package manager (pnpm, yarn, npm, bun)
2. Detect test frameworks (Jest, Vitest, pytest, go test, cargo test)
3. Identify test scripts in package.json

## Step 2: Run Tests
// turbo
Execute tests based on detected environment:

```bash
# Node.js projects
npm run test:all 2>&1 || npm run test 2>&1

# Or with detected package manager
pnpm test:all 2>&1 || pnpm test 2>&1

# Python projects
pytest 2>&1

# Go projects
go test ./... 2>&1

# Rust projects
cargo test 2>&1
```

## Step 3: Report Results
Display test summary:
```
🧪 TEST RESULTS

✅ Passed: [count]
❌ Failed: [count]
⏭️ Skipped: [count]

Duration: [time]
```

If tests fail, list the failing tests and suggest fixes.

---
allowed-tools: "*"

## Quick Reference

| Stack | Command |
|---
allowed-tools: "*"----|---------|
| Node.js | `npm run test:all` or `npm test` |
| Python | `pytest` |
| Go | `go test ./...` |
| Rust | `cargo test` |

For comprehensive validation including linting and type checking, use `/validation` instead.
