# Generative UX/UI Architecture: The "Universal List" via Server-Driven UI (SDUI)

**Document Status:** Draft
**Date:** March 2026
**Context:** Synthesis of BuyAnything's high-ticket marketplace with PopSavings' grocery-focused viral loop, powered by a truly Generative UI.

---

## 1. The Core Paradigm Shift

We are moving away from the "Netflix-style" horizontal rows of product tiles (BuyAnything V2) and standardizing entirely on a dead-simple, mobile-first **Chat + Shared List** interface.
This interface is the authenticated app workspace (for example, `/app`), **not** the public marketing home page (`/`).

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
- **Routing constraint:** This two-pane experience must not be the public home page. Keep affiliate-compliance content and disclosures on `/`; mount the app workspace on a dedicated app route.

### 3.2 Lists of Lists (`Projects`) & Collaboration
Users can maintain multiple lists (e.g., "Default Groceries", "Aspen Trip", "Office Supplies"). 
- **The "Default Groceries" list** is the sticky default that everyone uses daily.
- **Multi-User Dynamics:** Lists natively support collaboration. 
  - *For Families:* Shared household grocery lists where anyone can add items.
  - *For UHNW:* Executive Assistant (EA) acting as the operator, gathering options on a list, and sharing a read-only or approval-gated view with the Principal.
- Lists are highly shareable. Sharing a list URL acts as the primary viral growth loop (30% of **swap payouts only** are shared with the referrer who brought the new user to the platform — see §6.2).

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

The LLM selects the appropriate monetization-oriented `ActionRow` primitives, and the builder resolves/gates them using trusted bid data and backend state. This supports these four monetization models:

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
The builder detects `row.service_type` is set and the selected bid is already in post-decision fulfillment, so it assembles a timeline layout from standard primitives.
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
4. **Persist at Project + Row + Bid levels:** Project header schemas for global actions, Row schemas for comparison, and lazy Bid schemas on-expand for deep details.
5. **Monitor:** Watch fallback rates and click-through rates per `ActionRow` type.

*See [MIGRATION-PLAN-SDUI.md](./MIGRATION-PLAN-SDUI.md) for the full phased plan.* 

---

## 10. Immediate Workspace Polish & Missing Action Recovery (March 2026)

### 10.1 Why This Needs a Dedicated Pass

The new workspace direction is correct, but the current customer-facing content and action surface are not yet shippable.

We now have five distinct problems to solve together:

1. **Internal/product-strategy copy is visible in the workspace entry state.** Blocks like "What the home screen should communicate" and "Why this feels different" are useful during design, but they read like internal notes rather than customer-safe merchandising.
2. **The slate palette is too flat in key areas.** The current dark surfaces are tasteful, but several modules blend together instead of guiding the eye toward the primary action.
3. **Projects are under-explained.** Users are not being clearly taught that they can create named containers like "Zac's Birthday" or "Vegas Trip" and keep multiple searches inside them.
4. **Search duplication is missing.** Project duplication exists, but users cannot duplicate a single search/request and re-run it as a new row.
5. **The row action bar has regressed.** Favorite/like, select, comment, and share capabilities either still exist in the data model/API or have partial components in the codebase, but they are no longer visible or fully wired in the workspace row UI.

This section defines the product spec for fixing those issues without abandoning the current Chat + List workspace direction.

### 10.2 Goals

- Replace internal-facing workspace copy with customer-facing, outcome-oriented merchandising.
- Keep the slate foundation, but increase contrast, hierarchy, and visual pop.
- Teach Projects explicitly in the empty/home state.
- Add row-level duplication as a first-class workflow.
- Restore visible row actions for favoriting, selecting, commenting, and sharing.
- Preserve the anonymous-first, low-friction feel of the current entry experience.

### 10.3 Non-Goals

- Do not revert to the old Netflix-style board.
- Do not create a separate public marketing homepage for this work.
- Do not overload the first screen with enterprise jargon, roadmap language, or internal product philosophy.
- Do not require account creation before a user can understand how the product works.

### 10.4 Current-State Findings From the Implementation

The current codebase already contains several pieces we should reuse rather than rebuild:

- **Project support already exists.** `createProjectInDb`, `fetchProjectsFromDb`, and `duplicateProjectInDb` are wired in the frontend API layer, and backend project routes already support project duplication.
- **Share links already exist.** `/api/shares` supports `project`, `row`, and `bid` sharing with permissions like `view_only`, `can_comment`, and `can_select`.
- **Like persistence already exists.** `Bid.is_liked` and `Bid.liked_at` still exist in the data model, and backend likes routes already support toggling likes on bids.
- **Comment persistence already exists in generic form.** The backend generic comments routes support add/list/delete for row and bid comments.
- **The row UI no longer exposes the actions.** `VerticalListRow.tsx` currently renders `View Deal` / `Request Quote`, but no visible favorite/select/comment/share controls.
- **Some social UI is partially disconnected.** `LikeButton.tsx` exists but is not mounted, and `CommentPanel.tsx` is currently an explicit stub.
- **Sorting already respects liked/selected state.** `VerticalListRow` still floats liked and selected offers to the top, which means the data contract is still aligned with the intended UX.

