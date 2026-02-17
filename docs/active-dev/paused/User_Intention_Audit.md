# User Intention Audit: Spirit vs Letter of the Law

**Date**: 2026-02-15  
**Scope**: Full-stack audit of BuyAnything's ability to fulfill user *desires*, not just process user *inputs*

---

## Executive Summary

BuyAnything's stated mission is to let users purchase **anything** — from a child's toy to a mega-yacht. The current codebase has a solid technical foundation (chat → intent → search → rank → display), but several architectural patterns satisfy the *letter* of "finding results" without fulfilling the *spirit* of "understanding and satisfying what the user actually wants."

The core problem: **the system treats every request as a keyword search problem when it should treat every request as a desire-fulfillment problem.**

---

## Part 1: The Psychology of Loopholes (Why This Matters)

Research from MIT and Harvard (Bridgers et al., 2025, *Child Development*) studied how children use "loopholes" — intentional misunderstandings where a request is *technically* satisfied but the *underlying spirit* is violated. Key findings:

1. **Loopholes are "malicious compliance"** — doing what someone asked, but not what they *meant*. A parent says "put the tablet down" and the child puts it on the table and keeps playing.

2. **The child knows what was meant.** The parent knows what was meant. The child knows the parent knows. Yet the loophole persists because the *literal instruction* was satisfied.

3. **Applied to AI systems**: The researchers explicitly warned that "we as humans are currently developing new forms of machine intelligence which may not do what we want. If we end up building a genie, we better understand genies!"

4. **The fix isn't more rules — it's understanding intent.** More rules just create more loopholes. The solution is cooperative communication where the system *infers and acts on the spirit* of the request.

### How This Applies to BuyAnything

Our system has several "genie problems" — places where it technically does what was asked but not what was *meant*:

| User Spirit | What System Does (Letter) | Gap |
|---|---|---|
| "I want a private jet charter" | Searches Amazon for "private jet charter" | Returns irrelevant product listings |
| "Find me a mega-yacht" | Runs keyword search, gets 0 results | User gets "no results found" — conversation dies |
| "I need a custom diamond ring" | Creates a row, runs web search | Returns mass-produced rings, not bespoke jewelers |
| "Buy Acme Corp" (M&A) | Tries to search shopping providers | Complete dead end — no provider can handle this |
| User refines with "make it round trip" | System sometimes creates a *new* row | User's context and progress is lost |

---

## Part 2: Codebase Audit — Letter vs Spirit Gaps

### Gap 1: The Intent System Extracts Keywords, Not Desires

**File**: `services/intent.py`, `services/llm.py`

The `SearchIntentResult` model captures:
- `product_category`, `product_name`, `brand`, `model`
- `min_price`, `max_price`
- `keywords`, `features`

**What's missing**: There is no concept of *desire type*. The system doesn't distinguish between:

| Desire Type | Example | What's Needed |
|---|---|---|
| **Commodity purchase** | "AA batteries" | Amazon/eBay search — current system handles this |
| **Considered purchase** | "Laptop for video editing" | Comparison shopping + expert guidance |
| **Service procurement** | "Private jet SAN→EWR" | Vendor matching + RFP + quote comparison |
| **Bespoke/custom** | "Custom engagement ring" | Artisan matching + design consultation |
| **High-value asset** | "Mega-yacht" | Broker network + due diligence + contract management |
| **M&A/Corporate** | "Acquire a SaaS company" | Investment banking + legal + completely different workflow |

The current `service_type` hint is a step in the right direction but it's optional, string-typed, and only used to gate vendor directory lookups. The system treats a $5 toy and a $50M yacht through the same pipeline.

**Spirit violation**: The LLM prompt in `make_unified_decision()` (lines 206-303 of `llm.py`) asks the LLM to classify intent, but all paths converge to the same `create_row → search → display results` flow regardless of desire complexity.

### Gap 2: Search Is Keyword-Based, Not Desire-Based

**File**: `sourcing/repository.py`, `sourcing/scorer.py`

The search pipeline:
1. Takes a text query (e.g., "private jet charter SAN to EWR")
2. Sends it to Amazon/Google Shopping/eBay adapters verbatim (or with minor LLM cleanup)
3. Also does pgvector similarity search against vendor directory
4. Scores results using keyword matching against title text

