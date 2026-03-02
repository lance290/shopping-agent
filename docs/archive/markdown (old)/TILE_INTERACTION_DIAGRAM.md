# Tile Interaction System - Visual Architecture Diagrams

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                        RowStrip                               │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │  │
│  │  │ Request   │  │ OfferTile │  │ OfferTile │  │ OfferTile │ │  │
│  │  │   Tile    │  │           │  │ SELECTED  │  │           │ │  │
│  │  │           │  │ ♥ 15  💬 8│  │ ♥ 23  💬 3│  │ ♥ 7   💬 2│ │  │
│  │  │           │  │ [Select]  │  │ CHOSEN    │  │ [Select]  │ │  │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘ │  │
│  │                        ↓ sort by engagement                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────┐         ┌──────────────────────────────────┐ │
│  │ CommentPanel     │         │ SharePopover                      │ │
│  │ ┌──────────────┐ │         │ • Copy Link                       │ │
│  │ │ user@email   │ │         │ • Email                           │ │
│  │ │ Great deal!  │ │         │ • Slack (soon)                    │ │
│  │ │ [Reply][Like]│ │         └──────────────────────────────────┘ │
│  │ └──────────────┘ │                                               │
│  │ [Write comment...] │                                             │
│  └──────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Hierarchy

```
ProcurementBoard
  └── RowStrip (per row)
        ├── RequestTile
        └── OfferTile (per offer)
              ├── TileImage
              ├── TileBadges
              ├── TileContent
              ├── TileActions ← NEW
              │     ├── LikeButton
              │     ├── CommentButton
              │     └── ShareButton
              └── SelectButton

CommentPanel ← NEW (slide-in)
  ├── CommentList
  │     └── CommentItem (per comment)
  │           ├── UserInfo
  │           ├── CommentContent
  │           ├── CommentActions
  │           └── CommentReplies (nested)
  └── CommentInput

SharePopover ← NEW (popover)
  └── ShareOption (multiple)
```

## Data Flow Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │         │   Next.js    │         │   FastAPI    │
│  (React UI)  │◄───────►│  API Routes  │◄───────►│   Backend    │
└──────────────┘         └──────────────┘         └──────────────┘
       │                        │                         │
       │                        │                         ▼
       │                        │                  ┌──────────────┐
       │                        │                  │  PostgreSQL  │
       │                        │                  │              │
       │                        │                  │ • tile_like  │
       │                        │                  │ • tile_comment│
       ▼                        │                  │ • tile_share │
┌──────────────┐               │                  │ • bid        │
│    Zustand   │               │                  └──────────────┘
│    Store     │               │
│              │               │
│ tileEngagement│              │
│ tileComments  │              │
│ commentsPanelOpen│           │
└──────────────┘               │
```

## User Interaction Flow: Like

```
User clicks ♥ button
       │
       ▼
┌─────────────────────┐
│ Optimistic Update   │  ← Immediate UI feedback
│ like_count++        │
│ user_has_liked=true │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ POST /api/tiles/    │
│      {bidId}/like   │
└─────────────────────┘
       │
       ├──── Success ──────► Confirm state
       │                     Update last_interaction_at
       │                     Trigger re-sort
       │
       └──── Failure ──────► Rollback state
                             Show error toast
```

## Database Schema Relationships

```
┌────────────┐
│    User    │
│  id        │◄────┐
│  email     │     │
└────────────┘     │
       ▲           │
       │           │
       │           │
┌──────┴────────┐  │  ┌─────────────┐
│   TileLike    │  │  │ TileComment │
│  id           │  │  │  id         │
│  user_id      │──┘  │  user_id    │───┐
│  bid_id       │─┐   │  bid_id     │─┐ │
│  row_id       │ │   │  row_id     │ │ │
│  created_at   │ │   │  content    │ │ │
└───────────────┘ │   │  parent_id  │─┼─┘
                  │   │  created_at │ │
