# Alignment Check - task-001

## North Star Goals Supported
- Product North Star: Reliable multi-provider procurement search with structured intent extraction (ref: .cfoi/branches/dev/efforts/refactor-search-architecture-v2/product-north-star.md)
- Supports DoD signals: intent_extraction_accuracy, provider_adapter_activation baseline scaffolding

## Task Scope Validation
- **In scope**: Define SearchIntent, ProviderQuery, NormalizedResult dataclasses + serialization helpers in `apps/backend/sourcing/models.py`; expose them via package init; add unit tests.
- **Out of scope**: Provider adapter logic, DB persistence, API wiring, aggregator changes.

## Acceptance Criteria
- [ ] Pydantic models/dataclasses cover SearchIntent, ProviderQuery, ProviderQueryMap, NormalizedResult, ProviderStatusSnapshot.
- [ ] `apps/backend/tests/test_sourcing_models.py` instantiates models and validates serialization/deserialization.

## Approved by: Cascade
## Date: 2026-01-30
