# Server-Driven UI (SDUI) Schema Specification (v0)

**Document Status:** Draft
**Date:** March 2026
**Context:** This document is the single source of truth and binding contract for the Shopping Agent SDUI implementation across the Frontend, Backend, and LLM evaluation harness.

---

## 1. Top-Level Schema Structure (`ui_schema`)

Every `ui_schema` JSON object stored in the database must conform to this structure:

```typescript
type UISchema = {
  version: number;          // Must be 1 for v0/v1 launch
  layout: LayoutToken;      // Determines the structural container
  value_vector?: string;    // Data contract for the primary value axis
  value_rationale_refs?: string[]; // IDs pointing to the provenance of the value claim
  blocks: UIBlock[];        // Array of primitives (max: 8)
}
```

---

## 2. Layout Tokens (Enum)

**Core value prop: friction-free comparison shopping.** Every Row is a comparison — the user asked for something, the system found options. The layout token determines how those options are presented given the available data.

- `ROW_COMPACT`: Dense summary when options lack images (grocery text results, quick items). Still shows price comparison across bids.
- `ROW_MEDIA_LEFT`: Visual comparison when bids have product images. Image + price + badges per option.
- `ROW_TIMELINE`: Progress view for active deals/services where the comparison phase is over and the user is tracking fulfillment.

---

## 3. The "Lego" Component Registry (v0)

The deterministic schema builder may **only** select blocks from this exact registry.
*Note: Legacy complex components like "DealCard", "TipJar", or "ComparisonTable" are not primitives; they are composite patterns built by stacking these v0 primitives.*

### Display Primitives
1. `ProductImage`: `url` (string), `alt` (string)
2. `PriceBlock`: `amount` (number), `currency` (string), `label` (string, e.g., "Total", "Unit Price")
3. `DataGrid`: `items` (Array of `{ key: string, value: string }`). Replaces ComparisonTable.
4. `FeatureList`: `features` (Array of string)
5. `BadgeList`: `tags` (Array of string). Supports `source_refs` for provenance.
6. `MarkdownText`: `content` (string). Max length: 500 chars.

### Interactive Primitives
7. `Timeline`: `steps` (Array of `{ label: string, status: 'pending' | 'active' | 'done' }`)
8. `MessageList`: `messages` (Array of `{ sender: string, text: string }`)
9. `ChoiceFactorForm`: Maps directly to backend `factors` array.
10. `ActionRow`: `actions` (Array of `ActionObject`). 

### State-Driven Post-Purchase Primitives
*The builder includes these based on row/bid status, but the backend state machine enforces visibility.*
11. `ReceiptUploader`: `campaign_id` (string)
12. `WalletLedger`: (Reads directly from user state)
13. `EscrowStatus`: `deal_id` (string)

---

## 4. Strict Action Intents & Server URL Ownership

### 4.1 Affiliate & Outbound Links
The builder **does not** embed final tracking URLs in the schema, as these expire. 
- Schema contains: `{ "intent": "outbound_affiliate", "bid_id": "uuid-1234", "url": "https://raw-merchant-link.com/..." }`
- Frontend renders: `<a href="/api/out?bid_id=uuid-1234&url=encoded_url">`
- Backend (`/api/out`) handles the click, logs the analytics against the specific `Bid`, constructs the final live affiliate URL (appending `?tag=...`), and returns a 302 redirect.

**The `ActionObject` Contract:**
```typescript
type ActionObject = {
  label: string;
  intent: 'outbound_affiliate' | 'claim_swap' | 'fund_escrow' | 'send_tip' | 'contact_vendor' | 'view_all_bids' | 'view_raw' | 'edit_request';
  bid_id?: string;       // Required for outbound_affiliate to track exact click-throughs
  url?: string;          // The raw (non-affiliate) destination URL
  merchant_id?: string;  // E.g., 'amazon', 'ebay'
  product_id?: string;   // The raw ASIN or SKU
  amount?: number;       // For tips/escrow
  count?: number;        // For view_all_bids
}
```
*Backend Resolution:* If `intent === 'outbound_affiliate'`, the backend reads the `merchant_id`, verifies it against the server allowlist, appends the server-managed tracking parameters to the base URL, and serves the clean URL to the frontend.

