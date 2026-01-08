---
allowed-tools: "*"
description: Commit and push changes with automated build and tests
---
allowed-tools: "*"

# 🚀 Push Workflow

**Simple commit-and-push workflow with automated build and test validation**

---
allowed-tools: "*"

## 🎯 What This Does

This workflow helps you:
- Stage and commit your changes
- Run build (language-specific, if configured)
- Run tests via pre-push hook (language-specific)
- Push to remote repository

**The pre-push git hook automatically detects ALL project types and runs:**

**Node.js** (package.json):
- ✅ `npm run build` (if build script exists)
- ✅ `npm run test:all` (if script exists, otherwise skips)

**Go** (go.mod):
- ✅ `go build ./...`
- ✅ `go test ./...`

**Rust** (Cargo.toml):
- ✅ `cargo build`
- ✅ `cargo test`

**C/C++** (CMakeLists.txt):
- ✅ `cmake .. && make`

**Python** (pytest.ini or setup.py):
- ✅ `pytest`

**Generic** (Makefile):
- ✅ `make` (for build)
- ✅ `make test` (if test target exists)

**🎯 Monorepo Support:**
- Detects and runs **ALL** applicable build/test commands
- Example: Node.js frontend + Go backend + Python services all build/test together
- Each language's build/test runs independently
- ⚠️ Blocks push if **ANY** build or test fails (unless `.checkpoint` file exists)

---
allowed-tools: "*"

## Step 0: Check Status

// turbo
**AI: Show current git status:**
```bash
# Show what's changed
git status

# Show current branch
git branch --show-current
```

**AI: Report uncommitted changes and current branch.**

---
allowed-tools: "*"

## Step 1: Stage Changes

**AI: Ask what to commit:**

"What would you like to commit?"

1. **All changes** - Stage everything
2. **Specific files** - Choose files to stage
3. **Interactive** - Review each change

**AI: Based on choice, stage appropriately:**

// turbo
```bash
# Option 1: Stage all changes
git add -A

# Option 2: Stage specific files (AI asks which files)
git add <file1> <file2> ...

# Option 3: Interactive staging
git add -p
```

**AI: Confirm what was staged.**

---
allowed-tools: "*"

## Step 2: Commit Changes

**AI: Ask for commit message:**

"What's your commit message?"

// turbo
```bash
# Commit with message
git commit -m "your commit message here"

# Or open editor for detailed message
git commit
```

**AI: Confirm commit was created with hash.**

---
allowed-tools: "*"

## Step 3: Push to Remote

**AI: Explain what will happen:**

"Ready to push! The pre-push hook will automatically:
- ✅ Run build (if build script exists)
- ✅ Run all tests
- ⚠️ Block push if build or tests fail"

// turbo
```bash
# Push to current branch
BRANCH=$(git branch --show-current)
echo "📤 Pushing to origin/$BRANCH..."

git push origin "$BRANCH"
```

**AI: Report push status.**

**Note:** The pre-push hook (`.githooks/pre-push`) will automatically:
1. Detect your project type (Node.js, Go, Rust, C/C++, Python, Makefile)
2. Run appropriate build command (if configured)
3. Run appropriate test command (if configured)
4. Block the push if build or tests fail
5. Skip gracefully if no build/test setup detected

---
allowed-tools: "*"

## Step 4: Verify Push

// turbo
**AI: Confirm push succeeded:**
```bash
# Show last commit on remote
git log origin/$(git branch --show-current) -1 --oneline

# Show push status
echo "✅ Pushed to origin/$(git branch --show-current)"
```

**AI: Celebrate successful push!**

---
allowed-tools: "*"

## 🆘 Troubleshooting

### Build Failed
```bash
# Check build errors
npm run build

# Fix issues and try again
git push origin $(git branch --show-current)
```

### Tests Failed
```bash
# Run tests locally
npm run test:all

# Fix failing tests
# Then push again
git push origin $(git branch --show-current)
```

### Force Push (Use with Caution)
```bash
# Only if you know what you're doing
git push --force origin $(git branch --show-current)

# Or skip hooks (NOT RECOMMENDED)
git push --no-verify origin $(git branch --show-current)
```

---
allowed-tools: "*"

## 📚 Quick Reference

### Common Commands
```bash
# Stage all changes
git add -A

# Commit with message
git commit -m "message"

# Push to current branch
git push origin $(git branch --show-current)

# Check status
git status

# View recent commits
git log --oneline -5
```

### Pre-Push Hook Behavior
The `.githooks/pre-push` hook runs automatically and:
- 🔍 Detects project type (Node.js, Go, Rust, C/C++, Python, Makefile)
- ✅ Runs language-appropriate build command (if configured)
- ✅ Runs language-appropriate test command (if configured)
- ⏭️ Skips gracefully if no build/test setup detected
- ❌ Blocks push if build fails
- ❌ Blocks push if tests fail (unless `.checkpoint` file exists)

---
allowed-tools: "*"

## 🎉 Complete!

**Successfully pushed your changes! 🚀**

**What happened:**
- ✅ Staged your changes
- ✅ Created commit
- ✅ Build ran successfully (if applicable)
- ✅ Tests passed
- ✅ Pushed to remote

**Next steps:**
- Continue working on your branch
- Create a pull request
- Deploy with `/deploy` workflow
