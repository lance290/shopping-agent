# PRD v2: Netflix-Style Procurement Board with Choice Factors

**Owner:** Product / Engineering  
**Status:** Draft  
**Version:** 2.0  
**Last updated:** 2026-01-09  
**Audience:** Product, Design, Engineering

---

## 1. Summary

Evolve the Shopping Agent from a simple search-and-display tool into an **intelligent procurement assistant** with a **Netflix-style horizontal row layout**. Each procurement request becomes its own row, with the request as the first tile and matching options flowing horizontally to the right.

**Key innovation:** The LLM doesn't just search—it first identifies **choice factors** (decision criteria) for what you're buying, asks clarifying questions, then uses those answers to find and rank options.

---

## 2. What's Changing from V1

| Aspect | V1 | V2 |
|--------|----|----|
| **Layout** | Sidebar cards + single product grid | Horizontal rows (Netflix-style) |
| **Request display** | Card in sidebar | First tile in row |
| **Results display** | Grid of products | Horizontal scroll of tiles per row |
| **Search behavior** | Direct product search | Choice factors → refined search |
| **LLM role** | Create row + search | Identify criteria, ask questions, find sellers |
| **User refinement** | Chat-based | Click request tile → answer choice factors |

---

## 3. Vision

**"Netflix for procurement"** — Each row is a category of thing you want to buy. The first tile tells you what you're looking for and helps you refine it. The tiles to the right are your options, ranked and comparable.

The LLM acts as a **procurement advisor**:
1. Understands what you want
2. Knows what questions to ask (choice factors)
3. Finds sellers/options that match
4. Presents them in a comparable format

---

## 4. UI Layout

### 4.1 Three-Column Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CHAT (Left)          │  PROCUREMENT BOARD (Center + Right)             │
│                       │                                                  │
│  [+ New Request]      │  ┌─────────┬─────────┬─────────┬─────────┬────  │
│                       │  │ REQUEST │ Option  │ Option  │ Option  │ ...  │
│  User: I need         │  │  TILE   │  Tile   │  Tile   │  Tile   │      │
│  Montana State        │  │         │         │         │         │      │
│  shirts               │  │ "Montana│ $24.99  │ $29.99  │ $19.99  │      │
│                       │  │  State  │ Target  │ Fanatics│ eBay    │      │
│  Agent: What size?    │  │  shirts"│         │         │         │      │
│  What color? Budget?  │  └─────────┴─────────┴─────────┴─────────┴────  │
│                       │                                                  │
│  User: XL, blue,      │  ┌─────────┬─────────┬─────────┬─────────┬────  │
│  under $50            │  │ REQUEST │ Option  │ Option  │ Option  │ ...  │
│                       │  │  TILE   │  Tile   │  Tile   │  Tile   │      │
│  [+ New Request]      │  │ "Blue   │ $45.00  │ $38.99  │ $42.00  │      │
│                       │  │  hoodies│ Nike    │ Champion│ Adidas  │      │
│                       │  │  XL"    │         │         │         │      │
│                       │  └─────────┴─────────┴─────────┴─────────┴────  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Request Tile (First Tile in Row)

The **Request Tile** is special — it's not a product, it's the **definition of what you're buying**.

**Contains:**
- Title/summary of request
- Status indicator (Searching, Found X options, etc.)
- Choice factors as clickable tags/chips
- "Refine" button to re-open choice factor questions

**On click:** Opens a panel/modal with:
- Choice factor questions (FAQ style)
- Current answers
- Ability to change answers → triggers re-search

### 4.3 Option Tiles (Results)

Each option tile shows:
- Product image
- Title (truncated)
- Price (prominent)
- Seller/merchant
- Key differentiators (shipping, rating, etc.)
- "Select" or "View Details" action

**Horizontal scroll:** User can scroll right to see more options. Lazy-load as needed.

### 4.4 + New Request Button

- Appears at **top and bottom** of the request list
- Clicking it:
  1. Creates a new empty row
  2. Resets/focuses the chat for the new request
  3. Chat prompts: "What are you looking for?"

---

## 5. Choice Factors Flow

### 5.1 What Are Choice Factors?

Choice factors are the **decision criteria** for a purchase. The LLM identifies these based on the product category.

**Example: "Montana State shirts"**
- Size (S, M, L, XL, XXL)
- Color (blue, gold, white, etc.)
- Style (t-shirt, long sleeve, hoodie, polo)
- Price range
- Condition (new, used)
- Shipping speed
- Seller type (official store, marketplace, local)

**Example: "Laptop for video editing"**
- Screen size
- RAM
- Storage type/size
- GPU
- Brand preference
- Budget
- New vs refurbished

### 5.2 LLM Tool: `getChoiceFactors`

