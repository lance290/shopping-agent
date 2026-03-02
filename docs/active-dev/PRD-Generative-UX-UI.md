# Generative UX/UI Architecture: The "Universal List" via Server-Driven UI (SDUI)

**Document Status:** Draft
**Date:** March 2026
**Context:** Synthesis of BuyAnything's high-ticket marketplace with PopSavings' grocery-focused viral loop, powered by a truly Generative UI.

---

## 1. The Core Paradigm Shift

We are moving away from the "Netflix-style" horizontal rows of product tiles (BuyAnything V2) and standardizing entirely on a dead-simple, mobile-first **Chat + Shared List** interface. 

The value prop is **friction-free comparison shopping**. The user says what they want; the system finds options across retailers and sources; the UI makes comparing and choosing effortless. No tab switching, no manual price-checking, no hunting for coupons.

The magic lies in **Server-Driven UI (SDUI)**. To the user, everything is just an item on a list. But under the hood, the UI dynamically morphs based on a JSON blueprint — the LLM selects which UI primitives to show and in what order, and a server-side builder hydrates those primitives with real data from the Row and its Bids.

We **do not hardcode** "grocery UI" or "flight UI". We **do not classify** requests into tiers or categories. Instead, the LLM reasons about each request and picks the right combination of atomic UI primitives (Legos) from a bounded registry. A builder then fills in the actual field values (prices, images, URLs) from structured data — the LLM never touches those.

---

## 2. UX Principles: The "Zero-Shame" Universal Interface

Our user base now spans the widest possible economic spectrum: from **distressed families** optimizing grocery budgets to **Ultra-High-Net-Worth (UHNW) individuals** chartering yachts. 

To serve both without alienation, the UI must adhere to these principles:
1. **Zero-Shame UX:** Buying a $25 Roblox gift card or a gallon of milk must feel exactly as clean and premium as requesting a $25M yacht. The interface does not judge or segregate based on price.
2. **"Best Value", Not Just "Lowest Price":** The LLM must contextualize "value". For groceries, value = lowest unit price ($/oz). For private aviation, value = safety ratings, newer aircraft, and lack of repositioning fees. The UI schema must highlight the *correct* value vector.
3. **Trust & Confidentiality by Default:** UHNW users need EA/Principal privacy and vendor NDA masking. Budget-conscious users need transparency on payout mechanics and data usage. The UI must radiate security at all times.

---

## 3. Layout, Navigation & Delegation

### 3.1 The Two-Pane View
- **Desktop:** Split screen. Chat on the left, Active List on the right.
- **Mobile:** Two distinct tabs (Chat | List) with bottom navigation.

### 3.2 Lists of Lists (`Projects`) & Collaboration
Users can maintain multiple lists (e.g., "Default Groceries", "Aspen Trip", "Office Supplies"). 
- **The "Default Groceries" list** is the sticky default that everyone uses daily.
- **Multi-User Dynamics:** Lists natively support collaboration. 
  - *For Families:* Shared household grocery lists where anyone can add items.
  - *For UHNW:* Executive Assistant (EA) acting as the operator, gathering options on a list, and sharing a read-only or approval-gated view with the Principal.
- Lists are highly shareable. Sharing a list URL acts as the primary viral growth loop (30% revenue share to referrers).

---

## 4. The Generative List Item (`Row`)

Every item on a list is a `Row`. When the user expands a list item, the frontend reads a `ui_schema` JSON object stored on that `Row` (or its associated `Bid`s) and renders the components dynamically.

### 4.1 Schema Versioning & Backwards Compatibility
To prevent "schema drift" from breaking older lists as our UI library evolves:
- The database schema must include `ui_schema_version` (integer).
- The `DynamicRenderer` acts as a router, passing the JSON to the correct parser based on the version.

### 4.2 The "Lego" Primitives (v0 Registry)
The frontend implements a strict, bounded registry of safe, atomic components. The LLM may only select blocks from this registry (via `ui_hint`); the builder hydrates them with data. 

*(Note: Legacy complex components like "DealCard", "TipJar", or "ComparisonTable" are not primitives; they are composite patterns built by stacking these v0 primitives. For the full technical schema, see [PRD-SDUI-Schema-Spec.md](./PRD-SDUI-Schema-Spec.md))*

**Layout Tokens (v0 — three layouts, all serving comparison):**
- `ROW_COMPACT` — Dense text comparison when bids lack images
- `ROW_MEDIA_LEFT` — Visual comparison when bids have product images
- `ROW_TIMELINE` — Post-decision fulfillment tracking (comparison phase is over)

**Display Primitives:**
- `ProductImage` / `ImageGallery`
- `PriceBlock` (handles single prices, unit pricing, or multi-line breakdowns)
- `DataGrid` (key-value pairs for specs, dimensions)
- `FeatureList` (bulleted lists with checkmarks)
- `BadgeList` / `StatusBadge` (tags like "Organic", "Pop Swap", or deal statuses)
- `MarkdownText` (for descriptions, agreed terms)

