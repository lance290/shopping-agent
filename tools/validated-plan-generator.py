#!/usr/bin/env python3
"""
Multi-Model Validated Plan & Task Generator

Pipeline:
1. Low-level model (Haiku) generates draft plan from PRD
2. High-level model (Opus) validates against PRD + North Star + Codebase
3. Second high-level model (Sonnet) does independent validation
4. Loop until both pass
5. Repeat for tasks generation

Usage:
    python tools/validated-plan-generator.py --prd docs/prd/phase2/prd-tile-provenance.md
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Tuple, Optional
import anthropic

# Model configuration
MODELS = {
    "draft": "claude-sonnet-4-20250514",       # Fast drafts (Haiku deprecated)
    "validator_1": "claude-sonnet-4-20250514", # Deep thinking validation
    "validator_2": "claude-sonnet-4-20250514", # Independent second opinion
}
# Note: When Opus 4 is available, upgrade validator_1 to opus for deeper thinking

# Could upgrade validator_1 to opus when available:
# "validator_1": "claude-opus-4-20250514",

def load_file(path: str) -> str:
    """Load file contents."""
    with open(path, 'r') as f:
        return f.read()

def get_codebase_summary(repo_root: Path) -> dict:
    """Generate comprehensive summary of existing codebase structure."""
    summary = {
        "backend_models": [],
        "backend_routes": [],
        "frontend_components": [],
        "frontend_pages": [],
        "api_endpoints": [],
        "patterns": [],
        "existing_features": []
    }
    
    # Backend models - look for SQLModel classes
    models_path = repo_root / "apps/backend/models.py"
    if models_path.exists():
        content = load_file(str(models_path))
        for line in content.split('\n'):
            # Match: class Name(SQLModel, table=True) or class Name(SomeBase, table=True)
            if line.startswith('class ') and 'table=True' in line:
                class_name = line.split('(')[0].replace('class ', '').strip()
                summary["backend_models"].append(class_name)
            # Also match base classes like RowBase, ProjectBase
            elif line.startswith('class ') and 'Base' in line.split('(')[0]:
                class_name = line.split('(')[0].replace('class ', '').strip()
                summary["backend_models"].append(f"{class_name} (base)")
    
    # Backend routes
    routes_dir = repo_root / "apps/backend/routes"
    if routes_dir.exists():
        for f in routes_dir.glob("*.py"):
            if f.name != "__init__.py":
                summary["backend_routes"].append(f.stem)
                # Try to extract endpoint patterns
                try:
                    route_content = load_file(str(f))
                    for line in route_content.split('\n'):
                        if '@router.' in line or '@app.' in line:
                            # Extract HTTP method and path
                            if 'get(' in line.lower() or 'post(' in line.lower() or 'put(' in line.lower() or 'delete(' in line.lower():
                                summary["api_endpoints"].append(f"{f.stem}: {line.strip()[:80]}")
                except:
                    pass
    
    # Frontend components - check multiple locations
    component_dirs = [
        repo_root / "apps/frontend/components",
        repo_root / "apps/frontend/components/ui",
        repo_root / "apps/frontend/app/components",
    ]
    for comp_dir in component_dirs:
        if comp_dir.exists():
            for f in comp_dir.glob("*.tsx"):
                if not f.name.endswith('.test.tsx'):
                    summary["frontend_components"].append(f.stem)
    
    # Frontend pages (Next.js App Router)
    app_dir = repo_root / "apps/frontend/app"
    if app_dir.exists():
        for f in app_dir.rglob("page.tsx"):
            # Get relative path from app dir
            rel_path = str(f.relative_to(app_dir).parent)
            if rel_path == '.':
                summary["frontend_pages"].append("/")
            else:
                summary["frontend_pages"].append(f"/{rel_path}")
    
    # Check for existing features by scanning for key patterns
    feature_indicators = {
        "Like": "likes functionality",
        "Comment": "comments functionality", 
        "ClickoutEvent": "clickout/affiliate tracking",
        "AuditLog": "audit logging",
        "AuthSession": "session-based auth",
        "Clerk": "Clerk auth integration",
    }
    if models_path.exists():
        content = load_file(str(models_path))
        for indicator, feature in feature_indicators.items():
            if indicator in content:
                summary["existing_features"].append(feature)
    
    # Document patterns
    summary["patterns"] = [
        "Backend: FastAPI + SQLModel (not SQLAlchemy) + Alembic migrations",
        "Frontend: Next.js 14 App Router + Zustand state + TailwindCSS",
        "API: REST with streaming SSE for search results",
        "Auth: Clerk for user management + custom session tokens",
        "Testing: pytest (backend), vitest (frontend)",
        "Models: SQLModel with table=True for DB tables",
        "State: Zustand stores in apps/frontend/app/store.ts"
    ]
    
    return summary

def call_model(client: anthropic.Anthropic, model: str, system: str, user: str, max_tokens: int = 4096) -> str:
    """Call Anthropic API."""
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}]
    )
    return response.content[0].text

def generate_draft_plan(client: anthropic.Anthropic, prd: str, north_star: str, codebase: dict) -> str:
    """Generate initial plan draft using fast model."""
    system = """You are a technical planner. Generate a plan.md file from a PRD.