```typescript
getChoiceFactors: {
  description: 'Identify the key decision criteria for a product category',
  input: { 
    query: string,  // "Montana State shirts"
    category?: string 
  },
  output: {
    factors: [
      { name: 'size', type: 'select', options: ['S', 'M', 'L', 'XL', 'XXL'] },
      { name: 'color', type: 'select', options: ['blue', 'gold', 'white'] },
      { name: 'style', type: 'select', options: ['t-shirt', 'long sleeve', 'hoodie'] },
      { name: 'max_price', type: 'number', label: 'Budget' },
      { name: 'condition', type: 'select', options: ['new', 'used', 'any'] },
    ]
  }
}
```

### 5.3 Flow

1. **User:** "I need Montana State shirts"
2. **LLM:** Calls `getChoiceFactors("Montana State shirts")`
3. **LLM → User:** "Great! A few questions to find the best options:
   - What size? (S/M/L/XL/XXL)
   - Preferred color? (blue/gold/white/any)
   - Style? (t-shirt/long sleeve/hoodie)
   - Budget?"
4. **User:** "XL, blue, long sleeve, under $50"
5. **LLM:** Calls `createRow` with title + choice factors as constraints
6. **LLM:** Calls `findSellers` or `searchListings` with constraints
7. **System:** Creates row, populates option tiles

### 5.4 Refining via Request Tile

When user clicks the Request Tile:
- Shows current choice factor answers
- User can change any answer
- On save → triggers `updateRow` + new search
- Option tiles refresh

---

## 6. LLM Tools (V2)

### 6.1 Existing (Keep)
- `createRow` - Create a new procurement row
- `updateRow` - Update row title/constraints
- `searchListings` - Search for products (row-scoped)

### 6.2 New Tools

#### `getChoiceFactors`
Identify decision criteria for a product category.

```typescript
{
  name: 'getChoiceFactors',
  description: 'Get the key decision factors for a product category to ask the user',
  input: { query: string },
  output: { factors: ChoiceFactor[] }
}
```

#### `findSellers`
Find potential sellers for a product with specific attributes.

```typescript
{
  name: 'findSellers',
  description: 'Find sellers who offer products matching the criteria',
  input: { 
    query: string,
    constraints: Record<string, string>,
    location?: string
  },
  output: { 
    sellers: Seller[],
    reasoning: string 
  }
}
```

#### `askChoiceQuestion`
Prompt user with a specific choice factor question.

```typescript
{
  name: 'askChoiceQuestion',
  description: 'Ask the user a specific question about their requirements',
  input: { 
    factor: string,
    options?: string[],
    currentValue?: string
  }
}
```

---

## 7. Data Model Changes

### 7.1 Row (Updated)

```typescript
interface Row {
  id: number;
  user_id: number;
  title: string;
  status: 'gathering_info' | 'searching' | 'has_options' | 'selected' | 'closed';
  
  // V2: Choice factors
  choice_factors: ChoiceFactor[];
  choice_answers: Record<string, string | number>;
  
  // Existing
  request_spec: RequestSpec;
  created_at: Date;
  updated_at: Date;
}

interface ChoiceFactor {
  name: string;
  label: string;
  type: 'select' | 'number' | 'text' | 'boolean';
  options?: string[];
  required: boolean;
}
```

### 7.2 Option (New - replaces simple Product)

```typescript
interface Option {
  id: number;
  row_id: number;
  
  // Product info
  title: string;
  price: number;
  currency: string;
  image_url: string | null;
  product_url: string;
  
  // Seller info
  seller_name: string;
  seller_type: 'marketplace' | 'retailer' | 'direct' | 'local';
  seller_rating?: number;
  
  // Logistics
  shipping_cost: number | null;
  shipping_speed: string | null;
  availability: string;
  
  // Comparison
  match_score: number;  // How well it matches choice factors
  highlights: string[]; // Key differentiators
  
  // Status
  status: 'available' | 'selected' | 'rejected';
  created_at: Date;
}
```

---

## 8. API Changes

### 8.1 New Endpoints

```
POST /rows/{row_id}/choice-factors
  - Set/update choice factors for a row

GET /rows/{row_id}/options
  - Get all options for a row

POST /rows/{row_id}/options/{option_id}/select
  - Mark an option as selected

POST /v1/llm/choice-factors
  - LLM endpoint to generate choice factors for a query
```

### 8.2 Updated Endpoints

```
GET /rows
  - Include choice_factors and choice_answers in response

PATCH /rows/{row_id}
  - Accept choice_answers updates
  - Trigger re-search when answers change
```

---

## 9. Frontend Components (V2)

### 9.1 New Components

| Component | Description |
|-----------|-------------|
| `ProcurementRow` | Horizontal row with request tile + option tiles |
| `RequestTile` | First tile showing request summary + choice factors |
| `OptionTile` | Product/seller option tile |
| `ChoiceFactorPanel` | Modal/panel for answering choice factor questions |
| `HorizontalScroll` | Scroll container for option tiles |
| `NewRequestButton` | + button to create new row |

