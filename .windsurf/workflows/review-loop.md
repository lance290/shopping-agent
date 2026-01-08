---
allowed-tools: "*"
description: Deep iterative code review loop until passing
---
allowed-tools: "*"

# Review Loop Workflow

**Philosophy**: Tests passing ≠ quality code. LLMs write code that "works" but fails spectacularly in human code review. This workflow runs deep, iterative reviews until the code is actually good.

> **The Problem**: Click tests verify behavior. Tests verify assertions. Neither verifies:
> - Code structure and design
> - Maintainability and readability
> - Security and performance
> - Following project conventions
> - Future-proofing and extensibility
>
> **The Solution**: Review loop until a human reviewer would approve.

---
allowed-tools: "*"

## Step 0: Determine Scope
// turbo

1. Load current effort from `.cfoi/branches/[branch-name]/.current-effort`
2. Read `tasks.md` to identify all completed tasks
3. Collect all files changed in this effort by scanning:
   - `proof/*/build-log.md` for file lists
   - Git diff: `git diff main...HEAD --name-only`
4. Create review scope document at `review-loop/scope.md`:
   ```markdown
   # Review Scope - [effort-name]
   
   ## Files to Review
   - [file1.ts] (modified)
   - [file2.ts] (added)
   - [file3.ts] (modified)
   
   ## Out of Scope (unchanged)
   - [file4.ts] - existed before effort
   
   ## Review Started: [timestamp]
   ```

---
allowed-tools: "*"

## Step 0.5: Mandatory Fresh Read ⚠️ CRITICAL
// turbo

**DO NOT SKIP THIS. DO NOT RELY ON MEMORY OR SUMMARIES.**

For EACH file in scope:
1. **Actually read the file NOW** - Use the read tool, not your memory
2. **Do NOT trust checkpoint summaries** - They miss context
3. **Do NOT assume "I already reviewed this"** - You didn't, or you missed things
4. **Read the FULL file** - Not just the parts you think are relevant

```
⚠️ LLM ACCOUNTABILITY CHECK

For each file in scope, I MUST:
[ ] Read it fresh with the read_file tool RIGHT NOW
[ ] Not skip because "I viewed it earlier"
[ ] Not rely on summaries from previous sessions
[ ] Read ALL of it, not just search for specific patterns

Files I am about to read fresh:
- [file1.ts] - reading now...
- [file2.ts] - reading now...
```

**WHY THIS MATTERS**: You (the LLM) will try to skip this because you "remember" the file. Your memory is WRONG. Your summaries MISS THINGS. Read it fresh or you WILL miss bugs.

---
allowed-tools: "*"

## Step 1: Deep Review Pass
// turbo

For EACH file in scope, perform the following review layers:

### ⚠️ FIRST: Call Flow Tracing (Before Individual File Review)

**Do NOT review files in isolation.** Trace how they connect:

1. **Map the call graph** for this effort:
   - Which functions call which other functions?
   - Which files import from which other files?
   - Draw the dependency arrows

2. **For each function that calls another**:
   - Read BOTH files side-by-side
   - Verify arguments passed match parameters expected
   - Check return value is used correctly
   - Look for data transformation bugs (caller sends X, callee expects Y)

3. **Look for double-work bugs**:
   - Function A builds something
   - Function B receives it and rebuilds the same thing
   - Result: wasted compute, double API calls, double costs

4. **Check integration points**:
   - Where data crosses file boundaries
   - Where promises/callbacks hand off control
   - Where state is shared or passed

```
📊 CALL FLOW MAP - [effort-name]

[file1.ts] → functionA()
    ↓ calls
[file2.ts] → functionB(params)
    ↓ returns
[file1.ts] → uses result

INTEGRATION POINTS TO VERIFY:
- [ ] functionA → functionB: args match signature?
- [ ] functionB return → functionA usage: type correct?
- [ ] Any double-processing of same data?
```

**This step catches bugs that file-by-file review WILL MISS.**

---
allowed-tools: "*"

### Layer 1: Structural & DRY Review
- **File organization**: Imports grouped? Exports at bottom? Logical ordering?
- **File length**: Under 450 lines? If over, identify split points
- **Function length**: Functions under 50 lines? If over, identify extraction points
- **Single Responsibility**: Each function does ONE thing?
- **Dead code**: Unused imports, unreachable code, commented-out blocks?

