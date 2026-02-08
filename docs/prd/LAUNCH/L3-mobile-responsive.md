# PRD L3: Mobile Responsive Design

**Priority:** P1 — Pre-launch
**Target:** Week 3 (Feb 24–28, 2026)
**Depends on:** Landing page (L2)

---

## Problem

The current UI is desktop-only. The split-pane "chat + tiles" layout has no mobile breakpoints. In 2026, >65% of marketplace traffic comes from mobile devices. More critically, viral share links shared via text/social media open on phones — if the experience is broken on mobile, the viral loop dies.

---

## Solution

### R1 — Responsive Layout Breakpoints

| Breakpoint | Layout | Behavior |
|-----------|--------|----------|
| `< 640px` (mobile) | Single pane, stacked | Chat full-width. Tiles below or swipe-up sheet. |
| `640–1024px` (tablet) | Collapsible sidebar | Chat as slide-out drawer. Tiles primary view. |
| `> 1024px` (desktop) | Split pane (current) | No change. |

### R2 — Mobile Chat Experience

- Chat input pinned to bottom (like iMessage)
- Messages scroll above input
- "View results" button/tab switches to tiles pane
- Swipe or tab-based navigation between Chat ↔ Tiles

### R3 — Mobile Tiles Grid

- Single column card layout on mobile
- Swipeable tile cards (like Tinder/shopping apps)
- Tap to expand tile detail (slide-up panel)
- Like/comment actions accessible via tap (no hover)

### R4 — Mobile Vendor Contact Modal

- Full-screen modal on mobile (not centered popup)
- Sticky "Send" / "Copy" buttons at bottom
- Email body in scrollable textarea
- One-tap to switch between legs (round-trip)

### R5 — Mobile Share Experience

- Share button triggers native `navigator.share()` API where available
- Fallback: copy-to-clipboard with toast notification
- Shared links generate rich preview cards (OG meta tags)

---

## Key Pages to Make Responsive

| Page | Current State | Priority |
|------|--------------|----------|
| Landing page (`/`) | Doesn't exist yet (L2) | Build mobile-first |
| Workspace (`/workspace` or main chat) | Desktop-only split pane | P0 |
| Vendor Contact Modal | `max-w-md` = 448px, unusable on mobile | P0 |
| Tile detail panel | Backend only, no frontend yet | Build mobile-first |
| Share page (`/share/[token]`) | Exists, not tested on mobile | P1 |
| Merchant registration | Form page, likely OK | P2 — test only |
| Quote submission (`/quote/[token]`) | Form page, likely OK | P2 — test only |

---

## Acceptance Criteria

- [ ] All P0 pages render correctly on iPhone SE (375px) through iPhone 15 Pro Max (430px)
- [ ] All P0 pages render correctly on Android (360–412px common widths)
- [ ] No horizontal scroll on any page at any breakpoint
- [ ] Touch targets ≥ 44x44px (Apple HIG)
- [ ] Chat input doesn't get hidden by mobile keyboard
- [ ] `navigator.share()` works on iOS Safari
- [ ] Lighthouse mobile score > 70
