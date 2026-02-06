---
allowed-tools: "*"
description: Autonomously review, slice, plan, task, and implement all PRDs in a directory
---
# Build-All: Autonomous Full-Stack PRD-to-Implementation Workflow

**Purpose**: Given a directory of PRDs (or the default `docs/prd/`), autonomously review, slice, plan, task, and implement every PRD — in dependency order — without stopping to ask the user clarifying questions. Research the codebase and web instead.

> **When to use**: You have one or more PRDs ready and want the AI to build everything end-to-end.
> **When NOT to use**: You want fine-grained human control at every step — use the individual workflows instead.

---
## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| PRD directory | No | `docs/prd/` | Directory containing PRDs to process |
| Scope filter | No | All `prd-*.md` files | Glob or list of specific PRD files |
| Phase filter | No | All phases | Only process PRDs matching a phase (e.g., `MVP`, `v1.1`) |

**Example invocations:**
```
/build-all                              # Process all PRDs in docs/prd/
/build-all docs/prd/checkout-v2/        # Only PRDs in this subdirectory
/build-all --phase MVP                  # Only P0/MVP PRDs
```

---
## Philosophy

### Autonomous Decision-Making
This workflow does NOT stop to ask clarifying questions. Instead:
1. **Search the codebase first** — existing code, docs, configs, READMEs, architecture decisions
2. **Search the web second** — best practices, library docs, security advisories
3. **Document the assumption** — log what you decided and why in `DECISIONS.md`
4. **Confidence threshold** — if after research you are <60% confident, log the assumption as `⚠️ LOW CONFIDENCE` in DECISIONS.md so the human can review it later. Never silently guess.
5. **File/directory creation is authorized** — invoking `/build-all` grants permission to create required files and directories without asking, as long as changes stay within repo scope.

### Respect Existing Architecture
When running in an existing repo (especially one scaffolded with `/bootup`):
1. **Discover before deciding** — read `package.json`, `tsconfig.json`, `docker-compose*.yml`, `.env*`, existing source files, and any architecture docs before making technical choices
2. **Match existing patterns** — if the repo uses Next.js App Router, don't introduce Pages Router. If it uses Prisma, don't add Drizzle. If it uses pnpm, don't use npm.
3. **Extend, don't replace** — add to existing folder structures, reuse existing utilities, follow existing naming conventions
4. **Log discoveries** — record what you found in `DECISIONS.md` under an "Architecture Discovery" section

### Scoped Execution
- Only processes PRDs found in the specified directory (or default `docs/prd/`)
- Respects the traceability matrix (`docs/prd/TRACEABILITY.md`) for ordering and filtering
- If the user is on phase 3, phases 1 & 2 PRDs are untouched — only PRDs matching the scope are processed
- Already-completed PRDs (status: `Done` in traceability matrix) are skipped

### DRY Across Efforts
Before implementing individual efforts, identify shared code:
- Common utilities, middleware, types, components
- Shared API patterns, error handling, validation
- Extract these into shared modules FIRST, then reference from individual efforts

---
## Step 0: Orient & Discover
// turbo

### 0A: Identify Environment
1. Run `pwd` to confirm working directory
2. Run `git branch --show-current` to identify branch
3. Ensure `.cfoi/branches/[branch-name]/` exists (create if needed)

### 0B: Architecture Discovery (Existing Repo Awareness)
Scan the repo to understand what already exists:

1. **Package manager & dependencies**:
   ```bash
   # Detect package manager
   ls pnpm-lock.yaml yarn.lock bun.lockb package-lock.json 2>/dev/null
   # Read dependencies
   cat package.json 2>/dev/null
   ```

2. **Tech stack & patterns**:
   - Read `tsconfig.json`, `next.config.*`, `vite.config.*`, etc.
   - Check `src/` or `app/` structure for framework patterns
   - Scan for ORM: Prisma schema, Drizzle config, Sequelize models
   - Check for existing auth: NextAuth, Clerk, Auth0 configs
   - Look for existing UI: Tailwind config, component library imports

