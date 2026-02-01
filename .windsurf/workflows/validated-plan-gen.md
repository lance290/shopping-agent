---
description: Generate validated plans and tasks from PRDs using multi-model pipeline
---

# Validated Plan Generator

Multi-model pipeline that generates plans and tasks from PRDs with 3-way validation against:
1. **PRD** - What we're building
2. **North Star** - Why we're building it (`.cfoi/branches/dev/product-north-star.md`)
3. **Codebase** - How it fits existing architecture

## Prerequisites

- `ANTHROPIC_API_KEY` set in environment (add to `~/.zshrc` for persistence)
- Python 3.10+ with `anthropic` package installed

## Usage

### Single PRD
```bash
source ~/.zshrc
python tools/validated-plan-generator.py --prd docs/prd/phase2/prd-tile-provenance.md
```

Output goes to `.cfoi/branches/dev/efforts/phase2-{prd-name}-validated/`

### Custom Output Directory
```bash
python tools/validated-plan-generator.py \
  --prd docs/prd/phase2/prd-likes-comments.md \
  --output .cfoi/branches/dev/efforts/my-custom-effort
```

### Multiple PRDs (parallel)
```bash
python tools/validated-plan-generator.py --prd docs/prd/phase2/prd-a.md &
python tools/validated-plan-generator.py --prd docs/prd/phase2/prd-b.md &
wait
```

## Pipeline Stages

### Plan Generation
1. **Draft** (Sonnet) - Generates initial plan from PRD + North Star + codebase summary
2. **Validator 1** (Sonnet) - Checks alignment, finds gaps
3. **Validator 2** (Sonnet) - Independent second opinion
4. **Refine** - Incorporates feedback, loops until both pass or max iterations

### Task Generation
1. **Draft** (Sonnet) - Breaks plan into implementable tasks
2. **Validator 1** - Checks completeness, dependencies, file paths
3. **Validator 2** - Independent validation
4. **Refine** - Fixes issues, loops until both pass

## Output Files

```
.cfoi/branches/dev/efforts/{effort-name}/
├── plan.md      # Validated plan with technical approach
└── tasks.json   # Ordered tasks with acceptance criteria
```

## Validation Checks

The validators check for:
- North Star metric advancement
- PRD requirement coverage
- Codebase pattern alignment
- Missing implementation steps
- Dependencies on non-existent code
- Task ordering correctness
- File path accuracy

## Model Configuration

Edit `tools/validated-plan-generator.py` to change models:

```python
MODELS = {
    "draft": "claude-sonnet-4-20250514",
    "validator_1": "claude-sonnet-4-20250514",  # Upgrade to opus when available
    "validator_2": "claude-sonnet-4-20250514",
}
```

## Troubleshooting

**"Plan did not converge"** - Normal. Validators are strict. Best-effort output is still valuable.

**API errors** - Check `ANTHROPIC_API_KEY` is set: `echo $ANTHROPIC_API_KEY`

**Wrong file paths in tasks** - Codebase summary may be incomplete. Enhance `get_codebase_summary()` function.
