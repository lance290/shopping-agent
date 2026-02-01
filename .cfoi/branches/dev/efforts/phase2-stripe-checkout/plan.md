# Plan: Stripe Checkout (Retail Closing)

## Goal
Implement affiliate link-based retail purchases within our multi-provider procurement search platform, enabling users to purchase directly from retail providers through tracked affiliate links with purchase completion tracking and revenue attribution.

## Constraints
- Affiliate link-based: redirect to external retail sites for checkout
- Track clickouts with affiliate attribution and revenue measurement
- Must work within existing search result streaming (SSE) patterns
- Row owners only can access purchase functionality (collaborators view-only)
- Must integrate with existing Clerk authentication and clickout tracking
- Leverage existing clickout infrastructure in `backend/app/api/routes/clickout.py`

## Technical Approach

### Backend Changes

#### 1. Database Schema (Alembic Migration)
```sql
-- Extend existing clickout events with affiliate tracking
ALTER TABLE clickout_events ADD COLUMN affiliate_id TEXT;
ALTER TABLE clickout_events ADD COLUMN affiliate_revenue_cents INTEGER;
ALTER TABLE clickout_events ADD COLUMN affiliate_currency TEXT DEFAULT 'usd';
ALTER TABLE clickout_events ADD COLUMN purchase_completed_at TIMESTAMP WITH TIME ZONE;

-- Track successful procurement completions linked to clickouts
CREATE TABLE procurement_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bid_id UUID NOT NULL REFERENCES bids(id),
    clickout_event_id UUID REFERENCES clickout_events(id),
    user_id TEXT NOT NULL, -- Clerk user ID
    reported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completion_source TEXT -- 'user_reported', 'affiliate_webhook', etc.
);

-- Index for efficient affiliate lookups
CREATE INDEX idx_clickout_events_affiliate ON clickout_events(affiliate_id);
```

#### 2. Affiliate Link Service
**Extend existing clickout service `backend/app/services/clickout_service.py`:**
```python
class ClickoutService:
    # existing methods...
    def generate_affiliate_url(self, bid_id: str, user_id: str) -> str
    def track_affiliate_clickout(self, bid_id: str, user_id: str, affiliate_id: str) -> str
    def record_purchase_completion(self, clickout_id: str, revenue_cents: int) -> None
```

#### 3. SQLAlchemy Models
**Extend existing `ClickoutEvent` model in `backend/app/models/clickout.py`:**
- Add `affiliate_id`, `affiliate_revenue_cents`, `affiliate_currency`, `purchase_completed_at` fields
**New `ProcurementCompletion` model in `backend/app/models/clickout.py`**

#### 4. API Routes
**Extend existing `backend/app/api/routes/clickout.py`:**
- Modify `POST /api/clickout` to handle affiliate attribution
- Add `POST /api/clickout/completion` - User-reported successful procurement
- Add `POST /api/clickout/affiliate-webhook` - Handle affiliate completion callbacks
- Add `GET /api/clickout/status/{bid_id}` - Check purchase completion status for bid

#### 5. Update Search Results
**Modify `backend/app/api/routes/rows_search.py`:**
- Add retail purchase availability metadata to SSE bid data
- Include affiliate link eligibility flags based on Clerk permissions
- Add pricing information and affiliate attribution data for retail items

### Frontend Changes

#### 1. Components
**New purchase components:**
- `BuyNowButton.tsx` - Affiliate link button that triggers existing clickout flow
- `PurchaseStatusIndicator.tsx` - Show completed purchase status
- `CompletionReportModal.tsx` - User completion reporting interface

**Update existing components:**
- Extend `TileComponent.tsx` to show "Buy Now" buttons for retail items with affiliate links
- Enhance existing clickout tracking with affiliate attribution
- Add purchase completion status to search result tiles

#### 2. State Management
**Extend existing search store:**
```typescript
interface SearchStore {
  // existing search state...
  completions: Set<string>; // bid IDs with completed purchases
  initiateAffiliatePurchase: (bidId: string) -> Promise<void>;
  checkCompletionStatus: (bidId: string) -> Promise<CompletionStatus>;
  reportCompletion: (bidId: string) -> Promise<void>;
}
```

#### 3. Search Results Integration
- Enhance existing tile rendering with "Buy Now" affiliate link buttons
- Integrate completion status with current SSE result streaming
- Maintain existing search state management and clickout patterns
- Build on existing `useClickout` hook for affiliate tracking

#### 4. API Integration
**Extend existing API client in `frontend/src/lib/api/clickout.ts`:**
- Affiliate clickout creation with attribution parameters
- Purchase completion status checking
- Completion reporting functionality

### Integration Points

#### 1. Existing Clickout System
- Build on existing `POST /api/clickout` endpoint with affiliate parameters
- Leverage current clickout tracking patterns and database schema
- Maintain existing clickout analytics and attribution flow
- Extend existing `ClickoutEvent` model rather than creating new purchase tables

#### 2. Clerk Authentication
- Use existing `useUser()` hook for user identification in affiliate tracking
- Leverage existing row ownership permissions for purchase access control
- Maintain current authentication flow without modification

#### 3. Server-Sent Events (SSE)
- Extend existing search result streaming to include retail purchase metadata
- No changes to SSE connection pattern or data flow
- Purchase status updates operate within existing real-time updates

#### 4. Affiliate Integration
- Partner with retail providers for affiliate program enrollment
- Implement affiliate link generation with proper attribution tracking
- Set up webhook endpoints for affiliate purchase completion notifications

#### 5. Analytics Enhancement
- Track procurement funnel: search → result view → affiliate clickout → completion
- Monitor affiliate conversion rates and revenue attribution
- Integrate with existing clickout analytics infrastructure

## Success Criteria
- [ ] "Buy Now" buttons appear on retail search results for authenticated row owners
- [ ] Affiliate links are generated with proper attribution tracking
- [ ] Clickout events are created with affiliate_id and revenue tracking fields
- [ ] Users are redirected to retail partner sites for external checkout
- [ ] ≥80% of affiliate clickouts result in successful external site loads
- [ ] Purchase completion can be reported by users through interface
- [ ] Affiliate webhook integration updates completion status automatically
- [ ] Completed purchases show status indicators in search results
- [ ] Mobile affiliate links work correctly on iOS Safari and Android Chrome
- [ ] Non-row-owners cannot access purchase functionality
- [ ] Purchase analytics integrate with existing clickout analytics dashboard
- [ ] SSE search results include retail purchase metadata without performance impact

## Dependencies
- Affiliate program partnerships with retail providers
- Existing SSE search infrastructure (`rows_search.py`)
- Current Clerk authentication and row permissions system
- Existing clickout tracking system (`clickout.py`)
- Current tile rendering and search result components
- Retail vendor affiliate program APIs and webhook systems
- Existing search state management and analytics patterns

## Risks
- **Affiliate partner reliability**: Implement fallback direct links when affiliate programs fail
- **Attribution tracking accuracy**: Ensure affiliate parameters persist through external redirects
- **Webhook delivery failures**: Implement backup user-reported completion tracking
- **External site performance**: Handle slow-loading or broken retail partner sites
- **Mobile redirect experience**: Test affiliate link behavior on target mobile browsers
- **Permission boundary enforcement**: Verify row ownership checks work with existing Clerk integration
- **Revenue tracking accuracy**: Validate affiliate commission data and handle reporting delays
- **State management complexity**: Avoid conflicts with existing search and clickout patterns
- **Affiliate program changes**: Handle partner program modifications and link format updates