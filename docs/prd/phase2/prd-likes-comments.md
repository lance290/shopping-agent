# PRD: Likes & Comments Persistence

## Business Outcome
- **Measurable impact**: Enable collaborative decision-making → higher project completion rate (tied to North Star: persistence reliability)
- **Success criteria**: 100% of likes/comments survive page reload; ≥30% of rows have at least one like within first week
- **Target users**: Buyers and collaborators evaluating options

## Scope
- **In-scope**: 
  - Like state persists to backend on click
  - Like state restored on page reload
  - Comments saved with user attribution
  - Like/comment counts visible on tiles
  - Comments visible to collaborators
- **Out-of-scope**: 
  - Threaded comments / replies
  - Rich text / emoji reactions
  - Real-time collaborative updates (websockets)

## User Flow
### Likes
1. Buyer views tiles in a row
2. Buyer clicks heart/like icon on a tile
3. Like state immediately updates (optimistic UI)
4. Like persists to backend
5. On page reload, like state is restored
6. Collaborators see aggregated like counts

### Comments
1. Buyer clicks comment icon on a tile
2. Comment input appears
3. Buyer types comment and submits
4. Comment saved with user name + timestamp
5. Comment appears below tile or in detail panel
6. Collaborators can view and add their own comments

## Business Requirements

### Authentication & Authorization
- **Who needs access?** Authenticated buyers (owner) and invited collaborators
- **What actions are permitted?** 
  - Owners: like, unlike, comment, delete own comments
  - Collaborators: like, unlike, comment, delete own comments
  - Viewers (share link): view only
- **What data is restricted?** Comments contain user identity; only visible to project members

### Monitoring & Visibility
- **Business metrics**: 
  - % of rows with ≥1 like
  - % of rows with ≥1 comment
  - Average likes per row
  - Comment engagement rate
- **Operational visibility**: API error rates for like/comment endpoints
- **User behavior tracking**: Like/unlike patterns, comment length distribution

### Billing & Entitlements
- **Monetization**: None (core feature)
- **Entitlement rules**: Available to all authenticated users
- **Usage limits**: 
  - Max 1 like per user per bid
  - Max 100 comments per bid (prevent spam)

### Data Requirements
- **What must persist?** 
  - Like: user_id, bid_id, created_at
  - Comment: user_id, bid_id, content, created_at
- **Retention**: Same as bid retention
- **Relationships**: 
  - Like: User → Bid (M:N via likes table)
  - Comment: User → Bid (1:N)

### Performance Expectations
- **Response time**: Like toggle <200ms; Comment submit <500ms
- **Throughput**: Support 100 concurrent users per project
- **Availability**: Same as platform (99.9%)

### UX & Accessibility
- **Standards**: 
  - Heart icon for likes (filled = liked, outline = not liked)
  - Immediate visual feedback on click
  - Comment timestamps in relative format ("2 hours ago")
- **Accessibility**: 
  - Like button has aria-pressed state
  - Comments section has proper heading structure
- **Devices**: Desktop + tablet + mobile

### Privacy, Security & Compliance
- **Regulations**: None specific
- **Data protection**: Comments may contain user-generated text; sanitize for XSS
- **Audit trails**: Log like/comment events for analytics

## Dependencies
- **Upstream**: 
  - User authentication (Clerk) — provides user_id
  - Bid persistence — likes/comments attach to bids
- **Downstream**: 
  - Share Links — collaborators need auth context

## Risks & Mitigations
- **Optimistic UI race condition** → Implement proper retry/rollback on failure
- **Comment spam** → Rate limit + content length limits
- **Stale like state** → Refetch on row focus

## Acceptance Criteria (Business Validation)
- [ ] Like state persists: 100% of likes survive page reload (current: untested, target: 100%)
- [ ] Comment state persists: 100% of comments survive page reload (current: untested, target: 100%)
- [ ] Like toggle latency: ≤200ms p95 (baseline: N/A, standard for optimistic UI)
- [ ] Like/comment counts display correctly on tile (binary: yes/no)
- [ ] Collaborators can see owner's likes and comments (binary: yes/no)
- [ ] User can only delete their own comments (authorization test)

## Traceability
- **Parent PRD**: docs/prd/phase2/PRD.md
- **Product North Star**: .cfoi/branches/dev/product-north-star.md

---
**Note:** Technical implementation decisions (optimistic updates, caching strategy, etc.) are made during /plan and /task phases, not in this PRD.
