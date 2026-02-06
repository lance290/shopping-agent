# Decisions Log - feature-tile-provenance

> Track architectural and design decisions.

## Decisions

### D1: Build provenance in generic normalizer only
**Date**: 2026-02-06
**Decision**: Only modify `_normalize_result()` in `normalizers/__init__.py`, not provider-specific normalizers.
**Rationale**: Both `rainforest.py` and `google_cse.py` are pass-throughs to `normalize_generic_results`. No custom logic exists.

### D2: Merge search intent context at persistence time, not normalization time
**Date**: 2026-02-06
**Decision**: Enrich provenance with SearchIntent keywords/features in `_persist_results()`, not during normalization.
**Rationale**: The normalizer doesn't have access to the Row (search_intent, chat_history). The service layer does.

### D3: WattData/service bids excluded from provenance pipeline
**Date**: 2026-02-06
**Decision**: Service provider bids (created in `routes/outreach.py`) are not modified.
**Rationale**: They use VendorContactModal, not TileDetailPanel. Different UX path entirely.
