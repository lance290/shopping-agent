---
allowed-tools: "*"
description: Govern the product North Star and effort-level north stars
---
allowed-tools: "*"

# North Star Governance Workflow

## Overview
- **Purpose**: Maintain a single authoritative Product North Star (capitalized) while ensuring each effort carries a scoped north star aligned with the product vision.
- **Artifacts**:
  - Global Product North Star: `.cfoi/branches/<branch>/product-north-star.md`
  - Effort north star: `.cfoi/branches/<branch>/efforts/<effort>/product-north-star.md`
  - Alignment proof: `proof/<task>/alignment.md`
  - Update ledger: `.cfoi/branches/<branch>/north-star-history.md`

## Step 0: Confirm Branch & Effort Context
- Identify active branch via `git branch --show-current`.
- Resolve current effort using `.cfoi/branches/<branch>/.current-effort` when present.
- Load existing Product North Star path (branch-level) and effort north star path if it exists.

## Step 1: Author or Update the Product North Star (Capital N & S)
- **When**: New product, pivot, or significant strategic change.
- **Process**:
  - Draft in `.cfoi/branches/<branch>/product-north-star.md` following the template:
    - Mission statement
    - Target users & core jobs
    - Differentiators & guardrails
    - Key success metrics / OKRs
    - Non-negotiables & exclusions
  - Capture rationale, approver initials, and date in `.cfoi/branches/<branch>/north-star-history.md` (append log entry).
  - Notify stakeholders; require human approval recorded in the branch’s `north-star-history.md` before adoption.

## Step 2: Derive Effort-Level north star
- **Trigger**: New effort creation or Product North Star update affecting the effort.
- **Process**:
  - Create or refresh `.cfoi/branches/<branch>/efforts/<effort>/product-north-star.md`.
  - Include sections:
    - Effort goal statement referencing the Product North Star
    - Scope (in/out)
    - Acceptance checkpoints mapped to product-level metrics
    - Dependencies & key risks
  - Link back to the Product North Star version (commit hash or history entry).
  - Record creation/update in `proof/<task>/alignment.md` with timestamp.

## Step 3: Broadcast Updates to Active Workstreams
- Use `/swarm plan` or `/swarm implement` to propagate changes.
- Provide payload including:
  - Branch Product North Star path
  - Effort north star path(s)
  - Summary of changes from `north-star-history.md`
- Queen agent must acknowledge receipt; store acknowledgement in the swarm session `artifacts/alignment.md`.

## Step 4: Enforce Alignment in Implementation
- `/implement` Step 0 must verify both Product North Star and effort north star paths exist.
- Alignment swarm preflight (Step 2 of `/implement`) should:
  - Re-state key checkpoints from both north star docs.
  - Require human confirmation in `proof/<task>/alignment.md` that the task supports those checkpoints.
- `./tools/verify-implementation.sh` extensions should fail if evidence lacks explicit references to the north stars.

## Step 5: Review Cadence & Governance
- **Weekly**: Run a `north-star` review swarm (mode `plan`) to assess drift and backlog alignment.
- **Monthly or on major release**:
  - Revalidate Product North Star with leadership; append outcomes to `north-star-history.md`.
  - Archive previous versions under `.cfoi/branches/<branch>/north-star-archive/` if needed.
- **Effort closure**: Update effort north star with final status and lessons learned; mark as archived when effort completes.

## Guardrails
- Never operate without a current Product North Star; halt workflows and request human input if missing.
- Effort north stars must always cite the Product North Star version they derive from.
- All swarm or implement sessions touching scope must log alignment evidence referencing both levels of north star documentation.

## Template Snippets
```markdown
# Product North Star (vYYYY-MM-DD)
- Mission:
- Target Users / Jobs:
- Differentiators:
- Success Metrics:
- Non-Negotiables:
- Approver / Date:
```

```markdown
# Effort North Star (Effort: <name>, vYYYY-MM-DD)
- Goal Statement:
- Ties to Product North Star (section & metric):
- In Scope:
- Out of Scope:
- Acceptance Checkpoints:
- Dependencies / Risks:
- Approver / Date:
```