The plan should be actionable, specific, and fit the existing codebase patterns."""
    
    user = f"""Generate a plan.md for this PRD.

## PRD:
{prd}

## North Star (business context):
{north_star}

## Existing Codebase:
- Backend models: {', '.join(codebase['backend_models'])}
- Backend routes: {', '.join(codebase['backend_routes'])}
- Frontend components: {', '.join(codebase['frontend_components'])}
- Frontend pages: {', '.join(codebase.get('frontend_pages', []))}
- Existing features: {', '.join(codebase.get('existing_features', []))}
- Patterns: {'; '.join(codebase['patterns'])}

Output ONLY the plan.md content in markdown format. Include:
- Goal (1 sentence)
- Constraints
- Technical Approach (specific to this codebase)
- Success Criteria (checkboxes)
- Dependencies
- Risks"""

    print(f"  → Generating draft plan with {MODELS['draft']}...")
    return call_model(client, MODELS['draft'], system, user)

def validate_plan(client: anthropic.Anthropic, model: str, model_name: str,
                  draft: str, prd: str, north_star: str, codebase: dict) -> Tuple[bool, str]:
    """Validate plan against PRD, North Star, and codebase."""
    system = """You are a senior technical reviewer validating plans for alignment and completeness.
Be thorough but constructive. Your job is to catch issues before implementation."""

    user = f"""Review this draft plan for 3-way alignment.

## DRAFT PLAN TO REVIEW:
{draft}

## 1. PRD (what to build):
{prd}

## 2. North Star (why - business metrics):
{north_star}

## 3. Codebase (how it fits):
- Backend models: {', '.join(codebase['backend_models'])}
- Backend routes: {', '.join(codebase['backend_routes'])}
- Frontend components: {', '.join(codebase['frontend_components'])}
- Frontend pages: {', '.join(codebase.get('frontend_pages', []))}
- Existing features: {', '.join(codebase.get('existing_features', []))}
- Patterns: {'; '.join(codebase['patterns'])}

## CHECK FOR:
1. Does this advance North Star metrics?
2. Does this fulfill ALL PRD requirements?
3. Does this fit existing code patterns (no invented abstractions)?
4. Are there missing steps given current architecture?
5. Are there dependencies on code that doesn't exist yet?
6. Is the technical approach realistic?

## RESPOND WITH EXACTLY ONE OF:
PASS: <confidence 0-100>% - <brief reason>

OR

FEEDBACK:
- Issue 1: <specific problem>
- Issue 2: <specific problem>
- Suggested fix: <how to improve>"""

    print(f"  → Validating with {model_name} ({model})...")
    response = call_model(client, model, system, user)
    
    if response.strip().startswith("PASS"):
        return True, response
    else:
        return False, response

def generate_draft_tasks(client: anthropic.Anthropic, plan: str, prd: str, codebase: dict) -> str:
    """Generate tasks.json from validated plan."""
    system = """You are a task decomposer. Break down a plan into specific, implementable tasks.
Each task should be completable in 1-4 hours by a developer familiar with the codebase."""

    user = f"""Generate tasks.json from this validated plan.

## PLAN:
{plan}

## PRD (for acceptance criteria):
{prd}

## Codebase context:
- Backend models: {', '.join(codebase['backend_models'])}
- Backend routes: {', '.join(codebase['backend_routes'])}
- Frontend components: {', '.join(codebase['frontend_components'])}
- Frontend pages: {', '.join(codebase.get('frontend_pages', []))}
- Existing features: {', '.join(codebase.get('existing_features', []))}

