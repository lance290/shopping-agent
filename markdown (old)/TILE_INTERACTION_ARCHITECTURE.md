# Tile Interaction System - Architecture Design Document

## Executive Summary

This document outlines the complete architecture for adding social engagement features (like, comment, share) to the OfferTile component, along with dynamic tile reordering based on user interactions. The system preserves the existing selection mechanism while adding collaborative features that enable users to engage with and organize product offers.

---

## 1. Data Model Design

### 1.1 Database Schema

#### New Tables

```sql
-- TileLike: Tracks user likes on specific bids
CREATE TABLE tile_like (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    bid_id INTEGER NOT NULL REFERENCES bid(id) ON DELETE CASCADE,
    row_id INTEGER NOT NULL REFERENCES row(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Ensure one like per user per bid
    UNIQUE(user_id, bid_id),

    -- Index for fast aggregation queries
    INDEX idx_tile_like_bid (bid_id),
    INDEX idx_tile_like_row_created (row_id, created_at DESC)
);

-- TileComment: User comments on bids
CREATE TABLE tile_comment (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    bid_id INTEGER NOT NULL REFERENCES bid(id) ON DELETE CASCADE,
    row_id INTEGER NOT NULL REFERENCES row(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_comment_id INTEGER REFERENCES tile_comment(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,

    -- Indexes for threaded comments and pagination
    INDEX idx_tile_comment_bid_created (bid_id, created_at DESC),
    INDEX idx_tile_comment_parent (parent_comment_id)
);

-- TileShare: Track share events for analytics
CREATE TABLE tile_share (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    bid_id INTEGER NOT NULL REFERENCES bid(id) ON DELETE CASCADE,
    row_id INTEGER NOT NULL REFERENCES row(id) ON DELETE CASCADE,
    share_method VARCHAR(50) NOT NULL, -- 'link', 'email', 'slack', etc.
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    INDEX idx_tile_share_bid (bid_id),
    INDEX idx_tile_share_created (created_at DESC)
);
```

#### Schema Changes to Existing Tables

```sql
-- Add aggregated counts to Bid table for performance
ALTER TABLE bid
ADD COLUMN like_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN comment_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN share_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN last_interaction_at TIMESTAMP;

-- Index for sorting by engagement
CREATE INDEX idx_bid_row_engagement ON bid(row_id, like_count DESC, last_interaction_at DESC);

-- Add sort preference to Row table
ALTER TABLE row
ADD COLUMN tile_sort_mode VARCHAR(20) DEFAULT 'engagement',
ADD COLUMN tile_sort_updated_at TIMESTAMP;

-- tile_sort_mode values: 'original', 'price_asc', 'price_desc', 'engagement', 'manual'
```

### 1.2 SQLModel Definitions (Python)

```python
# /apps/backend/models.py additions

class TileLike(SQLModel, table=True):
    __tablename__ = "tile_like"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    bid_id: int = Field(foreign_key="bid.id", index=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TileComment(SQLModel, table=True):
    __tablename__ = "tile_comment"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    bid_id: int = Field(foreign_key="bid.id", index=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    content: str
    parent_comment_id: Optional[int] = Field(default=None, foreign_key="tile_comment.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = False


class TileShare(SQLModel, table=True):
    __tablename__ = "tile_share"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    bid_id: int = Field(foreign_key="bid.id", index=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    share_method: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Update existing Bid model
class Bid(SQLModel, table=True):
    # ... existing fields ...

    # New engagement fields
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    last_interaction_at: Optional[datetime] = None
```

### 1.3 TypeScript Interfaces (Frontend)

```typescript
// /apps/frontend/app/store.ts additions

export interface TileInteraction {
  like_count: number;
  comment_count: number;
  share_count: number;
  user_has_liked: boolean;
  last_interaction_at: string | null;
}

export interface TileComment {
  id: number;
  user_id: number;
  user_email: string; // For display
  bid_id: number;
  content: string;
  parent_comment_id: number | null;
  created_at: string;
  updated_at: string;
  replies?: TileComment[]; // For threaded comments
}

export interface Offer {
  // ... existing fields ...

  // New interaction fields
  interactions?: TileInteraction;
  bid_id?: number;
  is_selected?: boolean;
}

export type TileSortMode = 'original' | 'price_asc' | 'price_desc' | 'engagement' | 'manual';
```

---

## 2. API Endpoint Design

### 2.1 Like Endpoints

```
POST   /api/tiles/:bidId/like
DELETE /api/tiles/:bidId/like
GET    /api/tiles/:bidId/likes
```

#### POST /api/tiles/:bidId/like

**Request:**
```typescript
// No body needed (user from auth session)
```

**Response:**
```json
{
  "success": true,
  "like_count": 15,
  "user_has_liked": true
}
```

**Implementation Notes:**
- Idempotent: Multiple likes from same user don't create duplicates
- Atomically increments `bid.like_count`
- Updates `bid.last_interaction_at`
- Creates audit log entry
- Returns updated engagement counts

#### DELETE /api/tiles/:bidId/like

**Request:**
```typescript
// No body needed
```

**Response:**
```json
{
  "success": true,
  "like_count": 14,
  "user_has_liked": false
}
```

**Implementation Notes:**
- Atomically decrements `bid.like_count`
- Soft delete or hard delete (recommend hard delete for simplicity)

### 2.2 Comment Endpoints

```
POST   /api/tiles/:bidId/comments
GET    /api/tiles/:bidId/comments
PATCH  /api/tiles/:bidId/comments/:commentId
DELETE /api/tiles/:bidId/comments/:commentId
```

#### POST /api/tiles/:bidId/comments

