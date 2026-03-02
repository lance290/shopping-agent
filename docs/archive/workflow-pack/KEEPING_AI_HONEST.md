# How to Keep Your AI Honest

**TL;DR:** AIs wander, skip work, and leave TODOs. This guide shows you how to hold them accountable.

---

## 🎯 **The Problem**

When working with AI assistants (Windsurf, ChatGPT, Claude, etc.), you've probably noticed:

- 🚩 **"I'll implement X later"** → Then never does it
- 🚩 **Creates TODO comments** → Instead of actual code
- 🚩 **Says "it's done"** → But you find it's incomplete
- 🚩 **Skips error handling** → Only implements happy path
- 🚩 **Empty test files** → Just imports, no actual tests
- 🚩 **Wanders off topic** → Solves a different problem than you asked for

**Sound familiar?** You're not alone. This is a universal AI behavior pattern.

---

## ✅ **The Solution**

This workflow pack includes **5 enforcement mechanisms** that keep AI assistants honest and thorough.

---

## **Quick Start (3 Steps)**

### **1. Set Expectations Upfront**

Before starting any work with AI, say:

```markdown
Before we begin, please acknowledge these rules:

1. Complete ALL code (no TODOs or placeholders)
2. Show proof of completion (actual code, test output)
3. Run ./tools/verify-implementation.sh before claiming done
4. If you say you'll do something, do it immediately

Do you acknowledge these requirements?
```

### **2. Watch for Red Flags**

When AI says these things, **immediately stop and reject**:

🚩 "I'll implement X later"  
🚩 "Here's a basic version"  
🚩 "TODO: Add error handling"  
🚩 "See the updated file" (without showing code)  
🚩 "This should work" (without proving it)  
🚩 "Let me know if you want me to..."

**Your response:** "No. Do it now or explicitly defer with documented reason."

### **3. Demand Proof**

Never accept "it's done" without verification:

```bash
# AI claims task is complete

You: "Show me the completion checklist."
You: "Run ./tools/verify-implementation.sh"
You: "Show me the actual code changes."
You: "Show me the test output."

# Only after seeing proof: "Approved."
```

---

## **The 5 Enforcement Mechanisms**

### **1. Constitution (Auto-Loaded)**

The `.windsurf/constitution.md` file now includes AI Accountability Rules that Windsurf reads automatically.

**What it does:**

- Sets clear expectations for AI behavior
- Lists forbidden patterns (TODOs, placeholders, lazy implementations)
- Requires proof before claiming completion

**You don't need to do anything** - Windsurf reads this on startup.

---

### **2. Verification Script (Run Before Commit)**

**Location:** `tools/verify-implementation.sh`

**What it checks:**

- ✅ No TODO/FIXME comments in new code
- ✅ No placeholder functions
- ✅ Imports are at top of files
- ✅ Test files are substantial (not empty)
- ✅ Error handling is present

**How to use:**

```bash
# Before committing any AI-generated code
./tools/verify-implementation.sh

# If it passes ✅ → Safe to commit
# If it fails ❌ → AI cut corners, reject the work
```

**Pro tip:** Make this part of your workflow:

```bash
# After AI claims "done"
./tools/verify-implementation.sh && git add . && git commit
```

---

### **3. Completion Checklist (Use for Important Tasks)**

**Location:** `tools/ai-checklist-template.md`

**When to use:**

- Important features
- Complex implementations
- When training new team members
- When you need audit trail

**How to use:**

```bash
# 1. Copy template for your task
cp tools/ai-checklist-template.md .cfoi/branches/my-branch/proof/checklist.md

# 2. AI fills it out as they work
# 3. AI provides proof for each item
# 4. You review and approve/reject
```

**What it requires:**

- Actual code snippets (not "I did it")
- Test output (prove tests pass)
- Working demo (screenshot/curl/logs)
- Verification against original plan

---

### **4. Accountability Workflow (Reference Guide)**

**Command:** `/ai-accountability`

**What it is:** Complete reference guide on enforcement

**When to use:**

- When AI is being lazy
- When training new team members
- When you need to remind AI of standards

**Quick access:**

```markdown
# In Windsurf chat

/ai-accountability

# Or open file

.windsurf/workflows/ai-accountability.md
```

---

### **5. Git Hooks (Automatic Enforcement)**

**Location:** `.githooks/pre-commit` and `.githooks-node/pre-commit.js`

**What they catch automatically:**

