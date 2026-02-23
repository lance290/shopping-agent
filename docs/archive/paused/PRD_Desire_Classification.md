# PRD: Desire Classification & Intent Fulfillment

**Status**: Draft  
**Date**: 2026-02-15  
**Origin**: User Intention Audit (Gaps 1, 2, 4, 5, 6)  
**Priority**: P0 — prerequisite for Outreach and Quantum Re-Ranking PRDs

---

## 1. The Problem (Spirit)

BuyAnything promises users they can purchase *anything*. But every request — whether it's AA batteries or a mega-yacht — flows through the same pipeline: extract keywords → search Amazon/eBay/Google → rank by keyword overlap → display results.

This is like a concierge who responds to every request by looking it up on Amazon. Ask for a private jet charter? Amazon search. Ask to acquire a company? Amazon search. Ask for a custom engagement ring? Amazon search.

The system doesn't *understand what kind of help the user needs*. It just searches.

### The Genie Test

> "I searched for what you asked." — Yes, but the user wanted a jet charter and you showed them toy airplanes on Amazon. The letter was satisfied. The spirit was violated.

---

## 2. The Vision (What "Done" Looks Like)

A user says: **"I need a light jet from Teterboro to Aspen on March 15 for 4 passengers."**

The system should:
1. Recognize this is a **Service procurement** (not a commodity purchase)
2. Skip Amazon/eBay entirely — they can't help here
3. Search the vendor directory for charter operators matching route, aircraft class, and capacity
4. Extract structured constraints: `{origin: "TEB", destination: "ASE", date: "2026-03-15", pax: 4, aircraft_class: "light"}`
5. Present matching vendors with *why* they match (not just a list)
6. Offer to initiate outreach to top vendors (→ Autonomous Outreach PRD)

A user says: **"I need AA batteries."**

The system should:
1. Recognize this is a **Commodity** purchase
2. Search Amazon/eBay/Google Shopping — they're perfect for this
3. Rank by price, reviews, shipping speed
4. Present results immediately

**The same system, radically different behavior, driven by understanding the desire.**

---

## 3. Desire Tiers

| Tier | Signal Words | Provider Routing | Post-Search Action |
|---|---|---|---|
| **Commodity** | buy, order, get, need [common product] | Web search (Amazon, eBay, Google Shopping) | Display results, user self-serves |
| **Considered** | best, compare, recommend [complex product] | Web search + comparison engine | Display with pros/cons analysis |
| **Service** | hire, charter, book, schedule, install | Vendor directory (vector) + structured constraints | Offer outreach to matching vendors |
| **Bespoke** | custom, commission, design, handmade | Specialist/artisan directory + consultation | Connect with maker, start design process |
| **High-Value Asset** | yacht, aircraft, property, estate | Broker directory + due diligence pipeline | Broker introduction, NDA/LOI workflow |
| **Advisory** | acquire, merge, invest, incorporate | Advisory network (future) | Flag as out-of-scope or connect with partner |

### Classification Confidence

The LLM should return a confidence score. When confidence is low (< 0.7), the system asks a single clarifying question rather than guessing wrong:

> "Are you looking to *buy* a drone online, or *hire* a drone operator for a shoot?"

This is cheaper than running the wrong pipeline and showing irrelevant results.

---

## 4. Technical Design

### 4.1 Where Classification Happens

**File**: `services/llm.py` → `make_unified_decision()`

The existing LLM prompt already asks for intent classification. We extend the `UnifiedDecision` model:

```python
class UnifiedDecision(BaseModel):
    action: str                    # existing: create_row, update_row, clarify, etc.
    desire_tier: str               # NEW: commodity, considered, service, bespoke, high_value, advisory
    desire_confidence: float       # NEW: 0.0-1.0
    structured_constraints: dict   # NEW: extracted structured data (routes, dates, specs, etc.)
    search_query: str              # existing: flat text query for web search
    vendor_query: str              # NEW: optimized query for vendor directory
    skip_web_search: bool          # NEW: true if web search would be useless for this tier
    # ... existing fields ...
```

### 4.2 How Classification Drives Routing

**File**: `sourcing/service.py` → `search_and_persist()`

Currently all providers run in parallel regardless of desire type. New logic:

```python
async def search_and_persist(self, row, decision):
    tier = decision.desire_tier

    if tier in ("commodity", "considered"):
        # Web search providers + vendor directory
        results = await self.repo.search_all_with_status(
            query=decision.search_query,
            providers=self._web_providers + [self._vendor_provider]
        )
    elif tier in ("service", "bespoke"):
        # Vendor directory only, with structured constraints
        results = await self._vendor_provider.search(
            query=decision.vendor_query,
            constraints=decision.structured_constraints
        )
        # Skip web search entirely — it can't help
    elif tier == "high_value":
        # Broker directory (future) + vendor directory
        results = await self._vendor_provider.search(
            query=decision.vendor_query,
            constraints=decision.structured_constraints
        )
    elif tier == "advisory":
        # No search — flag for human review
        return self._advisory_response(decision)
```

### 4.3 Structured Constraint Extraction

The LLM already has the conversation context. We add a structured extraction step to the prompt:

```
If this is a service/bespoke/high-value request, extract structured constraints:
- For travel/charter: {origin, destination, date, return_date, passengers, aircraft_class}
- For construction/renovation: {location, scope, budget_range, timeline}
- For custom goods: {material, dimensions, style, budget_range, deadline}
- For high-value assets: {type, budget_range, location_preference, must_haves}
```

