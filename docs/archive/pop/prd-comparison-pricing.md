# PRD: Cross-Retailer Comparison Pricing with Unit Normalization

## Business Outcome
- Measurable impact: Users can make apples-to-apples price comparisons across retailers using standardized unit pricing ($/oz, $/ct, $/sheet, $/fl oz, etc.) — the same way Costco price tags break down every product.
- Success criteria: Every grocery list item shows total price AND unit price from multiple retailers, enabling users to spot the real deal — not just the cheapest sticker price.
- Target users: Budget-conscious shoppers who want to compare across Kroger, Amazon, Walmart, and other sources before committing.

## Problem Statement

Today, Pop shows a flat `savings_cents` value on swap offers ("Save $2.50") without any context:
- Users can't see the **original item's price** at their local store
- Users can't see the **swap item's price** side-by-side
- Users can't compare the **same item across retailers**
- A "12-pack for $8.99" looks cheaper than a "24-pack for $14.99" until you do the math — Pop should do that math

Without unit-price normalization, savings claims are hollow. A $2.50 coupon on a $15 product is different from $2.50 off a $4 product. Users need the full picture.

## Scope
- In-scope: Unit-price extraction, normalization engine, cross-retailer price comparison per list item, comparison display model, LLM-assisted size parsing for unstructured data.
- Out-of-scope: Historical price tracking ("was $X last week"), price alerts/notifications, multi-store trip optimization ("buy milk at Kroger, eggs at Walmart"), loyalty card integration.

## Core Concept: Costco-Style Unit Pricing

Every product in a comparison gets normalized to a **canonical unit**:

| Category | Canonical Unit | Examples |
|----------|---------------|----------|
| Liquids | $/fl oz | Milk, juice, soda, cooking oil, shampoo |
| Dry goods by weight | $/oz | Coffee, rice, cereal, flour, sugar, chips |
| Counted items | $/ct | Eggs, diapers, trash bags, K-cups, batteries |
| Sheet goods | $/sheet | Toilet paper, paper towels, dryer sheets |
| Produce by weight | $/lb | Apples, chicken, beef, potatoes |
| Capsules/tablets | $/ct | Vitamins, medicine, detergent pods |

The LLM selects the canonical unit for each product category. There is no hardcoded category-to-unit mapping — the LLM decides what normalization makes sense for each item based on context.

## User Flow

1. User adds "toilet paper" to their shopping list via Pop chat.
2. Pop enriches via Kroger MCP (local store pricing) + searches Amazon (Rainforest) + other enabled providers.
3. **Unit Price Engine** extracts size/quantity from each result and computes unit price:
   - Kroger: Charmin Ultra Soft 12 Mega Rolls (312 sheets/roll) — $15.99 → **$0.004/sheet**
   - Amazon: Charmin Ultra Soft 24 Mega Rolls — $27.49 → **$0.004/sheet**
   - Kroger: Angel Soft 12 Double Rolls (214 sheets/roll) — $7.99 → **$0.003/sheet**
4. Pop displays the comparison:
   ```
   🧻 Toilet Paper
   ┌──────────────────────────────────────────────┐
   │ Angel Soft 12 Double Rolls        Kroger     │
   │ $7.99  ·  $0.003/sheet  ·  BEST VALUE        │
   ├──────────────────────────────────────────────┤
   │ Charmin Ultra Soft 12 Mega Rolls  Kroger     │
   │ $15.99  ·  $0.004/sheet                      │
   ├──────────────────────────────────────────────┤
   │ Charmin Ultra Soft 24 Mega Rolls  Amazon     │
   │ $27.49  ·  $0.004/sheet  ·  bulk deal        │
   └──────────────────────────────────────────────┘
   ```
5. If a PopSwap is available, it's inserted into the comparison with its unit price too — making the savings claim verifiable.

## Data Architecture

### Unit Price Extraction Pipeline

```
Product Result (from any provider)
       │
       ▼
┌─────────────────────────┐
│  Structured Size Check  │  ← Kroger: items[].size field ("10 oz", "24 ct")
│  (provider-specific)    │
└───────────┬─────────────┘
            │ if missing
            ▼
┌─────────────────────────┐
│  LLM Size Extraction    │  ← Parse from product title: "Folgers Classic 48oz" → 48 oz
│  (batch, cached)        │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Unit Normalizer        │  ← Convert to canonical form: 48 oz @ $12.99 → $0.27/oz
│                         │
└───────────┬─────────────┘
            │
            ▼
  UnitPrice { amount_cents, unit, quantity, canonical_unit_price_cents }
```

### Provider Data Availability

| Provider | Structured Size Field | Size in Title | Price | Promo Price |
|----------|----------------------|---------------|-------|-------------|
| **Kroger** | ✅ `items[].size` (e.g., "10 oz") | ✅ Usually in description | ✅ `regular` | ✅ `promo` |
| **Rainforest/Amazon** | ❌ Not in search results | ✅ Almost always in title | ✅ | ❌ |
| **eBay** | ❌ | ⚠️ Sometimes in title | ✅ | ❌ |
| **Google CSE** | ❌ | ⚠️ Sometimes | ⚠️ | ❌ |

### New Fields

