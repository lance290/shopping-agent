# Plan: Tile Detail & Provenance

## Goal
Add click-to-expand tile detail panels that display product information and provenance data to increase buyer confidence and conversion rates from tile clicks to selections.

## Constraints
- Read-only provenance display (no editing)
- Use existing bid.provenance JSONB data only
- Detail panel must load in <300ms
- Must follow existing slide-out panel patterns
- Desktop + tablet support required (mobile nice-to-have)
- WCAG 2.1 AA compliance
- Authentication-aware: collaborators can act, share-link viewers read-only

## Technical Approach

### Database Changes
- **Add provenance field to bid model**:
  ```python
  # Migration: Add provenance JSONB field to bids table
  def upgrade():
      op.add_column('bids', sa.Column('provenance', postgresql.JSONB, nullable=True))
  ```
- **Update `app/models/bid.py`**:
  - Add `provenance = db.Column(db.JSON)` field
  - Include provenance in bid serialization methods

### Backend Changes
- **New API endpoint**: `GET /api/rows/{row_id}/bids/{bid_id}/detail`
  - Uses existing Clerk authentication middleware patterns
  - **Permission logic**: Based on existing auth patterns:
    - Collaborators (row members): can like, select, comment
    - Share-link viewers: read-only access
    - Non-authenticated: no access
  - **Response schema**:
    ```json
    {
      "bid": {
        "id": "string",
        "title": "string", 
        "price": "number",
        "merchant": "string",
        "image_url": "string",
        "provenance": {}
      },
      "permissions": {
        "can_like": "boolean",
        "can_select": "boolean", 
        "can_comment": "boolean"
      }
    }
    ```
  - **Error handling** (matching existing route patterns):
    - 404: Bid not found
    - 403: Row access denied
    - 401: Authentication required
    - 500: Server error
  - 200ms response time target using existing database connections

### Frontend Changes
- **Authentication integration**: 
  - Use existing Clerk auth patterns to check user permissions
  - Disable action buttons for share-link viewers based on API response
- **New components** (following existing slide-out patterns):
  - `components/TileDetailPanel.tsx` - main panel container
  - `components/ProvenanceDisplay.tsx` - shows provenance with structured fallbacks
  - `components/BasicProductInfo.tsx` - displays title, price, merchant, image
- **Enhanced `components/TileCard.tsx`**:
  - Add click handler that calls new detail API endpoint
- **State management**: 
  - Extend existing row state patterns to include `selectedBidDetail` 
  - Use existing state management approach (no new Zustand stores)
- **Responsive design**:
  - Desktop: Full slide-out panel (768px+ width)
  - Tablet: Condensed panel (481-767px width)
  - Mobile: Basic modal overlay (≤480px width)

### Data Flow
1. User clicks tile → fetch `/api/rows/{row_id}/bids/{bid_id}/detail`
2. API returns bid data + user permissions in <200ms
3. Panel opens with fetched data and permission-aware actions
4. `ProvenanceDisplay` renders with fallback logic:
   ```typescript
   const content = provenance?.matches?.length > 0 
     ? renderProvenance(provenance)
     : renderFallback("Matched based on your search criteria and preferences")
   ```
5. User actions (like/select) respect permission flags from API response

### Performance Optimization
- API endpoint uses existing database connections and caching patterns
- Panel pre-loads basic bid data, fetches additional details on demand
- Simple 300ms load time monitoring via client-side timing

## Success Criteria
- [ ] Migration adds `provenance` JSONB field to bids table
- [ ] New `/api/rows/{row_id}/bids/{bid_id}/detail` endpoint using existing Clerk auth
- [ ] Permission logic: collaborators can act, share-link viewers read-only
- [ ] Error responses match existing route patterns (401, 403, 404, 500)
- [ ] Detail panel displays product info (title, price, merchant, image)
- [ ] ProvenanceDisplay shows structured fallback: "Matched based on your search criteria and preferences"
- [ ] Panel loads in <300ms using existing API patterns
- [ ] Like/Select actions respect permission flags from API
- [ ] Panel is keyboard navigable (Tab, Escape to close)
- [ ] Screen reader announces panel content
- [ ] Responsive breakpoints: desktop (768+), tablet (481-767), mobile (≤480)
- [ ] Uses existing row state management patterns

## Dependencies
- **Backend**: Existing Clerk authentication middleware (✅ available)
- **Backend**: Database migration system (✅ available)
- **Frontend**: Current TileCard component and row state (✅ available)
- **Design**: Existing slide-out panel UI patterns (✅ available)

## Risks
- **Database migration**: Test migration on staging data before production deployment
- **API response time**: Mitigated by using existing database connections and simple queries
- **Sparse provenance data**: Clear fallback messaging covers gaps in provenance information
- **Permission edge cases**: Explicit permission flags handle auth variations
- **Mobile UX**: Simplified modal approach reduces complexity while maintaining functionality