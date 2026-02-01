# Plan: Likes & Comments Persistence

## Goal
Implement persistent likes and comments for bids with real-time UI updates and proper data synchronization across page reloads.

## Constraints
- Use existing Like and Comment models and API routes
- Maintain SQLModel patterns with table=True for DB models
- Follow FastAPI + Next.js 14 App Router architecture
- Use Zustand for state management
- Implement optimistic UI updates for likes
- Support authenticated users only (via Clerk + custom sessions)
- No real-time websockets (out of scope)

## Phase 1: Current State Analysis

### 1.1 Existing Backend Assessment
1. **Document Like/Comment model schemas**
   - Review actual fields and relationships in existing models
   - Test existing API routes in `/likes` and `/comments`
   - Verify current error handling and validation patterns
   - Document current response formats and status codes

2. **Authentication Integration Analysis**
   - Map AuthSession.user_id to Like.user_id and Comment.user_id relationships
   - Test `get_current_user` dependency with existing routes
   - Verify current auth error handling patterns

3. **Project Collaboration Current State**
   - Analyze existing Project model collaboration patterns
   - Document current project access control implementation
   - Test existing project membership queries and performance

### 1.2 Frontend Integration Points
1. **Zustand Store Analysis**
   - Review current store.ts structure and patterns
   - Identify existing state management conventions
   - Test current error handling and async patterns

2. **Component Architecture Review**
   - Analyze OfferTile component current props and layout
   - Review Board component state management patterns
   - Document existing drag/drop interaction patterns

## Phase 2: Gap Analysis & Requirements

### 2.1 Backend Gaps Assessment
1. **API Completeness Review**
   - Identify missing endpoints for social data aggregation
   - Check if batch operations are supported
   - Verify collaboration filtering in social queries
   - Document needed performance optimizations

2. **Security & Validation Gaps**
   - Review current input sanitization in comment routes
   - Check existing rate limiting implementation
   - Verify authorization checks for project-based access

### 2.2 Frontend Integration Gaps
1. **Store Integration Requirements**
   - Define social state integration with existing store patterns
   - Identify needed async action patterns
   - Plan optimistic update integration with current error handling

2. **Component Enhancement Needs**
   - Define OfferTile social UI integration requirements
   - Plan Board component overlay management
   - Design mobile-responsive social components

## Phase 3: Backend Implementation

### 3.1 API Route Enhancements
1. **Extend existing routes** based on gap analysis
   ```python
   # Enhance existing /api/likes endpoints
   POST /api/likes/{bid_id} - Ensure toggle functionality + count return
   GET /api/bids/{bid_id}/social - Add aggregated endpoint
   
   # Enhance existing /api/comments endpoints  
   GET /api/comments/{bid_id} - Ensure user attribution included
   POST /api/comments/{bid_id} - Verify sanitization + validation
   ```

2. **Project Access Integration**
   - Integrate existing project collaboration patterns with social queries
   - Add project membership filtering to all social data endpoints
   - Implement collaboration-aware authorization middleware

### 3.2 Performance & Security Enhancements
1. **Database Optimization**
   - Add indexes based on current query patterns analysis
   - Optimize social data aggregation queries
   - Implement batch social data retrieval

2. **Security Hardening**
   - Apply html.escape() to comment content using existing patterns
   - Integrate with existing rate limiting decorators
   - Enhance collaboration-based authorization checks

## Phase 4: Frontend Implementation

### 4.1 Zustand Store Integration
1. **Social State Integration** (following existing store patterns)
   ```typescript
   // Extend existing store.ts patterns
   interface StoreState extends ExistingState {
     bidSocialData: Record<string, BidSocialData>;
     loadBidSocial: (bidId: string) => Promise<void>;
     toggleLike: (bidId: string) => Promise<void>;
     addComment: (bidId: string, content: string) => Promise<void>;
     deleteComment: (commentId: string, bidId: string) => Promise<void>;
   }
   ```

2. **Optimistic Updates with Existing Error Patterns**
   - Integrate with current error handling and notification systems
   - Implement rollback using existing async action patterns
   - Follow current loading state management conventions

### 4.2 Social Components Development
1. **LikeButton Component**
   ```typescript
   interface LikeButtonProps {
     bidId: string;
     initialCount?: number;
     initialLiked?: boolean;
   }
   ```
   - Heart icon with consistent design system
   - Smooth animations following existing UI patterns
   - Accessibility compliance with current standards

2. **CommentPanel Component**
   ```typescript
   interface CommentPanelProps {
     bidId: string;
     isOpen: boolean;
     onClose: () => void;
   }
   ```
   - Mobile-first responsive design
   - Integration with existing overlay patterns
   - User attribution with current avatar/name patterns

### 4.3 Component Integration
1. **OfferTile Enhancement**
   - Extend existing props interface maintaining backward compatibility
   - Add social UI below existing content without layout disruption
   - Integrate with existing loading states and error handling

2. **Board Component Updates**
   - Manage CommentPanel state without interfering with drag/drop
   - Implement overlay management using existing modal patterns
   - Batch social data loading for visible tiles

## Phase 5: Testing & Performance Optimization

### 5.1 Performance Baseline & Improvement
1. **Backend Performance**
   - Establish current query performance baseline
   - Target 50% improvement in social data aggregation
   - Optimize collaboration filtering queries relative to baseline

2. **Frontend Responsiveness**
   - Measure current component render times
   - Target immediate optimistic updates (<100ms visual feedback)
   - Optimize social data loading to match existing component performance

### 5.2 Integration & Collaboration Testing
1. **Multi-user Access Scenarios**
   - Test project collaboration with social data visibility
   - Verify authorization across project boundaries
   - Test project membership changes and social data access

2. **Component Integration Testing**
   - Verify Board drag/drop functionality with social components
   - Test mobile responsive behavior across device sizes
   - Validate accessibility compliance with existing standards

## Success Criteria
- [ ] **Data persistence**: Social data persists across page reloads matching existing data patterns
- [ ] **Performance**: Like toggle optimistic UI matches existing component responsiveness
- [ ] **Performance**: Social queries perform within 50% of current baseline query times  
- [ ] **Security**: Comment XSS protection integrated with existing validation patterns
- [ ] **Security**: Rate limiting follows existing route protection patterns
- [ ] **Collaboration**: Social data respects existing project access controls
- [ ] **Authorization**: Delete permissions follow existing user authorization patterns
- [ ] **Accessibility**: Components meet current accessibility standards
- [ ] **Mobile**: Responsive design matches existing mobile component behavior
- [ ] **Integration**: No interference with existing Board drag/drop functionality
- [ ] **Layout**: OfferTile maintains existing design with seamless social addition

## Dependencies
- **Existing**: Like and Comment models and API routes (verified operational)
- **Existing**: Project collaboration and access control patterns
- **Existing**: Clerk authentication + AuthSession integration
- **Existing**: `get_current_user` dependency and rate limiting decorators
- **Existing**: OfferTile and Board component architecture
- **Existing**: Zustand store patterns and error handling systems

## Risk Mitigation
- **Integration conflicts**: Phase 1 analysis prevents assumptions about existing code
- **Performance regression**: Baseline measurement ensures relative improvement targets
- **State management conflicts**: Following existing store patterns prevents interference
- **Collaboration access bugs**: Integration with existing access control patterns
- **Mobile UX degradation**: Responsive testing against existing mobile components
- **Auth pattern disruption**: Integration with existing AuthSession patterns
- **Optimistic update issues**: Following existing async action and error handling patterns
- **Component layout breaks**: Incremental integration with existing OfferTile design