Output ONLY valid JSON in this format:
{{
  "tasks": [
    {{
      "id": "task-001",
      "title": "Short title",
      "description": "What to do",
      "status": "pending",
      "files": ["path/to/file.py"],
      "acceptance_criteria": ["Criterion 1", "Criterion 2"]
    }}
  ]
}}

Make tasks specific to actual files in this codebase. Order by dependency."""

    print(f"  → Generating draft tasks with {MODELS['draft']}...")
    response = call_model(client, MODELS['draft'], system, user, max_tokens=8192)
    
    # Extract JSON from response
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0]
    elif "```" in response:
        response = response.split("```")[1].split("```")[0]
    
    return response.strip()

def validate_tasks(client: anthropic.Anthropic, model: str, model_name: str,
                   tasks: str, plan: str, prd: str, codebase: dict) -> Tuple[bool, str]:
    """Validate tasks against plan and codebase."""
    system = """You are a senior technical reviewer validating task breakdowns.
Ensure tasks are complete, ordered correctly, and reference real code paths."""

    user = f"""Review these tasks for completeness and correctness.

## TASKS TO REVIEW:
{tasks}

## PLAN (tasks should implement this):
{plan}

## PRD (for acceptance criteria):
{prd}

## Codebase:
- Backend models: {', '.join(codebase['backend_models'])}
- Backend routes: {', '.join(codebase['backend_routes'])}  
- Frontend components: {', '.join(codebase['frontend_components'])}
- Frontend pages: {', '.join(codebase.get('frontend_pages', []))}
- Existing features: {', '.join(codebase.get('existing_features', []))}
- Patterns: {'; '.join(codebase['patterns'])}

## CHECK FOR:
1. Do tasks cover ALL plan items?
2. Are tasks in correct dependency order?
3. Do file paths reference real or reasonable new files?
4. Are acceptance criteria testable?
5. Are tasks appropriately sized (1-4 hours each)?
6. Any missing tasks for the PRD requirements?

## RESPOND WITH EXACTLY ONE OF:
PASS: <confidence 0-100>% - <brief reason>

OR

FEEDBACK:
- Issue 1: <specific problem>
- Issue 2: <specific problem>
- Suggested fix: <how to improve>"""

    print(f"  → Validating tasks with {model_name} ({model})...")
    response = call_model(client, model, system, user)
    
    if response.strip().startswith("PASS"):
        return True, response
    else:
        return False, response

def refine_with_feedback(client: anthropic.Anthropic, draft: str, feedback: str, artifact_type: str) -> str:
    """Refine draft based on validator feedback."""
    system = f"You are refining a {artifact_type} based on reviewer feedback. Make targeted improvements."
    
    user = f"""Improve this {artifact_type} based on the feedback.

## CURRENT DRAFT:
{draft}

## FEEDBACK:
{feedback}