3. **Infrastructure**:
   - Read `docker-compose*.yml`, `Dockerfile`, `railway.json`, `fly.toml`
   - Check `.env.example` or `.env.schema.json` for required env vars
   - Read `infra/` directory if it exists

4. **Existing architecture docs**:
   - Read `docs/` directory for architecture decisions, setup guides
   - Read any `CLAUDE.md`, `ARCHITECTURE.md`, `README.md`
   - Check `.windsurf/` for constitution or custom rules

5. **Record findings** — create or update `.cfoi/branches/[branch-name]/build-all/architecture-discovery.md`:
   ```markdown
   # Architecture Discovery - [timestamp]

   ## Tech Stack
   - Framework: [e.g., Next.js 14 App Router]
   - Language: [e.g., TypeScript 5.x]
   - Package Manager: [e.g., pnpm]
   - ORM: [e.g., Prisma]
   - Auth: [e.g., NextAuth v5]
   - UI: [e.g., Tailwind + shadcn/ui]
   - Testing: [e.g., Vitest + Playwright]

   ## Folder Structure
   [key directories and their purposes]

   ## Patterns to Follow
   - [naming conventions observed]
   - [API patterns observed]
   - [component patterns observed]

   ## Constraints
   - [env vars required]
   - [services required (DB, Redis, etc.)]
   ```

### 0C: Locate PRDs
1. Resolve the PRD directory:
   - If user provided a path → use that
   - Default → `docs/prd/`
   - If directory doesn't exist → HALT:
     ```
     ❌ No PRD directory found at [path]

     Create PRDs first, then run /build-all.
     ```

2. Inventory all PRD files:
   ```bash
   find [prd-dir] -name "prd-*.md" -type f | sort
   ```

3. Check for traceability matrix at `docs/prd/TRACEABILITY.md`
   - If exists → use it for ordering, priority, and status filtering
   - If missing → will be created during slicing phase (or Step 4A if no slicing occurs)

4. Display inventory:
   ```
   📦 BUILD-ALL INVENTORY
   PRD Directory: [path]
   PRDs Found: [count]
   Traceability Matrix: [exists/missing]

   Files:
   - [prd-file-1.md] (status from matrix or "untracked")
   - [prd-file-2.md] (status from matrix or "untracked")
   ```

---
## Step 1: Product North Star (Autonomous)
// turbo

1. Check if Product North Star exists at `.cfoi/branches/[branch-name]/product-north-star.md`
2. If **missing**:
   - Search the repo for any existing north star docs (`docs/north-star/`, `docs/strategy/`, `README.md`)
   - If found, use it as input to create the Product North Star
   - If not found, search the PRDs themselves for mission/vision/metrics statements
   - Draft a Product North Star from discovered context
   - Log the draft and confidence in `DECISIONS.md` (flag `⚠️ LOW CONFIDENCE` if <60%)
3. If **exists** → load and display:
   ```
   ✅ Product North Star loaded from: [path]
   Mission: [one-line summary]
   ```

---
## Step 2: PRD Review & Gap Analysis
// turbo

For EACH PRD file in scope (respecting dependency order if traceability matrix exists):

### 2A: Deep Read
1. Read the full PRD
2. Read any related PRDs (parent, siblings, dependencies)
3. Cross-reference against the Product North Star

### 2B: Gap Analysis
Check each PRD for:
- **Business Outcome** — is it measurable? Tied to north star metric?
- **Scope** — clear in/out boundaries? No ambiguity?
- **User Flow** — step-by-step flow present? Entry/exit points defined?
- **Cross-cutting concerns** — all 7 areas addressed?
  - Authentication & Authorization
  - Monitoring & Visibility
  - Billing & Entitlements
  - Data Requirements
  - Performance Expectations
  - UX & Accessibility
  - Privacy, Security & Compliance