**The fundamental problem**: Shopping APIs are designed for commodity products. They will never return meaningful results for services, bespoke items, or high-value assets. The system runs the search anyway and returns whatever comes back.

**Evidence in code** — `triage_provider_query()` in `llm.py` (line 466):
```python
prompt = """You are generating a concise search query to send to
shopping providers (Amazon/Google Shopping/eBay)..."""
```

This is the right approach for commodities but the wrong approach for everything else. There's no logic to say "this request cannot be fulfilled by Amazon — route it differently."

### Gap 3: The Scorer Uses Shallow Signals

**File**: `sourcing/scorer.py`

Current scoring weights:
- **Relevance (50%)**: Keyword matching in title text
- **Quality (20%)**: Rating, review count, has image, has shipping info
- **Price (20%)**: Within budget range
- **Diversity (10%)**: Provider variety bonus

**Spirit violations**:
1. **Relevance is keyword-counting, not semantic understanding.** If the user wants a "light jet with Wi-Fi for 4 passengers" and a result title says "Citation CJ3+ Charter — Wi-Fi Equipped, 7 Seats", the keyword matcher will partially match "wi-fi" and "jet" but miss the semantic fit entirely.

2. **Quality signals are Amazon-shaped.** Rating, review count, and shipping info make sense for consumer products. They're meaningless for charter jets, bespoke jewelry, or professional services. Vendor directory results always get `quality_score = 0.3` (base only) because they have no ratings/reviews.

3. **No "fit" scoring.** The scorer doesn't ask "does this result actually satisfy the user's *constraints*?" A jet charter result showing a heavy jet when the user asked for a light jet scores the same as a matching light jet.

### Gap 4: The Chat-to-Search Handoff Loses Context

**File**: `routes/chat.py`

When the chat creates a row and triggers search:
```python
row = await _create_row(session, user_id, title, project_id,
    is_service, service_category, constraints, search_query)
```

The `search_query` is a flat string. All the rich structured data from the conversation (origin airport, destination, date, passenger count, aircraft preferences) gets compressed into a search string like "private jet charter SAN to EWR". The providers then try to keyword-match this string.

**The vendor_directory pgvector search** is better — it uses embedding similarity. But it doesn't use the structured constraints at all. A vector search for "private jet charter" will find all charter providers equally, regardless of whether they fly the right routes or have the right aircraft.

### Gap 5: `_fetch_vendors` Calls a Deleted Endpoint

**File**: `routes/chat.py` (lines 183-220)

The `_fetch_vendors()` function makes an HTTP call to `{_SELF_BASE_URL}/outreach/vendors/{service_category}` — **but this endpoint was deleted** in the cleanup. This means:

1. For `create_row` and `update_row` actions with a `service_category`, the chat tries to fetch vendors
2. The HTTP call returns 404
3. The error is silently caught
4. The user gets no vendor results from this path

Vendor results only come through the `vendor_directory` provider in the search pipeline now, which is correct. But the dead `_fetch_vendors` code adds latency (15s timeout) and confusing log noise.

### Gap 6: No Concept of "Unfulfillable by Search"

There is no mechanism to recognize that a user request *cannot be fulfilled* by any search provider and needs a fundamentally different workflow:

- **"Buy me a $50M yacht"** → Needs broker introduction, not Amazon search
- **"I want to acquire a SaaS company doing $5M ARR"** → Needs M&A advisory
- **"Commission a mural for my office"** → Needs artist matching, not product search
- **"Cater my 200-person wedding"** → Needs RFP to caterers, not Google Shopping