Output ONLY the improved {artifact_type}, nothing else."""

    print(f"  → Refining {artifact_type} based on feedback...")
    return call_model(client, MODELS['draft'], system, user, max_tokens=8192)

def run_pipeline(prd_path: str, output_dir: str, max_iterations: int = 3):
    """Run the full validation pipeline."""
    
    # Initialize client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Determine paths
    repo_root = Path(__file__).parent.parent
    prd_path = Path(prd_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load context
    print("\n📚 Loading context...")
    prd = load_file(str(prd_path))
    
    north_star_path = repo_root / ".cfoi/branches/dev/product-north-star.md"
    north_star = load_file(str(north_star_path)) if north_star_path.exists() else "No north star defined"
    
    codebase = get_codebase_summary(repo_root)
    print(f"  → Found {len(codebase['backend_models'])} models, {len(codebase['backend_routes'])} routes, {len(codebase['frontend_components'])} components, {len(codebase.get('frontend_pages', []))} pages")
    print(f"  → Existing features: {', '.join(codebase.get('existing_features', [])) or 'none detected'}")
    
    # === PLAN GENERATION ===
    print("\n" + "="*60)
    print("📋 PLAN GENERATION PIPELINE")
    print("="*60)
    
    # Generate draft
    draft_plan = generate_draft_plan(client, prd, north_star, codebase)
    
    # Validation loop
    for i in range(max_iterations):
        print(f"\n--- Validation Round {i+1}/{max_iterations} ---")
        
        # Validator 1
        pass1, feedback1 = validate_plan(client, MODELS['validator_1'], "Validator 1", 
                                          draft_plan, prd, north_star, codebase)
        print(f"  Validator 1: {'✅ PASS' if pass1 else '❌ FEEDBACK'}")
        if not pass1:
            print(f"    {feedback1[:200]}...")
        
        if not pass1:
            draft_plan = refine_with_feedback(client, draft_plan, feedback1, "plan")
            continue
        
        # Validator 2 (independent)
        pass2, feedback2 = validate_plan(client, MODELS['validator_2'], "Validator 2",
                                          draft_plan, prd, north_star, codebase)
        print(f"  Validator 2: {'✅ PASS' if pass2 else '❌ FEEDBACK'}")
        if not pass2:
            print(f"    {feedback2[:200]}...")
        
        if pass1 and pass2:
            print("\n✅ Plan validated by both reviewers!")
            break
        else:
            draft_plan = refine_with_feedback(client, draft_plan, feedback2, "plan")
    else:
        print(f"\n⚠️  Plan did not converge after {max_iterations} iterations. Using best effort.")
    
    # Save plan
    plan_path = output_path / "plan.md"
    with open(plan_path, 'w') as f:
        f.write(draft_plan)
    print(f"\n💾 Saved: {plan_path}")
    
    # === TASK GENERATION ===
    print("\n" + "="*60)
    print("📝 TASK GENERATION PIPELINE")
    print("="*60)
    
    # Generate draft tasks
    draft_tasks = generate_draft_tasks(client, draft_plan, prd, codebase)
    
    # Validation loop
    for i in range(max_iterations):
        print(f"\n--- Validation Round {i+1}/{max_iterations} ---")
        
        # Validator 1
        pass1, feedback1 = validate_tasks(client, MODELS['validator_1'], "Validator 1",
                                           draft_tasks, draft_plan, prd, codebase)
        print(f"  Validator 1: {'✅ PASS' if pass1 else '❌ FEEDBACK'}")
        if not pass1:
            print(f"    {feedback1[:200]}...")
        
        if not pass1:
            draft_tasks = refine_with_feedback(client, draft_tasks, feedback1, "tasks")
            continue
        
        # Validator 2
        pass2, feedback2 = validate_tasks(client, MODELS['validator_2'], "Validator 2",
                                           draft_tasks, draft_plan, prd, codebase)
        print(f"  Validator 2: {'✅ PASS' if pass2 else '❌ FEEDBACK'}")
        if not pass2:
            print(f"    {feedback2[:200]}...")
        
        if pass1 and pass2:
            print("\n✅ Tasks validated by both reviewers!")
            break
        else:
            draft_tasks = refine_with_feedback(client, draft_tasks, feedback2, "tasks")
    else:
        print(f"\n⚠️  Tasks did not converge after {max_iterations} iterations. Using best effort.")
    
    # Save tasks
    tasks_path = output_path / "tasks.json"
    with open(tasks_path, 'w') as f:
        # Ensure valid JSON
        try:
            parsed = json.loads(draft_tasks)
            json.dump(parsed, f, indent=2)
        except json.JSONDecodeError:
            f.write(draft_tasks)
    print(f"💾 Saved: {tasks_path}")
    
    print("\n" + "="*60)
    print("🎉 PIPELINE COMPLETE")
    print("="*60)
    print(f"  Plan: {plan_path}")
    print(f"  Tasks: {tasks_path}")
    print("\nReady for implementation!")

def main():
    parser = argparse.ArgumentParser(description="Multi-model validated plan & task generator")
    parser.add_argument("--prd", required=True, help="Path to PRD file")
    parser.add_argument("--output", default=None, help="Output directory (default: effort dir)")
    parser.add_argument("--max-iterations", type=int, default=3, help="Max validation iterations")
    
    args = parser.parse_args()
    
    # Default output to effort directory based on PRD name
    if args.output is None:
        prd_name = Path(args.prd).stem.replace("prd-", "")
        args.output = f".cfoi/branches/dev/efforts/phase2-{prd_name}"
    
    run_pipeline(args.prd, args.output, args.max_iterations)

if __name__ == "__main__":
    main()
