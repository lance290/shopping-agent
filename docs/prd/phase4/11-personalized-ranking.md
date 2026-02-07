# PRD: Personalized Ranking / Learning-to-Rank

**Status:** Partial — non-compliant (scoring exists but not surfaced or learned)  
**Created:** 2026-02-07  
**Last Updated:** 2026-02-07  
**Priority:** P2  
**Origin:** `PRD-buyanything.md` Section 4.4 — "As the buyer clicks/reorders, ranking should improve (initially heuristic; later learned)"

---

## Problem Statement

Offer tiles are currently displayed without a visible, user-facing ranking model. There is an internal scoring function in the search pipeline, but scores are not persisted to bids, not exposed in the UI, and there is no behavioral learning loop. The original PRD envisioned a feedback loop where buyer interactions (clicks, thumbs up/down, selections) improve result quality over time.

Two distinct problems:

1. **Scoring exists but is not persisted or surfaced** — results lack `relevance_score`, `price_score`, or `combined_score` on persisted `Bid` records
2. **No learning from behavior** — user signals (clicks, likes, selections) are logged but never fed back into ranking

---

## Requirements

### Phase A: Heuristic Scoring (P1 — prerequisite)

Before learning, results need a baseline score.

#### R1: Static Scoring Model

Score each offer tile against the user's choice factors and constraints.

**Scoring dimensions (aligned with existing `sourcing/scorer.py`):**
| Dimension | Weight | Source |
|-----------|--------|--------|
| `price_score` | 0.35 | How well price fits `min_price`/`max_price` from `choice_answers` |
| `relevance_score` | 0.30 | Text similarity of offer title/description to search query + choice factors |
| `quality_score` | 0.25 | Rating, reviews count, seller verification level |
| `diversity_bonus` | 0.10 | Small bonus for results from underrepresented providers |

**Note:** These weights match the existing scorer in `sourcing/scorer.py`. The scorer already computes these dimensions and stores them in `provenance.score`. The gap is that scores are **not persisted to `Bid` fields** and **not exposed in the UI**.

**Combined:** `combined_score = Σ(weight × dimension_score)`

**Acceptance criteria:**
- [ ] Each `Bid` gets `combined_score` computed on creation
- [ ] Tiles sorted by `combined_score` descending by default
- [ ] Score dimensions stored for explainability (tile detail panel)
- [ ] Price scoring uses `choice_answers.min_price` / `max_price` when available

#### R2: Choice-Factor Matching

When a row has `choice_factors` and `choice_answers`, score offers against them.

**Example:** User wants a bike, specified `frame_material: carbon`, `bike_size: L`. Offers mentioning "carbon frame" and "size L" score higher on relevance.

**Implementation:** LLM-based or keyword matching against offer `description` + `source_payload`.

**Acceptance criteria:**
- [ ] Offers matching explicit choice factor values score 20% higher on relevance
- [ ] Matching factors highlighted in tile detail view

---

### Phase B: Behavioral Learning (P3 — after heuristic is stable)

#### R3: Signal Collection

Capture implicit and explicit user signals.

| Signal | Type | Weight | Source |
|--------|------|--------|--------|
| Clickout | Implicit positive | 0.3 | `ClickoutEvent` |
| Like | Explicit positive | 0.5 | `Like` on bid |
| Select/lock-in | Explicit strong positive | 1.0 | `Bid.is_selected` |
| Thumbs down | Explicit negative | -0.5 | New: `Dislike` model or `Like.value = -1` |
| Dwell time on tile | Implicit positive | 0.2 | Frontend beacon (time on hover/expanded view) |
| Skip (viewed but not clicked) | Implicit negative | -0.1 | Frontend beacon |

**Acceptance criteria:**
- [ ] All signals logged with `user_id`, `bid_id`, `row_id`, `timestamp`
- [ ] Signals stored in a `UserSignal` table (not mixed into existing models)

#### R4: Per-User Preference Model

Build a lightweight preference model per user.

**Approach (start simple):**
- Track user's preferred `merchant_domain`s (clicked/liked more often)
- Track user's preferred `source` providers
- Track price range preferences (from actual clicks vs. stated budget)
- Track category affinities

**Storage:** `UserPreference` table with key-value pairs per user.

**Application:** Boost scores for offers matching user preferences by 10-15%.

**Acceptance criteria:**
- [ ] Preferences updated after each clickout/like/select
- [ ] Preferences applied as a score modifier on subsequent searches
- [ ] User can reset preferences ("Show me fresh results")

#### R5: Cross-User Learning (P4 — future)

Aggregate signals across users to improve ranking for new users.

**Approach:** Collaborative filtering — "users who clicked X also clicked Y."

**Acceptance criteria:**
- [ ] Popular offers (high click rate across users) get a small boost
- [ ] New users get recommendations based on similar users' behavior
- [ ] Cold-start handled gracefully (fall back to heuristic scoring)

---

## Technical Implementation

### Backend

**New models:**
- `UserSignal(user_id, bid_id, row_id, signal_type, value, timestamp)`
- `UserPreference(user_id, preference_key, preference_value, updated_at)`

**Modified models:**
- `Bid` — Add `combined_score`, `relevance_score`, `price_score`, `quality_score`, `diversity_bonus`

**New files:**
- `apps/backend/services/scoring.py` — Heuristic scoring engine
- `apps/backend/services/ranking.py` — Preference-based re-ranking

**Modified files:**
- `apps/backend/routes/rows.py` — Apply scoring on search results before returning
- `apps/backend/sourcing/repository.py` — Score normalization step

### Frontend

- Sort tiles by `combined_score` (already sorted server-side)
- Thumbs down button on tiles (new interaction)
- "Why this result?" link in tile detail (shows score breakdown)
- Dwell-time beacon (track hover/expanded time, send to backend)

### BFF

- No changes — scoring is backend-only.

---

## Dependencies

- `01-search-architecture-v2.md` — Scoring builds on the aggregator layer (L5)
- `07-workspace-tile-provenance.md` — Tile detail panel needed to show score breakdown
- `09-analytics-success-metrics.md` — CTR metrics needed to measure ranking quality

---

## Effort Estimate

- **Phase A (R1-R2):** Medium (2-3 days — scoring engine + integration)
- **Phase B (R3-R4):** Large (1 week — signal collection + preference model)
- **R5:** Large (future — requires significant user base for meaningful signal)
