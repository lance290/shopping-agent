# PRD: AI Procurement Agent + Conversational RFP Builder

## Business Outcome
- Measurable impact: Reduce buyer effort by replacing manual forms with conversational choice-factor extraction. Agent should produce a structured RFP and initial tile row within seconds.
- Target users:
  - Buyers (all segments: B2C, B2B, C2C)

## Scope
- In-scope:
  - Conversational entry point ("What can I help you buy today?")
  - LLM-driven choice-factor identification for any category
  - Conversational RFP builder: agent asks questions to fill out structured requirements
  - Generation of first tile row from RFP + sourcing results
  - Dynamic tile updates when buyer provides feedback (thumbs up/down)
  - Disambiguation flow for ambiguous intent (prioritize Discovery questions before results)
- Out-of-scope:
  - Tile UI rendering (covered by Workspace + Tile Provenance)
  - Vendor outreach (covered by Multi-Channel Sourcing)
  - Closing/checkout (covered by Unified Closing Layer)

## User Flow
1. Buyer enters a natural language intent (e.g., "I need to furnish a 50-person office").
2. Agent queries LLM for relevant choice factors for the category.
3. Agent asks buyer questions conversationally to complete the RFP.
4. Agent generates a structured RFP and triggers sourcing.
5. First tile row appears: lead tile shows buyer's need + choice-factor highlights; remaining tiles are initial matches.
6. Buyer interacts (thumbs up/down); agent updates tile ranking in real-time.

## Business Requirements

### Authentication & Authorization
- Buyer must be authenticated to persist RFPs and projects.
- RFP content is private to the buyer (and authorized collaborators) unless explicitly shared.

### Monitoring & Visibility
- Track:
  - Time from intent to first tile row
  - Number of questions asked per RFP
  - Choice factors identified per category
  - Disambiguation rate (ambiguous intents detected)

### Billing & Entitlements
- No direct billing for RFP creation in MVP.
- Must support future premium tiers (e.g., priority sourcing, advanced choice-factor analysis).

### Data Requirements
- Persist:
  - RFP structure (questions, answers, choice factors)
  - Mapping of RFP → project row
  - Chat log for provenance

### Performance Expectations
- Agent should generate first tile row within 30 seconds of RFP completion.
- Choice-factor extraction should not block conversation flow.

### UX & Accessibility
- Chat UI must be accessible (keyboard navigable, screen-reader friendly).
- Agent should confirm ambiguous terms before proceeding.

### Privacy, Security & Compliance
- Chat logs may contain sensitive buyer info; apply redaction rules as needed.
- LLM prompts must not leak PII to external APIs beyond what's necessary.

## Dependencies
- Upstream:
  - Product North Star
- Downstream:
  - Workspace + Tile Provenance (renders tiles)
  - Multi-Channel Sourcing (retrieves offers)

## Risks & Mitigations
- Agent hallucination in RFP specs → require buyer approval of generated RFP summary before vendor outreach.
- Ambiguous intent → prioritize Discovery questions; do not show results until category is clear.

## Acceptance Criteria (Business Validation)
- [ ] Agent identifies at least 3 relevant choice factors for any category (binary).
- [ ] Agent can complete an RFP via conversational Q&A (binary).
- [ ] First tile row appears within 30 seconds of RFP completion (binary).
- [ ] Tiles update dynamically when buyer provides thumbs up/down feedback (binary).
- [ ] Ambiguous intent triggers disambiguation flow before results (binary).

## Traceability
- Parent PRD: `docs/prd/marketplace-pivot/parent.md`
- Product North Star: `.cfoi/branches/main/product-north-star.md`
- Strategy: `need sourcing_ next ebay.md`

---
**Note:** Technical implementation decisions are made during /plan and /task.