**DRY Violations (Critical)** - Hunt for these aggressively:
- **Copy-paste code**: Same logic in 2+ places, even with slight variations?
- **Similar functions**: Two functions that do almost the same thing?
- **Repeated conditionals**: Same if/else chain in multiple places?
- **Duplicate validation**: Same checks repeated across files?
- **Config duplication**: Same constants/settings defined multiple times?
- **Pattern duplication**: Same fetch→parse→handle pattern copy-pasted?
- **Extract candidates**: Logic that should be a shared utility?

### Layer 2: Naming & Clarity Review
- **Variable names**: Descriptive? No single letters except loops? No abbreviations?
- **Function names**: Verb-based? Describes what it does? Not what it is?
- **Boolean names**: Uses `is`, `has`, `should`, `can` prefix?
- **Magic values**: Any hardcoded numbers/strings without explanation?
- **Comments**: Explain WHY not WHAT? No obvious comments?

### Layer 3: Error Handling Review
- **Try-catch**: All async operations wrapped? Specific error types caught?
- **Null checks**: Optional chaining or explicit checks before access?
- **Input validation**: Function parameters validated before use?
- **Error messages**: Descriptive? Include context (IDs, values)?
- **Error propagation**: Errors logged AND thrown/returned appropriately?
- **Edge cases**: Empty arrays, null inputs, zero values, boundary conditions?

### Layer 4: Security & Privacy Review
**Authentication/Authorization:**
- **Authn gaps**: All protected routes require authentication?
- **Authz gaps**: Permission checks before data access? Role checks?
- **Session handling**: Secure cookies? Token expiration?

**Injection & Input:**
- **SQL/NoSQL injection**: Using parameterized queries?
- **XSS**: Output encoding in place?
- **SSRF**: Server-side requests validated? URL allowlists?
- **Deserialization**: Safe parsing of untrusted data?
- **Unsafe eval**: No eval(), new Function(), innerHTML with user data?
- **Input sanitization**: User input sanitized before use?

**Secrets & PII:**
- **Secrets in code**: No hardcoded API keys, passwords, tokens?
- **Secrets in logs**: Logging sanitizes sensitive data?
- **PII handling**: Personal data encrypted? Minimized? Retention policy?

**Web Security:**
- **CSRF**: Tokens on state-changing requests?
- **CORS**: Origin checks appropriate? Not overly permissive?
- **Storage encryption**: Sensitive data encrypted at rest?
- **Transport encryption**: HTTPS enforced? Certificate validation?

**Other:**
- **Rate limiting**: On public endpoints? On auth endpoints?
- **Dependency risk**: Known vulnerabilities in packages?

### Layer 5: Performance & Scaling Review
**Database:**
- **N+1 queries**: Database calls in loops?
- **Query correctness**: Queries return what's expected? Correct joins?
- **Missing indexes**: Queries need index hints?
- **Missing pagination**: Unbounded result sets?

**Network:**
- **Chatty calls**: Multiple requests that could be batched?
- **Large fan-out**: Single request causing many downstream calls?
- **Blocking I/O**: Synchronous calls on hot paths?

**Memory & CPU:**
- **Unnecessary allocations**: Creating objects in tight loops?
- **Memory leaks**: Event listeners cleaned up? Intervals cleared?
- **Large objects**: Passed by reference where appropriate?

**Frontend:**
- **Unnecessary re-renders**: React deps arrays correct?
- **Bundle size**: Large imports that could be code-split?

**Caching:**
- **Missing caching**: Expensive operations not cached?
- **Cache invalidation**: Stale data risks? Invalidation strategy?

**Async:**
- **Sequential awaits**: Should use Promise.all?
- **Missing timeouts**: Requests that could hang forever?

### Layer 6: Project Convention Review
- **Folder structure**: Files in correct directories per constitution?
- **Import paths**: Using aliases? Consistent relative/absolute?
- **Naming patterns**: Matches project conventions (kebab-case files, PascalCase components)?
- **API patterns**: Following REST conventions? Consistent response format?
- **Error format**: Using project's standard error format?
- **Type definitions**: In correct location? Following project patterns?
- **Test patterns**: Test files co-located? Following naming convention?