**Interactive Primitives:**
- `Timeline` / `StatusTracker` (visual progress)
- `MessageList` (excerpts of conversations or vendor messages)
- `ChoiceFactorForm` (interactive inputs for refining search)
- `ActionRow` (buttons: "Claim", "Fund Escrow", "View on Amazon", "Connect")

**State-Driven Post-Purchase Primitives:**
*Crucially, the LLM can request these blocks, but the backend state machine determines if they are actually rendered to prevent hallucinated payment requests.*
- `ReceiptUploader` (for Pop claim validation)
- `WalletLedger` (for displaying earned credits)
- `EscrowStatus` (for tracking high-ticket funds)

### 4.3 Trust, Provenance, and the Fallback Row
- **Provenance:** Every block that implies a claim (like a "Best Value" badge or safety rating) must support a `source_refs` array pointing to backend IDs. The UI must allow the user to click to see "Why we're saying this."
- **The "Minimum Viable Row" Fallback:** If the LLM generates an invalid schema, or if the runtime validator rejects it, the frontend must gracefully fail to a guaranteed fallback row: `Title`, `Status`, `Last Updated`, and an `ActionRow` with "View Raw Options" and "Message Support."

---

## 5. Data Model Alignment

The beauty of SDUI is that the schema becomes extremely flexible without altering the relational database heavily:

- **`Project`:** Maps directly to a "List". Users can invite `ProjectMember`s to collaborate.
  - **New Field:** `ui_schema` (JSONB) - List-level UI: tip jar, savings stats, onboarding prompts, share actions. Regenerated on status changes (purchases, new members, first item added).
- **`Row`:** An item on the list.
  - **New Field:** `ui_schema` (JSONB) - The comparison view for this request. Generated after sourcing completes; regenerated on bid changes and status transitions.
- **`Bid`:** An option for that list item.
  - **New Field:** `ui_schema` (JSONB) - Detail view for a specific option. **Generated lazily on-expand only** — not pre-generated for every bid. Most users click through to the merchant site directly from the row comparison view.
- **`PopSwap` / `PopSwapClaim`:** Core models remain intact for handling the economics of grocery coupons. The builder adds `BadgeList` and `ActionRow` blocks into the Row's `ui_schema` when bids with `is_swap=True` are present.

---

## 6. Monetization & Value Capture Models

The generative UI must seamlessly surface the correct revenue capture mechanism for the item's context. Because users range from budget-conscious families to UHNWIs, the platform must never block a transaction just to extract a fee. Instead, we provide immense value and capture revenue where friction is lowest.

The deterministic schema builder injects the appropriate `ActionRow` primitives based on bid data and these four monetization models:

### 6.1 Affiliate & Retail (Low Friction, High Volume)
- **Target:** Everyday products (Amazon, Walmart, eBay), consumer travel (Kayak, Booking.com).
- **Mechanism:** The LLM generates an `ActionRow` with `intent: 'outbound_affiliate'`. **The server owns the URL construction.** The LLM passes the `merchant_id` and `product_id`, and the backend maps it to the allowlist and appends tracking IDs before passing the URL to the frontend.
- **Revenue:** 1–8% CPA paid by the merchant network.
- **UI UX:** Completely invisible to the user. They click "Buy on Amazon" and the transaction happens off-site.

### 6.2 Brand Bidding / Grocery Swaps (In-Store Purchases)
- **Target:** Groceries and CPG items bought physically in-store.
- **Mechanism:** Users claim "Pop Swaps" via an `ActionRow` button (`intent: 'claim_swap'`). Post-purchase, the backend state machine renders the `ReceiptUploader` primitive.
- **Revenue:** We receive a flat payout (e.g., ~$1.00) from the Groflo MCP (or similar clearinghouse) for every verified receipt showing the sponsored item.
- **Viral Growth Loop:** 30% of this payout is routed to the user who invited them to the platform. 

### 6.3 The Escrow Flow (High-Ticket / Concierge)
- **Target:** Charters, luxury rentals, custom services where vendors submit direct quotes.
- **Mechanism:** The LLM generates a composite "Deal Room" layout using `DataGrid` and `MarkdownText`. If the user accepts, they fund the purchase via an `ActionRow` (`intent: 'fund_escrow'`), triggering the `EscrowStatus` primitive.
- **Revenue:** A defined service/platform fee is baked into the escrow transaction before payout to the vendor.
- **Reality Check:** UHNWIs and vendors may bypass our escrow and wire money directly. We do not block this; the list serves as the system of record. If they bypass, we fall back to the Tip Jar.

### 6.4 The "Value-Add" Tip Jar (Universal Fallback)
- **Target:** Any transaction, but specifically high-ticket items where the users bypass our escrow, or situations where we provided immense time-savings (e.g., EA sourcing 5 caterers).
- **Mechanism:** An `ActionRow` with `intent: 'send_tip'`. It can appear globally (at the top of the list) or contextually attached to a specific completed `Row`.
- **UX Copy:** *"If we saved you time or money today, feel free to leave a tip."*
- **Revenue:** Direct, high-margin revenue driven by goodwill. 

