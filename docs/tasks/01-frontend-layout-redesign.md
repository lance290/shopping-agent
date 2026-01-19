# Task 01: Frontend Layout Redesign

**Priority:** P0  
**Estimated Time:** 2 days  
**Dependencies:** None  
**Outcome:** Deployable UX for initial user feedback

---

## Objective

Transform the current 3-pane layout into the PRD-specified 2-pane layout:
- **Left (1/3):** Chat with agent
- **Right (2/3):** Rows of tiles (each row = one procurement task)

---

## Current State

```
[RequestsSidebar 320px] [Chat 1/3] [Board 2/3 grid]
```

**Problems:**
- Sidebar shows a list of "Requests" — wrong paradigm
- Board is a flat grid of products, not rows
- No "Request Tile" (first tile showing what user wants)
- Chat component is monolithic (398 lines) with regex parsing

---

## Target State

```
[Chat Pane 1/3] [Rows Pane 2/3]
                 ┌─────────────────────────────────────┐
                 │ Row 1: "blue hoodie under $50"      │
                 │ [RFP Tile] [Offer1] [Offer2] [...]  │
                 ├─────────────────────────────────────┤
                 │ Row 2: "Montana State shirt XXL"    │
                 │ [RFP Tile] [Offer1] [Offer2] [...]  │
                 └─────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1.1: Remove RequestsSidebar from Main Layout

**File:** `apps/frontend/app/page.tsx`

```tsx
// FROM:
<main className="flex h-screen w-full bg-white overflow-hidden">
  <RequestsSidebar />
  <Chat />
  <ProcurementBoard />
</main>

// TO:
<main className="flex h-screen w-full bg-white overflow-hidden">
  <Chat />
  <ProcurementBoard />
</main>
```

- [ ] Remove `RequestsSidebar` import
- [ ] Update layout to 2-pane (Chat 1/3, Board 2/3)
- [ ] Verify responsive behavior

**Test:** Visual inspection, no console errors

---

### Step 1.2: Create RowStrip Component

**New File:** `apps/frontend/app/components/RowStrip.tsx`

```tsx
interface RowStripProps {
  row: Row;
  offers: Offer[];
  isActive: boolean;
  onSelect: () => void;
}