┌─────────────┐   │   └─────────────┘ │
│  TileShare  │   │                   │
│  id         │   │                   │
│  user_id    │   │                   │
│  bid_id     │───┤                   │
│  row_id     │   │                   │
│  share_method│  │                   │
│  created_at │   │                   │
└─────────────┘   │                   │
                  ▼                   │
             ┌────────────┐           │
             │    Bid     │◄──────────┘
             │  id        │
             │  row_id    │
             │  seller_id │
             │  price     │
             │  is_selected│
             │            │
             │ like_count ◄── Denormalized
             │ comment_count│  for performance
             │ share_count│
             │ last_interaction_at│
             └────────────┘
                  ▲
                  │
             ┌────┴───────┐
             │    Row     │
             │  id        │
             │  title     │
             │  status    │
             │  tile_sort_mode│
             └────────────┘
```

## API Endpoint Map

```
Tile Interactions
  POST   /api/tiles/:bidId/like              ← Toggle like
  DELETE /api/tiles/:bidId/like              ← Remove like
  GET    /api/tiles/:bidId/likes             ← Get all likes

  POST   /api/tiles/:bidId/comments          ← Add comment
  GET    /api/tiles/:bidId/comments          ← Get comments (paginated)
  PATCH  /api/tiles/:bidId/comments/:id      ← Edit comment
  DELETE /api/tiles/:bidId/comments/:id      ← Delete comment

  POST   /api/tiles/:bidId/share             ← Track share + generate URL
  GET    /api/tiles/:bidId/share-url         ← Get shareable URL

Row Engagement
  GET    /api/rows/:rowId/tiles/engagement   ← Bulk load all engagement
  PATCH  /api/rows/:rowId                    ← Update tile_sort_mode
```

## State Synchronization Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend State (Zustand)                  │
│                                                               │
│  tileEngagement: {                                           │
│    42: { like_count: 15, user_has_liked: true, ... }        │
│    43: { like_count: 7, user_has_liked: false, ... }        │
│  }                                                            │
└───────────────────────────────────────────────────────────┬─┘
                                                             │
        ┌────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────┐      ┌──────────────────────────┐
│  User Action            │      │  Polling (30s interval)  │
│  • Like/Unlike          │      │  • Fetch engagement      │
│  • Add comment          │      │  • Compare counts        │
│  • Share                │      │  • Update if changed     │
└────────────┬────────────┘      └────────┬─────────────────┘
             │                            │
             ▼                            ▼
     Optimistic Update           Server Reconciliation
     • Immediate UI change       • Fetch truth from DB
     • API call queued           • Merge with local state
     • Rollback on error         • Show "New activity" badge
```

## Tile Sorting Algorithm

```
sortTiles(offers: Offer[], mode: TileSortMode): Offer[]

  IF mode === 'engagement':
    ┌──────────────────────────────────────┐
    │ Step 1: Selected tiles first         │
    │   is_selected: true → position 0     │
    └──────────────────────────────────────┘
              │
              ▼
    ┌──────────────────────────────────────┐
    │ Step 2: Sort by like_count (DESC)    │
    │   Higher likes → left side           │
    └──────────────────────────────────────┘
              │
              ▼
    ┌──────────────────────────────────────┐
    │ Step 3: Tiebreaker - last_interaction│
    │   More recent → left side            │
    └──────────────────────────────────────┘
              │
              ▼
    ┌──────────────────────────────────────┐
    │ Step 4: Engagement score             │
    │   like*3 + comment*2 + share         │
    └──────────────────────────────────────┘
              │
              ▼
          Sorted tiles

  ELSE IF mode === 'price_asc':
    Sort by price ascending

  ELSE IF mode === 'price_desc':
    Sort by price descending

  ELSE:
    Return original order
```

## Animation Flow: Tile Reordering