- **Acceptance Criteria** — quantitative thresholds with sources? No vague criteria?
- **Dependencies** — upstream/downstream explicit?
- **Consistency** — no contradictions with other PRDs or existing codebase?
- **Overreach** — PRD doesn't specify technical implementation details?

### 2C: Fill Gaps
For each gap found:
1. Research the codebase for context (existing patterns, related code, docs)
2. Search the web for best practices if needed
3. Fill the gap directly in the PRD file
4. Log the change in `DECISIONS.md`:
   ```markdown
   ## PRD Gap Fill: [prd-name] - [timestamp]
   - **Gap**: [what was missing]
   - **Resolution**: [what was added]
   - **Source**: [codebase pattern / web reference / inference]
   - **Confidence**: [high/medium/⚠️ LOW CONFIDENCE]
   ```

### 2D: Cross-PRD Consistency Check
After all individual reviews:
1. Check for contradictions between PRDs (conflicting scope, duplicate features)
2. Check for missing handoffs (PRD A depends on something no PRD provides)
3. Check for scope gaps (user journeys that fall between PRDs)
4. Fix inconsistencies and log in `DECISIONS.md`

---
## Step 3: Slice PRDs (if needed)
// turbo

For each PRD that is a **parent** (broad scope, multiple features):

1. Run the `/prd-slice` workflow logic:
   - Extract candidate slices by functional seam
   - Generate child PRD skeletons with cross-cutting concerns
   - Create/update traceability matrix

2. **Post-slice review** — for each child PRD:
   - Check for gaps (same as Step 2B)
   - Check for overreach (scope creep from parent)
   - Check for discrepancies with parent and siblings
   - Fill gaps using codebase/web research

3. **Second review pass** — re-read all child PRDs looking for:
   - Cross-child consistency
   - Dependency completeness
   - Scope coverage (no gaps between children)

4. Update traceability matrix with final ordering

For PRDs that are already well-scoped (single feature, clear boundaries) → skip slicing, proceed as-is.

---
## Step 4: Build Dependency Graph & Extract Shared Components
// turbo

### 4A: Dependency Ordering
1. Read `docs/prd/TRACEABILITY.md` for explicit ordering
2. Build a dependency graph from PRD `Dependencies` sections
3. If no explicit dependencies exist:
   - Default to lexicographic PRD order
   - Log the fallback in `DECISIONS.md`
4. Topological sort → produce ordered execution list
5. Apply filters (phase filter, status filter — skip `Done` PRDs)
6. Display execution plan:
   ```
   📋 EXECUTION ORDER
   ┌───┬─────────────────────┬──────────┬─────────────────┐
   │ # │ PRD                 │ Priority │ Dependencies    │
   ├───┼─────────────────────┼──────────┼─────────────────┤
   │ 1 │ prd-auth.md         │ P0       │ none            │
   │ 2 │ prd-data-model.md   │ P0       │ none            │
   │ 3 │ prd-dashboard.md    │ P0       │ auth, data-model│
   │ 4 │ prd-billing.md      │ P1       │ auth            │
   └───┴─────────────────────┴──────────┴─────────────────┘
   ```

### 4B: Shared Component Identification
Before creating individual efforts, scan across all PRDs for shared needs:
1. **Common patterns**: auth middleware, API error handling, validation schemas, shared types
2. **Common UI**: layout components, form components, common pages (404, loading)
3. **Common infrastructure**: database client, cache layer, logging setup, env config
4. **Common utilities**: date formatting, string helpers, API client wrapper

If shared components are identified:
1. Create a "shared-foundation" effort FIRST (if substantial enough)
2. Or note them as "extract during first effort that needs them" (if minor)
3. Log in `DECISIONS.md`:
   ```markdown
   ## Shared Components Plan - [timestamp]
   - **Foundation effort**: [yes/no]
   - **Shared modules**: [list]
   - **Strategy**: [build first / extract on first use]
   ```