**Request:**
```json
{
  "content": "This looks like a great deal! Has anyone purchased from this seller?",
  "parent_comment_id": null  // Optional, for replies
}
```

**Response:**
```json
{
  "success": true,
  "comment": {
    "id": 123,
    "user_id": 5,
    "user_email": "user@example.com",
    "bid_id": 42,
    "content": "This looks like a great deal!...",
    "parent_comment_id": null,
    "created_at": "2026-01-20T15:30:00Z",
    "updated_at": "2026-01-20T15:30:00Z"
  },
  "comment_count": 8
}
```

**Validation:**
- Content: 1-2000 characters
- Parent comment must exist if provided
- Parent comment must be on same bid

#### GET /api/tiles/:bidId/comments

**Query Parameters:**
- `limit`: number (default: 50, max: 100)
- `offset`: number (default: 0)
- `sort`: 'newest' | 'oldest' (default: 'newest')

**Response:**
```json
{
  "comments": [
    {
      "id": 123,
      "user_id": 5,
      "user_email": "user@example.com",
      "bid_id": 42,
      "content": "Great deal!",
      "parent_comment_id": null,
      "created_at": "2026-01-20T15:30:00Z",
      "replies": [
        {
          "id": 124,
          "user_id": 6,
          "user_email": "other@example.com",
          "content": "Agreed!",
          "parent_comment_id": 123,
          "created_at": "2026-01-20T15:35:00Z"
        }
      ]
    }
  ],
  "total": 8,
  "has_more": false
}
```

#### PATCH /api/tiles/:bidId/comments/:commentId

**Request:**
```json
{
  "content": "Updated comment text"
}
```

**Authorization:** Only comment author can edit

#### DELETE /api/tiles/:bidId/comments/:commentId

**Implementation:** Soft delete (set `is_deleted = true`)
- Preserves comment structure for replies
- Display as "[deleted]" in UI

### 2.3 Share Endpoints

```
POST /api/tiles/:bidId/share
GET  /api/tiles/:bidId/share-url
```

#### POST /api/tiles/:bidId/share

**Request:**
```json
{
  "method": "link"  // 'link', 'email', 'slack'
}
```

**Response:**
```json
{
  "success": true,
  "share_url": "https://app.example.com/shared/tiles/abc123def",
  "share_count": 5
}
```

**Implementation:**
- Generate shareable short URL (JWT-signed token with bid_id, row_id)
- Token expires in 30 days
- Increment share count
- Audit log entry

#### GET /api/tiles/:bidId/share-url

**Response:**
```json
{
  "share_url": "https://app.example.com/shared/tiles/abc123def",
  "expires_at": "2026-02-19T15:30:00Z"
}
```

### 2.4 Bulk Engagement Endpoint

```
GET /api/rows/:rowId/tiles/engagement
```

**Purpose:** Fetch all engagement data for tiles in a row (single query)

**Response:**
```json
{
  "engagement": {
    "42": {
      "like_count": 15,
      "comment_count": 8,
      "share_count": 3,
      "user_has_liked": true,
      "last_interaction_at": "2026-01-20T15:30:00Z"
    },
    "43": {
      "like_count": 7,
      "comment_count": 2,
      "share_count": 1,
      "user_has_liked": false,
      "last_interaction_at": "2026-01-19T10:15:00Z"
    }
  }
}
```

**Optimization:** Single SQL query with JOIN to fetch all engagement for row

---

## 3. State Management (Zustand)

### 3.1 Store Additions

