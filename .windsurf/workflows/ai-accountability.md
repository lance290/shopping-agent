---
allowed-tools: "*"
description: Enforce AI thoroughness and prevent wandering or skipping work
---
allowed-tools: "*"

# /ai-accountability

This workflow enforces AI thoroughness when implementing features.

## Problem This Solves

AIs (including Windsurf) have tendencies to:

- Wander off track from the original goal
- Skip "boring" but critical implementation details
- Say "I'll do X" then not actually do X
- Leave TODOs instead of completing work
- Create placeholder code instead of real implementations

## Enforcement Mechanisms

### 1. Explicit Checklist Validation

Before claiming a task is complete, the AI must explicitly confirm:

```markdown
## Task Completion Checklist

- [ ] Original goal from /plan is fully addressed
- [ ] All code files mentioned in /task are created/modified
- [ ] No placeholder functions (no `// TODO`, `pass`, `raise NotImplementedError`)
- [ ] No fake data (all examples use realistic values)
- [ ] All imports are added at top of files
- [ ] All environment variables are documented in env.example
- [ ] Tests are written (not just "test files created")
- [ ] Error handling is implemented (not just happy path)
- [ ] All edge cases from /clarify are handled
- [ ] Documentation is updated (README, comments)
- [ ] Evidence cites active product/effort north star (build-log, manual, automation proof)
```

### 2. Pre-Commit Validation

Git hooks check for:

```javascript
// Check for lazy patterns
const lazyPatterns = [
  /\/\/ TODO:/,
  /\/\/ FIXME:/,
  /raise NotImplementedError/,
  /pass\s*$/,
  /placeholder/i,
  /implement this/i,
  /coming soon/i,
];
```

### 3. Task Decomposition Review

After `/task` creates tasks, require explicit confirmation:

```markdown
## Task Review Before Implementation

For each task:

1. Is the scope crystal clear?
2. Are all dependencies listed?
3. Are acceptance criteria defined?
4. Is the time estimate realistic?

If ANY answer is "no", the task must be clarified before /implement.
```

### 4. Implementation Progress Tracking

During `/implement`, require status updates:

```markdown
## Implementation Progress (Update Every 30 Minutes)

Current task: [name]
Status: [not started | in progress | testing | complete]
Blockers: [list any blockers]
Completed files: [list with line counts]
Remaining work: [be specific]
North star checkpoint: [which product/effort checkpoint the work advances]
```

### 5. Post-Implementation Verification

After claiming completion, verify:

```bash
# Run this verification script
./tools/verify-implementation.sh

Checks:
✓ All planned files exist
✓ No TODO comments in new code
✓ All tests pass
✓ No placeholder functions
✓ All imports resolve
✓ Documentation updated
```

## Usage

When starting work with AI:

```markdown
Before we begin, please acknowledge these accountability rules:

1. Complete all work fully (no placeholders)
2. Verify against original plan
3. Tie every proof artifact back to the active product/effort north star
4. Update progress regularly
5. Confirm completion checklist
6. Run verification before claiming done

Do you acknowledge these requirements?
```

## Windsurf-Specific Enforcement

Add to `.windsurf/constitution.md`:

```markdown
## AI Accountability Rules

When implementing features:

REQUIRED:

- Complete ALL code (no TODOs or placeholders)
- Add ALL imports at top of files
- Implement error handling (not just happy path)
- Write actual tests (not empty test files)
- Update documentation as you go
- Verify against original /plan before completing

FORBIDDEN:

- Saying "I'll do X" then not doing X
- Creating placeholder functions
- Leaving TODO comments in new code
- Fake data or hardcoded examples only
- Claiming completion without verification
- Wandering from original goal

VERIFICATION:

- Read back your own changes
- Confirm each checklist item
- Run tests before claiming done
- Show proof of completion (file contents, test output)
```

## Example Enforcement Conversation

**Human:** Implement user authentication

**AI:** I'll create the auth system with JWT tokens, password hashing, and...

**Human:** STOP. Show me the /task breakdown first with explicit acceptance criteria.

**AI:** [Shows detailed tasks]

**Human:** Good. Now /implement task 1. When you claim it's done, I'll verify the checklist.

**AI:** [Implements task 1, shows code]

**Human:** Checklist verification:

- [ ] Is error handling implemented? (show me the code)
- [ ] Are tests written? (show me test file contents)
- [ ] Are imports at top? (show me line 1-10)
- [ ] Is documentation updated? (show me README section)

**AI:** [Provides proof for each item]

**Human:** Verified. Proceed to task 2.

## Tools to Build

### verify-implementation.sh

```bash
#!/usr/bin/env bash
# Verify AI hasn't cut corners

echo "🔍 Verifying implementation quality..."

# Check for lazy patterns
LAZY_COUNT=$(git diff HEAD --cached | grep -E '(TODO:|FIXME:|NotImplementedError|placeholder|implement this)' | wc -l)
if [ "$LAZY_COUNT" -gt 0 ]; then
  echo "❌ Found $LAZY_COUNT lazy patterns (TODO, FIXME, placeholders)"
  exit 1
