# Alignment Check - task-006

## North Star Goals Supported
- Effort North Star: provider query adapters and taxonomy mapping to enable multi-provider reliability and auditability.
- Metrics: provider_adapter_activation (0.3 weight), persistence reliability (100%).

## Task Scope Validation
- In scope: build provider query adapters (rainforest, google_cse) and taxonomy mapping utilities.
- Out of scope: executor/normalizer changes and result aggregation (task-007+).

## Acceptance Criteria
- [ ] Provider adapters generate per-provider query payloads from SearchIntent.
- [ ] Provider query map persists adapter outputs for configured providers.
- [ ] Unit test validates adapter outputs.

## Approved by: Cascade
## Date: 2026-01-30
