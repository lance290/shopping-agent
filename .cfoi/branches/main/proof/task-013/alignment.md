# Alignment Check - task-013

## North Star Goals Supported
- **Goal Statement**: "Multi-category procurement via structured RFPs + project workspace..."
- **Support**: This task implements the "Project Workspace" primitive, allowing users to organize multiple related procurement rows (e.g., "Trip to Japan" -> "Flights", "Hotels") under a single parent entity.

## Task Scope Validation
- **In scope**:
  - Backend: New `Project` entity and `Row.project_id` relationship.
  - Backend: CRUD endpoints for Projects.
  - Frontend: UI to create projects.
  - Frontend: UI to group rows under projects visually.
- **Out of scope**:
  - Complex drag-and-drop reordering (unless easy).
  - Project-level budgets or aggregate stats (future).
  - Sharing entire projects (Task 004 covers sharing, but we'll focus on structure first).

## Acceptance Criteria
- [ ] User can click "New Project" to create a named group.
- [ ] User can add a new row specifically *under* a project.
- [ ] Project grouping persists after page refresh (DB persistence).
- [ ] Ungrouped rows still appear at the top level.
- [ ] Deleting a project handles child rows (archive or ungroup? Default: archive/delete children for now, or warn).

## Approved by: Cascade
## Date: 2026-01-23
