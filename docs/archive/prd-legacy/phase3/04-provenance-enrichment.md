# PRD: Tile Provenance Enrichment

**Phase:** 3 — Closing the Loop  
**Priority:** P1  
**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Parent:** [Phase 3 Parent](./parent.md)

---

## 1. Problem Statement

The `TileDetailPanel` is well-built — it renders matched features, product info, and chat excerpts from the `Bid.provenance` JSON field. But in practice, **most tiles show the generic "Based on your search" fallback** because provenance data is never populated during sourcing.

The provenance system was designed to answer **"Why was this tile recommended?"** — a core differentiator from plain search engines. Without it, the detail panel adds no value over clicking through to the merchant site.

---

## 2. Solution Overview

Enrich the sourcing pipeline to populate `Bid.provenance` at **bid creation time** by:

1. **Extracting product info** from the raw provider response (brand, specs, condition, shipping).
2. **Matching against choice factors** — which of the user's stated criteria does this product satisfy?
3. **Capturing chat excerpts** — relevant snippets from the conversation that led to this search.

This is a **backend-only change** — the frontend already renders all three provenance sections.

---

## 3. Scope

### In Scope
- Populate `Bid.provenance` JSON during bid creation in `routes/rows_search.py`
- Extract structured product info from provider response payloads
- Match product attributes against row's `choice_factors` and `choice_answers`
- Extract relevant chat excerpts from `Row.chat_history`
- Backfill provenance for existing bids via a one-time migration script

### Out of Scope
- LLM-generated provenance summaries (too expensive per tile; defer to Phase 4)
- User-facing provenance editing
- Provenance for service provider tiles (different UX — they show contact info instead)

---

## 4. User Stories

**US-01:** As a buyer, I want to click on a tile and see WHY it was recommended so I can make informed decisions.

**US-02:** As a buyer comparing two similar tiles, I want to see which of my stated criteria each tile matches so I can quickly identify the best fit.

**US-03:** As a buyer, I want to see the conversation context that led to this recommendation so I can recall what I asked for.

---

## 5. Acceptance Criteria

| ID | Criteria |
|----|----------|
| AC-01 | ≥60% of newly created bids have non-empty `provenance` JSON. |
| AC-02 | `product_info` section includes at minimum: brand (if available), source provider, condition. |
| AC-03 | `matched_features` lists specific choice factors this bid satisfies (e.g., "Budget: under $500 ✓"). |
| AC-04 | `chat_excerpts` includes 1–3 relevant user messages from the row's chat history. |
| AC-05 | TileDetailPanel renders all three sections without changes (existing code already handles this). |
| AC-06 | Provenance generation adds <100ms to bid creation time (no LLM calls). |

---

## 6. Technical Design

### 6.1 Provenance Schema

The `Bid.provenance` field stores JSON with this structure (already expected by `TileDetailPanel`):

```json
{
  "product_info": {
    "brand": "Sony",
    "condition": "new",
    "source_provider": "serpapi_google_shopping",
    "specs": {
      "weight": "1.2 lbs",
      "dimensions": "6x4x2 in"
    }
  },
  "matched_features": [
    "Price $299 is within your $500 budget",
    "Brand: Sony (matches your preference)",
    "Condition: New (as requested)",
    "Free shipping available"
  ],
  "chat_excerpts": [
    { "role": "user", "content": "I need wireless headphones under $500" },
    { "role": "assistant", "content": "I'll search for wireless headphones within your budget." }
  ]
}
```

### 6.2 Provenance Builder

Create `utils/provenance.py`:

```python
def build_provenance(
    raw_result: dict,          # Raw provider response
    row: Row,                  # The row this bid belongs to
    source_provider: str,      # e.g., "serpapi_google_shopping"
) -> dict:
    """Build structured provenance data for a bid."""

    provenance = {}

    # 1. Product Info — extract from raw provider data
    provenance["product_info"] = extract_product_info(raw_result, source_provider)

    # 2. Matched Features — compare against choice factors
    provenance["matched_features"] = match_choice_factors(
        raw_result, row.choice_factors, row.choice_answers
    )

    # 3. Chat Excerpts — extract relevant snippets
    provenance["chat_excerpts"] = extract_chat_excerpts(row.chat_history, row.title)

    return provenance
```

### 6.3 Product Info Extraction

Provider-specific extractors that normalize raw response data:

