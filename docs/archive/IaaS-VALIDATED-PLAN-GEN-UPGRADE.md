# IaaS Upgrade: Multi-Model Validated Plan Generator

## Summary

We built a multi-model validation pipeline that generates plans and tasks from PRDs with **3-way alignment checks** against:
1. The PRD itself
2. The Product North Star
3. The existing codebase structure

This replaces/augments manual `/plan` and `/task` workflows with automated generation + validation.

## What IaaS Needs to Do

### Option A: Add as New Workflow
Create a new `/validated-plan-gen` workflow that:
1. Reads a PRD file
2. Calls the pipeline script
3. Outputs validated `plan.md` and `tasks.json`

### Option B: Upgrade Existing `/plan` and `/task` Workflows
Modify existing workflows to:
1. Use low-level model for initial draft generation
2. Pass draft to validator models for alignment checks
3. Loop until validators pass or max iterations reached

## Files to Reference

### Core Script
```
/Volumes/PivotNorth/Shopping Agent/tools/validated-plan-generator.py
```

Key functions:
- `get_codebase_summary()` - Scans repo for models, routes, components
- `generate_draft_plan()` - Initial plan from PRD
- `validate_plan()` - 3-way alignment check
- `generate_draft_tasks()` - Break plan into tasks
- `validate_tasks()` - Check task completeness/ordering
- `refine_with_feedback()` - Incorporate validator feedback

### Workflow Documentation
```
/Volumes/PivotNorth/Shopping Agent/.windsurf/workflows/validated-plan-gen.md
```

### Example Outputs (7 validated efforts)
```
/Volumes/PivotNorth/Shopping Agent/.cfoi/branches/dev/efforts/
├── phase2-tile-provenance-validated/
├── phase2-likes-comments-validated/
├── phase2-share-links-validated/
├── phase2-quote-intake-validated/
├── phase2-wattdata-outreach-validated/
├── phase2-stripe-checkout-validated/
└── phase2-docusign-contracts-validated/
```

### Context Files Used by Pipeline
```
.cfoi/branches/dev/product-north-star.md  # North Star alignment
apps/backend/models.py                     # Codebase models
apps/backend/routes/                       # Route patterns
apps/frontend/components/                  # Component patterns
```

## Pipeline Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    PRD      │────▶│   DRAFT     │────▶│ VALIDATOR 1 │
│             │     │  (Sonnet)   │     │  (Sonnet)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐            │ PASS?
                    │   REFINE    │◀───────────┤
                    │  (Sonnet)   │     NO     │
                    └──────┬──────┘            │
                           │                   ▼ YES
                           │            ┌─────────────┐
                           └───────────▶│ VALIDATOR 2 │
                                        │  (Sonnet)   │
                                        └──────┬──────┘
                                               │
                                               ▼ BOTH PASS?
                                        ┌─────────────┐
                                        │   OUTPUT    │
                                        │ plan.md     │
                                        │ tasks.json  │
                                        └─────────────┘
```

## Validation Prompts

The key innovation is the **3-way alignment check**. Validators receive:

```
## 1. PRD (what to build):
{prd_content}

## 2. North Star (why):
{north_star_content}

## 3. Codebase (how it fits):
- Backend models: {models_list}
- Backend routes: {routes_list}
- Frontend components: {components_list}
- Patterns: FastAPI + SQLAlchemy, Next.js + Zustand, etc.
```

And check for:
- North Star metric advancement
- PRD requirement coverage
- Codebase pattern alignment
- Missing implementation steps
- Dependencies on non-existent code
- Task ordering correctness

## Real Issues Caught by Validators

During our test runs, validators caught:
- Missing database migrations
- Auth patterns not matching Clerk
- Wrong FK relationships
- Missing cascade delete logic
- XSS sanitization gaps
- North Star misalignment (share-links feature)
- Incorrect task dependencies
- Wrong file paths

## Configuration

Model selection in script:
```python
MODELS = {
    "draft": "claude-sonnet-4-20250514",
    "validator_1": "claude-sonnet-4-20250514",
    "validator_2": "claude-sonnet-4-20250514",
}
```

Upgrade `validator_1` to Opus when available for deeper thinking.

## Usage

```bash
# Single PRD
python tools/validated-plan-generator.py --prd path/to/prd.md

# Custom output
python tools/validated-plan-generator.py --prd path/to/prd.md --output path/to/effort

# Parallel (multiple PRDs)
python tools/validated-plan-generator.py --prd prd-a.md &
python tools/validated-plan-generator.py --prd prd-b.md &
wait
```

## Questions for IaaS

1. Do you want this as a standalone workflow or integrated into existing `/plan` + `/task`?
2. Should validators be configurable (different models for different projects)?
3. Do you need streaming output or is batch OK?
4. Should this integrate with claude-flow swarm for parallel validation?