This means most of the recovery work is **product definition + UI wiring + test coverage**, not a greenfield rebuild.

### 10.5 Replace the Current Home-State Content With Customer-Safe Content

#### 10.5.1 Replace "What the home screen should communicate"

This module should stop explaining the design team's intent and instead show concrete customer use cases.

Recommended replacement:

**Section title:** `Start with a real project`

**Cards:**

- `Zac's Birthday` — "Keep gifts, party supplies, and venue ideas in one place."
- `Vegas Trip` — "Track hotels, flights, outfits, and reservation ideas together."
- `Kitchen Remodel` — "Compare appliances, fixtures, contractors, and inspiration links."

Each card should have a direct CTA:

- `Create project`
- `Start this example`

The point of this module is to teach that a Project is a named container for multiple searches, not just a folder hidden in the UI chrome.

#### 10.5.2 Replace "Why this feels different"

This module should stop sounding like product strategy copy and instead explain the customer benefit in plain language.

Recommended replacement:

**Section title:** `Why people use BuyAnything`

**Cards:**

- `Ask once, compare everywhere.`
  - "Search retail listings, specialist vendors, and relevant guides in one workflow."
- `Keep everything organized.`
  - "Put multiple searches inside a project like a trip, event, room, or shopping mission."
- `Share before you decide.`
  - "Send a project or a search to a spouse, teammate, EA, or client for review."
- `Save your favorites as you go.`
  - "Like, comment on, and select the options worth revisiting."

These cards should feel customer-legible even if they appear in a screenshot, ad, demo, or support article.

#### 10.5.3 Content Tone Rules

Customer-facing home-state copy must:

- use real-life examples
- emphasize outcomes, not architecture
- avoid phrases like "what the screen should communicate"
- avoid phrases like "why this feels different"
- avoid exposing internal product reasoning or workshop language

### 10.6 Slate Palette Refresh: Keep the Mood, Increase the Pop

The palette should remain slate-led, but the hierarchy needs to be more intentional.

#### 10.6.1 Visual Direction

- Keep a **deep slate / midnight** foundation for premium feel.
- Brighten card surfaces slightly so adjacent modules do not collapse into one dark mass.
- Use accent colors more selectively to guide action, not merely decorate.
- Increase contrast between:
  - background
  - container
  - elevated card
  - interactive card
  - primary CTA

#### 10.6.2 Palette Principles

- **Base:** slate / ink / midnight
- **Primary CTA accent:** gold
- **Secondary accents:** sky, violet, emerald
- **Text:** stronger white and near-white hierarchy; reduce washed-out gray copy in primary modules
- **Borders:** more visible slate-blue borders instead of barely-there charcoal outlines

#### 10.6.3 Specific UI Recommendations

- Hero content cards should use stronger separation from the background via brighter surface fill, slightly clearer borders, and more obvious hover states.
- The right-pane modules should alternate subtle accent treatments so they are scannable at a glance.
- The project-education block should use a slightly lighter or warmer surface than generic informational blocks so it reads as an action area.
- The primary CTA should remain the brightest visual element above the fold.

### 10.7 Teach Projects Explicitly in the Empty / Home State

Users should understand Projects without having to infer the concept from a small `New Project` button.

#### 10.7.1 Product Definition

A **Project** is a named container for multiple searches/rows.

Examples:

- `Zac's Birthday`
- `Vegas Trip`
- `New Apartment`
- `Office Move`

Each Project can contain many searches, such as:

- gifts
- flights
- hotels
- outfits
- venue options
- catering

#### 10.7.2 UX Requirements

- The home state must visually explain: `Projects hold multiple searches`.
- The user must be able to create a project from the home state, not just from secondary chrome.
- Example projects should be clickable and should either:
  - prefill a new project title, or
  - create a draft project with starter prompts.
- The workspace should show a clear relationship between:
  - current project
  - rows/searches inside that project

#### 10.7.3 Acceptance Criteria

- A new user can understand the purpose of Projects from the first screen without reading docs.
- A user can create a project with a custom name in one obvious interaction path.
- The UI includes at least three example project names from real life situations.

### 10.8 New Feature: Duplicate Search

Project duplication already exists. We also need **row/search duplication**.

#### 10.8.1 Product Definition

`Duplicate search` creates a new row in the same project using the existing row as the seed.

The duplicated row should:

- copy the row title / request text
- copy choice answers / constraints when present
- copy relevant provider preferences when present
- create a fresh row ID
- start as a new search instance
- re-run sourcing independently of the original row

The duplicated row should **not**:

- inherit old comments by default
- inherit old like state by default
- inherit old selected offer by default
- mutate or overwrite the original row