- Files with TODO/FIXME
- Placeholder implementations
- Imports not at top
- Empty test files

**You don't need to run these** - they run automatically on `git commit`

---

## **Practical Examples**

### **Example 1: AI Leaves a TODO**

**AI says:** "I've implemented the authentication system."

**You check the code:**

```javascript
function validatePassword(password) {
  // TODO: Add password complexity validation
  return true;
}
```

**Your response:**

```markdown
❌ REJECTED

The code contains a TODO comment. Per our accountability rules:

- No TODOs in new code
- Implement password complexity validation NOW
- Show me the actual validation logic
- Provide test cases proving it works
```

**AI fixes it:**

```javascript
function validatePassword(password) {
  if (password.length < 8) return false;
  if (!/[A-Z]/.test(password)) return false;
  if (!/[a-z]/.test(password)) return false;
  if (!/[0-9]/.test(password)) return false;
  return true;
}
```

**You verify:**

```bash
./tools/verify-implementation.sh  # ✅ Passes
```

**Your response:** "✅ Approved. Commit it."

---

### **Example 2: AI Creates Empty Test**

**AI says:** "I've written tests for the authentication system."

**You check:**

```javascript
// auth.test.js
import { validatePassword } from "./auth";

// Tests go here
```

**Your response:**

```markdown
❌ REJECTED

This is an empty test file. Per our accountability rules:

- Tests must actually test the code
- Show me test cases for:
  - Password too short
  - Password missing uppercase
  - Password missing number
  - Valid password
- Run the tests and show me the output
```

---

### **Example 3: AI Wanders Off Topic**

**You asked:** "Add error handling to the user signup endpoint"

**AI says:** "I've refactored the entire authentication system to use a new library..."

**Your response:**

```markdown
⚠️ STOP

You've wandered from the original task. The task was:
"Add error handling to user signup endpoint"

Your changes:

- Refactored authentication system ❌ (not asked for)
- Changed libraries ❌ (not asked for)
- Error handling on signup ❓ (need to verify)

Please:

1. Revert the unnecessary changes
2. Focus ONLY on error handling for signup
3. Show me the specific error cases handled
```

---

## **Training Your Team**

### **For Developers:**

**Day 1: Learn the Red Flags**

```markdown
Have each team member review this file and identify red flags in:

1. Past PR that had issues
2. AI conversation logs
3. Code reviews they've done

Goal: Build red flag recognition
```

**Week 1: Practice Rejection**

```markdown
Pair programming with AI:

- Person A: Works with AI
- Person B: Watches for red flags
- Switch roles after each task

Goal: Build muscle memory for spotting lazy AI
```

**Week 2: Run Enforcement**

```markdown
Every task must include:

1. Run verification script
2. Demand proof of completion
3. Review completion checklist

Goal: Make enforcement automatic
```

---

### **For Interns:**

**Simplified Rules:**

✅ **DO:**