### Layer 7: Logic & Correctness Review
- **Off-by-one errors**: Array bounds checked?
- **Race conditions**: Concurrent state updates handled?
- **State consistency**: State updates atomic where needed?
- **Cleanup on unmount/exit**: Resources released?
- **Retry logic**: Idempotent? Backoff implemented?
- **Timezone handling**: Using UTC internally?
- **Floating point**: Using appropriate comparison for floats?

**Logic Errors (Will This Even Work?):**
- **Wrong comparison**: Using `=` instead of `===`? Comparing wrong types?
- **Inverted logic**: Condition that's backwards from intent?
- **Missing return**: Function path that doesn't return when it should?
- **Wrong variable**: Using `item` when you meant `items[i]`?
- **Stale closure**: Referencing variable that changes but closure captures old value?
- **Async confusion**: Forgetting await? Returning promise instead of value?
- **Wrong order**: Operations that depend on order but aren't guaranteed?
- **Mutation bugs**: Mutating input parameter? Mutating shared state?
- **Type coercion**: Truthy/falsy bugs? "0" vs 0? [] vs null?

### Layer 8: Spaghetti Detection (Code That Will Break)

**Control Flow Chaos:**
- **Deeply nested**: More than 3 levels of nesting? (if inside if inside if...)
- **Early return missing**: Long functions that should bail out early?
- **Goto-style jumps**: Break/continue/return scattered randomly?
- **Callback hell**: Nested callbacks instead of async/await?
- **Flag variables**: Boolean flags controlling complex branching?

**Coupling & Dependencies:**
- **God functions**: One function that does everything?
- **Hidden dependencies**: Function relies on global state or external setup?
- **Tight coupling**: Components that can't work without each other?
- **Circular imports**: A imports B imports A?
- **Action at a distance**: Modifying state that affects distant code?

**Readability Red Flags:**
- **Clever code**: Would a junior dev understand this in 5 seconds?
- **Dense expressions**: Chained ternaries? Complex one-liners?
- **Implicit behavior**: Code that relies on side effects?
- **Misleading names**: Function name doesn't match what it does?
- **Context required**: Must read 3 other files to understand this one?

**Fragility Indicators:**
- **No defensive coding**: Assumes inputs are always valid?
- **Brittle parsing**: Will break if format changes slightly?
- **Order-dependent**: Only works if called in specific sequence?
- **Environment-dependent**: Works locally but will fail in prod?
- **Timing-dependent**: Race condition waiting to happen?

### Layer 9: Best Practices Audit

**SOLID Principles:**
- **Single Responsibility**: Class/function doing too many things?
- **Open/Closed**: Would need to modify existing code to extend?
- **Liskov Substitution**: Subtypes behave differently than expected?
- **Interface Segregation**: Forcing clients to depend on unused methods?
- **Dependency Inversion**: High-level modules depending on low-level details?

**Clean Code Principles:**
- **Functions do one thing**: And do it well?
- **Meaningful names**: Self-documenting without comments?
- **Small functions**: Under 20 lines ideal, max 50?
- **No side effects**: Pure functions where possible?
- **Command-query separation**: Functions either do something OR return something?
- **Fail fast**: Validate early, fail with clear message?

**Modern Patterns:**
- **Immutability**: Using spread/Object.assign instead of mutation?
- **Composition over inheritance**: Preferring composition?
- **Dependency injection**: Dependencies passed in, not created internally?
- **Separation of concerns**: Business logic separate from I/O?
- **Error boundaries**: Graceful degradation on failure?

### Layer 10: Test Coverage & Quality Review
**Missing Test Scenarios** - Name exact scenarios needed:
- **Happy path**: Basic success case covered?
- **Error cases**: What happens when it fails?
- **Edge cases**: Empty input, null, zero, max values, boundary conditions?
- **Specific scenarios to check**:
  - "Fails when header is absent"
  - "Large payload handling"
  - "Retries exhausted"
  - "Time skew / clock drift"
  - "Partial success (some items fail)"
  - "Concurrent writes / race conditions"
  - "i18n / RTL text handling"
  - "Network timeout"
  - "Auth token expired mid-operation"