#### 10.8.2 UX Requirements

- Add a visible `Duplicate search` action on each row.
- On desktop, this can live in a row action bar or overflow menu.
- On mobile, this can live in the row action sheet.
- After duplication, the new row should appear directly below the original with a fresh loading/search state.

#### 10.8.3 Suggested Backend Contract

Add a route like:

- `POST /rows/{row_id}/duplicate`

Response should return the newly created row so the frontend can insert it immediately and stream the fresh search.

### 10.9 Restore the Missing Row Actions

These are not optional polish items. They are core workspace controls and should be treated as a regression-recovery track.

#### 10.9.1 Favorite / Like

**User need:** "Save this option for later."

Spec:

- Restore a visible favorite control on each offer/bid.
- Reuse the existing `Bid.is_liked` persistence model and existing like routes where possible.
- Favoriting must update the UI optimistically.
- Favorited results must remain pinned near the top of the row, consistent with current sorting behavior.

Acceptance criteria:

- Clicking like updates immediately.
- Reloading the row preserves like state.
- Streaming updates do not wipe an explicitly toggled like.

#### 10.9.2 Select

**User need:** "This is the winning option." 

Spec:

- Restore a clear `Select` action for each offer.
- Selected state must be visually stronger than liked state.
- Selecting one option must unselect other options in the same row.
- Selected state must survive refresh and later re-ranking.

Acceptance criteria:

- The selected offer is visually obvious.
- The selected offer remains pinned.
- Only one offer per row can be selected at a time.

#### 10.9.3 Comment

**User need:** "Discuss this option or leave a note."

Spec:

- Restore comments as a visible per-offer or per-row action.
- Reuse the existing generic comments API if it satisfies the data model; otherwise normalize the contract instead of maintaining parallel comment systems.
- Comments should support quick add, list existing comments, and delete own comment.
- On mobile, comments may open in a sheet; on desktop, inline panel or side panel is acceptable.

Acceptance criteria:

- A signed-in user can add a comment from the row UI.
- Existing comments are visible in context.
- Comments persist after refresh.

#### 10.9.4 Share

**User need:** "Send this project or search to someone else."

Spec:

- Restore a visible `Share` action at both:
  - project level
  - row/search level
- Reuse existing share-link routes and permission model.
- The UI must expose share permissions in simple language:
  - `View only`
  - `Can comment`
  - `Can select`

Acceptance criteria:

- A user can generate a share link for a project.
- A user can generate a share link for a row.
- The generated experience clearly reflects the chosen permission level.

### 10.10 UX Structure Changes Required in `AppView` / `VerticalListRow`

#### 10.10.1 Home / Empty State

- Replace internal-note cards with customer-safe value modules.
- Add a dedicated project-onboarding module.
- Keep trending intents and editorial guides, but subordinate them to the clearer project/message hierarchy.

#### 10.10.2 Row Header / Row Actions

- Add a visible action cluster for:
  - duplicate search
  - share
  - delete
  - rerun search
- Ensure the actions are discoverable on touch devices and not hover-only.

#### 10.10.3 Offer-Level Actions

- Add an action row on each offer card/list item for:
  - like/favorite
  - select
  - comment
  - share
- Keep `View Deal` / `Request Quote` as the primary commerce CTA.
- Secondary actions must not visually compete with the primary CTA, but they must remain visible enough to be used.

### 10.11 Engineering Plan

#### Frontend

- Update `AppView.tsx` home-state modules and project education content.
- Update color tokens / classes across the home-state cards for stronger slate hierarchy.
- Extend `VerticalListRow.tsx` with explicit row and offer action bars.
- Reconnect `LikeButton.tsx` or replace it with a slimmer row-action variant.
- Replace the current `CommentPanel.tsx` stub with a real comments implementation or a new comments surface backed by the existing API.
- Add UI for row duplication and share-link generation.

#### Backend

- Add row duplication endpoint and service logic.
- Validate whether the current generic likes/comments routes are sufficient for the desired workspace UX. If not, converge on one canonical social/action API surface.
- Ensure share permissions map cleanly to frontend affordances.

#### Product / Content

- Replace all internal-note copy in the workspace home state.
- Create a customer-facing project example set.
- Review slate palette in context across desktop and mobile, not just as isolated components.

### 10.12 Testing & Verification

Add or update tests for:

- home-state customer copy rendering
- project onboarding CTAs
- duplicate search creation flow
- row action visibility on desktop and mobile
- like/select/comment/share interactions
- persistence of liked and selected states after SSE updates
- share-link creation for project and row
- comments create/list/delete behavior from the workspace UI

### 10.13 Rollout Priority

#### P0

- Replace customer-unsafe home-state copy
- Teach Projects clearly
- Restore favorite/select/comment/share visibility

#### P1

- Ship duplicate search
- Improve slate hierarchy and contrast

#### P2

- Refine share-permission UX
- Add more polished project templates / starter packs

---