---

## 7. Backend Architecture & Prompting Strategy

To make SDUI production-grade, the LLM cannot directly write to the database. We must implement a strict validation pipeline.

### 7.1 The Schema Build Pipeline (LLM Selects, Builder Hydrates)
Schema generation is split into two responsibilities:
1. **LLM selects the blueprint (`ui_hint`):** As part of its existing decision call, the LLM outputs a lightweight hint — a layout token and an ordered list of block types from the v0 registry. This is the "generative" part: the LLM reasons about what UI is appropriate for *any* request, including novel ones.
2. **Builder hydrates with data:** `hydrate_ui_schema(ui_hint, row, bids)` fills in every field value from structured data. The LLM **never** populates prices, URLs, or images.
3. **State Machine Check:** If a post-purchase block (e.g., `EscrowStatus`, `ReceiptUploader`) would be included, the server verifies the actual database state permits it.
4. **Validation:** Pydantic schema enforces limits (max blocks, text length, etc.) as a safety net.
5. **Persistence:** `ui_schema` and `ui_schema_version` saved to the DB.
6. **Fallback:** If `ui_hint` is missing or invalid, a deterministic fallback derives layout from the data (see [Schema Spec §8](./PRD-SDUI-Schema-Spec.md)).

### 7.2 Example Schema (Service Request with Vendor Quotes)
The builder detects `row.service_type` is set and `row.status` is pre-decision, so it assembles a timeline-ready layout from standard primitives.
```json
{
  "version": 1,
  "layout": "ROW_TIMELINE",
  "value_vector": "safety",
  "blocks": [
    { "type": "DataGrid", "items": [{"key": "Origin", "value": "SAN"}, {"key": "Dest", "value": "ASE"}, {"key": "Pax", "value": "4"}] },
    { "type": "BadgeList", "tags": ["Wyvern Wingman Certified"], "source_refs": ["vendor_safety_db_44"] },
    { "type": "ActionRow", "actions": [{"label": "Request Firm Quotes", "intent": "contact_vendor"}] },
    { "type": "ActionRow", "actions": [{"label": "Leave a Tip", "intent": "send_tip", "amount": 100}] }
  ]
}
```

### 7.3 Observability & Metrics
This system requires aggressive monitoring because UI failures are now data failures. We must track three points:
1. **Prompt inputs:** What did we ask the model to render?
2. **Raw output:** What did the model actually output?
3. **Validation metrics:** 
   - Schema validation failure rate (Zod rejections).
   - Fallback rate (how often did we render the "Minimum Viable Row").
   - Click-through rate (CTR) per `ActionRow` type to measure UI effectiveness.

---

## 8. Frontend Architecture (React/Next.js)

The frontend becomes a "dumb" renderer of smart data. We build a dynamic parser instead of hardcoded route templates.

```tsx
// Example pseudo-code for the dynamic renderer

const COMPONENT_REGISTRY = {
  ProductImage: ProductImageComponent,
  PriceBlock: PriceBlockComponent,
  BadgeList: BadgeListComponent,
  ActionRow: ActionRowComponent,
  DataGrid: DataGridComponent,
  FeatureList: FeatureListComponent,
};

export function DynamicRenderer({ schema }: { schema: UI_Schema }) {
  if (!schema || !schema.blocks) return <FallbackBasicList />;

  return (
    <div className={`layout-${schema.layout}`}>
      {schema.blocks.map((block, idx) => {
        const Component = COMPONENT_REGISTRY[block.type];
        if (!Component) return null;
        return <Component key={idx} {...block} />;
      })}
    </div>
  );
}
```

### Safety & Persistence
By saving the `ui_schema` to the database:
1. **It's Safe:** The LLM cannot execute malicious code, it can only output JSON referencing our pre-vetted `COMPONENT_REGISTRY`.
2. **It's Fast & Persistent:** When a user shares a list with their spouse, the spouse's phone reads the saved JSON and renders instantly. We don't need to re-prompt the LLM on every page load.

---

## 9. Migration & Next Steps (Smallest Path to Test)

1. **Remove legacy classification:** Delete `desire_tier` and `intent.category` from models, LLM prompts, routes, and tests.
2. **Implement Core SDUI Infrastructure:** Build the `DynamicRenderer`, the v0 primitive registry, `build_ui_schema()`, and the "Minimum Viable Row" fallback.
3. **Ship One Domain (Groceries):** Wire the builder into the Pop pipeline. Every grocery row gets a schema built from its bids.
4. **Persist at Row Level Only:** Skip Bid-level overrides for v1 to keep state simple.
5. **Monitor:** Watch fallback rates and click-through rates per `ActionRow` type.

*See [MIGRATION-PLAN-SDUI.md](./MIGRATION-PLAN-SDUI.md) for the full phased plan.* 

---