export default function RowStrip({ row, offers, isActive, onSelect }: RowStripProps) {
  return (
    <div 
      className={`border rounded-lg p-3 mb-3 ${isActive ? 'ring-2 ring-blue-500' : ''}`}
      onClick={onSelect}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="font-medium">{row.title}</span>
        <span className="text-xs px-2 py-0.5 rounded bg-gray-100">{row.status}</span>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-2">
        <RequestTile row={row} />
        {offers.map((offer, idx) => (
          <OfferTile key={idx} offer={offer} index={idx} rowId={row.id} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] Create component file
- [ ] Horizontal scrolling for many offers
- [ ] Visual distinction for active row
- [ ] Click to select row (sets context for chat)

**Test:** Renders row with tiles, scrolls horizontally

---

### Step 1.3: Create RequestTile Component

**New File:** `apps/frontend/app/components/RequestTile.tsx`

This is the leftmost tile in each row showing what the user is looking for.

```tsx
interface RequestTileProps {
  row: Row;
}

export default function RequestTile({ row }: RequestTileProps) {
  return (
    <div className="min-w-[180px] bg-blue-50 border-2 border-blue-200 rounded-lg p-3 flex-shrink-0">
      <div className="text-xs text-blue-600 font-medium mb-1">LOOKING FOR</div>
      <div className="font-medium text-sm">{row.title}</div>
      {row.budget_max && (
        <div className="text-xs text-gray-500 mt-1">
          Budget: up to {row.currency} {row.budget_max}
        </div>
      )}
      <div className="text-xs text-gray-400 mt-2">
        {/* Future: show choice factors here */}
        Click to refine
      </div>
    </div>
  );
}
```

- [ ] Create component file
- [ ] Show row title and budget
- [ ] Placeholder for choice factors (Task 05)
- [ ] Distinct styling from offer tiles

**Test:** Renders correctly with row data

---

### Step 1.4: Create OfferTile Component

**New File:** `apps/frontend/app/components/OfferTile.tsx`

Replaces the inline product card in current `Board.tsx`.

```tsx
interface OfferTileProps {
  offer: Offer;
  index: number;
  rowId: number;
}

export default function OfferTile({ offer, index, rowId }: OfferTileProps) {
  // Build clickout URL (Task 02 will make this real)
  const clickUrl = `/api/out?url=${encodeURIComponent(offer.url)}&row_id=${rowId}&idx=${index}&source=${offer.source}`;
  
  return (
    <a
      href={clickUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="min-w-[160px] max-w-[180px] bg-white border rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-400 transition-all flex-shrink-0"
    >
      {offer.image_url && (
        <img 
          src={offer.image_url} 
          alt={offer.title}
          className="w-full h-24 object-cover"
        />
      )}
      <div className="p-2">
        <div className="text-xs font-medium line-clamp-2">{offer.title}</div>
        <div className="text-sm font-bold text-green-600 mt-1">
          {offer.currency} {offer.price}
        </div>
        <div className="text-xs text-gray-500">{offer.merchant}</div>
        {offer.rating && (
          <div className="text-xs text-yellow-600">★ {offer.rating}</div>
        )}
      </div>
    </a>
  );
}
```

- [ ] Create component file
- [ ] Image, title, price, merchant, rating
- [ ] Links to `/api/out` (will 404 until Task 02, but wiring is correct)
- [ ] Compact card design

**Test:** Renders offer data, link href is correct

---

### Step 1.5: Update Offer Interface in Store

**File:** `apps/frontend/app/store.ts`

```tsx
// Rename Product -> Offer to match PRD terminology
export interface Offer {
  title: string;
  price: number;
  currency: string;
  merchant: string;
  url: string;               // canonical URL (raw from provider)
  image_url: string | null;
  rating: number | null;
  reviews_count: number | null;
  shipping_info: string | null;
  source: string;
  // New fields for future (can be null for now):
  merchant_domain?: string;
  click_url?: string;        // Will be populated by backend in Task 02
  match_score?: number;
}

// Update all references from Product to Offer
```

- [ ] Rename `Product` to `Offer`
- [ ] Add optional future fields
- [ ] Update all type references in store
- [ ] Update imports in components

**Test:** TypeScript compiles, no type errors

---

### Step 1.6: Rewrite Board.tsx as RowsPane

**File:** `apps/frontend/app/components/Board.tsx` → rename or rewrite

```tsx
'use client';

import { useShoppingStore } from '../store';
import RowStrip from './RowStrip';

export default function RowsPane() {
  const rows = useShoppingStore(state => state.rows);
  const activeRowId = useShoppingStore(state => state.activeRowId);
  const rowResults = useShoppingStore(state => state.rowResults);
  const setActiveRowId = useShoppingStore(state => state.setActiveRowId);

  if (rows.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 text-gray-500">
        <div className="text-center">
          <p className="text-lg">No procurement tasks yet</p>
          <p className="text-sm mt-2">Start by telling the agent what you need</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-gray-50 p-4 overflow-y-auto">
      <div className="text-xs text-gray-500 mb-3 flex justify-between items-center">
        <span>We may earn a commission from qualifying purchases.</span>
        <span>{rows.length} active request{rows.length !== 1 ? 's' : ''}</span>
      </div>
      
      {rows.map(row => (
        <RowStrip
          key={row.id}
          row={row}
          offers={rowResults[row.id] || []}
          isActive={row.id === activeRowId}
          onSelect={() => setActiveRowId(row.id)}
        />
      ))}
    </div>
  );
}
```

- [ ] Rewrite as RowsPane (or rename file)
- [ ] Render RowStrip per row
- [ ] Add disclosure text at top
- [ ] Empty state message
- [ ] Update import in `page.tsx`

**Test:** Rows render with offers, disclosure visible

---

### Step 1.7: Simplify Chat.tsx

**File:** `apps/frontend/app/components/Chat.tsx`

Refactoring goals:
1. Remove regex parsing of stream (move to structured tool results)
2. Extract helper functions to separate utils
3. Add row selector in chat header (replaces sidebar)

```tsx
// Add to chat header:
<div className="p-4 border-b border-gray-200 bg-white shadow-sm">
  <h2 className="text-lg font-semibold flex items-center gap-2">
    <Bot className="w-5 h-5 text-blue-600" />
    Shopping Agent
  </h2>
  {activeRowId && (
    <div className="text-xs text-gray-500 mt-1">
      Active: Row #{activeRowId} — {rows.find(r => r.id === activeRowId)?.title}
    </div>
  )}
</div>
```

- [ ] Add active row indicator to header
- [ ] Extract `persistRowToDb`, `runSearch`, `createRowInDb`, `fetchRowsFromDb` to `utils/api.ts`
- [ ] Simplify stream parsing (or defer until BFF sends structured events)
- [ ] Remove unused sidebar-related code

**Test:** Chat still works, creates rows, triggers searches

---

### Step 1.8: Delete or Archive RequestsSidebar

**File:** `apps/frontend/app/components/RequestsSidebar.tsx`

- [ ] Delete file (or move to `components/_archive/`)
- [ ] Remove any imports

**Test:** App builds without sidebar

---

### Step 1.9: Update Tests

**Files:**
- `apps/frontend/app/tests/board-display.test.ts`
- `apps/frontend/app/tests/chat-board-sync.test.ts`
- `apps/frontend/app/tests/sidebar-interaction.test.ts`

- [ ] Update `board-display.test.ts` for new RowsPane structure
- [ ] Remove or update sidebar tests
- [ ] Add test for RowStrip rendering
- [ ] Add test for OfferTile clickout URL format

**Test:** `npm run test` passes

---

### Step 1.10: Deploy and Get Feedback

- [ ] Run full E2E test suite locally
- [ ] Commit changes with clear message
- [ ] Deploy to staging/production (Railway)
- [ ] Share with 2-3 users for feedback

**Test:** Production URL loads, core flows work

---

## Acceptance Criteria

- [ ] Layout is 2-pane: Chat (left 1/3) + Rows (right 2/3)
- [ ] Each row displays horizontally with Request Tile + Offer Tiles
- [ ] Clicking a row sets it as active (visible in chat header)
- [ ] Clicking an offer tile navigates to `/api/out?...` (will 404 until Task 02)
- [ ] Disclosure text visible: "We may earn a commission..."
- [ ] All existing tests pass (or are updated)
- [ ] Deployed to production

---

## Rollback Plan

If deployment fails:
1. Revert commit: `git revert HEAD`
2. Redeploy previous version
3. Document what broke

---

## Files Changed

| File | Action |
|------|--------|
| `apps/frontend/app/page.tsx` | Modify (remove sidebar) |
| `apps/frontend/app/store.ts` | Modify (Product → Offer) |
| `apps/frontend/app/components/Board.tsx` | Rewrite as RowsPane |
| `apps/frontend/app/components/Chat.tsx` | Simplify |
| `apps/frontend/app/components/RequestsSidebar.tsx` | Delete |
| `apps/frontend/app/components/RowStrip.tsx` | **New** |
| `apps/frontend/app/components/RequestTile.tsx` | **New** |
| `apps/frontend/app/components/OfferTile.tsx` | **New** |
| `apps/frontend/app/tests/*.ts` | Update |