### 9.2 Updated Components

| Component | Changes |
|-----------|---------|
| `Chat` | Add "New Request" flow, context-aware per row |
| `Board` | Replace grid with horizontal rows |
| `Sidebar` | Remove (requests now shown as first tile in rows) |

---

## 10. User Flows

### Flow A: New Request (Happy Path)

1. User clicks **[+ New Request]**
2. Chat resets, prompts "What are you looking for?"
3. User: "Montana State shirts"
4. LLM identifies choice factors, asks questions
5. User answers (size, color, budget, etc.)
6. Row created with Request Tile showing summary
7. LLM searches, Option Tiles populate to the right
8. User scrolls, compares, selects

### Flow B: Refine via Request Tile

1. User clicks Request Tile
2. Choice Factor Panel opens with current answers
3. User changes "color" from "blue" to "gold"
4. User saves
5. System re-searches with new constraints
6. Option Tiles refresh

### Flow C: Refine via Chat

1. User (with row selected): "Actually make it under $30"
2. LLM calls `updateRow` with new budget constraint
3. Option Tiles refresh with filtered results

### Flow D: Multiple Rows

1. User has Row 1: "Montana State shirts"
2. User clicks **[+ New Request]**
3. Chat resets for new context
4. User: "Also need a laptop bag"
5. Row 2 created below Row 1
6. Each row independent, scrollable

---

## 11. What Stays the Same

- **Authentication:** Same session-based auth with `sa_session` cookie
- **Chat UI:** Left panel, streaming responses
- **Search API:** Backend search endpoint (enhanced with choice factors)
- **User isolation:** All data scoped to authenticated user
- **Tech stack:** Next.js frontend, Fastify BFF, FastAPI backend, PostgreSQL

---

## 12. Migration Path

### Phase 1: UI Refactor
- Replace sidebar + grid with horizontal rows
- Request tile = current row card
- Option tiles = current product cards (horizontal)

### Phase 2: Choice Factors
- Add `getChoiceFactors` LLM tool
- Add choice factor storage to Row model
- Build Choice Factor Panel UI

### Phase 3: Enhanced Search
- Add `findSellers` tool
- Improve search with choice factor constraints
- Add match scoring to options

### Phase 4: Polish
- Animations for tile loading
- Keyboard navigation
- Mobile responsive

---

## 13. Success Metrics

| Metric | Target |
|--------|--------|
| Time to first options | < 10 seconds |
| Choice factor completion rate | > 80% |
| Options per row | ≥ 5 |
| User refinement rate | > 50% use choice factors |
| Row completion rate | > 30% select an option |

---

## 14. Open Questions

1. **How many choice factors per category?** Cap at 5-6 to avoid overwhelming user?
2. **Should choice factors be pre-defined or fully LLM-generated?** Hybrid approach?
3. **How to handle "no results" for strict constraints?** Suggest relaxing which factor?
4. **Mobile layout?** Vertical stack instead of horizontal scroll?
5. **Row ordering?** Most recent on top, or drag-to-reorder?

---

## 15. Example Interaction

```
[+ New Request]

User: I need Montana State shirts

Agent: Great! Let me help you find the perfect Montana State shirt. 
A few questions:

📏 What size do you need?
   [ S ] [ M ] [ L ] [ XL ] [ XXL ]

🎨 Preferred color?
   [ Blue ] [ Gold ] [ White ] [ Any ]

👕 Style?
   [ T-shirt ] [ Long sleeve ] [ Hoodie ] [ Polo ]

💰 Budget?
   [ Under $25 ] [ $25-50 ] [ $50-100 ] [ Any ]

User: XL, blue, long sleeve, under $50

Agent: Perfect! Searching for blue Montana State long sleeve shirts 
in XL under $50...

[Row appears with Request Tile + 6 Option Tiles scrolling right]

Request Tile:
┌─────────────────┐
│ Montana State   │
│ Long Sleeve     │
│ ────────────── │
│ Size: XL        │
│ Color: Blue     │
│ Budget: <$50    │
│ ────────────── │
│ 6 options found │
│ [Refine]        │
└─────────────────┘

Option Tiles: [Target $24.99] [Fanatics $34.99] [Amazon $29.99] ...
```

---

## Appendix: V1 → V2 Component Mapping

| V1 Component | V2 Equivalent |
|--------------|---------------|
| `RequestsSidebar` | Removed (merged into `ProcurementRow`) |
| `ProcurementBoard` (grid) | `ProcurementBoard` (horizontal rows) |
| Row card in sidebar | `RequestTile` (first tile in row) |
| Product card in grid | `OptionTile` (in horizontal scroll) |
| `Chat` | `Chat` (with new request flow) |
| `store.searchResults` | `store.rowOptions[rowId]` |
| `store.activeRowId` | `store.activeRowId` (same) |