---

## 5. Value Vector & Provenance Contract

"Best Value" is defined as a strict data contract, not a loose principle.
- **Value Vectors:** `"unit_price" | "safety" | "speed" | "reliability" | "durability"`
- **Provenance (`source_refs`):** Any block that implies a claim (like a `BadgeList` tag of "Safest Jet") must include an array of `source_refs` (UUIDs) pointing to the source data in the backend. 
- **UI Behavior:** The frontend uses `source_refs` to render a clickable "Why we're saying this" tooltip.

---

## 6. Schema Levels, Precedence & Generation Timing

### Three Schema Levels

| Level | Model | Purpose | When Generated |
|---|---|---|---|
| **Project** | `Project.ui_schema` | List-level UI: tip jar, savings stats, list actions, onboarding prompts | On project load; regenerated on status changes (e.g., after a purchase, after first item added) |
| **Row** | `Row.ui_schema` | Comparison view for a single request — the core experience | After sourcing completes (or on row creation for skeleton); regenerated on bid changes / status transitions |
| **Bid** | `Bid.ui_schema` | Detail view for a specific option — specs, full description, vendor messages | **Lazy: generated on-expand only.** Not pre-generated for every bid. |

### Precedence Rules

To prevent UI whiplash, schema resolution follows strict precedence:

1. **List Header:** Render `Project.ui_schema` above all rows. This is where global actions live (tip jar, list stats, share link).
2. **List Feed / Row Summary:** Render `Row.ui_schema` for each row. This is the comparison view.
3. **Expanded Option Detail:** When the user taps a specific bid:
   - Request `Bid.ui_schema` from the server (lazy hydration).
   - If the bid schema is not yet generated, the server hydrates it on-demand using the Row's `ui_hint` as a base, enriched with bid-specific data.
   - If hydration fails, fall back to `Row.ui_schema` with the bid's data injected into the existing blocks.

### Why Lazy Bid Schemas?

Most users in a comparison flow will either click through to the merchant site directly from the row view or expand 1-2 options at most. Pre-generating schemas for 10-50 bids per row is wasted work. Lazy generation keeps the hot path fast (row-level comparison) and defers detail-view hydration to the moment the user actually needs it (~50-100ms, no LLM call).

### Project-Level Schema (`ui_hint` for Lists)

The LLM can output a `project_ui_hint` alongside `ui_hint` when the context warrants list-level UI changes:

```typescript
type ProjectUIHint = {
  blocks: BlockType[];  // From v0 registry — typically ActionRow, BadgeList, MarkdownText
}
```

Examples of when the builder regenerates `Project.ui_schema`:
- **First item added:** Show onboarding tips (`MarkdownText` + `ActionRow` with "Share this list")
- **After a purchase:** Show tip jar (`ActionRow` with `intent: 'send_tip'`) + savings summary (`BadgeList`)
- **List shared with household member:** Show collaboration status (`BadgeList` with member names)

If `project_ui_hint` is missing, the builder uses a static default (list title + "Share" action).

---

## 7. Schema Limits & Unknown Block Behavior

### Validation Limits (Zod & Pydantic)
- Max blocks per row: **8**
- Max text length per `MarkdownText` block: **500 characters**
- Max items in a `DataGrid`: **12**
- Max actions in an `ActionRow`: **3**
- **Row Cardinality Limit:** The Row-level schema hydrates data for a **maximum of 5 bids**. If more exist, the builder appends a "View All (X)" action. This keeps the Row JSON payload <5KB.