```typescript
// /apps/frontend/app/store.ts

interface ShoppingState {
  // ... existing fields ...

  // Engagement state
  tileEngagement: Record<number, TileInteraction>; // bidId -> engagement
  tileComments: Record<number, TileComment[]>; // bidId -> comments
  commentsPanelOpen: number | null; // bidId or null

  // Actions
  setTileEngagement: (bidId: number, engagement: TileInteraction) => void;
  toggleTileLike: (bidId: number, rowId: number) => Promise<void>;
  loadComments: (bidId: number) => Promise<void>;
  addComment: (bidId: number, content: string, parentId?: number) => Promise<void>;
  setCommentsPanelOpen: (bidId: number | null) => void;
  trackShare: (bidId: number, method: string) => Promise<void>;

  // Bulk loading
  loadRowEngagement: (rowId: number) => Promise<void>;
}

// Implementation
export const useShoppingStore = create<ShoppingState>((set, get) => ({
  // ... existing state ...

  tileEngagement: {},
  tileComments: {},
  commentsPanelOpen: null,

  setTileEngagement: (bidId, engagement) => set((state) => ({
    tileEngagement: { ...state.tileEngagement, [bidId]: engagement }
  })),

  toggleTileLike: async (bidId, rowId) => {
    const current = get().tileEngagement[bidId];
    const hasLiked = current?.user_has_liked || false;

    // Optimistic update
    const optimistic: TileInteraction = {
      like_count: (current?.like_count || 0) + (hasLiked ? -1 : 1),
      comment_count: current?.comment_count || 0,
      share_count: current?.share_count || 0,
      user_has_liked: !hasLiked,
      last_interaction_at: new Date().toISOString(),
    };
    get().setTileEngagement(bidId, optimistic);

    try {
      const method = hasLiked ? 'DELETE' : 'POST';
      const res = await fetch(`/api/tiles/${bidId}/like`, { method });
      const data = await res.json();

      if (res.ok) {
        get().setTileEngagement(bidId, {
          ...optimistic,
          like_count: data.like_count,
        });
      } else {
        // Revert on failure
        get().setTileEngagement(bidId, current || optimistic);
      }
    } catch (err) {
      // Revert on error
      get().setTileEngagement(bidId, current || optimistic);
    }
  },

  loadComments: async (bidId) => {
    try {
      const res = await fetch(`/api/tiles/${bidId}/comments`);
      const data = await res.json();

      if (res.ok) {
        set((state) => ({
          tileComments: { ...state.tileComments, [bidId]: data.comments }
        }));
      }
    } catch (err) {
      console.error('Failed to load comments:', err);
    }
  },

  addComment: async (bidId, content, parentId) => {
    try {
      const res = await fetch(`/api/tiles/${bidId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, parent_comment_id: parentId }),
      });
      const data = await res.json();

      if (res.ok) {
        // Reload comments to get updated list
        await get().loadComments(bidId);

        // Update engagement count
        const current = get().tileEngagement[bidId];
        if (current) {
          get().setTileEngagement(bidId, {
            ...current,
            comment_count: data.comment_count,
          });
        }
      }
    } catch (err) {
      console.error('Failed to add comment:', err);
    }
  },

  setCommentsPanelOpen: (bidId) => set({ commentsPanelOpen: bidId }),

  trackShare: async (bidId, method) => {
    try {
      const res = await fetch(`/api/tiles/${bidId}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method }),
      });
      const data = await res.json();

      if (res.ok) {
        const current = get().tileEngagement[bidId];
        if (current) {
          get().setTileEngagement(bidId, {
            ...current,
            share_count: data.share_count,
          });
        }
        return data.share_url;
      }
    } catch (err) {
      console.error('Failed to track share:', err);
    }
  },

  loadRowEngagement: async (rowId) => {
    try {
      const res = await fetch(`/api/rows/${rowId}/tiles/engagement`);
      const data = await res.json();

      if (res.ok) {
        set((state) => ({
          tileEngagement: { ...state.tileEngagement, ...data.engagement }
        }));
      }
    } catch (err) {
      console.error('Failed to load row engagement:', err);
    }
  },
}));
```

---

## 4. UI/UX Design (Text Description)

### 4.1 OfferTile Component Updates

#### Like Button Placement
- Position: Bottom section of tile, below price/shipping info
- Layout: Horizontal row with three action buttons
- Design: Minimalist icon buttons with counts

```
┌─────────────────────────┐
│      [Product Image]     │
├─────────────────────────┤
│ Merchant                │
│ Product Title           │
│ $99.99                  │
│ ★ 4.5 (123 reviews)     │
├─────────────────────────┤
│ [♥ 15] [💬 8] [⤴ 3]    │  <- Action row
│ [Select Deal]           │
└─────────────────────────┘
```

#### Like Button States
1. **Unliked**: Outline heart icon, gray color (#6B7280)
2. **Liked**: Filled heart icon, red color (#EF4444)
3. **Hover**: Scale 1.1, cursor pointer
4. **Animation**: On like - heart scales to 1.3 then back to 1.1, with bounce easing

#### Comment Button
- Icon: MessageCircle (Lucide icon)
- Shows comment count badge
- Click opens comment panel (slide-in from right)
- Badge color: Blue (#3B82F6) when count > 0

#### Share Button
- Icon: Share2 (Lucide icon)
- Click opens share menu (popover)
- Options: "Copy Link", "Email", "Slack" (future)
- Toast notification on copy

### 4.2 Selected Tile Visual Enhancement

Current: Green border (`border-status-success`)

**Enhanced Design:**
```css
.tile-selected {
  border: 2px solid #10B981; /* status-success */
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.1); /* Glow effect */
  position: relative;
}

.tile-selected::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: inherit;
  background: linear-gradient(135deg, #10B981, #059669);
  opacity: 0.1;
  pointer-events: none;
}
```

**Badge Enhancement:**
- Move "Selected" badge to top-right (current position)
- Add subtle animation: Pulse effect on initial selection
- Icon: ShieldCheck with checkmark

### 4.3 Comment Panel Design

**Slide-in Panel (Right Side):**
- Width: 400px
- Background: White with subtle shadow
- Overlay: Semi-transparent backdrop (closes on click)
- Animation: Slide-in from right (300ms ease-out)

**Panel Structure:**
```
┌─────────────────────────────────────┐
│ Comments (8)                    [×] │  <- Header
├─────────────────────────────────────┤
│                                     │
│ ┌─────────────────────────────────┐│
│ │ user@example.com    2h ago      ││  <- Comment
│ │ This looks like a great deal!   ││
│ │ [Reply] [Like]                  ││
│ └─────────────────────────────────┘│
│                                     │
│   ┌───────────────────────────────┐│
│   │ other@example.com   1h ago    ││  <- Reply (indented)
│   │ Agreed!                       ││
│   └───────────────────────────────┘│
│                                     │
├─────────────────────────────────────┤
│ [Write a comment...]                │  <- Input
│                              [Send] │
└─────────────────────────────────────┘
```

**Features:**
- Threaded comments (1 level deep)
- Auto-scroll to latest
- Real-time character count (max 2000)
- Markdown support (future enhancement)
- Edit/delete for own comments

### 4.4 Share Menu Design

**Popover Menu (Triggered by Share Button):**
- Position: Below share button
- Width: 200px
- Arrow pointing to button

```
┌──────────────────────────┐
│ 🔗 Copy Link            │
│ 📧 Email                │
│ 💬 Slack (coming soon)  │
└──────────────────────────┘
```

**Copy Link Flow:**
1. Click "Copy Link"
2. Generate shareable URL (API call)
3. Copy to clipboard
4. Show toast: "Link copied!"
5. Close popover

**Email Flow:**
1. Click "Email"
2. Open `mailto:` with pre-filled subject and body
3. Track share event
4. Close popover

### 4.5 Tile Reordering Animation

**Strategy: Framer Motion Layout Animations**

```typescript
import { motion, AnimatePresence } from 'framer-motion';

<motion.div
  layout
  layoutId={`tile-${offer.bid_id}`}
  initial={{ opacity: 0, scale: 0.8 }}
  animate={{ opacity: 1, scale: 1 }}
  exit={{ opacity: 0, scale: 0.8 }}
  transition={{
    layout: { duration: 0.5, ease: 'easeInOut' },
    opacity: { duration: 0.3 },
    scale: { duration: 0.3 }
  }}
>
  {/* OfferTile content */}
</motion.div>
```

**Behavior:**
- On like: Tile smoothly transitions to new position
- Stagger effect: Tiles shift in sequence (50ms delay each)
- No layout shift on unlike (stays in position until page refresh)

---

## 5. Sorting and Reordering Logic

### 5.1 Sort Modes

```typescript
export type TileSortMode =
  | 'original'     // As returned from search API
  | 'price_asc'    // Lowest price first
  | 'price_desc'   // Highest price first
  | 'engagement'   // Most liked first
  | 'manual';      // User-defined order (future)
```

### 5.2 Engagement-Based Sorting Algorithm

```typescript
function sortByEngagement(offers: Offer[]): Offer[] {
  return [...offers].sort((a, b) => {
    // 1. Selected tile always first
    if (a.is_selected && !b.is_selected) return -1;
    if (!a.is_selected && b.is_selected) return 1;

    // 2. Sort by like count (descending)
    const likeDiff = (b.interactions?.like_count || 0) - (a.interactions?.like_count || 0);
    if (likeDiff !== 0) return likeDiff;

    // 3. Tiebreaker: Most recent interaction
    const aTime = a.interactions?.last_interaction_at;
    const bTime = b.interactions?.last_interaction_at;
    if (aTime && bTime) {
      return new Date(bTime).getTime() - new Date(aTime).getTime();
    }
    if (aTime) return -1;
    if (bTime) return 1;

    // 4. Final tiebreaker: Original order (stable sort)
    return 0;
  });
}
```

### 5.3 Handling Ties

**Strategy: Multi-level tiebreaker**
1. Like count (primary)
2. Last interaction timestamp (secondary)
3. Total engagement score: `like_count * 3 + comment_count * 2 + share_count` (tertiary)
4. Preserve original order (stable sort)

### 5.4 Sort Mode Persistence

**Per-Row Preference:**
- Store in `row.tile_sort_mode` column
- Update on dropdown change
- Persist to database immediately (PATCH /api/rows/:id)
- Default: 'engagement' for new rows

### 5.5 Real-time Reordering Behavior

**On Like/Unlike:**
- Optimistic update to like count
- If in 'engagement' mode: Re-sort immediately
- Animate tile movement to new position
- Debounce rapid interactions (300ms)

**On Other Users' Likes:**
- Polling strategy: Fetch engagement data every 30 seconds
- Compare like counts, re-sort if changed
- Smooth animation for position changes
- Show subtle indicator: "2 new likes" badge

---

## 6. Technical Implementation

### 6.1 Component Structure

```
OfferTile (Enhanced)
├── TileImage
├── TileBadges (Negotiable, Selected, Best Match)
├── TileContent
│   ├── Merchant
│   ├── Title
│   ├── Price
│   ├── Rating/Reviews
│   └── Shipping
├── TileActions (NEW)
│   ├── LikeButton
│   ├── CommentButton
│   └── ShareButton
└── SelectButton

CommentPanel (NEW)
├── CommentList
│   └── CommentItem
│       ├── UserInfo
│       ├── CommentContent
│       ├── CommentActions
│       └── CommentReplies
└── CommentInput

SharePopover (NEW)
├── ShareOption (Copy Link)
├── ShareOption (Email)
└── ShareOption (Slack - disabled)
```

### 6.2 Component File Structure

```
/apps/frontend/app/components/
├── OfferTile.tsx (enhanced)
├── TileActions.tsx (new)
├── CommentPanel.tsx (new)
├── CommentItem.tsx (new)
├── SharePopover.tsx (new)
└── RowStrip.tsx (enhanced)
```

### 6.3 API Client Utilities

```typescript
// /apps/frontend/app/utils/tile-api.ts

export async function toggleTileLike(bidId: number): Promise<TileInteraction> {
  const res = await fetch(`/api/tiles/${bidId}/like`, { method: 'POST' });
  return res.json();
}

export async function removeTileLike(bidId: number): Promise<TileInteraction> {
  const res = await fetch(`/api/tiles/${bidId}/like`, { method: 'DELETE' });
  return res.json();
}

export async function loadComments(bidId: number): Promise<TileComment[]> {
  const res = await fetch(`/api/tiles/${bidId}/comments`);
  const data = await res.json();
  return data.comments;
}

export async function addComment(
  bidId: number,
  content: string,
  parentId?: number
): Promise<TileComment> {
  const res = await fetch(`/api/tiles/${bidId}/comments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, parent_comment_id: parentId }),
  });
  const data = await res.json();
  return data.comment;
}

export async function shareTile(
  bidId: number,
  method: string
): Promise<string> {
  const res = await fetch(`/api/tiles/${bidId}/share`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ method }),
  });
  const data = await res.json();
  return data.share_url;
}

