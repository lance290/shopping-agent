# Adding AI Accountability to Existing Projects

**Goal:** Add AI accountability rules to a project that doesn't have this workflow pack.

**Time required:** 10-15 minutes (or 30 seconds with the import script!)

---

## ⚡ **Super Quick Setup (One Command!)** - NEW!

```bash
# From this workflow pack directory:
./tools/import-ai-accountability.sh /path/to/your/existing/project

# That's it! Takes 30 seconds.
# The script copies all files, tests everything, and shows next steps.
```

**What the script does:**

- ✅ Creates necessary directories
- ✅ Copies all 4 core files
- ✅ Copies documentation guides
- ✅ Makes scripts executable
- ✅ Tests the installation
- ✅ Shows you next steps

**Example:**

```bash
cd ~/Projects/windsurf-workflow-pack-extended
./tools/import-ai-accountability.sh ~/Projects/my-startup-mvp

# Output:
# ✓ Directories created
# ✓ Constitution copied
# ✓ Workflow copied
# ✓ Verification script copied
# ✓ Checklist template copied
# ✅ Import complete!
```

---

## 🚀 **Manual Setup (Copy 4 Files)** - If you prefer doing it yourself

### **Step 1: Copy the Core Files** (5 minutes)

From this workflow pack repository to your existing project:

```bash
# Navigate to your existing project
cd /path/to/your/existing/project

# Create necessary directories
mkdir -p .windsurf/workflows
mkdir -p tools

# Copy the 4 essential files from workflow pack
# Replace SOURCE_PATH with path to this workflow pack

# 1. Constitution with AI rules
cp SOURCE_PATH/.windsurf/constitution.md .windsurf/constitution.md

# 2. AI Accountability workflow
cp SOURCE_PATH/.windsurf/workflows/ai-accountability.md .windsurf/workflows/ai-accountability.md

# 3. Verification script
cp SOURCE_PATH/tools/verify-implementation.sh tools/verify-implementation.sh
chmod +x tools/verify-implementation.sh

# 4. Checklist template
cp SOURCE_PATH/tools/ai-checklist-template.md tools/ai-checklist-template.md
```

**That's it!** The core enforcement is now in place.

---

### **Step 2: Optional - Copy Reference Guide** (2 minutes)

```bash
# Copy the "How to Keep Your AI Honest" guide
cp SOURCE_PATH/KEEPING_AI_HONEST.md ./KEEPING_AI_HONEST.md
```

This gives your team a user-friendly reference.

---

### **Step 3: Test the Setup** (3 minutes)

```bash
# Test the verification script works
./tools/verify-implementation.sh

# You should see:
# 🔍 Verifying implementation quality...
# ✅ Implementation verification PASSED
```

---

### **Step 4: Train Your Team** (5 minutes)

Share these quick rules with your team:

```markdown
# Quick AI Accountability Rules

BEFORE working with AI:
→ Set expectations: "Complete all code, no TODOs, show proof"

DURING work:
→ Watch for red flags (see KEEPING_AI_HONEST.md)

AFTER AI claims done:
→ Run: ./tools/verify-implementation.sh
→ Review actual code
→ Verify tests pass

RED FLAGS to reject:
🚩 "I'll do X later"
🚩 "TODO: ..."
🚩 "This should work" (without proof)
```

---

## 📋 **Detailed Setup (If You Want Git Hooks Too)**

If you want automatic enforcement on `git commit`, follow these additional steps:

### **Option A: Node.js Git Hooks** (if your project uses Node.js)

```bash
# 1. Copy git hooks
cp -r SOURCE_PATH/.githooks-node .githooks-node

# 2. Install dependencies (if not already installed)
npm install --save-dev prettier

# 3. Set up git hooks
# Add to package.json:
{
  "scripts": {
    "prepare": "[ -d .git ] && git config core.hooksPath .githooks-node || true"
  }
}

# 4. Run setup
npm run prepare
```

### **Option B: Bash Git Hooks** (if your project doesn't use Node.js)

```bash
# 1. Copy git hooks
cp -r SOURCE_PATH/.githooks .githooks

# 2. Configure git to use them
git config core.hooksPath .githooks

# 3. Make them executable
chmod +x .githooks/*
```

