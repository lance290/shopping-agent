# Plan: Share Links

**Effort:** phase2-share-links  
**PRD:** docs/prd/phase2/prd-share-links.md  
**Created:** 2026-01-31

## Goal
Enable buyers to share projects/rows/tiles via URL for viral growth and collaboration.

## Constraints
- Anonymous viewers get read-only access
- Share links don't expire (MVP)
- Track access for viral coefficient measurement

## Technical Approach
1. **Backend**: Create share_links table, POST /share and GET /s/{token} endpoints
2. **Frontend**: "Copy Link" button on project/row/tile, share resolver page
3. **Tracking**: Increment access_count on each view

## Success Criteria
- [ ] Copy Link works for project, row, tile
- [ ] Shared link resolves to correct content
- [ ] Anonymous viewer sees read-only view
- [ ] access_count increments on view
- [ ] All tests pass

## Dependencies
- Project/Row/Bid persistence (✅ complete)
- User authentication for share creation (✅ Clerk)

## Risks
- Unintended data exposure → clear UI warning
- Link abuse → rate limiting (future)