These constraints flow into both vendor search (for filtering) and outreach drafts (for specificity).

### 4.4 Vendor Search with Constraints

**File**: `sourcing/vendor_provider.py`

Currently does pure embedding similarity. Add constraint-based post-filtering:

```python
async def search(self, query, constraints=None):
    # Step 1: Vector similarity (existing)
    candidates = await self._vector_search(query)

    # Step 2: Constraint filtering (new)
    if constraints:
        candidates = self._apply_constraints(candidates, constraints)

    return candidates

def _apply_constraints(self, candidates, constraints):
    """Filter vendor results by structured constraints."""
    filtered = []
    for c in candidates:
        score_adjustment = 0.0
        # Check route coverage (if vendor has route data)
        if "origin" in constraints and c.raw_data.get("routes"):
            if constraints["origin"] in c.raw_data["routes"]:
                score_adjustment += 0.2
        # Check aircraft class
        if "aircraft_class" in constraints and c.raw_data.get("aircraft_classes"):
            if constraints["aircraft_class"] in c.raw_data["aircraft_classes"]:
                score_adjustment += 0.15
        # ... more constraint checks
        c.match_score += score_adjustment
        filtered.append(c)
    return sorted(filtered, key=lambda x: x.match_score, reverse=True)
```

### 4.5 Kill Dead Code (Quick Win)

**File**: `routes/chat.py`

Remove `_fetch_vendors()` function entirely. It calls a deleted endpoint and adds 15s timeout latency. Vendor results already flow through the `vendor_directory` provider in the search pipeline.

---

## 5. Data Model Changes

### 5.1 Row Model Extension

```sql
ALTER TABLE rows ADD COLUMN desire_tier VARCHAR(20);
ALTER TABLE rows ADD COLUMN structured_constraints JSONB;
```

The `desire_tier` on the row enables:
- Different UI treatment per tier (e.g., "Outreach Queue" button for service tier)
- Analytics on what types of desires users have
- Per-tier conversion tracking

### 5.2 Vendor Model Extension

Vendors need richer metadata for constraint matching:

```sql
ALTER TABLE vendors ADD COLUMN service_capabilities JSONB;
-- Example: {"routes": ["TEB-ASE", "TEB-MIA"], "aircraft_classes": ["light", "midsize"]}
ALTER TABLE vendors ADD COLUMN preferred_contact_method VARCHAR(20);
-- → feeds into Autonomous Outreach PRD
```

---

## 6. Success Metrics

### Letter Metrics (necessary but insufficient)
- Classification accuracy vs human labels (target: > 85%)
- Time to first result (should not increase)
- API cost per request (should decrease — fewer wasted web searches)

### Spirit Metrics (what actually matters)
- **Desire fulfillment rate**: Of requests classified as Service/Bespoke, what % led to a vendor connection? (Baseline: ~0%. Target: > 40%)
- **Zero-result rate by tier**: What % of each tier returns no results? (Commodity should be < 5%. Service should be < 20% with vendor directory.)
- **User re-query rate**: How often does a user rephrase the same desire? (High re-query = system didn't understand the first time)
- **Conversation-to-outreach rate**: For service tier, what % of conversations lead to outreach being initiated? (Target: > 30%)

---

## 7. Rollout Plan

### Phase 1: Classification Only (1-2 weeks)
- Add `desire_tier` and `desire_confidence` to `UnifiedDecision`
- Update LLM prompt with tier definitions
- Log classifications but don't change routing yet
- Validate accuracy against manual labels from production traffic

### Phase 2: Routing Split (1 week)
- For `service` tier: skip web search, boost vendor results
- For `commodity` tier: skip vendor directory (faster, cheaper)
- Remove `_fetch_vendors()` dead code
- Monitor: do service-tier users see better results?

### Phase 3: Structured Constraints (2 weeks)
- Extract structured constraints in the LLM prompt
- Pass constraints to vendor_provider for filtering
- Store constraints on Row model
- Monitor: do vendor results become more specific?

### Phase 4: Advisory Tier (future)
- Build the "this needs human help" pathway
- Partner integrations for M&A, brokerage, etc.

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| LLM misclassifies → wrong pipeline runs | Confidence threshold + clarification question fallback |
| Over-classification → too many tiers to maintain | Start with 3 tiers (commodity, service, high-value); expand only with data |
| Vendor directory too thin for service tier | Graceful fallback to web search if vendor results < 3 |
| Structured constraint extraction unreliable | Constraints are *additive* scoring, not hard filters; bad extraction degrades to status quo |
| Latency increase from classification step | Classification is part of existing LLM call, not a separate round-trip |

---

## 9. Dependencies

- **Upstream**: None — this is the foundational change
- **Downstream**: Autonomous Outreach PRD (needs desire_tier to know when to activate), Quantum Re-Ranking PRD (uses structured constraints for scoring)

---

## 10. The Spirit Check

Before shipping any milestone, ask:

> If a user says "I need a private jet from Teterboro to Aspen" and the system searches Amazon — have we shipped anything of value?

> If a user says "I need AA batteries" and the system asks them 5 clarifying questions about their "desire tier" — have we shipped anything of value?

The system should be **invisible when it works**. Batteries go to Amazon instantly. Jet charters go to the vendor directory with structured constraints. The user never thinks about the routing — they just get the right kind of help.