```
User likes Tile B (currently at position 2)
       │
       ▼
┌─────────────────────────┐
│ Update like_count       │
│ Tile B: 7 → 8           │
└─────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Re-calculate sort       │
│ Tile B now position 1   │
└─────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Framer Motion layout    │
│ animation triggers      │
│                         │
│ Tile A: pos 1 → pos 2   │ ← Slides right
│ Tile B: pos 2 → pos 1   │ ← Slides left
│ Tile C: stays at pos 3  │
└─────────────────────────┘
       │
       ▼
  Smooth 500ms transition
```

## Security & Performance Architecture

```
┌───────────────────────────────────────────────────────────┐
│                     Security Layer                         │
│                                                             │
│  • JWT Authentication (session tokens)                     │
│  • Authorization checks (user owns row access)             │
│  • Rate limiting (10 likes/min, 5 comments/min)           │
│  • Input validation (XSS prevention, SQL injection)        │
│  • CSRF tokens on mutations                                │
└───────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│                   Performance Layer                        │
│                                                             │
│  • Database indexes on foreign keys                        │
│  • Denormalized counts (like_count on Bid)                │
│  • Bulk loading (GET /rows/:id/tiles/engagement)          │
│  • Redis caching (30s TTL for hot rows)                   │
│  • Optimistic updates (no loading spinners)               │
│  • Debounced re-sorting (300ms delay)                     │
└───────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│                    Monitoring Layer                        │
│                                                             │
│  • Audit logs (all like/comment/share actions)            │
│  • Analytics tracking (Mixpanel events)                    │
│  • Error tracking (Sentry)                                 │
│  • Performance monitoring (P95 latency)                    │
│  • Database query profiling                                │
└───────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      Production Environment                 │
└────────────────────────────────────────────────────────────┘

     ┌──────────────┐         ┌──────────────┐
     │   Vercel     │         │   Railway    │
     │  (Frontend)  │◄───────►│  (Backend)   │
     │              │         │              │
     │ • Next.js    │         │ • FastAPI    │
     │ • Static     │         │ • Python     │
     │   assets     │         │ • Gunicorn   │
     └──────────────┘         └──────┬───────┘
                                     │
                                     ▼
                            ┌────────────────┐
                            │   PostgreSQL   │
                            │   (Railway)    │
                            │                │
                            │ • Persistent   │
                            │   storage      │
                            │ • Backups      │
                            └────────────────┘
                                     ▲
                                     │
                            ┌────────┴────────┐
                            │  Redis Cache    │
                            │  (Optional)     │
                            │                 │
                            │ • Engagement    │
                            │   counts        │
                            │ • 30s TTL       │
                            └─────────────────┘
```

## Feature Flag Rollout Strategy

```
Week 1-3: Development & Testing
  ├── Internal testing (100% devs)
  └── Staging environment

Week 4: Canary Release
  ├── 10% of production users
  ├── Monitor metrics: error rate, latency, engagement
  └── Rollback if error rate > 1%

Week 5: Gradual Rollout
  ├── 25% of users (Day 1-2)
  ├── 50% of users (Day 3-4)
  ├── 75% of users (Day 5-6)
  └── 100% of users (Day 7)

Post-Launch: Monitoring
  ├── Dashboard: engagement metrics
  ├── Alerts: error spikes
  └── User feedback: support tickets
```

## Mobile Responsiveness

```
Desktop (>1024px)
┌─────────────────────────────────────────────────┐
│  [Tile] [Tile] [Tile] [Tile] [Tile] [Tile]    │
│  ♥ 15   ♥ 12   ♥ 8    ♥ 5    ♥ 3    ♥ 1       │
└─────────────────────────────────────────────────┘
          ↓ Horizontal scroll

Tablet (768px - 1024px)
┌──────────────────────────────────────┐
│  [Tile] [Tile] [Tile] [Tile]        │
│  ♥ 15   ♥ 12   ♥ 8    ♥ 5           │
└──────────────────────────────────────┘
          ↓ Horizontal scroll

Mobile (<768px)
┌────────────────────┐
│     [Tile]         │  ← Larger cards
│     ♥ 15  💬 8     │
│                    │
│     [Tile]         │
│     ♥ 12  💬 3     │
│                    │
└────────────────────┘
    ↓ Vertical scroll

CommentPanel on Mobile:
  • Full-screen overlay (not slide-in)
  • Header: "Comments" + close button
  • Easier to type on keyboard
```

