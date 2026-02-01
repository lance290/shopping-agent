# Plan: Likes & Comments Persistence

## Goal
Enable likes and comments on bid/row entries with full persistence across page reloads to support collaborative procurement decisions while maintaining the 100% persistence reliability guarantee.

## Constraints
- Must integrate with existing Clerk authentication
- Follow existing FastAPI + SQLAlchemy backend patterns
- Use Zustand for frontend state management
- Maintain optimistic UI for likes with proper rollback
- No real-time updates (websockets) - polling acceptable for comments
- Comments limited to 1000 characters to prevent abuse

## Technical Approach

### Backend Implementation
1. **Database Models** (`app/models/`)
   - Create `BidLike` model with `user_id`, `bid_id`, `created_at` fields
     - Foreign key to existing `rows` table (confirmed via existing schema)
     - Unique composite constraint on `(user_id, bid_id)`
   - Create `BidComment` model with `user_id`, `bid_id`, `content`, `created_at` fields

2. **Authentication Integration**
   - Use existing Clerk middleware pattern from current authenticated endpoints
   - Extract `user_id` from request context following established pattern in existing API routes
   - Apply existing `@require_auth` decorator to all interaction endpoints

3. **API Routes** (`app/api/`)
   - **Phase 1**: Separate interaction endpoints to avoid impacting core search performance:
     - `POST /api/bids/{bid_id}/likes` and `DELETE /api/bids/{bid_id}/likes`
     - `GET /api/bids/{bid_id}/interactions` (returns likes + comments for single bid)
     - `POST /api/bids/{bid_id}/comments`, `DELETE /api/comments/{comment_id}`
   - **Phase 2**: After performance validation, optionally add interaction counts to search results
   - Batch interaction loading: `POST /api/bids/interactions` (accepts array of bid_ids)

4. **Database Migration**
   - Alembic migration with indexes:
     - Unique composite: `(user_id, bid_id)` on BidLike
     - Query optimization: `bid_id` index on both tables
     - User queries: `user_id` index on BidComment

### Frontend Implementation
1. **State Management Integration**
   - Extend existing Zustand store following current pattern used for search results:
     ```typescript
     interface InteractionState {
       interactions: Record<string, { 
         likes: { count: number; userLiked: boolean }, 
         comments: Comment[] 
       }>;
       loadInteractions: (bidIds: string[]) => Promise<void>;
       toggleLike: (bidId: string) => Promise<void>;
       addComment: (bidId: string, content: string) => Promise<void>;
     }
     ```
   - Use same persistence mechanism as search results (localStorage + hydration)
   - Implement simple optimistic updates: immediate UI update + revert on failure (no complex operation tracking)

2. **API Integration** (`lib/api/`)
   - Follow existing API client patterns from search implementation
   - Batch load interactions after search results load to avoid blocking core functionality
   - Simple retry logic matching existing error handling patterns

3. **UI Components** (`components/`)
   - `BidLikeButton`: Follow existing button component patterns
   - `BidCommentSection`: Match existing form and list component styles
   - Integrate seamlessly with current `BidRow` component structure

### Persistence Integration Strategy
1. **Phased Loading**:
   - Primary: Load search results using existing flow (maintains current performance)
   - Secondary: Batch load interaction data for visible bids
   - Store both datasets in Zustand with existing persistence pattern

2. **Performance Safeguards**:
   - Benchmark current search endpoint performance (establish baseline)
   - Load interactions separately to prevent search latency impact
   - Implement timeout fallbacks (interactions load or search continues)

3. **State Reliability**:
   - Mirror existing search result persistence pattern for interactions
   - Graceful degradation: show search results even if interaction loading fails
   - Simple optimistic updates that revert cleanly on failure

## Success Criteria
- [ ] **Performance Maintained**: Core search performance unchanged (baseline + 5% tolerance)
- [ ] **100% Persistence Reliability**: Interactions persist across reloads using existing mechanism
- [ ] **Authentication**: Proper user context using established Clerk integration
- [ ] **Simple Optimistic Updates**: Like button responds immediately with clean failure recovery
- [ ] **Integration**: Works within existing component and state management patterns

## Implementation Plan
### Phase 1: Foundation (Week 1)
1. Create database models and migration
2. Implement authentication-enabled API endpoints
3. Add interaction state to existing Zustand store
4. Basic like/comment UI components

### Phase 2: Integration (Week 2)
1. Integrate components with existing BidRow
2. Implement batch interaction loading
3. Add persistence using existing localStorage pattern
4. Performance testing and optimization

### Phase 3: Polish (Week 3)
1. Error handling and loading states
2. Comment management (edit/delete)
3. Interaction count display optimization
4. Final testing and performance validation

## Risk Mitigation
1. **Performance Impact**: Separate interaction loading prevents search slowdown
2. **Persistence Reliability**: Reuse proven localStorage + Zustand pattern
3. **State Complexity**: Simple optimistic updates match existing patterns
4. **Authentication**: Use established Clerk middleware from current endpoints
5. **Rollback Strategy**: Phase 1 implementation allows easy reversal if issues arise