export async function loadRowEngagement(
  rowId: number
): Promise<Record<number, TileInteraction>> {
  const res = await fetch(`/api/rows/${rowId}/tiles/engagement`);
  const data = await res.json();
  return data.engagement;
}
```

### 6.4 Backend API Implementation (FastAPI)

```python
# /apps/backend/main.py additions

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, func
from typing import List, Optional

router = APIRouter(prefix="/api/tiles")

@router.post("/{bid_id}/like")
async def like_tile(
    bid_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Toggle like on a tile."""
    # Check if already liked
    existing = await session.exec(
        select(TileLike).where(
            TileLike.bid_id == bid_id,
            TileLike.user_id == user.id
        )
    ).first()

    if existing:
        # Already liked - this is idempotent, just return current state
        bid = await session.get(Bid, bid_id)
        return {
            "success": True,
            "like_count": bid.like_count,
            "user_has_liked": True
        }

    # Create like
    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(404, "Bid not found")

    like = TileLike(
        user_id=user.id,
        bid_id=bid_id,
        row_id=bid.row_id
    )
    session.add(like)

    # Increment count
    bid.like_count += 1
    bid.last_interaction_at = datetime.utcnow()
    session.add(bid)

    await session.commit()
    await session.refresh(bid)

    return {
        "success": True,
        "like_count": bid.like_count,
        "user_has_liked": True
    }


@router.delete("/{bid_id}/like")
async def unlike_tile(
    bid_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Remove like from a tile."""
    like = await session.exec(
        select(TileLike).where(
            TileLike.bid_id == bid_id,
            TileLike.user_id == user.id
        )
    ).first()

    if not like:
        # Not liked - return current state
        bid = await session.get(Bid, bid_id)
        return {
            "success": True,
            "like_count": bid.like_count,
            "user_has_liked": False
        }

    # Remove like
    await session.delete(like)

    bid = await session.get(Bid, bid_id)
    bid.like_count = max(0, bid.like_count - 1)
    session.add(bid)

    await session.commit()
    await session.refresh(bid)

    return {
        "success": True,
        "like_count": bid.like_count,
        "user_has_liked": False
    }


@router.get("/{bid_id}/comments")
async def get_comments(
    bid_id: int,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Get comments for a tile."""
    # Fetch top-level comments
    comments = await session.exec(
        select(TileComment)
        .where(
            TileComment.bid_id == bid_id,
            TileComment.parent_comment_id == None,
            TileComment.is_deleted == False
        )
        .order_by(TileComment.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    # Fetch replies for each comment
    comment_ids = [c.id for c in comments]
    replies = await session.exec(
        select(TileComment)
        .where(
            TileComment.parent_comment_id.in_(comment_ids),
            TileComment.is_deleted == False
        )
        .order_by(TileComment.created_at.asc())
    ).all()

    # Group replies by parent
    replies_map = {}
    for reply in replies:
        if reply.parent_comment_id not in replies_map:
            replies_map[reply.parent_comment_id] = []
        replies_map[reply.parent_comment_id].append(reply)

    # Build response
    result = []
    for comment in comments:
        comment_dict = comment.dict()
        comment_dict['replies'] = replies_map.get(comment.id, [])
        result.append(comment_dict)

    total = await session.exec(
        select(func.count(TileComment.id))
        .where(
            TileComment.bid_id == bid_id,
            TileComment.parent_comment_id == None,
            TileComment.is_deleted == False
        )
    ).one()

    return {
        "comments": result,
        "total": total,
        "has_more": (offset + len(comments)) < total
    }


@router.post("/{bid_id}/comments")
async def add_comment(
    bid_id: int,
    content: str,
    parent_comment_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Add a comment to a tile."""
    # Validate
    if not content or len(content) > 2000:
        raise HTTPException(400, "Content must be 1-2000 characters")

    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(404, "Bid not found")

    # Create comment
    comment = TileComment(
        user_id=user.id,
        bid_id=bid_id,
        row_id=bid.row_id,
        content=content,
        parent_comment_id=parent_comment_id
    )
    session.add(comment)

    # Increment count
    bid.comment_count += 1
    bid.last_interaction_at = datetime.utcnow()
    session.add(bid)

    await session.commit()
    await session.refresh(comment)
    await session.refresh(bid)

    return {
        "success": True,
        "comment": comment,
        "comment_count": bid.comment_count
    }


@router.post("/{bid_id}/share")
async def share_tile(
    bid_id: int,
    method: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Track a share event and generate shareable URL."""
    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(404, "Bid not found")

    # Create share record
    share = TileShare(
        user_id=user.id,
        bid_id=bid_id,
        row_id=bid.row_id,
        share_method=method
    )
    session.add(share)

    # Increment count
    bid.share_count += 1
    bid.last_interaction_at = datetime.utcnow()
    session.add(bid)

    await session.commit()
    await session.refresh(bid)

    # Generate shareable URL (JWT token)
    import jwt
    from datetime import timedelta

    token = jwt.encode(
        {
            'bid_id': bid_id,
            'row_id': bid.row_id,
            'exp': datetime.utcnow() + timedelta(days=30)
        },
        os.getenv('JWT_SECRET'),
        algorithm='HS256'
    )

    share_url = f"{os.getenv('APP_URL')}/shared/tiles/{token}"

    return {
        "success": True,
        "share_url": share_url,
        "share_count": bid.share_count
    }


@router.get("/rows/{row_id}/tiles/engagement")
async def get_row_engagement(
    row_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Get engagement data for all tiles in a row."""
    # Fetch all bids for row
    bids = await session.exec(
        select(Bid).where(Bid.row_id == row_id)
    ).all()

    bid_ids = [b.id for b in bids]

    # Fetch user's likes
    likes = await session.exec(
        select(TileLike.bid_id)
        .where(
            TileLike.row_id == row_id,
            TileLike.user_id == user.id
        )
    ).all()

    user_liked_bids = set(likes)

    # Build engagement map
    engagement = {}
    for bid in bids:
        engagement[bid.id] = {
            "like_count": bid.like_count,
            "comment_count": bid.comment_count,
            "share_count": bid.share_count,
            "user_has_liked": bid.id in user_liked_bids,
            "last_interaction_at": bid.last_interaction_at.isoformat() if bid.last_interaction_at else None
        }

    return {"engagement": engagement}
```

### 6.5 Next.js API Routes

```typescript
// /apps/frontend/app/api/tiles/[bidId]/like/route.ts

import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { COOKIE_NAME } from '../../../auth/constants';

const BFF_URL = process.env.BFF_URL || 'http://localhost:8080';

async function getAuthHeader() {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function POST(
  request: NextRequest,
  { params }: { params: { bidId: string } }
) {
  try {
    const authHeader = await getAuthHeader();
    if (!authHeader['Authorization']) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(`${BFF_URL}/api/tiles/${params.bidId}/like`, {
      method: 'POST',
      headers: authHeader,
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error liking tile:', error);
    return NextResponse.json({ error: 'Failed to like tile' }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { bidId: string } }
) {
  try {
    const authHeader = await getAuthHeader();
    if (!authHeader['Authorization']) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(`${BFF_URL}/api/tiles/${params.bidId}/like`, {
      method: 'DELETE',
      headers: authHeader,
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error unliking tile:', error);
    return NextResponse.json({ error: 'Failed to unlike tile' }, { status: 500 });
  }
}
```

### 6.6 State Synchronization Strategy

**Pattern: Optimistic Updates with Rollback**

1. User action (like, comment, share)
2. Immediate optimistic state update (Zustand)
3. Visual feedback (animation, count increment)
4. API call in background
5. On success: Confirm state with server response
6. On failure: Rollback to previous state, show error toast

**Polling Strategy:**
- Poll engagement data every 30 seconds when row is visible
- Use Intersection Observer to detect visibility
- Pause polling when tab is inactive (visibilitychange event)
- Compare engagement counts, update only if changed
- Show subtle notification: "New activity" badge

### 6.7 Performance Considerations

**Optimization 1: Bulk Engagement Loading**
- Load all engagement for row in single API call
- Cache in Zustand store
- Reduces N+1 query problem

**Optimization 2: Virtual Scrolling (Future)**
- If row has 50+ tiles, implement virtual scrolling
- Only render visible tiles + buffer
- Library: `react-window` or `@tanstack/react-virtual`

**Optimization 3: Comment Pagination**
- Load first 10 comments initially
- "Load more" button for additional comments
- Lazy load replies

**Optimization 4: Database Indexes**
```sql
-- Already added in schema above
CREATE INDEX idx_tile_like_bid ON tile_like(bid_id);
CREATE INDEX idx_tile_comment_bid_created ON tile_comment(bid_id, created_at DESC);
CREATE INDEX idx_bid_row_engagement ON bid(row_id, like_count DESC, last_interaction_at DESC);
```

**Optimization 5: Caching Strategy**
- Redis cache for engagement counts (30-second TTL)
- Invalidate on write (like, comment, share)
- Reduces database load for read-heavy workload

---

## 7. Edge Cases and Solutions

### 7.1 Multiple Users Liking Same Tile

**Problem:** Race condition when two users like simultaneously

**Solution:**
- Database constraint: UNIQUE(user_id, bid_id) on tile_like
- Idempotent API: POST /api/tiles/:bidId/like returns success even if already liked
- Atomic increment on bid.like_count using SQL: `UPDATE bid SET like_count = like_count + 1`
- Frontend polling updates counts from server

### 7.2 Comment Moderation

**Phase 1 (MVP):**
- No moderation, users can delete own comments
- Soft delete: Set is_deleted = true, show "[deleted]"
- Admin flag on User model for future moderation tools

**Phase 2 (Future):**
- Report comment feature
- Admin dashboard to review reports
- Auto-hide comments with 3+ reports
- Email notification to comment author

### 7.3 Share Link Expiration

**Implementation:**
- JWT token with 30-day expiration
- Frontend: Decode token, check exp claim
- Show "Link expired" page with option to request new link
- Track expiration in analytics

**Database:**
- No need to store share links (stateless JWT)
- TileShare table only tracks analytics, not access control

### 7.4 Selected + Liked Tile Priority

**Sorting Logic:**
```typescript
function sortTiles(offers: Offer[]): Offer[] {
  return [...offers].sort((a, b) => {
    // Rule 1: Selected tile ALWAYS first
    if (a.is_selected && !b.is_selected) return -1;
    if (!a.is_selected && b.is_selected) return 1;

    // Rule 2: If both selected (impossible in current system) or both not selected,
    // sort by engagement
    return sortByEngagement([a, b])[0] === a ? -1 : 1;
  });
}
```

**Visual Treatment:**
- Selected tile keeps enhanced border
- Show both "Selected" badge AND engagement counts
- Position: Fixed at index 0, regardless of like count

### 7.5 Anonymous vs. Authenticated Interactions

**Current System:** All interactions require authentication

**Future Enhancement:**
- Allow anonymous likes (track by session_id instead of user_id)
- Prompt for login after 3 anonymous interactions
- Migrate anonymous interactions on signup

### 7.6 Handling Deleted Bids

**Problem:** User likes/comments on bid, then bid is deleted

**Solution:**
```sql
-- Foreign key with CASCADE delete
bid_id INTEGER REFERENCES bid(id) ON DELETE CASCADE
```

- When bid is deleted, all likes/comments are automatically deleted
- No orphaned engagement data
- Audit log preserves history for analytics

### 7.7 Real-time Sync Across Devices

**Phase 1 (Polling):**
- Poll every 30 seconds
- Update engagement counts
- Show "New activity" badge if changed

**Phase 2 (WebSockets - Future):**
- WebSocket connection per row
- Server pushes engagement updates in real-time
- Client subscribes: `subscribe:row:123`
- Events: `tile:liked`, `tile:commented`, `tile:shared`

### 7.8 Tile Reordering Performance

**Problem:** Re-sorting 50+ tiles on every like causes jank

**Solution:**
- Debounce re-sort: Wait 300ms after last engagement update
- Use `requestAnimationFrame` for smooth animations
- Memoize sort function: `useMemo(() => sortTiles(offers), [offers, sortMode])`
- Framer Motion's layout animations are GPU-accelerated

### 7.9 Comment Spam Prevention

**Measures:**
- Rate limit: 10 comments per user per minute
- Minimum 5-second delay between comments from same user
- Content validation: No URLs in first 3 comments from new users
- Character limit: 2000 characters
- Future: Sentiment analysis to flag toxic comments

### 7.10 Engagement Gaming

**Problem:** User spamming likes to boost their bid

**Prevention:**
- Cannot like own bid (check bid.seller_id vs user.id)
- Cannot unlike then re-like rapidly (rate limit)
- Admin dashboard to detect anomalies
- Cap like weight in sort: After 100 likes, diminishing returns

---

## 8. Migration and Rollout Plan

### Phase 1: Database Migration (Week 1)

```bash
# Create Alembic migration
alembic revision -m "add_tile_interactions"
```

```python
# Migration file
def upgrade():
    # Create tables
    op.create_table('tile_like', ...)
    op.create_table('tile_comment', ...)
    op.create_table('tile_share', ...)

    # Add columns to bid
    op.add_column('bid', sa.Column('like_count', sa.Integer(), default=0))
    op.add_column('bid', sa.Column('comment_count', sa.Integer(), default=0))
    op.add_column('bid', sa.Column('share_count', sa.Integer(), default=0))
    op.add_column('bid', sa.Column('last_interaction_at', sa.DateTime()))

    # Add indexes
    op.create_index('idx_tile_like_bid', 'tile_like', ['bid_id'])
    op.create_index('idx_bid_row_engagement', 'bid', ['row_id', 'like_count', 'last_interaction_at'])

def downgrade():
    # Reverse all changes
    ...
```

### Phase 2: Backend API (Week 1-2)

1. Implement tile interaction endpoints
2. Add engagement aggregation logic
3. Write unit tests
4. Deploy to staging
5. Integration tests with Postman/Pytest

### Phase 3: Frontend Components (Week 2-3)

1. Create TileActions component
2. Implement LikeButton with animation
3. Build CommentPanel component
4. Create SharePopover component
5. Update Zustand store
6. Component testing with Vitest

### Phase 4: Integration (Week 3)

1. Connect components to API
2. Implement optimistic updates
3. Add error handling and rollback
4. Polling mechanism
5. E2E tests with Playwright

### Phase 5: Visual Enhancements (Week 4)

1. Selected tile glow effect
2. Tile reordering animations
3. Loading states and skeletons
4. Toast notifications
5. Accessibility audit (keyboard navigation, ARIA labels)

### Phase 6: Rollout (Week 4-5)

1. Deploy to staging
2. Internal testing (dogfooding)
3. Fix bugs and polish
4. Feature flag: Enable for 10% of users
5. Monitor metrics (engagement rate, error rate)
6. Gradual rollout: 25% → 50% → 100%

### Phase 7: Monitoring and Iteration (Ongoing)

1. Analytics dashboard (Mixpanel/Amplitude)
2. Track metrics: Likes per tile, comments per tile, share rate
3. A/B test variations (icon styles, placement)
4. Gather user feedback
5. Plan Phase 2 features (real-time sync, moderation)

---

## 9. Success Metrics

### Engagement Metrics
- **Like Rate:** % of tiles that receive at least 1 like
- **Comment Rate:** % of tiles with comments
- **Share Rate:** % of tiles shared
- **Engagement per User:** Average interactions per user per session

### Product Metrics
- **Time on Board:** Average session duration (expect +30%)
- **Tile Interactions:** Total likes + comments + shares per day
- **Selected Tiles:** % of selected tiles that have likes (hypothesis: >80%)
- **Return Rate:** % of users who return within 7 days (expect +15%)

### Technical Metrics
- **API Latency:** P95 response time for like/comment endpoints (<200ms)
- **Error Rate:** % of failed interactions (<0.1%)
- **Load Time:** Time to load engagement data for row (<500ms)

### Business Metrics
- **Clickthrough Rate:** % of users who click tile links (expect +20%)
- **Affiliate Revenue:** Commission per tile click (expect +10%)
- **User Retention:** 30-day retention rate (expect +25%)

---

## 10. Future Enhancements

### Real-time Collaboration (Phase 2)
- WebSocket connections for live updates
- Show which users are currently viewing the row
- Live cursor positions (collaborative shopping)

### Advanced Comment Features
- Markdown support (bold, italic, links)
- Mention users (@username)
- Emoji reactions on comments
- Inline image/video uploads

### Gamification
- Badge system: "Top Commenter", "Deal Hunter"
- Leaderboard: Most helpful comments
- Reputation score based on likes received

### AI-Powered Features
- Auto-generate comparison comments
- Sentiment analysis on comments
- Smart reply suggestions
- Flag suspicious/spam comments

### Social Features
- Follow other users
- Share entire rows (not just tiles)
- Collaborative boards (multiple users can edit)
- Activity feed: "User X liked Y"

### Advanced Sorting
- Machine learning: Personalized tile order
- Filter by: Only liked tiles, Only commented tiles
- Search within row
- Custom manual drag-and-drop ordering

---

## 11. Technical Risks and Mitigations

### Risk 1: Database Performance

**Concern:** Engagement queries slow down row loading

**Mitigation:**
- Denormalize counts on Bid table (like_count, comment_count)
- Bulk engagement endpoint (single query for all tiles)
- Database indexes on foreign keys
- Redis caching for hot rows

### Risk 2: Animation Performance

**Concern:** Tile reordering causes jank on slower devices

**Mitigation:**
- Use CSS transforms (GPU-accelerated)
- Framer Motion's optimized layout animations
- Limit concurrent animations (stagger)
- Performance profiling with React DevTools

### Risk 3: Race Conditions

**Concern:** Multiple users liking same tile causes count drift

**Mitigation:**
- Database constraints (UNIQUE on user_id + bid_id)
- Atomic SQL updates (UPDATE ... SET count = count + 1)
- Periodic count reconciliation (cron job)
- Idempotent API endpoints

### Risk 4: Spam and Abuse

**Concern:** Users game the system with fake likes/comments

**Mitigation:**
- Rate limiting (10 likes/min, 5 comments/min)
- Cannot like own bids
- Admin moderation tools
- Anomaly detection (flag users with >100 likes/day)

### Risk 5: Scale

**Concern:** System slows down with 10,000+ tiles per row

**Mitigation:**
- Pagination: Load 20 tiles at a time
- Virtual scrolling for large lists
- Lazy load comments (fetch on panel open)
- CDN for static assets (images)

---

## 12. Accessibility Considerations

### Keyboard Navigation
- Tab through tiles: Focus on card, then action buttons
- Enter/Space: Trigger like, comment, share
- Escape: Close comment panel/share popover
- Arrow keys: Navigate between tiles (future)

### Screen Reader Support
- ARIA labels: "Like this product", "15 likes", "View 8 comments"
- Live regions: Announce like count changes
- Semantic HTML: Use `<button>` for actions, not `<div>`
- Alt text for icons: "Heart icon", "Comment icon"

### Visual Accessibility
- Color contrast: WCAG AA compliant (4.5:1 for text)
- Focus indicators: 2px solid outline on focus
- No color-only indicators (icons + text for engagement)
- High contrast mode support

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  .tile-reorder {
    transition: none;
  }
  .like-button-animation {
    animation: none;
  }
}
```

---

## 13. Testing Strategy

### Unit Tests
- Zustand store actions (toggleTileLike, addComment)
- Sorting functions (sortByEngagement)
- API utilities (tile-api.ts)
- Coverage target: 80%

### Component Tests (Vitest + Testing Library)
- OfferTile: Renders with engagement data
- TileActions: Like button click triggers API
- CommentPanel: Loads and displays comments
- SharePopover: Copy link to clipboard

### Integration Tests (Playwright)
- User can like a tile
- User can add comment
- User can share tile
- Engagement updates across sessions
- Tile reordering on like

### Performance Tests
- Load 50 tiles with engagement data (<2s)
- Re-sort 50 tiles on like (<100ms)
- Comment panel opens (<200ms)

### Load Tests (Artillery)
- 100 concurrent users liking tiles
- 1000 requests/sec to engagement endpoint
- Database query performance under load

---

## 14. Documentation Deliverables

1. **API Documentation:** OpenAPI/Swagger spec for tile endpoints
2. **Component Storybook:** Visual documentation of TileActions, CommentPanel, etc.
3. **User Guide:** Help article explaining like/comment/share features
4. **Developer Guide:** Setup instructions, architecture overview
5. **Runbook:** Troubleshooting common issues (engagement counts drift, etc.)

---

## 15. Appendix: File Change Summary

### New Files
```
/apps/backend/
├── alembic/versions/XXXX_add_tile_interactions.py

/apps/frontend/app/
├── components/
│   ├── TileActions.tsx
│   ├── CommentPanel.tsx
│   ├── CommentItem.tsx
│   └── SharePopover.tsx
├── utils/
│   └── tile-api.ts
└── api/
    └── tiles/
        └── [bidId]/
            ├── like/route.ts
            ├── comments/route.ts
            └── share/route.ts
```

### Modified Files
```
/apps/backend/
├── models.py (add TileLike, TileComment, TileShare models)
└── main.py (add tile interaction endpoints)

/apps/frontend/app/
├── store.ts (add engagement state and actions)
├── components/
│   ├── OfferTile.tsx (integrate TileActions)
│   └── RowStrip.tsx (add engagement loading)
└── package.json (add framer-motion)
```

---

## Conclusion

This architecture provides a comprehensive foundation for adding social engagement features to the shopping agent's tile system. The design prioritizes:

1. **Performance:** Optimistic updates, bulk loading, caching
2. **User Experience:** Smooth animations, real-time feedback, accessibility
3. **Scalability:** Database indexes, pagination, future WebSocket support
4. **Maintainability:** Clean separation of concerns, TypeScript types, comprehensive testing

The phased rollout plan ensures safe deployment with feature flags and gradual adoption. Success metrics are clearly defined to measure impact on user engagement and business outcomes.

Next steps: Review this architecture with stakeholders, prioritize features for MVP, and begin Phase 1 implementation.