**On `SearchResult` (sourcing layer):**
```python
class SearchResult(BaseModel):
    # ... existing fields ...
    size_raw: Optional[str] = None        # Raw size text from provider: "10 oz", "24 ct"
    size_quantity: Optional[float] = None  # Parsed numeric quantity: 10.0, 24.0
    size_unit: Optional[str] = None        # Parsed unit: "oz", "ct", "sheet", "fl_oz", "lb"
    unit_price_cents: Optional[int] = None # Computed: price / quantity in cents
    canonical_unit: Optional[str] = None   # Display unit: "$/oz", "$/ct", "$/sheet"
```

**On `Bid` model (persisted):**
```python
# New nullable columns
size_raw: Optional[str] = None
size_quantity: Optional[float] = None
size_unit: Optional[str] = None
unit_price_cents: Optional[int] = None
canonical_unit: Optional[str] = None
```

**On `PopSwap` model (swap offers):**
```python
# New nullable columns
swap_size_raw: Optional[str] = None
swap_size_quantity: Optional[float] = None
swap_size_unit: Optional[str] = None
swap_unit_price_cents: Optional[int] = None
swap_canonical_unit: Optional[str] = None
target_price_cents: Optional[int] = None      # Original product's price (for comparison)
target_unit_price_cents: Optional[int] = None  # Original product's unit price
```

## LLM Size Extraction

When a provider doesn't return structured size data (Amazon, eBay, Google), the LLM parses size from the product title. This is done as a **batch call** — all results for a single list item are sent in one LLM request to amortize cost.

**Example LLM prompt:**
```
For each product below, extract the size/quantity information and determine the appropriate unit for price comparison.

Products:
1. "Folgers Classic Roast Ground Coffee, 48 Ounce" — $12.99
2. "Maxwell House Original Roast Ground Coffee 30.6 oz Canister" — $8.47
3. "Starbucks Medium Roast K-Cup Pods 72 Count" — $38.99

For each, return:
- quantity: numeric value
- unit: oz, fl_oz, ct, lb, sheet, g, ml, etc.
- canonical_unit: the best unit for comparing these products (all should use the same unit if possible)
```

**Key rules:**
- The LLM decides the canonical unit — no hardcoded mapping
- If products in the same category use different units (oz vs ct for coffee), the LLM picks the most meaningful comparison unit and flags items that can't be compared
- Results are cached per product title hash to avoid re-parsing

## Business Requirements

### Authentication & Authorization
- Comparison pricing is visible to all users (authenticated or anonymous).
- No new auth gates — this enriches existing list item data.

### Monitoring & Visibility
- Track unit-price extraction success rate by provider (Kroger structured vs LLM-parsed).
- Track LLM extraction accuracy (manual spot-check cadence TBD).
- Surface comparison coverage gaps (items where no unit price could be determined).

### Billing & Entitlements
- LLM extraction adds cost (~1 batch call per list item per search). Monitor token usage.
- Consider caching aggressively — the same product title always yields the same size extraction.

### Data Requirements
- Persist extracted unit-price data on Bid rows for display without re-computation.
- Persist on PopSwap for swap comparison context.
- Retain raw size text for audit and extraction debugging.

### Performance Expectations
- Kroger structured extraction: <1ms (string parse).
- LLM batch extraction: <2s for up to 20 products (single call, cached).
- Unit price computation: negligible (division).
- Total added latency to search flow: <2s (LLM extraction runs in parallel with scoring).

### UX & Accessibility
- Unit price displayed in a consistent format: `$X.XX/unit` (e.g., "$0.27/oz").
- "BEST VALUE" badge on the lowest unit-price option per list item.
- Comparison view must be accessible (screen reader announces unit price, retailer, total price).
- When products can't be meaningfully compared (different units), show total price only with a note.

### Privacy, Security & Compliance
- No user data exposed to LLM during size extraction (only product titles + prices).
- Comparison data is derived from public product listings — no privacy concerns.
- Unit-price calculations must be auditable (raw inputs preserved).

## Dependencies
- Upstream: `prd-shared-list-collaboration.md` (list items exist), `prd-swap-discovery-and-claiming.md` (swaps exist to compare against).
- Downstream: Future "price alerts" or "trip optimizer" features would build on unit-price data.
- External: Kroger API (size field), Rainforest API (title parsing), LLM provider (Gemini for extraction).

## Risks & Mitigations
- **LLM extraction errors** (e.g., "12 oz" parsed as "12 ct"): Mitigation — cache and spot-check; structured provider data preferred when available.
- **Incomparable units** (K-cups vs ground coffee oz): Mitigation — LLM flags when comparison is not meaningful; UI shows "can't compare" gracefully.
- **Missing size data** (some products have no size info anywhere): Mitigation — show total price only, no unit price badge.
- **Price staleness** (Amazon price changes hourly): Mitigation — unit prices are computed at search time, not cached indefinitely. Display "as of" timestamp.

## Acceptance Criteria (Business Validation)
- [ ] A list item with Kroger + Amazon results shows unit prices from both retailers side-by-side.
- [ ] Unit prices use the correct canonical unit for the product category (LLM-determined, not hardcoded).
- [ ] "BEST VALUE" badge appears on the lowest unit-price option.
- [ ] PopSwap offers show unit-price comparison against the original product.
- [ ] Products where size can't be determined show total price only (no broken/zero unit prices).
- [ ] Unit-price extraction success rate >90% for Kroger (structured), >80% for Amazon (LLM-parsed).

## Traceability
- Parent PRD: `docs/prd/bob-shopping-agent/parent.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`

---

**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
