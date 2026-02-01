# Plan: Tile Detail & Provenance

**Effort:** phase2-tile-provenance  
**PRD:** docs/prd/phase2/prd-tile-provenance.md  
**Created:** 2026-01-31

## Goal
When buyer clicks a tile, show WHY it was recommended with matched choice factors and provenance data.

## Constraints
- Load time <300ms (use cached bid data, no extra API calls)
- WCAG 2.1 AA accessible
- Must work on desktop + tablet

## Technical Approach
1. **Backend**: Add `provenance` field to bid response with matched_features, intent_match_score, price_match
2. **Frontend**: Create slide-out TileDetailPanel component
3. **State**: Track selected tile in Zustand store

## Success Criteria
- [ ] Clicking tile opens detail panel
- [ ] Panel shows "Why recommended" with matched features
- [ ] Panel loads in <300ms
- [ ] Keyboard navigable (Escape closes)
- [ ] All tests pass

## Dependencies
- Search Architecture v2 (✅ complete)
- Bid persistence (✅ complete)

## Risks
- Sparse provenance data → fallback messaging
- Panel blocks main content → proper z-index/overlay
