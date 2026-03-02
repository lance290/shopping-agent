# PRD: SDUI Friction-Free Comparison

## Business Outcome
- **Measurable impact:** Increase the percentage of user searches that result in a click-through or transaction by 20%. Reduce the time from search-to-decision by 30%.
- **Success criteria:** "Fallback" error rate for UI generation remains <5%; 95% of grocery requests render a valid comparison view; users interact with at least one option on 60% of all generated rows.
- **Target users:** All shoppers across all domains who need to evaluate multiple options quickly.

## Scope
- **In-scope:** Implementing Server-Driven UI (SDUI) where the LLM selects the UI blueprint and the server hydrates it with trusted data. The UI must support three core comparison layouts (Compact, Media-Left, Timeline) built from a strict registry of 13 atomic primitives (Legos). Must include schema versioning for backwards compatibility, the Value Vector & Provenance system for trust, and a row cardinality cap of 5 bids for performance.
- **Out-of-scope:** Building new backend sourcing integrations; monetizing the clicks (this is handled in `prd-dynamic-monetization.md`).

## User Flow
1. User requests an item via chat.
2. A "Draft" skeleton row immediately appears on their list, indicating a search is active.
3. The system sources options in the background.
4. Once sourcing completes, the Row instantly morphs into a rich comparison view (e.g., a list of options with prices, images, and "Best Value" badges).
5. *(Optional)* The user answers a **Choice Factor** question (e.g., "Do you prefer organic?"). The system re-ranks bids and the comparison view instantly updates via SSE.
6. The user taps an option to expand it, instantly seeing deeper details (specs, full description).
7. The user clicks a link to purchase or contact the vendor.

## Business Requirements

### Authentication & Authorization
- **Who needs access?** Any user viewing a populated list.
- **What actions are permitted?** Users can expand options, view provenance (why a badge was assigned), and click out to external sites.

### Monitoring & Visibility
- **What business metrics matter?** Row expansion rate, click-through rate per layout type, time spent comparing options.
- **What operational visibility is needed?** Real-time monitoring of schema validation failures and fallback rendering rates.

### Billing & Entitlements
- **How is this monetized?** N/A (Handled in next slice).

### Data Requirements
- **What information must persist?** The JSON schema blueprint (`ui_schema`) and its version counter (`ui_schema_version`) must be saved on `Project`, `Row`, and `Bid`.
- **Schema versioning:** `ui_schema_version` starts at 0 (never had a schema). The builder sets it to 1 on first write, increments on each replacement. The `DynamicRenderer` routes schemas to the correct parser based on version for backwards compatibility. (See Schema Spec §1 and PRD §4.1.)
- **Row cardinality cap:** The Row-level schema hydrates data for a **maximum of 5 bids**. If more exist, the builder appends a "View All (X)" action. This keeps the Row JSON payload <5KB. (See Schema Spec §7.)
- **How long must data be retained?** Indefinitely to support persistent shared lists.
- **Schema invalidation:** When a bid's core data changes (price, status, image), its cached `Bid.ui_schema` is set to NULL (re-hydrated on next expand). When bids are added/removed or Row status changes, the Row schema is fully rebuilt and `ui_schema_version` incremented. (See Schema Spec §6.)
- **Concurrency:** Concurrent schema writes (e.g., status change + webhook) are resolved via optimistic locking (`WHERE id=X AND ui_schema_version=Y`); on conflict, refetch and rebuild. (See Migration Plan §7.)

### Performance Expectations
- **What response times are acceptable?** The UI must transition from "Draft" to "Complete" the moment sourcing finishes without requiring a manual refresh. Expanding a bid for more details must feel instant (UI hydration <50ms p99).
- **What availability is required?** If schema generation fails, the system must gracefully degrade to a "Minimum Viable Row" rather than breaking the page.

### UX & Accessibility
- **What user experience standards apply?** Avoid "UI Whiplash" (don't constantly resize the row while options are streaming in). Use clear provenance ("Why are we saying this is the best value?").
- **What accessibility requirements?** All dynamically generated UI blocks (DataGrids, FeatureLists) must map to semantic HTML with correct ARIA roles.

### Value Vector & Provenance
- **Value Vectors:** Each Row schema may include a `value_vector` field (`"unit_price" | "safety" | "speed" | "reliability" | "durability"`) that defines what "best value" means for that specific request. (See Schema Spec §5.)
- **Provenance (`source_refs`):** Any block that implies a claim (e.g., a `BadgeList` tag of "Safest Jet" or a "Best Value" badge) must include `source_refs` (UUIDs) pointing to the backend data source. The frontend must render a clickable "Why we're saying this" tooltip.
- **Trust contract:** Users must be able to verify every recommendation the system makes. This is a core differentiator.

### Privacy, Security & Compliance
- **What data protection is required?** The LLM must be strictly prohibited from generating raw URLs or prices (to prevent hallucinated phishing links or deceptive pricing). All data values must be hydrated by the server from trusted database columns.

## Dependencies
- **Upstream:** `prd-unified-list.md` (the container).
- **Downstream:** `prd-dynamic-monetization.md` (the buttons).

## Risks & Mitigations
- **Risk:** The LLM hallucinates UI blocks that the frontend doesn't understand, causing the page to crash.
- **Mitigation:** Strict Pydantic validation on the server; unknown blocks are stripped out; a guaranteed "Minimum Viable Row" fallback exists.

## Acceptance Criteria (Business Validation)
- [ ] Schema validation failure rate is <5% of all LLM `ui_hint` outputs (baseline: 0% — new capability).
- [ ] Time to expand a bid and view details is <50ms p99.
- [ ] 0% occurrence of LLM-hallucinated prices appearing in the UI (all prices must map exactly to the underlying database values).
- [ ] If sourcing returns zero results, the UI gracefully displays a "No options found" state rather than a broken or blank row.
- [ ] Every `BadgeList` block that makes a claim (e.g., "Best Value") includes `source_refs` and the frontend renders a clickable provenance tooltip.
- [ ] Row schemas never exceed 5 bids; overflow shows a "View All (X)" action.
- [ ] Choice Factor interaction: answering a factor re-ranks bids and pushes an updated schema via SSE within 2 seconds.

## Traceability
- Parent PRD: `docs/active-dev/sdui-universal-list/parent.md`
