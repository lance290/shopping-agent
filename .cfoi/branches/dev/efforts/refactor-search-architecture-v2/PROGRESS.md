# Progress Log - refactor-search-architecture-v2

> **Purpose**: Quick context loading for fresh sessions. Read this FIRST.

## Current State
- **Status**: 🏗️ Implementation in Progress
- **Current task**: task-004 (pending)
- **Last working commit**: da22cd6
- **App status**: Green (Baseline verified)

## Quick Start
```bash
# Run this to start development environment
cd apps/backend && uv run uvicorn main:app --reload --port 8000
cd apps/bff && pnpm dev
cd apps/frontend && pnpm dev
```

## Task Summary
| ID | Description | Status |
|----|-------------|--------|
| task-001 | Scaffold sourcing models and dataclasses | ✅ completed |
| task-002 | Implement canonical URL + currency utils | ✅ completed |
| task-003 | Add DB migrations for search_intent/bid metadata | ✅ completed |
| task-004 | BFF intent extraction service (LLM + fallback) | ⬜ pending |
| task-005 | Persist search_intent and provider_query_map | ⬜ pending |
| task-006 | Provider query adapters and taxonomy mapping | ⬜ pending |
| task-007 | Split executors/normalizers with status instrumentation | ⬜ pending |
| task-008 | Result aggregator + canonical bid persistence | ⬜ pending |
| task-009 | Wire provider stats through BFF + minimal frontend | ⬜ pending |
| task-010 | Observability, regression tests, feature flag rollout | ⬜ pending |

## Definition of Done (DoD)
- **Status**: Active (v1)
- **Thresholds**:
  - [ ] search_success_rate ≥ 0.90 (measured)
  - [ ] price_filter_accuracy ≥ 0.95 (measured)
  - [ ] persistence_reliability = 1.0 (measured)
  - [ ] provider_status_reporting = 1.0 (measured)
- **Signals** (weighted):
  - [ ] intent_extraction_accuracy (0.4)
  - [ ] provider_adapter_activation (0.3)
  - [ ] bid_metadata_complete (0.2)
  - [ ] search_latency_p95 ≤ 12s (0.1)
- **Approved by**: Lance on 2026-01-30T04:48:59Z

## Session History

### 2026-01-29 20:23 - Session 1 (Initial Setup)
- Created effort: refactor-search-architecture-v2
- Type: refactor
- Description: implement a more robust and flexible architecture to deal with multiple sellers and search engines
- Next: Run /plan to create implementation plan

### 2026-01-29 21:05 - Session 2 (Planning & Task Breakdown)
- Plan approved by Lance @ 2026-01-30T05:04:20Z
- Decomposed plan into 10 tasks (~425 minutes total)
- Initialized tracking files (metrics.json, proof stubs)
- Next: Run /implement to start task-001

### 2026-01-30 21:45 - Session (Task-009 wiring + FE test setup)
- Completed: FE test setup for jest-dom matchers (Vitest) and fixed ProviderStatusBadge tests
- Completed: Frontend store wiring for provider status snapshots (row-scoped)
- Completed: UI wiring for provider status badges on row header
- Completed: BFF `/api/chat` SSE `search_results` event now includes `provider_statuses` from backend `/rows/:id/search`
- Completed: Frontend `Chat.tsx` SSE handler consumes `provider_statuses` and calls `store.setRowResults(rowId, results, providerStatuses)`
- Runtime ports (local): backend `8000`, frontend `3003`, BFF `8081` (PORT is set in `apps/bff/.env`)
- Note: `metrics.json` was expected by workflow but was not found at repo root during compaction
- Next: Manual verification in UI (search + confirm badges render + partial failure states), then add manual proof for task-009

## How to Use This File

**At session start:**
1. Read "Current State" to understand where we are
2. Check "Last working commit" - if app is broken, revert here
3. Review recent session history for context

**At session end:**
1. Update "Current State" with latest status
2. Add session entry with what was accomplished
3. Note any blockers or next steps

 **⚠️ IMPORTANT**: Keep this file updated!**