---
## Step 5: Execute Effort Loop
// turbo

For EACH PRD in execution order (from Step 4A):

### 5A: Create Effort
Run `/effort-new` workflow logic:
1. Create effort directory at `.cfoi/branches/[branch-name]/efforts/[effort-name]/`
2. Initialize `effort.json` with metadata from PRD
3. Set as current effort
4. Create `PROGRESS.md`
5. Create effort-level north star from Product North Star + PRD context

### 5B: Plan (with double review)
Run `/plan` workflow logic:
1. Generate technical plan using:
   - PRD requirements
   - Architecture discovery from Step 0B
   - Existing codebase patterns
   - Product and effort north stars
2. **For clarifying questions** — DO NOT ask the user:
   - Search existing code for how similar things are done
   - Search docs for architectural guidance
   - Search the web for best practices
   - Log the decision in `DECISIONS.md` with confidence level

3. **First gap review**:
   - Read the full plan
   - Check: Does every PRD requirement have a plan item?
   - Check: Are technical choices consistent with existing architecture?
   - Check: Are there missing integration points?
   - Check: Is the plan DRY across what's already been built?
   - Fill gaps

4. **Second gap review**:
   - Re-read the plan fresh
   - Check: Any vague steps that need specificity?
   - Check: Any missing error handling or edge cases?
   - Check: Does the plan reference shared components from Step 4B?
   - Fill gaps

5. Save approved plan

### 5C: Task Decomposition (with double review)
Run `/task` workflow logic:
1. Break plan into <45-minute tasks with E2E flows
2. Generate `tasks.json` and `tasks.md`

3. **First gap review**:
   - Check: Every plan item covered by at least one task?
   - Check: Tasks are in correct dependency order?
   - Check: Each task has clear manual verification steps?
   - Check: No mega-tasks (>45 min)?
   - Fill gaps

4. **Second gap review**:
   - Re-read all tasks fresh
   - Check: Are test requirements specified per task?
   - Check: File lists accurate (check if files exist already)?
   - Check: Are shared component references correct?
   - Fill gaps

5. Save approved tasks

### 5D: Implement All Tasks
For EACH task in the effort:
1. Run `/implement` workflow logic (Steps 0 through 7 + Wrap Up)
2. This includes:
   - Green baseline verification
   - North star alignment check
   - Implementation
   - Automated tests
   - Quick review gate (type check, DRY scan, logic check, integration check)
3. After each task completes, update `PROGRESS.md`

### 5E: Checkpoint After Effort
After ALL tasks in an effort are complete:
1. Run tests to verify everything works together
2. Run `/review-loop` workflow logic scoped to files changed in this effort
3. Commit with descriptive message:
   ```
   feat([effort-name]): implement [PRD title]

   - [summary of what was built]
   - Tasks completed: [count]
   - PRD: [path]
   ```
4. Update traceability matrix: set PRD status to `Done`
5. Update `PROGRESS.md` with effort completion
6. Switch to next effort (if more remain)

---
## Step 6: Scope Creep Guard

During ANY step, if a gap or issue is found that expands scope:

### P0 Gaps (Critical — blocks the current PRD from working)
- Fix inline immediately
- Log in `DECISIONS.md`

### P1 Gaps (Important — would improve quality but not blocking)
- Log as a new item in `docs/prd/BACKLOG.md`:
  ```markdown
  ## Backlog Item: [title] - [timestamp]
  - **Source**: Found during build-all, effort [name], step [X]
  - **Priority**: P1
  - **Description**: [what's needed]
  - **Rationale**: [why it matters]
  ```
- Do NOT implement now — continue with current scope

### P2 Gaps (Nice-to-have — future improvement)
- Log in `docs/prd/BACKLOG.md` with P2 priority
- Move on immediately

---
## Step 7: Integration Verification
// turbo

After ALL efforts are complete:

