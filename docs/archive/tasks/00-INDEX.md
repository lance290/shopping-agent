# BuyAnything.ai Implementation Tasks

**Created:** 2026-01-18  
**PRD Reference:** `docs/PRD-buyanything.md`  
**Status:** Implementation Complete

---

## Execution Order

| # | Task | Priority | Est. Days | Depends On | Outcome |
|---|------|----------|-----------|------------|---------|
| 01 | [Frontend Layout Redesign](./01-frontend-layout-redesign.md) | **P0** | 2 | — | Deployable UX for user feedback |
| 02 | [Clickout + Tracking](./02-clickout-tracking.md) | **P0** | 2 | 01 | Every click logged, redirect works |
| 03 | [Affiliate Handler Registry](./03-affiliate-handler-registry.md) | **P0** | 2 | 02 | Pluggable affiliate URL transformation |
| 04 | [Parallel Sourcing + Normalization](./04-parallel-sourcing.md) | P1 | 1 | — | Faster search, unified Offer model |
| 05 | [Choice Factors + RFP](./05-choice-factors-rfp.md) | P1 | 2 | 01, 04 | LLM-driven requirements gathering |
| 06 | [Production Hardening + Audit](./06-production-hardening.md) | **P0** | 3 | 01-05 | Money-safe, auditable, compliant |

**Total estimated:** 12 days (can parallelize some)

---

## Phase 1: UX Feedback (Tasks 01)
Get a deployable frontend in front of users ASAP to validate the chat+tiles paradigm.

## Phase 2: Monetization (Tasks 02-03)
Enable affiliate revenue. Without this, we can't sustain operations.

## Phase 3: Quality (Tasks 04-05)
Improve speed and UX with parallel sourcing and structured RFPs.

## Phase 4: Production (Task 06)
Harden for handling real money: audit logging, error handling, compliance.

---

## Validation Checkpoints

Each task has:
- **Acceptance Criteria** (what "done" looks like)
- **Test Requirements** (unit, integration, E2E)
- **Rollback Plan** (if something breaks)
- **Audit Considerations** (for money-handling compliance)

---

## How to Use This

1. Work through tasks in order (dependencies are explicit)
2. Each task file has step-by-step implementation details
3. Check off items as completed
4. Update status in this index when task is done

---

## Current Status

| Task | Status | Notes |
|------|--------|-------|
| 01 | ✅ Done | Frontend layout redesign complete, tests passing |
| 02 | ✅ Done | Clickout tracking, redirects, and admin endpoint live |
| 03 | ✅ Done | Handler registry, Amazon/eBay handlers, docs created |
| 04 | ✅ Done | Parallel sourcing, deduplication, match scoring, metrics |
| 05 | ✅ Done | Choice factors schema, LLM tools, and UI panel implemented |
| 06 | ✅ Done | Audit logging, rate limiting, admin controls, FTC disclosure |
