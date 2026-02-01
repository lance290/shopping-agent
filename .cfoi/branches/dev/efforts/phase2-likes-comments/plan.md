# Plan: Likes & Comments Persistence

**Effort:** phase2-likes-comments  
**PRD:** docs/prd/phase2/prd-likes-comments.md  
**Created:** 2026-01-31

## Goal
Ensure likes and comments persist across page reloads and are visible to collaborators.

## Constraints
- Like toggle <200ms (optimistic UI)
- Must work with existing backend endpoints
- No real-time sync (polling acceptable for MVP)

## Technical Approach
1. **Backend**: Verify existing /bids/{id}/like and /bids/{id}/comments endpoints
2. **Frontend**: Fix state sync - persist to backend on action, restore on load
3. **UI**: Show like/comment counts on tiles

## Success Criteria
- [ ] Like state persists across reload
- [ ] Comment state persists across reload
- [ ] Collaborators see each other's likes/comments
- [ ] Like toggle <200ms
- [ ] All tests pass

## Dependencies
- User authentication (✅ Clerk)
- Bid persistence (✅ complete)

## Risks
- Race conditions on optimistic updates → proper error handling
- Stale state → refetch on focus
