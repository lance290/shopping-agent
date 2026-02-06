# Effort North Star (Effort: feature-tile-provenance, v2026-02-06)

## Goal Statement
Populate structured provenance data on every bid created during search so buyers can see "why this result" in the detail panel, increasing confidence and selection rate.

## Ties to Product North Star
- **Product Mission**: "Deliver reliable, transparent, multi-provider procurement search that produces persistable, negotiable offers"
- **Supports Metric**: Persistence reliability (provenance data persists with bid), Search success rate (transparency increases buyer confidence → higher engagement)

## In Scope
- Build provenance data during search normalization/persistence pipeline
- Add `provenance` field to `NormalizedResult` model
- Populate provenance in `_persist_results()` with: product info, matched features, search context
- Improve "Based on your search" fallback when no specific provenance exists
- Ensure keyboard accessibility (Tab navigation between panel sections)
- Add ARIA labels for screen reader support

## Out of Scope
- Editing provenance data
- AI-generated explanations (use extracted data only, per PRD)
- Real-time provenance updates after bid creation
- Analytics/clickout tracking for detail panel opens (can be a follow-up)

## Acceptance Checkpoints
- [ ] New bids created via search have non-null provenance JSON
- [ ] Detail panel renders matched features for ≥80% of bids with provenance
- [ ] Panel loads in ≤300ms from click
- [ ] Panel navigable via keyboard (Tab + Escape)
- [ ] All existing tests pass + new provenance pipeline tests pass

## Dependencies & Risks
- **Dependencies**: Search Architecture v2 (complete), existing Bid/BidWithProvenance models (exist)
- **Risks**: Sparse raw provider data may limit matched features; mitigated by "Based on your search" fallback

## Approver / Date
- Approved by: Lance
- Date: 2026-02-06