- Always run `./tools/verify-implementation.sh`
- Ask AI to show code, not just describe it
- Look for TODO comments (that's cheating!)
- Run tests before saying "done"

❌ **DON'T:**

- Accept "I'll do it later"
- Trust without verifying
- Skip error handling
- Write empty test files

**Checklist for Interns:**

```markdown
Before marking any task complete:
□ Did I see the actual code?
□ Did I run the tests?
□ Did verification script pass?
□ Is there error handling?
□ Are there any TODOs?
□ Does it do what I originally asked?
```

---

## **Enforcement Levels**

Choose your enforcement level based on project stage:

### **Level 1: Basic (Quick MVPs)**

- ✅ Run verification script
- ✅ Watch for obvious red flags
- ✅ Spot-check AI claims

**Time investment:** +5 minutes per task

---

### **Level 2: Standard (Production Code)**

- ✅ Run verification script
- ✅ Demand proof of completion
- ✅ Review red flags carefully
- ✅ Verify tests actually test

**Time investment:** +15 minutes per task

---

### **Level 3: Strict (Critical Features)**

- ✅ Full completion checklist
- ✅ Code review of all AI output
- ✅ Manual test verification
- ✅ Documentation review

**Time investment:** +30 minutes per task

---

## **Measuring AI Performance**

Track AI quality over time:

```markdown
## Weekly AI Scorecard

Tasks completed: [X]
Tasks requiring rework: [Y]
Rework rate: [Y/X * 100]%

Red flags caught:

- TODOs found: [count]
- Empty tests: [count]
- Wandering off topic: [count]

Quality trend: ↑ Improving / → Stable / ↓ Declining

Action items:

- [What to improve]
```

**Good AI performance:**

- <10% rework rate
- <2 red flags per task
- Stable or improving trend

**Poor AI performance:**

- > 30% rework rate
- Multiple red flags per task
- Declining quality

**If AI performance is poor:** Increase enforcement level

---

## **Common Objections**

### **"This feels like micromanaging the AI"**

**Response:** Would you accept incomplete work from a junior developer? AI should be held to the same standards. This isn't micromanaging - it's quality control.

### **"It takes too long to verify everything"**

**Response:** Fixing bugs in production takes longer. The verification script runs in 5 seconds. Demanding proof takes 2 minutes. Finding and fixing incomplete work later takes hours.

### **"The AI said it's done, shouldn't I trust it?"**

**Response:** Trust, but verify. AI doesn't have accountability or consequences. You do. Always verify.

### **"This seems unnecessarily strict"**

**Response:** Start with Level 1 (basic). If you find issues, increase to Level 2. Only use Level 3 for critical features. Adjust based on your needs.

---

## **Quick Reference Card**

Print this and keep it visible:

```
╔══════════════════════════════════════════╗
║  HOW TO KEEP YOUR AI HONEST              ║
╠══════════════════════════════════════════╣
║                                          ║
║  BEFORE starting:                        ║
║  → Set expectations explicitly           ║
║                                          ║
║  DURING work:                            ║
║  → Watch for red flags                   ║
║  → Demand proof, not promises            ║
║                                          ║
║  AFTER AI claims "done":                 ║
║  → Run ./tools/verify-implementation.sh  ║
║  → Review actual code                    ║
║  → Verify tests pass                     ║
║                                          ║
║  RED FLAGS (reject immediately):         ║
║  🚩 "I'll do X later"                    ║
║  🚩 "Here's a basic version"             ║
║  🚩 "TODO: ..."                          ║
║  🚩 "This should work"                   ║
║  🚩 "See the updated file"               ║
║                                          ║
║  ALWAYS:                                 ║
║  ✓ Verify before accepting               ║
║  ✓ Demand complete work                  ║
║  ✓ No placeholders or TODOs              ║
║                                          ║
╚══════════════════════════════════════════╝
```

---

## **Success Stories**

### **Before Enforcement:**

- Intern ships feature with 5 TODO comments
- Production bugs from missing error handling
- Empty test files give false sense of security
- AI refactors entire codebase instead of fixing one bug

### **After Enforcement:**

- Verification script catches TODOs before commit
- Error handling checked automatically
- Tests prove functionality works
- AI stays focused on original task

---

## **Advanced: Custom Enforcement**

Add your own project-specific rules:

**Edit:** `.windsurf/constitution.md`

```markdown
## Project-Specific AI Rules

REQUIRED for our project:

- All API endpoints must have rate limiting
- All database queries must use prepared statements
- All user input must be validated
- All errors must be logged with request ID

FORBIDDEN in our project:

- Direct database queries from controllers
- Hardcoded API keys
- console.log in production code
- Synchronous file I/O
```

---

## **Tools Summary**

| Tool                                       | Purpose             | When to Use         |
| ------------------------------------------ | ------------------- | ------------------- |
| `./tools/verify-implementation.sh`         | Automated checks    | Every commit        |
| `tools/ai-checklist-template.md`           | Proof of completion | Important tasks     |
| `.windsurf/workflows/ai-accountability.md` | Full reference      | Training, reminders |
| `.windsurf/constitution.md`                | Auto-loaded rules   | Always active       |

---

## **Getting Help**

**Stuck?** Here's your decision tree:

```
AI claims task is done
    ↓
Run verification script
    ↓
Does it pass?
    ├─ No → Reject, AI must fix
    └─ Yes → Review code manually
        ↓
    Any red flags?
        ├─ Yes → Reject, reference this guide
        └─ No → Approve and commit
```

---

## **Remember**

> **AI is a powerful tool, but it's YOUR responsibility to ensure quality.**
>
> These rules aren't about distrusting AI - they're about professional standards.
>
> Trust, but verify. Always.

---

**Questions?** See:

- Full workflow: `.windsurf/workflows/ai-accountability.md`
- Verification script: `tools/verify-implementation.sh`
- Checklist template: `tools/ai-checklist-template.md`
- Constitution: `.windsurf/constitution.md`