```python
def extract_product_info(raw: dict, provider: str) -> dict:
    info = {
        "source_provider": provider,
        "condition": raw.get("condition", "new"),
    }

    # SerpAPI Google Shopping
    if provider.startswith("serpapi"):
        info["brand"] = raw.get("brand") or raw.get("product_info", {}).get("brand")
        info["specs"] = raw.get("specifications", {})

    # Rainforest API (Amazon)
    elif provider.startswith("rainforest"):
        info["brand"] = raw.get("brand")
        info["specs"] = {
            s.get("name", ""): s.get("value", "")
            for s in raw.get("specifications", [])
        }

    # Generic fallback
    else:
        info["brand"] = raw.get("brand")

    return {k: v for k, v in info.items() if v}  # Remove empty values
```

### 6.4 Choice Factor Matching

```python
def match_choice_factors(raw: dict, factors_json: str, answers_json: str) -> list[str]:
    factors = json.loads(factors_json) if factors_json else []
    answers = json.loads(answers_json) if answers_json else {}
    matched = []

    price = raw.get("price") or raw.get("extracted_price")

    # Budget check
    budget = answers.get("max_budget") or answers.get("budget")
    if budget and price:
        try:
            if float(price) <= float(budget):
                matched.append(f"Price ${price} is within your ${budget} budget")
        except (ValueError, TypeError):
            pass

    # Brand check
    preferred_brand = answers.get("preferred_brand") or answers.get("brand")
    product_brand = raw.get("brand", "")
    if preferred_brand and product_brand:
        if preferred_brand.lower() in product_brand.lower():
            matched.append(f"Brand: {product_brand} (matches your preference)")

    # Condition check
    preferred_condition = answers.get("condition")
    product_condition = raw.get("condition", "new")
    if preferred_condition and preferred_condition.lower() == product_condition.lower():
        matched.append(f"Condition: {product_condition} (as requested)")

    # Shipping check
    shipping = raw.get("shipping") or raw.get("delivery")
    if shipping and "free" in str(shipping).lower():
        matched.append("Free shipping available")

    # Rating check
    rating = raw.get("rating")
    if rating and float(rating) >= 4.0:
        matched.append(f"Highly rated: {rating}/5 stars")

    return matched
```

### 6.5 Chat Excerpt Extraction

```python
def extract_chat_excerpts(chat_history_json: str, row_title: str, max_excerpts: int = 3) -> list[dict]:
    if not chat_history_json:
        return []

    try:
        messages = json.loads(chat_history_json)
    except (json.JSONDecodeError, TypeError):
        return []

    # Take the first user message and the first assistant response
    excerpts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content and len(content) > 10:
            excerpts.append({
                "role": role,
                "content": content[:200]  # Truncate long messages
            })
            if len(excerpts) >= max_excerpts:
                break

    return excerpts
```

### 6.6 Integration Point

In `routes/rows_search.py`, where bids are created from search results, call `build_provenance()`:

```python
from utils.provenance import build_provenance

# When creating a Bid from a search result:
provenance = build_provenance(
    raw_result=result.raw_data,  # The raw provider response
    row=row,
    source_provider=result.source,
)
bid.provenance = json.dumps(provenance)
```

### 6.7 Backfill Script

`scripts/backfill_provenance.py` — one-time script to populate provenance for existing bids that have `source_payload` data:

```python
async def backfill():
    async with get_session() as session:
        bids = await session.exec(
            select(Bid).where(Bid.provenance.is_(None), Bid.source_payload.isnot(None))
        )
        for bid in bids:
            row = await session.get(Row, bid.row_id)
            raw = json.loads(bid.source_payload) if bid.source_payload else {}
            provenance = build_provenance(raw, row, bid.source)
            bid.provenance = json.dumps(provenance)
        await session.commit()
```

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Bids with non-empty provenance | ≥60% of new bids |
| Bids with ≥1 matched feature | ≥40% of new bids |
| TileDetailPanel "Based on your search" fallback rate | <40% (down from ~95%) |
| Provenance build time per bid | <100ms |

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Raw provider data doesn't include brand/specs | Populate what's available; fallback gracefully |
| Chat history is empty for rows created via URL share | Use row title as fallback excerpt |
| Provenance data gets stale if user changes choice answers | Re-build provenance on re-search (already happens since new bids are created) |

---

## 9. Implementation Checklist

- [ ] Create `utils/provenance.py` with `build_provenance()`, `extract_product_info()`, `match_choice_factors()`, `extract_chat_excerpts()`
- [ ] Integrate provenance building into bid creation in `routes/rows_search.py`
- [ ] Ensure `source_payload` is populated during sourcing (may need to pass raw data through)
- [ ] Create `scripts/backfill_provenance.py`
- [ ] Write unit tests for each provenance builder function
- [ ] Verify TileDetailPanel renders enriched data (manual click-test)
- [ ] Monitor provenance population rate in production