## Edge Case: Concurrent Likes

```
Scenario: User A and User B like same tile simultaneously

  User A                    Server                    User B
    │                         │                         │
    │ POST /api/tiles/42/like │                         │
    ├────────────────────────►│                         │
    │                         │◄────────────────────────┤
    │                         │ POST /api/tiles/42/like │
    │                         │                         │
    │                         │ ┌───────────────────┐  │
    │                         │ │ DB Transaction 1  │  │
    │                         │ │ INSERT like (A)   │  │
    │                         │ │ UPDATE count=1    │  │
    │                         │ └───────────────────┘  │
    │                         │                         │
    │                         │ ┌───────────────────┐  │
    │                         │ │ DB Transaction 2  │  │
    │                         │ │ INSERT like (B)   │  │
    │                         │ │ UPDATE count=2    │  │
    │                         │ └───────────────────┘  │
    │                         │                         │
    │ { like_count: 2 }       │                         │
    │◄────────────────────────┤                         │
    │                         ├────────────────────────►│
    │                         │       { like_count: 2 } │
    │                         │                         │

Result: Both see like_count = 2 (correct!)

Protection:
  • UNIQUE constraint on (user_id, bid_id)
  • Atomic SQL: UPDATE bid SET like_count = like_count + 1
  • Serializable isolation level
```

## Testing Pyramid

```
                    ┌────────────┐
                    │    E2E     │  ← 10% (Playwright)
                    │  Tests     │     • Full user flows
                    └────────────┘     • Like → reorder
                         │              • Comment → display
                    ┌────┴──────┐
                    │Integration│  ← 30% (Vitest)
                    │  Tests    │     • Component + API
                    └───────────┘     • State sync
                         │              • Error handling
                    ┌────┴──────┐
                    │   Unit    │  ← 60% (Vitest/Pytest)
                    │  Tests    │     • Sort functions
                    └───────────┘     • API endpoints
                                       • Store actions
```

---

## Summary: Key Design Decisions

1. **Denormalized Counts:** Store like/comment/share counts on Bid table
   - Rationale: Fast reads, no JOIN needed
   - Trade-off: Slight complexity on writes

2. **Optimistic Updates:** Update UI before API response
   - Rationale: Instant feedback, perceived performance
   - Trade-off: Need rollback logic

3. **Polling > WebSockets (MVP):** 30-second polling for engagement updates
   - Rationale: Simpler to implement, sufficient for MVP
   - Future: Migrate to WebSockets for real-time

4. **Selected Tiles Always First:** Regardless of like count
   - Rationale: Preserve user's decision, clear visual hierarchy
   - Trade-off: None (aligns with user intent)

5. **Soft Delete Comments:** Set is_deleted flag instead of hard delete
   - Rationale: Preserve conversation structure for replies
   - Trade-off: Need to filter deleted comments in queries

6. **JWT-Based Share Links:** Stateless, self-contained tokens
   - Rationale: No database storage needed, scales well
   - Trade-off: Cannot revoke individual links (only on expiration)

7. **Framer Motion for Animations:** Library for layout animations
   - Rationale: GPU-accelerated, smooth performance
   - Trade-off: 20KB bundle size (acceptable)

8. **Comment Limit: 2000 chars:** Balance expressiveness and database size
   - Rationale: Allows detailed feedback without spam
   - Trade-off: May need to truncate long-form reviews
