# PRD: Mobile Responsive Layout

**Phase:** 3 — Closing the Loop  
**Priority:** P2  
**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Parent:** [Phase 3 Parent](./parent.md)

---

## 1. Problem Statement

The current UI is designed for desktop with a **fixed two-pane layout** (Chat left, Board right) and horizontal scrolling tile rows. On mobile:

- The split pane is unusable — the chat pane compresses or overflows.
- Tile rows scroll horizontally but tiles are too wide to read on small screens.
- The resizable divider handle is not touch-friendly.
- `MobileDetailTooltip` exists as a partial solution for tile detail on mobile, but no comprehensive mobile layout was built.
- The seller dashboard (PRD-03) and admin dashboard (PRD-06) will need mobile considerations too.

The PRD-v2 explicitly listed **"Mobile layout? Vertical stack?"** as an open question. It's time to answer it.

---

## 2. Solution Overview

Implement a **vertical stack layout for viewports < 768px**:

1. **Full-screen Chat** as the default mobile view (the primary interaction is conversational).
2. **Board as a secondary view** — accessible via a tab/toggle or swipe gesture.
3. **Vertical tile cards** — tiles stack vertically instead of horizontal scroll.
4. **Bottom navigation** — Chat / Board / Profile tabs.
5. **Touch-friendly interactions** — larger tap targets, swipe to dismiss, pull to refresh.

---

## 3. Scope

### In Scope
- Responsive breakpoint system (mobile < 768px, tablet 768–1024px, desktop > 1024px)
- Mobile chat view (full-width, sticky input at bottom)
- Mobile board view (vertical tile list, collapsible rows)
- Bottom tab navigation (Chat / Board)
- Touch-friendly tile interactions (tap to expand, swipe to like)
- Mobile-optimized RequestTile and OfferTile variants
- Mobile quote form (`/quote/[token]`)
- Mobile share page (`/share/[token]`)

### Out of Scope
- Native mobile app (React Native / Flutter) — Phase 4+
- Offline support / PWA (Phase 4+)
- Mobile push notifications (Phase 4+)
- Mobile-specific animations beyond basic transitions

---

## 4. User Stories

**US-01:** As a mobile buyer, I want to chat with the agent in a full-screen view so I can type and read comfortably.

**US-02:** As a mobile buyer, I want to switch to my board to see search results without losing my chat context.

**US-03:** As a mobile buyer, I want to view tile details by tapping on a card so I can see product info and provenance.

**US-04:** As a mobile seller, I want to submit a quote via magic link on my phone so I can respond to RFPs from anywhere.

---

## 5. Acceptance Criteria

| ID | Criteria |
|----|----------|
| AC-01 | On viewports < 768px, the layout switches from side-by-side to full-screen tabbed views. |
| AC-02 | Chat view is full-width with the input fixed at the bottom of the viewport. |
| AC-03 | Board view shows rows as collapsible sections with tiles stacked vertically. |
| AC-04 | Bottom navigation shows Chat and Board tabs with active indicator. |
| AC-05 | Tapping an OfferTile on mobile opens the detail panel as a full-screen overlay (not side panel). |
| AC-06 | The quote form (`/quote/[token]`) is usable on mobile without horizontal scrolling. |
| AC-07 | The share page (`/share/[token]`) renders correctly on mobile. |
| AC-08 | All interactive elements have minimum 44x44px touch targets. |

---

## 6. Technical Design

### 6.1 Layout Strategy

**`page.tsx`** — Detect viewport and render accordingly:

```tsx
const isMobile = useMediaQuery('(max-width: 767px)');

if (isMobile) {
  return (
    <MobileLayout>
      {activeTab === 'chat' && <Chat />}
      {activeTab === 'board' && <ProcurementBoard mobile />}
      <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
    </MobileLayout>
  );
}

// Desktop layout (existing)
return (
  <main className="flex h-screen ...">
    <Chat />
    <Divider />
    <ProcurementBoard />
  </main>
);
```

### 6.2 Mobile Board Layout

```tsx
// Board.tsx — when mobile prop is true
<div className="flex flex-col gap-4 pb-20"> {/* pb-20 for bottom nav */}
  {rows.map(row => (
    <MobileRowCard key={row.id} row={row}>
      {/* Tiles stack vertically */}
      <div className="flex flex-col gap-3">
        {offers.map(offer => (
          <MobileOfferCard key={offer.bid_id} offer={offer} />
        ))}
      </div>
    </MobileRowCard>
  ))}
</div>
```

### 6.3 Mobile OfferTile

A compact card variant:
- **Width:** full-width of the mobile viewport (with padding)
- **Height:** auto (content-driven, not fixed 450px)
- **Layout:** horizontal — image left (80x80), info right
- **Actions:** Like/comment/share as icon row at bottom
- **Tap:** Opens full-screen TileDetailPanel

### 6.4 Bottom Navigation

```tsx
function BottomNav({ activeTab, onTabChange }) {
  return (
    <nav className="fixed bottom-0 inset-x-0 bg-white border-t h-14 flex z-50">
      <button
        className={cn("flex-1 flex flex-col items-center justify-center", activeTab === 'chat' && "text-agent-blurple")}
        onClick={() => onTabChange('chat')}
      >
        <MessageSquare size={20} />
        <span className="text-[10px]">Chat</span>
      </button>
      <button
        className={cn("flex-1 flex flex-col items-center justify-center", activeTab === 'board' && "text-agent-blurple")}
        onClick={() => onTabChange('board')}
      >
        <LayoutGrid size={20} />
        <span className="text-[10px]">Board</span>
      </button>
    </nav>
  );
}
```

### 6.5 Responsive Utilities

Add a `useMediaQuery` hook:

```typescript
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);
  return matches;
}
```

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Mobile usability score (Lighthouse) | ≥80 |
| All interactive elements ≥44px touch target | 100% |
| No horizontal scroll on mobile viewports | 100% of pages |
| Mobile bounce rate | <60% |

---

## 8. Implementation Checklist

- [ ] Add `useMediaQuery` hook to `utils/`
- [ ] Create `MobileLayout` wrapper component
- [ ] Create `BottomNav` component
- [ ] Create mobile-optimized `MobileOfferCard` component
- [ ] Create mobile-optimized `MobileRowCard` component
- [ ] Update `page.tsx` with responsive layout switching
- [ ] Update `TileDetailPanel` to render full-screen on mobile
- [ ] Update `Chat.tsx` for full-width mobile layout (sticky bottom input)
- [ ] Verify `/quote/[token]` on mobile viewports
- [ ] Verify `/share/[token]` on mobile viewports
- [ ] Add responsive Tailwind classes throughout existing components
- [ ] Test on iOS Safari and Android Chrome
- [ ] Run Lighthouse mobile audit