fi

# Check for missing imports
for file in $(git diff --cached --name-only --diff-filter=AM | grep -E '\.(js|ts|py)$'); do
  if grep -q 'import\|from\|require' "$file"; then
    FIRST_IMPORT=$(grep -n 'import\|from\|require' "$file" | head -1 | cut -d: -f1)
    if [ "$FIRST_IMPORT" -gt 10 ]; then
      echo "❌ $file: Imports not at top of file (line $FIRST_IMPORT)"
      exit 1
    fi
  fi
done

# Check for empty test files
for file in $(git diff --cached --name-only --diff-filter=AM | grep -E '\.test\.(js|ts|py)$'); do
  LINES=$(wc -l < "$file" | tr -d ' ')
  if [ "$LINES" -lt 10 ]; then
    echo "❌ $file: Test file is suspiciously short ($LINES lines)"
    exit 1
  fi
done

echo "✅ Implementation verification passed"
```

### ai-checklist.md (template)

```markdown
# Implementation Completion Checklist

Date: [auto-filled]
Task: [auto-filled from /task]
Implementer: [AI name]

## Code Completeness

- [ ] All files from /task are created/modified (list them)
- [ ] No TODO or FIXME comments in new code
- [ ] No placeholder functions (all functions have real implementation)
- [ ] All imports are at top of files
- [ ] Error handling is implemented (show examples)
- [ ] Edge cases from /clarify are handled (list them)
- [ ] Build-log, manual, and automation proof files cite `product-north-star.md`

## Testing

- [ ] Unit tests written (show test file path and line count)
- [ ] Tests actually test the code (not just imports)
- [ ] Tests pass locally (show output)
- [ ] Coverage is adequate (show coverage %)
- [ ] Automation proof references product/effort north star and notes alignment

## Documentation

- [ ] env.example updated with new environment variables
- [ ] README updated if API changed
- [ ] Code comments explain "why" not "what"
- [ ] Complex logic is documented

## Integration

- [ ] Code integrates with existing codebase
- [ ] No breaking changes (or documented if intentional)
- [ ] Database migrations created if needed
- [ ] API contracts match /plan
- [ ] Alignment proof (`proof/[task]/alignment.md`) references product north star version

## Verification Proof

Paste proof for each item above:

- File contents (show relevant sections)
- Test output (show pass/fail)
- Coverage report
- Working demo (screenshot or logs)
- North star checkpoint referenced with doc path and version

## Sign-Off

I confirm all items above are complete and verified.
AI Signature: [name]
Human Verification: [ ] Approved [ ] Needs work
```

## Integration with Existing Workflows

### Update /implement workflow:

```markdown
# /implement

Steps:

1. Review task from /task
2. **NEW:** Create ai-checklist.md for this task
3. Implement code
4. **NEW:** Fill out checklist as you go (not at end)
5. **NEW:** Run ./tools/verify-implementation.sh
6. **NEW:** Provide proof for each checklist item
7. Commit only after verification passes
```

### Update /task workflow:

```markdown
# /task

For each task, include:

- Clear scope
- **NEW:** Explicit acceptance criteria (AI must verify these)
- **NEW:** Definition of "done" (what does complete mean?)
- Dependencies
- Time estimate
- **NEW:** Verification steps (how to prove it's done)
```

## Accountability Metrics

Track AI performance:

```markdown
## AI Performance Scorecard

Task: User Authentication Implementation
Total Tasks: 5

Quality Metrics:

- Tasks completed on first try: 3/5 (60%)
- Tasks requiring rework: 2/5 (40%)
- TODO comments in commits: 0 ✅
- Placeholder functions: 0 ✅
- Missing imports: 1 ⚠️
- Tests incomplete: 1 ⚠️

Overall Score: B (80%)

Improvement Areas:

- Remember to add imports
- Write tests while implementing, not after
```

## Red Flags to Watch For

These indicate AI is being lazy:

🚩 **"I'll implement X later"** → No. Implement it now.
🚩 **"Here's a basic version"** → Define "basic". Show full implementation.
🚩 **"TODO: Add error handling"** → Not acceptable. Add it now.
🚩 **"This should work"** → Prove it works. Run it.
🚩 **"See the updated file"** → Show me the actual code, don't just say it's done.
🚩 **"Let me know if you want me to..."** → I told you what to do. Do it.
🚩 **Large commit with no proof** → Show test output, show working demo.

## Enforcement Script for Humans

```bash
# When AI claims something is done
./tools/ai-verify.sh

# Asks:
# 1. Did AI show you the actual code changes?
# 2. Did AI provide test output?
# 3. Did AI verify against original plan?
# 4. Are you satisfied with completeness?

# If any answer is "no", reject the work
```

---
allowed-tools: "*"

**Remember: Trust but verify. AI is a tool, not a supervisor.**