**Test Quality:**
- **Flaky patterns**: Tests depending on timing, order, or external state?
- **Deterministic checks**: Can test be made deterministic?
- **Mocking**: Appropriate mocks? Not over-mocked?
- **Assertions**: Actually asserting something meaningful?
- **Coverage gaps**: Code paths not exercised?

### Layer 11: UX & Accessibility Review
**State Handling:**
- **Loading states**: Shown while async operations in progress?
- **Error states**: Clear error messages? Recovery options?
- **Empty states**: Helpful message when no data?
- **Partial states**: Graceful handling of incomplete data?

**Accessibility:**
- **Keyboard navigation**: All interactions keyboard-accessible?
- **Screen reader**: Proper labels, roles, announcements?
- **ARIA**: Correct aria-* attributes where needed?
- **Focus management**: Focus moves appropriately? Visible focus indicator?
- **Motion**: Respects prefers-reduced-motion?
- **Contrast**: Text meets contrast requirements?

**UX Concerns:**
- **Confusing copy**: Clear, actionable text?
- **Irreversible actions**: Confirmation dialogs? Undo option?
- **Feedback**: User knows action succeeded/failed?
- **Progressive disclosure**: Not overwhelming user with options?

### Layer 12: API & Contract Review
**Backward Compatibility:**
- **Breaking changes**: Will this break existing clients?
- **Versioning**: API versioned appropriately?
- **Deprecation**: Old endpoints deprecated gracefully?

**Payload & Types:**
- **Payload shapes**: Match documented schema?
- **Enums**: New enum values handled by clients?
- **Optional fields**: Clients handle missing fields?
- **Type changes**: Field type changes break anything?

**Rollout Safety:**
- **Feature flags**: Behind flag for gradual rollout?
- **Migrations**: Data migration needed? Reversible?
- **Rollback**: Can we roll back safely if issues?
- **Observability**: Metrics/logs to detect issues?

**Config & Environment:**
- **Env assumptions**: Works in all environments (dev/staging/prod)?
- **Config validation**: Missing config fails fast with clear error?
- **Feature detection**: Graceful degradation if feature unavailable?

---
allowed-tools: "*"

## Step 2: Generate Issue Report
// turbo

Create `review-loop/issues-[iteration].md`:

```markdown
# Code Review Issues - Iteration [N]

## Summary
- **Total Issues**: [count]
- **Critical**: [count] (must fix)
- **Major**: [count] (should fix)
- **Minor**: [count] (nice to fix)
- **Nits**: [count] (optional polish)

## Critical Issues 🔴
These BLOCK approval. Must be fixed.

### C1: [Short description]
- **File**: [path:line]
- **Category**: [Security/Logic/Error Handling]
- **Problem**: [Detailed explanation of the issue]
- **Risk**: [What could go wrong]
- **Fix**: [Specific code change needed]
```code
// Current (bad)
...

// Should be (good)
...
```

## Major Issues 🟠
These require attention. Should be fixed.

### M1: [Short description]
- **File**: [path:line]
- **Category**: [Performance/DRY/Structure]
- **Problem**: [Explanation]
- **Fix**: [Specific change]

## Minor Issues 🟡
These improve quality. Nice to fix.

### m1: [Short description]
- **File**: [path:line]
- **Category**: [Naming/Comments/Convention]
- **Suggestion**: [Improvement]

## Nits 🟢
Polish items. Fix if time permits.

### n1: [Description]
- [Quick suggestion]

---
allowed-tools: "*"

## Verdict: [FAIL / PASS_WITH_SUGGESTIONS / PASS]

[If FAIL]: Fix all Critical and Major issues, then re-run /review-loop
[If PASS_WITH_SUGGESTIONS]: Consider minor issues, ready for human review
[If PASS]: Code is clean, ready for merge
```

---
allowed-tools: "*"

## Step 3: Await User Decision
<!-- NO turbo - requires human decision -->

Display summary and await decision:

```
🔍 REVIEW LOOP - Iteration [N]

📊 ISSUES FOUND:
┌──────────┬───────┬─────────────────────────────────────┐
│ Severity │ Count │ Action Required                     │
├──────────┼───────┼─────────────────────────────────────┤
│ 🔴 Critical │ [N] │ MUST fix - blocks approval          │
│ 🟠 Major    │ [N] │ Should fix - impacts quality        │
│ 🟡 Minor    │ [N] │ Nice to fix - improves polish       │
│ 🟢 Nits     │ [N] │ Optional - perfectionism            │
└──────────┴───────┴─────────────────────────────────────┘

📋 TOP 3 CRITICAL/MAJOR ISSUES:
1. [Issue summary + file:line]
2. [Issue summary + file:line]
3. [Issue summary + file:line]

📁 Full report: review-loop/issues-[N].md

🎯 VERDICT: [FAIL / PASS_WITH_SUGGESTIONS / PASS]

What would you like to do?
- "fix" or "fix all" → Fix all Critical + Major issues automatically
- "fix critical" → Fix only Critical issues
- "fix [C1, M2, m3]" → Fix specific issues by ID
- "skip" → Accept current state (not recommended if FAIL)
- "details [C1]" → Show more details about specific issue
```

---
allowed-tools: "*"

## Step 4: Fix Issues (if requested)
// turbo

For each issue to fix:

1. **Read the file** containing the issue
2. **Apply the fix** from the issue report
3. **Verify** the fix doesn't break anything:
   - Run affected tests
   - Check no new issues introduced
4. **Log** the fix in `review-loop/fixes-[iteration].md`:
   ```markdown
   # Fixes Applied - Iteration [N]
   
   ## [Issue ID]: [Short description]
   - **File**: [path]
   - **Change**: [what was changed]
   - **Tests**: [passed/failed]
   ```

**Continue immediately to Step 5 after all fixes applied.**

---
allowed-tools: "*"

## Step 5: Re-Review Changed Files
// turbo

1. Re-run Step 1 ONLY on files that were modified in Step 4
2. Check if fixes introduced new issues
3. Generate new issue report (increment iteration)

**If new issues found**: Return to Step 3 (display + await decision)
**If no issues OR only Nits remain**: Continue to Step 6

---
allowed-tools: "*"

## Step 6: Final Summary
// turbo

When review passes (no Critical/Major issues):

```
🎉 REVIEW LOOP COMPLETE!

📊 REVIEW HISTORY:
┌───────────┬──────────┬────────┬───────────────┐
│ Iteration │ Issues   │ Fixed  │ Result        │
├───────────┼──────────┼────────┼───────────────┤
│ 1         │ 12 total │ 8      │ Re-review     │
│ 2         │ 3 total  │ 3      │ Re-review     │
│ 3         │ 1 nit    │ 0      │ PASS          │
└───────────┴──────────┴────────┴───────────────┘

✅ FINAL STATUS: APPROVED

📁 Review artifacts:
- review-loop/scope.md
- review-loop/issues-1.md
- review-loop/fixes-1.md
- review-loop/issues-2.md
- review-loop/fixes-2.md
- review-loop/issues-3.md (final - clean)

🏆 Code quality verified (12 layers):
- [X] Structural integrity & DRY
- [X] Naming & clarity
- [X] Error handling
- [X] Security & privacy
- [X] Performance & scaling
- [X] Project conventions
- [X] Logic correctness
- [X] No spaghetti code
- [X] Best practices (SOLID, Clean Code)
- [X] Test coverage & quality
- [X] UX & accessibility
- [X] API contracts & rollout safety

📍 NEXT STEPS:
1. /checkpoint → Save this state
2. /push → Push changes
3. Human PR review (should be smooth now!)
```

Save final summary to `review-loop/summary.md`.

---
allowed-tools: "*"

## Review Severity Guide

| Severity | Definition | Examples |
|---
allowed-tools: "*"-------|------------|----------|
| 🔴 **Critical** | Would fail human review immediately. Security risk, data loss, broken functionality | SQL injection, missing auth check, infinite loop, memory leak, data corruption |
| 🟠 **Major** | Significant quality issue. Would require changes in PR review | N+1 query, 300-line function, copy-pasted code blocks, no error handling on critical path |
| 🟡 **Minor** | Noticeable issue but not blocking. Reviewer would mention | Unclear variable name, missing JSDoc, inconsistent spacing, could use optional chaining |
| 🟢 **Nit** | Perfectionism. Reviewer might not even mention | Slightly better way to write something, personal style preference |