---

## 🎯 **Minimal Setup (Just Constitution)**

If you only want the constitution (Windsurf reads this automatically):

```bash
# Create directory
mkdir -p .windsurf

# Copy just the constitution
cp SOURCE_PATH/.windsurf/constitution.md .windsurf/constitution.md
```

**Pros:**

- Windsurf reads this on startup
- Sets expectations automatically
- Zero overhead

**Cons:**

- No automated verification
- Relies on manual enforcement
- No checklist template

**Best for:** Small projects, solo development

---

## 🔧 **Customizing for Your Project**

### **Edit the Constitution**

Add project-specific rules to `.windsurf/constitution.md`:

```markdown
## Project-Specific AI Rules

REQUIRED for our codebase:

- All React components must use TypeScript
- All API calls must have timeout handling
- All forms must have client-side validation
- All images must have alt text

FORBIDDEN in our codebase:

- Using `any` type in TypeScript
- Inline styles in React components
- Unhandled promise rejections
- Direct DOM manipulation in React
```

### **Customize Verification Script**

Edit `tools/verify-implementation.sh` to add your checks:

```bash
# Add custom check for your project
echo "🔒 Checking for inline API keys..."
if grep -rE '(apiKey|api_key|API_KEY).*=.*"[A-Za-z0-9]{20,}"' "$file" 2>/dev/null; then
  echo "  ❌ Hardcoded API key found"
  FAIL=$((FAIL+1))
fi
```

---

## 📦 **For Different Project Types**

### **Python Projects**

```bash
# Copy core files (same as above)
# Then customize for Python:

# Edit tools/verify-implementation.sh
# Change file patterns from .js to .py:
STAGED=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.py$' || true)

# Add Python-specific checks:
# - Check for `pass` in new functions
# - Check for `raise NotImplementedError`
# - Check for proper __init__.py files
```

### **Go Projects**

```bash
# Copy core files (same as above)
# Then customize for Go:

# Edit tools/verify-implementation.sh
# Change file patterns to .go:
STAGED=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.go$' || true)

# Add Go-specific checks:
# - Check for error handling (if err != nil)
# - Check for proper package declarations
# - Check for exported function documentation
```

### **Java Projects**

```bash
# Copy core files (same as above)
# Then customize for Java:

# Edit tools/verify-implementation.sh
# Change file patterns to .java:
STAGED=$(git diff --cached --name-only --diff-filter=AM | grep -E '\.java$' || true)

# Add Java-specific checks:
# - Check for proper exception handling
# - Check for @Override annotations
# - Check for JavaDoc on public methods
```

---

## 🎓 **Gradual Adoption Strategy**

### **Week 1: Awareness**

```markdown
1. Copy KEEPING_AI_HONEST.md to project
2. Share with team in standup
3. No enforcement yet, just awareness
```

### **Week 2: Voluntary**

```markdown
1. Copy verification script
2. Encourage team to run it
3. Track who uses it
4. Celebrate good examples
```

### **Week 3: Recommended**

```markdown
1. Add to PR template:
   [ ] Ran ./tools/verify-implementation.sh
   [ ] Reviewed for AI red flags
2. Code reviewers check for TODOs
```

### **Week 4: Required**

```markdown
1. Set up git hooks (automatic)
2. Require verification in CI/CD
3. Block PRs with TODOs/placeholders
```

---

## 🔍 **Verification Checklist**

After setup, verify everything works:

```markdown
Setup Verification:
□ .windsurf/constitution.md exists
□ tools/verify-implementation.sh is executable
□ Running verification script shows output
□ Team has access to KEEPING_AI_HONEST.md
□ (Optional) Git hooks are configured
□ (Optional) Checklist template is available

Test Run:
□ Create test file with TODO comment
□ Run ./tools/verify-implementation.sh
□ Should fail with error about TODO
□ Remove TODO
□ Re-run script
□ Should pass ✅

Team Onboarding:
□ Shared KEEPING_AI_HONEST.md with team
□ Explained red flags
□ Demonstrated verification script
□ Set expectations for AI work
```

---

## 🚨 **Troubleshooting**

