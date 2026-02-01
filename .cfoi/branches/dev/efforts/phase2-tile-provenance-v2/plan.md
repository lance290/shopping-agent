# Plan: Tile Detail & Provenance

## Goal
Implement a click-to-expand tile detail panel that shows product information and provenance data to increase buyer confidence and conversion rates.

## Constraints
- Read-only provenance display (no editing)
- Use existing bid.provenance JSONB data only
- Panel load time <300ms
- Maintain existing tile design patterns
- WCAG 2.1 AA accessibility compliance
- Desktop + tablet support only (mobile explicitly excluded from MVP)

## Technical Approach

### Backend Changes
- **Enhance existing bid endpoint** in `apps/backend/app/routers/bids.py`:
  - Extend existing `GET /api/bids/{bid_id}` endpoint with optional `?include_provenance=true` parameter
  - Return expanded provenance JSONB data when parameter is present
  - Add error handling for missing/malformed provenance data in existing endpoint logic
- **Extend existing Bid SQLModel** in `apps/backend/app/models/bid.py`:
  - Create `BidWithProvenance(Bid)` SQLModel class that extends base `Bid` model
  - Add computed fields for structured provenance data parsing
  - Include fallback fields for sparse provenance scenarios using SQLModel's `Field` validation
  - Maintain inheritance from existing SQLModel base patterns

### Frontend Changes
- **Extend OfferTile component** in `apps/frontend/components/OfferTile.tsx`:
  - Add click handler to trigger detail panel
  - Maintain existing tile layout and styling
- **Create TileDetailPanel component** in `apps/frontend/components/TileDetailPanel.tsx`:
  - Slide-out panel using TailwindCSS transitions (z-index: 50, consistent with existing modals)
  - Display product info, matched features, chat excerpts
  - Implement focus management following established modal patterns:
    - Use `useRef` to track initial focus element on panel open
    - Move focus to panel heading when opened using `useEffect`
    - Create focus trap using `tabindex` management within panel
    - Restore focus to original tile when panel closes
    - Close panel on `Escape` key press using `useKeyboard` hook pattern
  - Screen reader announcements using `aria-live` regions
  - Wrap component in error boundary for malformed provenance data
- **Add error boundary** in `apps/frontend/components/TileDetailPanelErrorBoundary.tsx`:
  - Follow existing `ErrorBoundary.tsx` component structure
  - Extend base error boundary class with panel-specific fallback UI
  - Log errors to existing error reporting system using established error patterns
- **Create dedicated store slice** in `apps/frontend/stores/detailPanelStore.ts`:
  - Follow existing store pattern from `apps/frontend/stores/` directory structure
  - Create isolated store slice: `selectedBidId: string | null`, `isOpen: boolean`, `bidData: BidWithProvenance | null`, `loading: boolean`, `error: string | null`
  - Add actions: `openPanel(bidId: string)`, `closePanel()`, `fetchBidDetail(bidId: string)`, `setBidData()`, `setLoading()`, `setError()`
  - Use existing async action patterns with promise handling and error catching
- **Update Board component** in `apps/frontend/components/Board.tsx` to handle panel overlay without disrupting grid layout

### Data Flow
1. User clicks tile → detailPanelStore updates `selectedBidId` and sets `isOpen: true`
2. Store dispatches `fetchBidDetail(bidId)` using existing API client patterns
3. Enhanced API endpoint `GET /api/bids/{bid_id}?include_provenance=true` returns `BidWithProvenance`
4. TileDetailPanel renders from `bidData` state with loading/error states
5. Existing like/comment/select actions work within panel context using current action patterns

### Error Handling
- **API errors**: Display "Unable to load details" message with retry button using existing error UI patterns
- **Malformed provenance JSON**: Show basic product info with "Details unavailable" fallback handled by SQLModel validation
- **Missing bid data**: Return 404 from enhanced endpoint, show "Item no longer available" message
- **Network timeouts**: Use existing timeout configuration with retry option
- **Frontend error boundary**: Use TileDetailPanelErrorBoundary following `ErrorBoundary.tsx` patterns

### Responsive Design
- **Desktop (≥1024px)**: Full slide-out panel from right side
- **Tablet (768-1023px)**: Full-screen overlay with close button
- **Mobile (<768px)**: Explicitly not supported - show tooltip "Open on desktop for details"

### Accessibility Implementation
- **Focus management** following existing modal component patterns:
  - Use existing `useFocusManagement` hook if available, or create following established patterns
  - Move focus to panel heading (`role="dialog"`) when panel opens
  - Implement focus trap within panel using established `tabindex` management
  - Return focus to originating tile button when panel closes
- **ARIA attributes**:
  - Panel container: `role="dialog"` `aria-modal="true"` `aria-labelledby="panel-heading"`
  - Loading states: `aria-live="polite"` announcements
  - Error states: `aria-live="assertive"` for critical errors
- **Keyboard navigation**:
  - `Escape` key closes panel using existing keyboard event patterns
  - `Tab`/`Shift+Tab` cycles through interactive elements within panel
  - All clickable elements have visible focus indicators following existing focus styles

### Monitoring & Analytics
- **Add click tracking** to existing audit logging system using established `AuditLog` patterns
- **Instrument panel interactions** using existing analytics event structure
- **Track API performance** for enhanced detail endpoint using existing monitoring
- **Track conversion metrics** (detail view → like/select) with existing conversion tracking
- **Monitor error rates** for malformed provenance data using existing error monitoring

## Success Criteria
- [ ] Tile clicks trigger detail panel in <300ms (including API call)
- [ ] Panel displays product info (title, price, merchant, image, rating)
- [ ] "Why this result" section shows matched features from provenance
- [ ] Chat excerpts display when available
- [ ] Fallback "Based on your search" shown for sparse provenance
- [ ] Error states display gracefully for missing/malformed data
- [ ] Existing like/comment/select actions work within panel
- [ ] Panel closes on outside click, Escape key, or close button
- [ ] Focus moves to panel heading when opened, returns to tile when closed
- [ ] Tab navigation works throughout panel without escaping to background
- [ ] Screen reader announces panel content and state changes correctly
- [ ] Panel works on desktop (full slide-out) and tablet (full-screen overlay)
- [ ] Mobile shows "not supported" tooltip instead of broken panel
- [ ] Click events logged to existing audit system
- [ ] API errors handled with retry mechanisms

## Dependencies
- **Existing**: Search Architecture v2 with bid.provenance data
- **Frontend**: OfferTile, Button, Card components, existing error boundary patterns from `apps/frontend/components/`
- **Backend**: Existing Bid SQLModel from `apps/backend/app/models/bid.py`, existing bids router structure
- **State**: Existing store pattern from `apps/frontend/stores/` directory, established async action patterns
- **Styling**: TailwindCSS transition utilities, responsive breakpoints matching existing modal styles
- **Accessibility**: Existing focus management and keyboard event handling patterns from modal components

## Risks
- **API latency**: Enhanced endpoint adds data processing - mitigate with loading states and 300ms SLA
- **Sparse provenance data**: Mitigate with fallback messaging and graceful degradation using SQLModel validation
- **Panel z-index conflicts**: Use z-index consistent with existing modal hierarchy
- **Large provenance JSON**: Implement server-side truncation with "show more" expansion
- **Accessibility**: Complex panel navigation - follow existing modal patterns and test with screen readers
- **Error handling complexity**: Multiple failure modes require comprehensive error boundary testing with TileDetailPanelErrorBoundary