---
allowed-tools: "*"

## When to Use

- **After `/implement`** completes all tasks
- **Before `/push`** or creating PR
- **When you suspect quality issues** but tests pass
- **Before human code review** to save reviewer time

---
allowed-tools: "*"

## Anti-Patterns This Catches

LLMs commonly produce code that:

**DRY Violations:**
1. **Copy-paste everywhere** - Same logic in 3+ places with slight variations
2. **Almost-duplicate functions** - Two functions that do 90% the same thing
3. **Repeated patterns** - Same fetch→parse→handle copied throughout

**Logic Errors:**
4. **Wrong but passes tests** - Logic that happens to work for test cases but fails in prod
5. **Inverted conditions** - If/else that's backwards from intent
6. **Missing await** - Async code that returns promises instead of values
7. **Stale closures** - Capturing variables that change
8. **Mutation bugs** - Changing inputs or shared state unexpectedly

**Spaghetti Code:**
9. **God functions** - 500-line function that does everything
10. **Nesting nightmare** - 6 levels of if/else/for/try
11. **Callback hell** - Nested callbacks instead of async/await
12. **Hidden dependencies** - Only works if called after some other function
13. **Action at a distance** - Changes here break things over there

**Best Practice Violations:**
14. **No separation of concerns** - Business logic mixed with I/O
15. **Tight coupling** - Components that can't exist without each other
16. **No defensive coding** - Assumes inputs are always valid
17. **Fragile parsing** - Will break if format changes slightly

**And the classics:**
18. **Works but is insecure** - Missing auth, injection vulnerabilities
19. **Works but is slow** - N+1 queries, unnecessary re-renders
20. **Works but leaks resources** - Memory, connections, file handles

**Cross-File Bugs (Require Call Flow Tracing):**
21. **Double-work bugs** - Function A builds prompt, Function B rebuilds same prompt around it = 2x API calls, 2x cost
22. **Signature drift** - Caller passes 3 args, callee expects 4 (or different types)
23. **Return value ignored** - Function returns important data, caller doesn't use it
24. **Data transformation mismatch** - Caller sends raw data, callee expects processed
25. **Integration orphans** - New function exists but nothing calls it

---
allowed-tools: "*"

## LLM Review Failures (Why Reviews Miss Bugs)

**These are failure modes of the LLM doing the review, not the code:**

1. **Relying on memory** - "I already read this file" → No you didn't, or you missed things
2. **Trusting summaries** - Checkpoint says "viewed gemini.ts" → Doesn't mean you understood it
3. **Narrow focus** - Asked about pricing → Only checked pricing, missed logic bugs next to it
4. **Isolated file review** - Reviewed file A, reviewed file B, never traced A→B call flow
5. **Pattern matching** - Searched for "DRY violations" → Missed the double-prompt bug that IS a DRY violation but doesn't LOOK like one
6. **Skipping "boring" files** - Utility files, config files → Often where bugs hide
7. **Assuming tests catch it** - "Tests pass so logic must be right" → Tests don't test everything

**The fix**: Step 0.5 (mandatory fresh read) + Call Flow Tracing

---
allowed-tools: "*"

## Configuration

To customize review strictness, create `review-loop/config.md`:

```markdown
# Review Loop Configuration

## Enabled Layers (12 total)
- [x] Layer 1: Structural & DRY Review
- [x] Layer 2: Naming & Clarity
- [x] Layer 3: Error Handling
- [x] Layer 4: Security & Privacy
- [x] Layer 5: Performance & Scaling
- [x] Layer 6: Project Conventions
- [x] Layer 7: Logic & Correctness
- [x] Layer 8: Spaghetti Detection
- [x] Layer 9: Best Practices Audit
- [x] Layer 10: Test Coverage & Quality
- [x] Layer 11: UX & Accessibility
- [x] Layer 12: API & Contract Review

## Thresholds
- Max file length: 450 lines (default)
- Max function length: 50 lines (default)
- DRY threshold: 2 occurrences (default)

## Skip Patterns
- test/**/* (don't review test files for structure)
- **/*.d.ts (generated types)
- **/migrations/* (database migrations)

## Project-Specific Rules
- [Add any custom rules here]
```