### Unknown Block & Zero Results Behavior
The deterministic builder cannot produce unknown block types. This guard exists as defense-in-depth for future LLM-generated schemas (Phase 3+):
- **Dev Environment:** Render a highly visible debug stub: `[Unsupported block: {type} (vX)]`
- **Prod Environment:** The backend normalizer strips the unknown block before persistence. If stripping it violates the "Minimum Viable Row" requirement, the entire schema is rejected and replaced with the Fallback Schema.

**Zero Results Fallback:** If sourcing completes with 0 bids, the builder emits a `ROW_COMPACT` layout with a `MarkdownText` block ("No options found") and an `ActionRow` to edit the request.

### Minimum Viable Row (Fallback)
If schema generation fails or is rejected by Zod, the server guarantees this fallback:
```json
{
  "version": 1,
  "layout": "ROW_COMPACT",
  "blocks": [
    { "type": "MarkdownText", "content": "**{row.title}**" },
    { "type": "BadgeList", "tags": ["{row.status}"] },
    { "type": "ActionRow", "actions": [{"label": "View Raw Options", "intent": "view_raw"}] }
  ]
}
```

---

## 8. Schema Generation Strategy (LLM Selects, Builder Hydrates)

### Decision

Schema generation is split into two responsibilities:

1. **The LLM selects the blueprint.** As part of its existing decision call, the LLM outputs a lightweight `ui_hint` — just a layout token and an ordered list of block types from the v0 registry. This is the "generative" part: the LLM reasons about what UI is appropriate for *any* request, including novel ones we haven't pre-coded templates for.

2. **The builder hydrates with data.** A server-side function `hydrate_ui_schema(ui_hint, row, bids)` takes the LLM's blueprint and fills in every field value from structured data (prices, images, URLs, badges, statuses). The LLM **never** populates field values — no hallucinated prices, no broken URLs, no fabricated images.

**There is no `desire_tier` or `intent.category` field.** The LLM does not classify requests into tiers. It directly selects the UI primitives that best serve comparison shopping for the specific request.

### The `ui_hint` Contract

The LLM includes this in its decision response (alongside `message`, `intent`, `action`):

```typescript
type UIHint = {
  layout: LayoutToken;                  // One of: ROW_COMPACT, ROW_MEDIA_LEFT, ROW_TIMELINE
  blocks: BlockType[];                  // Ordered list from v0 registry (max: 8)
  value_vector?: string;                // Optional: what "best value" means for this request
}
```

Example LLM output for "organic free-range eggs":
```json
{
  "ui_hint": {
    "layout": "ROW_MEDIA_LEFT",
    "blocks": ["ProductImage", "PriceBlock", "BadgeList", "ActionRow"],
    "value_vector": "unit_price"
  }
}
```

Example for "charter a jet SAN → ASE for 4 passengers":
```json
{
  "ui_hint": {
    "layout": "ROW_TIMELINE",
    "blocks": ["DataGrid", "BadgeList", "Timeline", "ActionRow"],
    "value_vector": "safety"
  }
}
```

Example for "birthday party for 12 kids at a trampoline park":
```json
{
  "ui_hint": {
    "layout": "ROW_MEDIA_LEFT",
    "blocks": ["ProductImage", "DataGrid", "PriceBlock", "FeatureList", "ActionRow"]
  }
}
```

### The Builder (`hydrate_ui_schema`)

```python
def hydrate_ui_schema(ui_hint: UIHint, row: Row, bids: list[Bid]) -> UISchema:
    schema = UISchema(
        version=1,
        layout=ui_hint.layout,
        value_vector=ui_hint.value_vector,
        blocks=[]
    )
    for block_type in ui_hint.blocks:
        block = hydrate_block(block_type, row, bids)
        if block:  # skip if no data available for this block type
            schema.blocks.append(block)
    return validate(schema)  # Pydantic validation as safety net
```

The builder is a pure function — testable, fast (<1ms), and guaranteed to produce valid field values.

### Fallback: Deterministic Layout Derivation

If the LLM omits `ui_hint`, returns an invalid one, or the hint fails validation, the system falls back to a deterministic layout selector. This is the **safety net**, not the primary path.