### **Problem: Verification script says "command not found"**

```bash
# Make sure it's executable
chmod +x tools/verify-implementation.sh

# Make sure you're in project root
pwd  # Should show your project directory
```

### **Problem: Git hooks not running**

```bash
# Check git hook path
git config core.hooksPath

# Should show: .githooks or .githooks-node

# If not set:
git config core.hooksPath .githooks-node  # or .githooks
```

### **Problem: Windsurf not reading constitution**

```bash
# Restart Windsurf to reload constitution
# Or explicitly reference it:

"Please review the AI accountability rules in .windsurf/constitution.md
before we begin this task."
```

### **Problem: Verification script has false positives**

```bash
# Edit tools/verify-implementation.sh
# Adjust patterns to match your project
# Or add exceptions for specific patterns
```

---

## 📊 **Measuring Adoption**

Track adoption in your team:

```markdown
Week 1: [X]% of PRs ran verification script
Week 2: [X]% of PRs ran verification script
Week 3: [X]% of PRs ran verification script
Week 4: [X]% of PRs ran verification script

TODOs found in code reviews:
Before: [X] per week
After: [X] per week

Rework due to incomplete AI code:
Before: [X]% of PRs
After: [X]% of PRs
```

**Success metrics:**

- > 80% of PRs use verification script
- <2 TODOs found per week in review
- <10% rework rate

---

## 🎯 **Different Adoption Levels**

Choose based on your team's needs:

### **Level 1: Constitution Only**

**Files:** `.windsurf/constitution.md`  
**Effort:** 2 minutes  
**Enforcement:** Manual, AI-awareness only  
**Best for:** Solo developers, small projects

### **Level 2: Constitution + Verification**

**Files:** Constitution + `verify-implementation.sh`  
**Effort:** 10 minutes  
**Enforcement:** Semi-automated (must run script)  
**Best for:** Small teams, MVP projects

### **Level 3: Full Setup**

**Files:** All 4 core files + git hooks  
**Effort:** 15 minutes  
**Enforcement:** Mostly automated  
**Best for:** Production projects, team environments

### **Level 4: Full + Checklists**

**Files:** Everything + mandatory checklists  
**Effort:** 20 minutes + process setup  
**Enforcement:** Fully enforced  
**Best for:** Critical systems, regulated industries

---

## 🔄 **Updating Rules**

When you want to update rules from the workflow pack:

```bash
# Pull latest from workflow pack
cd /path/to/workflow-pack
git pull origin main

# Copy updated files to your project
cd /path/to/your-project

# Update constitution (review changes first!)
diff /path/to/workflow-pack/.windsurf/constitution.md .windsurf/constitution.md
cp /path/to/workflow-pack/.windsurf/constitution.md .windsurf/constitution.md

# Update verification script
cp /path/to/workflow-pack/tools/verify-implementation.sh tools/verify-implementation.sh
chmod +x tools/verify-implementation.sh
```

---

## 📝 **Sample Commit Message**

When adding to your project:

```
feat: add AI accountability framework

Add AI accountability rules to prevent lazy implementations:
- Constitution with AI behavioral rules
- Verification script for automated checks
- Checklist template for proof of completion
- Reference guide for team

This ensures AI assistants:
✓ Complete all code (no TODOs)
✓ Implement error handling
✓ Write real tests
✓ Provide proof of completion

Run verification: ./tools/verify-implementation.sh
Reference guide: KEEPING_AI_HONEST.md

Closes #[issue-number]
```

---

## ✅ **Success!**

After setup, your team should:

1. **Know the red flags** (see KEEPING_AI_HONEST.md)
2. **Run verification script** before committing AI code
3. **Demand proof** from AI (not just promises)
4. **Reject incomplete work** (no TODOs, no placeholders)

**The workflow pack rules are now protecting your codebase!** 🎉

---

## 📞 **Getting Help**

- **Full documentation:** KEEPING_AI_HONEST.md
- **Workflow reference:** .windsurf/workflows/ai-accountability.md
- **Verification script:** tools/verify-implementation.sh
- **Checklist template:** tools/ai-checklist-template.md

**Questions?** Open an issue in the workflow pack repository.