### 7A: Full Test Suite
1. Run the complete test suite across all efforts:
   ```bash
   # Discover and run tests (language-specific)
   # 1) package.json scripts (prefer: test, test:watch, e2e, ci)
   # 2) docker compose (up -d), then run test command in container
   # 3) Makefile (make test)
   # 4) language fallback: pytest | go test ./... | cargo test | ./gradlew test | mvn test
   ```
2. If any tests fail → fix them before proceeding

### 7B: Cross-Effort Integration Check
1. Verify shared components are used consistently
2. Check for duplicate code across efforts (DRY violation)
3. Verify data flows across effort boundaries work correctly
4. Test user journeys that span multiple efforts

### 7C: Build Verification
1. Run the full build:
   ```bash
   # Discover build command
   # 1) package.json scripts (prefer: build)
   # 2) docker compose (up -d), then run build command in container
   # 3) Makefile (make build)
   # 4) language fallback: go build ./... | cargo build | ./gradlew build | mvn package
   ```
2. If build fails → fix before proceeding

---
## Step 8: Final Review
// turbo

Run `/review-loop` workflow logic across ALL files changed during build-all:
1. Collect all changed files across all efforts
2. Perform the 12-layer deep review
3. Fix Critical and Major issues
4. Re-review until clean

---
## Step 9: Summary Report

Generate `BUILD-ALL-REPORT.md` at `.cfoi/branches/[branch-name]/build-all/BUILD-ALL-REPORT.md`:

```markdown
# Build-All Report - [timestamp]

## Scope
- PRD Directory: [path]
- PRDs Processed: [count]
- PRDs Skipped (already done): [count]
- Phase Filter: [if any]

## Architecture
- Framework: [discovered]
- Key Patterns: [followed]
- New Dependencies Added: [list]

## Execution Summary
| # | PRD | Effort | Tasks | Status | Duration |
|---|-----|--------|-------|--------|----------|
| 1 | prd-auth.md | feature-auth | 5 | ✅ Done | ~2h |
| 2 | prd-dashboard.md | feature-dashboard | 8 | ✅ Done | ~3h |

## Decisions Made
- [count] decisions logged in DECISIONS.md
- [count] flagged as ⚠️ LOW CONFIDENCE (requires human review)

## Scope Creep Items (Deferred)
- [count] P1 items in BACKLOG.md
- [count] P2 items in BACKLOG.md

## Quality
- Review Loop: [iterations] iterations, [issues found] → [issues fixed]
- Final Verdict: [PASS/PASS_WITH_SUGGESTIONS]
- Test Coverage: [if measurable]

## Artifacts
- Architecture Discovery: .cfoi/branches/[branch]/build-all/architecture-discovery.md
- Decisions Log: .cfoi/branches/[branch]/build-all/DECISIONS.md
- Backlog: docs/prd/BACKLOG.md
- Traceability: docs/prd/TRACEABILITY.md
- Per-effort: .cfoi/branches/[branch]/efforts/[name]/PROGRESS.md (each)

## Next Steps
- [ ] Review ⚠️ LOW CONFIDENCE decisions in DECISIONS.md
- [ ] Review P1 backlog items
- [ ] Run /push to commit and push
- [ ] Human PR review
```

Display final summary:
```
🎉 BUILD-ALL COMPLETE!

📊 Results:
- [X] PRDs processed
- [Y] efforts created
- [Z] tasks implemented
- [W] decisions logged ([N] need human review)

📁 Full report: .cfoi/branches/[branch]/build-all/BUILD-ALL-REPORT.md

⚠️ ACTION REQUIRED:
- Review [N] low-confidence decisions in DECISIONS.md
- Review [M] deferred backlog items

🚦 NEXT: /push to commit and push all changes
```

---
## Failure Handling

### ⚠️ Band-Aid Loop Prevention (CRITICAL FOR BUILD-ALL)

**Build-all is especially vulnerable to band-aid loops** because it runs autonomously and can burn hundreds of credits chasing symptoms instead of root causes.