```python
def derive_layout_fallback(row: Row, bids: list[Bid]) -> UIHint:
    """Last resort when LLM ui_hint is missing or invalid."""
    if row.status in ("funded", "in_progress", "shipped", "delivered"):
        return UIHint(layout="ROW_TIMELINE", blocks=["MarkdownText", "Timeline", "ActionRow"])

    if any(b.image_url for b in bids):
        return UIHint(layout="ROW_MEDIA_LEFT", blocks=["ProductImage", "PriceBlock", "BadgeList", "ActionRow"])

    return UIHint(layout="ROW_COMPACT", blocks=["MarkdownText", "PriceBlock", "ActionRow"])
```

### Why This Split Works

- **Truly generative.** The LLM can reason about novel request types (birthday parties, pet grooming, car repairs) without us pre-coding a template for each.
- **Data safety.** Field values always come from structured data — no hallucinated prices, URLs, or images.
- **Low token overhead.** `ui_hint` is ~30 tokens added to the existing decision response. No second LLM call needed.
- **Graceful degradation.** If the LLM fails to produce a hint, the deterministic fallback ensures the UI never breaks.
- **No classification labels.** The LLM selects primitives directly — no intermediate `desire_tier` or `intent.category` that can drift.

### Search Routing (Context-Derived)

Search routing remains purely data-driven — no LLM involvement needed:

```python
def should_skip_web_search(row: Row) -> bool:
    if row.service_type:
        return True
    budget = _extract_budget(row.choice_answers)
    if budget and budget > 100_000:
        return True
    return False
```

---

## 9. Real-Time Schema Update Lifecycle

### Principle

**`ui_schema` is a derived output of `f(Row, Bids, UserState)`, never locally mutated by the frontend.** When any input changes, the server regenerates the full schema and pushes it.

### Update Events (via existing SSE stream)

New SSE event type: `ui_schema_updated`

```typescript
// SSE payload
{
  event: "ui_schema_updated",
  data: {
    entity_type: "project" | "row",
    entity_id: number,
    schema: UISchema,       // Full replacement, not a patch
    version: number,
    trigger: string         // Why the schema changed (for observability)
  }
}
```

*Note: SSE is for real-time pushes only. On page load or reconnect, the frontend fetches the current persisted state via standard GET requests. It does not rely on SSE to backfill missed events.*

### Lifecycle Sequence

```
① Row Created (no bids yet)
   → hydrate_ui_schema(ui_hint, row, bids=[])
   → Skeleton schema: MarkdownText(title) + BadgeList(["Searching…"])
   → Persisted as `ui_schema_version = 1`
   → SSE: ui_schema_updated { trigger: "row_created" }

② Search Batches Arrive (streaming)
   → Do NOT regenerate per batch (causes UI whiplash)
   → Wait for more_incoming: false

③ All Providers Complete
   → hydrate_ui_schema(ui_hint, row, top_5_bids)
   → Replaced in-place: `ui_schema_version = 2`
   → SSE: ui_schema_updated { trigger: "search_complete" }

④ User Answers Choice Factor
   → Backend filters/re-ranks bids, rebuilds schema
   → SSE: ui_schema_updated { trigger: "choice_factor_updated" }

⑤ Status Transition (e.g., swap claimed, escrow funded)
   → Backend rebuilds with state-driven blocks (ReceiptUploader, EscrowStatus)
   → SSE: ui_schema_updated { trigger: "status_transition" }
```

### Frontend Behavior

- **On `ui_schema_updated`:** Replace the row's schema in the Zustand store. Re-render via `DynamicRenderer`.
- **Between updates:** Show the last-known schema. Never locally mutate it.
- **Optimistic UX:** While waiting for a schema update after user action, the frontend MAY show a shimmer/loading overlay on the affected row, but MUST NOT speculatively edit the schema.
- **Stale schema safety:** If no `ui_schema_updated` arrives within 10s of a triggering action, the frontend falls back to `MinimumViableRow`.