The system will dutifully search Amazon for all of these and return either nothing or irrelevant results. The *letter* is satisfied (search was performed) but the *spirit* is violated (user's desire is unaddressed).

### Gap 7: No Post-Purchase / Contract / Commission Tracking

For high-value transactions that BuyAnything facilitates, there is no system for:
- Contract management
- Commission tracking for BuyAnything's revenue
- Integration with a system of record for completed sales
- Conversation history linked to transactions

The `Bid` model tracks `is_selected` but there's no workflow after selection.

---

## Part 3: What Others Are Doing (Research)

### Bloomreach (AI Search Intent)
- Categorizes intent into **informational**, **navigational**, and **transactional**
- Uses NLP to understand *meaning*, not just keywords
- Personalizes results based on user history and behavior patterns
- **Key insight**: "41% of major ecommerce sites have poor search functionality" — even basic intent classification is a differentiator

### Perplexity "Buy with Pro" (Agentic Commerce, late 2024)
- Uses LLM to understand product requirements conversationally
- Performs multi-source research (not just one API)
- Presents findings with *reasoning* (why this result matches your needs)
- **Key insight**: The LLM doesn't just search — it *evaluates and recommends*

### OpenAI Operator (January 2025)
- Agentic approach: the AI *takes actions* on behalf of the user
- Books travel, makes reservations, completes purchases
- **Key insight**: The system doesn't just find results — it *completes the transaction*

### Quantum Reranking (from HeyLois/eco-system/quantum)

The `XanaduQuantumReranker` in the sibling project provides:
- **Photonic quantum kernel**: Maps embeddings to quantum circuit parameters, runs interference patterns
- **Blended scoring**: `blend_factor` (default 0.7) combines quantum and classical similarity
- **Novelty scoring**: Surfaces results that are *surprisingly good* — high quantum score but low classical score (serendipitous discoveries)
- **Coherence scoring**: Measures alignment stability between query and result

This is directly applicable to BuyAnything's result ranking. The `QuantumRerankerService` accepts `query_embedding` + `search_results` with embeddings and returns reranked results with `blendedScore`, `noveltyScore`, and `coherenceScore`.

**Integration path**: Since our `vendor_directory` results already have embeddings (1536-dim), and we can generate query embeddings, the quantum reranker could slot in after the current `scorer.py` to provide semantic reranking that goes beyond keyword matching.

---

## Part 4: Recommendations — Fulfilling the Spirit

### R1: Implement Desire Classification (High Priority)

Before any search, classify the user's desire into a tier:

| Tier | Examples | Routing |
|---|---|---|
| **Commodity** | Batteries, shoes, books | Web search (Amazon/eBay/Google) |
| **Considered** | Laptop, camera, furniture | Web search + comparison engine |
| **Service** | Charter, HVAC, catering | Vendor directory + RFP workflow |
| **Bespoke** | Custom jewelry, murals | Artisan/specialist matching |
| **High-Value Asset** | Yacht, aircraft, real estate | Broker network + due diligence |
| **Corporate/M&A** | Company acquisition | Advisory network + deal workflow |

This classification should happen in `make_unified_decision()` and drive fundamentally different downstream workflows — not just different search queries.

### R2: Replace Keyword Scoring with Semantic + Constraint Scoring (High Priority)

The current `scorer.py` should be augmented or replaced with:

1. **Semantic similarity** (embedding-based, not keyword-based) — use the same pgvector embeddings we already generate
2. **Constraint satisfaction scoring** — does the result satisfy the user's structured constraints (route, date, passengers, aircraft class)?
3. **Quantum reranking** — port the `XanaduQuantumReranker` from the quantum project for novelty/serendipity scoring on results that have embeddings

### R3: Kill `_fetch_vendors()` Dead Code (Quick Win)

Remove the `_fetch_vendors()` function from `chat.py`. Vendor results already flow through the `vendor_directory` provider. The dead code adds 15s timeout latency and log noise.

### R4: Build "Unfulfillable by Search" Detection (Medium Priority)

Add a check after desire classification:
- If the desire tier is **Bespoke**, **High-Value Asset**, or **Corporate/M&A**, skip web search entirely
- Instead, route to a specialist matching workflow that connects the user with the right kind of intermediary
- This is where contract management and commission tracking become essential

### R5: Pass Structured Constraints to Vendor Matching (Medium Priority)

The vendor pgvector search currently only uses the text query embedding. It should also filter on structured constraints:
- Aircraft class / jet size
- Route capability
- Availability dates
- Certifications (ARGUS, Wyvern)

This would make vendor results *actually satisfy* the user's constraints instead of just being semantically similar.

### R6: Build Post-Selection Workflow (Longer Term)

After a user selects a bid/offer:
1. Track the selection event with metadata
2. For service providers: initiate outreach (already partially built)
3. For high-value: create contract/deal record
4. Track commission and close status
5. Sync to external system of record (CRM, ERP)

### R7: Add Conversation-to-Transaction Linking (Longer Term)

Every chat conversation that leads to a purchase should be:
1. Stored with the transaction record
2. Available for audit/compliance
3. Usable for training the system to better understand desire patterns

---

## Part 5: The "Genie Test"

For every feature we build, apply this test:

> If a clever teenager were using this system and wanted to claim they "technically" fulfilled our requirement while doing the bare minimum — would they succeed?

Examples:
- **"Search was performed"** → Yes, but did the results actually match what the user wanted?
- **"Results were ranked"** → Yes, but by keywords or by actual fit to the user's desire?
- **"Vendors were returned"** → Yes, but do they serve the right routes/dates/aircraft?
- **"The chat understood the request"** → Yes, it extracted keywords, but did it understand the *type* of purchase and route accordingly?

If the answer is "the teenager would get away with it," we have a letter-vs-spirit gap.

---

## Part 6: The Path Forward — Three PRDs

This audit identified seven gaps. They cluster into three workstreams, each with a dedicated PRD:

### PRD 1: Desire Classification & Intent Fulfillment

**Addresses**: Gaps 1, 2, 4, 5, 6

The highest-leverage change. Before the system touches any search API, it must classify *what kind of desire* the user has and route accordingly. A request for batteries should go to Amazon. A request for a jet charter should go to the vendor directory + outreach pipeline. A request to acquire a company should trigger a fundamentally different workflow.

**Spirit test**: "Did the system understand what kind of help the user needs, or did it just run the same pipeline regardless?"

→ See `docs/active-dev/PRD_Desire_Classification.md`

### PRD 2: Autonomous Outreach

**Addresses**: Gaps 6, 7, and the existing `Autonomous_Outreach_Strategy.md`

Once the system classifies a desire as Service/Bespoke/High-Value, it needs to *act* — not just return search results. The outreach system drafts, tracks, compares, and negotiates on behalf of the user, with the EA always in the loop.

**Spirit test**: "Did the system help the user actually *get* what they want, or did it just show them a list and say 'good luck'?"

→ See `docs/active-dev/PRD_Autonomous_Outreach.md`

### PRD 3: Quantum Re-Ranking

**Addresses**: Gap 3

Replace keyword-counting with semantic + quantum scoring. Port the `XanaduQuantumReranker` from the sibling project. Add constraint-satisfaction scoring. Surface serendipitous discoveries via novelty scoring.

**Spirit test**: "Are the top results the ones that best satisfy the user's *actual constraints*, or just the ones with the most keyword overlap?"

→ See `docs/active-dev/PRD_Quantum_ReRanking.md`

### Dependency Graph

```
Desire Classification (PRD 1)
    │
    ├── Commodity/Considered tier → existing web search + Quantum Re-Ranking (PRD 3)
    │
    └── Service/Bespoke/High-Value tier → Autonomous Outreach (PRD 2)
                                              + Quantum Re-Ranking (PRD 3) for vendor ranking
```

PRD 1 is the prerequisite. PRD 2 and PRD 3 can be built in parallel once desire classification exists.

---

## Appendix: Files Audited

| File | What It Does | Key Gaps Found |
|---|---|---|
| `services/llm.py` | LLM decision engine | No desire tier classification; all requests → same flow |
| `services/intent.py` | Intent extraction | Keyword-focused; no desire type or complexity assessment |
| `routes/chat.py` | Main chat endpoint | `_fetch_vendors()` calls deleted endpoint; context compression |
| `sourcing/repository.py` | Provider orchestration | All providers get same flat query regardless of desire type |
| `sourcing/scorer.py` | Result ranking | Keyword-based relevance; Amazon-shaped quality signals |
| `sourcing/vendor_provider.py` | Vendor vector search | No constraint filtering; pure embedding similarity |
| `sourcing/service.py` | Search orchestration | No desire-based routing; uniform pipeline |
| `sourcing/constants.py` | Source classification | Clean after wattdata removal |

## Appendix: External Sources

- Bridgers et al. (2025). "Learning Loopholes: The Development of Intentional Misunderstandings in Children." *Child Development*. SRCD.
- Bloomreach (2025). "Understanding Customer Intent With AI Search."
- McKinsey QuantumBlack (2025). "The Agentic Commerce Opportunity."
- HeyLois/eco-system/quantum: `XanaduQuantumReranker`, `QuantumRerankerService`, `IntelligentMandateMatchingService`