**The `/implement` workflow contains the full Root Cause Protocol.** The key rules that apply here:

1. **2-attempt limit per issue** — after 2 failed fix attempts on the same error, trigger the mandatory diagnostic pause (stop coding, read full error, `git diff`, trace upstream)
2. **Never suppress errors** — no `as any`, `@ts-ignore`, empty `try/catch`, `?.` where null shouldn't exist
3. **Fix at the origin, not the symptom** — if you're patching where the error appears instead of where bad state originates, you're band-aiding
4. **3 strikes = revert and rethink** — if 3 attempts fail, revert to last known-good commit and re-approach with a completely different strategy
5. **Review-loop cap: 4 iterations** — if `/review-loop` hits 4 iterations and still has Critical/Major issues, HALT and generate a stuck-report

**Credit budget awareness**: If you've spent 3+ fix attempts across a single effort without forward progress, the effort is likely blocked by a design issue. Mark it blocked and move on.

### Task Implementation Fails
1. Log the failure in `PROGRESS.md`
2. Attempt to fix (up to 2 retries per task — **follow Root Cause Protocol, not random patches**)
3. On each retry: write a root cause hypothesis BEFORE attempting the fix
4. If still failing after retries:
   - Revert to last known-good commit for that effort
   - Mark task as `blocked` in `tasks.json`
   - Log blocker in `DECISIONS.md` as `🚨 BLOCKED` with root cause analysis
   - **Continue to next task** (don't halt the entire build)
5. At the end, report all blocked tasks in the summary

### Effort Fails Entirely
1. Revert the effort's changes
2. Mark PRD status as `Blocked` in traceability matrix
3. Log the failure and continue to next effort
4. Dependent efforts are automatically skipped (dependency graph)
5. Ask before any destructive operations (e.g., `git reset --hard`, deleting volumes)

### Context Window Approaching Limit
1. Update `PROGRESS.md` with exact current state
2. Update `BUILD-ALL-REPORT.md` with partial results
3. Display resume instructions:
   ```
   ⚠️ Context limit approaching. Progress saved.

   To resume: /build-all
   - Will read PROGRESS.md and BUILD-ALL-REPORT.md
   - Will skip completed efforts
   - Will resume from: [current effort, current task]
   ```

---
## Resume Support

When `/build-all` is invoked and a previous run exists:

1. Check for `.cfoi/branches/[branch-name]/build-all/BUILD-ALL-REPORT.md`
2. If found → offer to resume:
   ```
   📋 Previous build-all run detected!

   Last run: [timestamp]
   Completed: [X/Y] efforts
   Current: [effort-name], task [task-id]

   Resume from where we left off? (yes/restart)
   ```
3. If resuming:
   - Load architecture discovery (skip Step 0B)
   - Skip completed PRDs (check traceability matrix)
   - Resume current effort at current task
   - Continue execution loop

---
## Key Rules

1. **Never ask clarifying questions** — research codebase and web instead, log decisions
2. **Respect existing architecture** — discover and match, don't replace
3. **Scope to provided directory** — don't touch PRDs outside the specified path
4. **Skip completed work** — check traceability matrix status before processing
5. **DRY across efforts** — identify and extract shared code early
6. **Double-review everything** — plans get two gap reviews, tasks get two gap reviews
7. **Log all decisions** — every autonomous choice goes in DECISIONS.md with confidence
8. **Fail forward** — blocked tasks/efforts don't halt the entire build
9. **Checkpoint often** — commit after each effort completes
10. **Preserve git integrity** — never use `--no-verify`
11. **Ask before destructive actions** — `git reset --hard`, deleting volumes, removing `node_modules`
12. **File/directory creation is authorized** — `/build-all` grants permission to create required files/dirs without asking
13. **Root Cause Protocol enforced** — max 2 fix attempts per issue before diagnostic pause, max 4 review-loop iterations, never suppress errors with band-aids
