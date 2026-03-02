# PRD: SDUI Friction-Free Comparison

## Business Outcome
- **Measurable impact:** Increase the percentage of user searches that result in a click-through or transaction by 20%. Reduce the time from search-to-decision by 30%.
- **Success criteria:** "Fallback" error rate for UI generation remains <5%; 95% of grocery requests render a valid comparison view; users interact with at least one option on 60% of all generated rows.
- **Target users:** All shoppers across all domains who need to evaluate multiple options quickly.

## Scope
- **In-scope:** Implementing Server-Driven UI (SDUI) where the LLM selects the UI blueprint and the server hydrates it with trusted data. The UI must support three core comparison layouts (Compact, Media-Left, Timeline) built from a strict registry of atomic primitives (Legos).
- **Out-of-scope:** Building new backend sourcing integrations; monetizing the clicks (this is handled in `prd-dynamic-monetization.md`).

## User Flow
1. User requests an item via chat.
2. A "Draft" skeleton row immediately appears on their list, indicating a search is active.
3. The system sources options in the background.
4. Once sourcing completes, the Row instantly morphs into a rich comparison view (e.g., a list of options with prices, images, and "Best Value" badges).
5. The user taps an option to expand it, instantly seeing deeper details (specs, full description).
6. The user clicks a link to purchase or contact the vendor.

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
- **What information must persist?** The JSON schema blueprint (`ui_schema`) must be saved for both the `Row` (comparison view) and `Bid` (expanded detail view).
- **How long must data be retained?** Indefinitely to support persistent shared lists.
- **Data Limits:** The Row-level schema payload must be capped to ensure fast rendering (<5KB).

### Performance Expectations
- **What response times are acceptable?** The UI must transition from "Draft" to "Complete" the moment sourcing finishes without requiring a manual refresh. Expanding a bid for more details must feel instant (UI hydration <50ms p99).
- **What availability is required?** If schema generation fails, the system must gracefully degrade to a "Minimum Viable Row" rather than breaking the page.

### UX & Accessibility
- **What user experience standards apply?** Avoid "UI Whiplash" (don't constantly resize the row while options are streaming in). Use clear provenance ("Why are we saying this is the best value?").
- **What accessibility requirements?** All dynamically generated UI blocks (DataGrids, FeatureLists) must map to semantic HTML with correct ARIA roles.

### Privacy, Security & Compliance
- **What data protection is required?** The LLM must be strictly prohibited from generating raw URLs or prices (to prevent hallucinated phishing links or deceptive pricing). All data values must be hydrated by the server from trusted database columns.

## Dependencies
- **Upstream:** `prd-unified-list.md` (the container).
- **Downstream:** `prd-dynamic-monetization.md` (the buttons).

## Risks & Mitigations
- **Risk:** The LLM hallucinates UI blocks that the frontend doesn't understand, causing the page to crash.
- **Mitigation:** Strict Pydantic validation on the server; unknown blocks are stripped out; a guaranteed "Minimum Viable Row" fallback exists.

## Acceptance Criteria (Business Validation)
- [ ] Schema validation failure rate is <5% of all LLM outputs (baseline: 0%).
- [ ] Time to expand a bid and view details is <50ms p99.
- [ ] 0% occurrence of LLM-hallucinated prices appearing in the UI (all prices must map exactly to the underlying database values).
- [ ] If sourcing returns zero results, the UI gracefully displays a "No options found" state rather than a broken or blank row.

## Traceability
- Parent PRD: `docs/active-dev/sdui-universal-list/parent.md`
