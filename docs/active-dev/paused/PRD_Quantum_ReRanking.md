# PRD: Quantum Re-Ranking

**Status**: Draft  
**Date**: 2026-02-15  
**Origin**: User Intention Audit (Gap 3) + HeyLois/eco-system/quantum analysis  
**Priority**: P1 — parallel workstream with Autonomous Outreach  
**Depends on**: PRD_Desire_Classification (for structured constraints used in scoring)

---

## 1. The Problem (Spirit)

The current scorer (`sourcing/scorer.py`) ranks results by counting keywords in titles. This is the equivalent of a librarian who recommends books by checking if the title contains the words you said, rather than understanding what you're actually looking for.

**Current scoring weights:**
- Relevance (50%): Keyword overlap in title text
- Quality (20%): Rating, review count, has image, has shipping info
- Price (20%): Within budget range
- Diversity (10%): Provider variety bonus

**Where this fails:**

| User wants | Top result (by keyword counting) | What should rank #1 |
|---|---|---|
| "Light jet with Wi-Fi for 4 pax" | "Jet Engine Model Kit — Great Reviews!" | "Citation CJ3+ Charter — Wi-Fi, 7 Seats" |
| "Organic cotton baby blanket" | "Baby Cotton Balls 100-pack" | "Coyuchi Organic Muslin Swaddle Blanket" |
| "Mid-century modern desk lamp" | "Desk Lamp LED — Modern Design" | "Noguchi Akari Table Lamp (1951)" |

The keyword matcher doesn't understand that "Citation CJ3+" *is* a light jet, that "Coyuchi" *is* organic cotton, or that "Noguchi Akari" *is* mid-century modern. It just counts word overlaps.

**For vendor directory results, it's even worse.** Vendors don't have ratings, review counts, or shipping info. They always get `quality_score = 0.3` (base minimum). A world-class charter operator with 30 years of experience scores the same quality as a fly-by-night broker.

### The Genie Test

> "I ranked the results for you." — Yes, but the best result is on page 2 because it didn't contain the exact keywords, and a keyword-stuffed irrelevant result is #1. The letter was satisfied. The spirit was violated.

---

## 2. The Vision (What "Done" Looks Like)

A user searches for: **"Light jet charter from Teterboro to Aspen, 4 passengers, Wi-Fi preferred"**

The system:
1. Generates a query embedding (1536-dim, same as vendor embeddings)
2. Retrieves candidates from web search + vendor directory
3. Generates embeddings for web search results that don't have them
4. Runs **quantum re-ranking**: each candidate scored by photonic quantum kernel against the query
5. Applies **constraint satisfaction**: does the vendor fly TEB→ASE? Light jets? Wi-Fi equipped?
6. Computes **blended score**: quantum similarity + constraint fit + classical signals (price, quality)
7. Surfaces **serendipitous discoveries**: vendors with high quantum score but low keyword overlap (e.g., a boutique operator the user wouldn't have found via text search)

**The top results are the ones that best satisfy the user's actual desire — not the ones with the most keyword overlap.**

---

## 3. The Quantum Advantage (Why Not Just Cosine Similarity?)

The sibling project (`HeyLois/eco-system/quantum`) has a production `XanaduQuantumReranker` that uses continuous-variable photonic quantum computing for similarity scoring. Key advantages over classical cosine similarity:

### 3.1 Interference-Based Similarity

Classical cosine similarity computes a single dot product. The quantum kernel maps embeddings to photonic circuit parameters and measures interference patterns. This captures non-linear relationships between embedding dimensions that cosine similarity misses.

**Concrete example**: Two charter operators might have similar embeddings (both are "jet charters") but different interference patterns when measured against a query about "light jets for 4 passengers." The quantum kernel can distinguish "light jet operator" from "heavy jet operator" even when their embeddings are close in cosine space.

### 3.2 Novelty Scoring

The quantum reranker computes a `noveltyScore`: results where the quantum score is *higher* than the classical score. These are **serendipitous discoveries** — results that a keyword/cosine system would rank low but that the quantum kernel identifies as highly relevant.

For BuyAnything, this surfaces:
- A boutique charter operator who's a perfect fit but doesn't use the keywords the user typed
- A bespoke jeweler whose style matches what the user described but whose listing title is cryptic
- A vendor in a related category the user didn't think to search (e.g., searching for "HVAC" and discovering a geothermal installer)

### 3.3 Coherence Scoring

The `coherenceScore` measures how stable the quantum similarity is across measurement repetitions. High coherence = strong, robust match. Low coherence = the match is fragile/coincidental.

This is a quality signal that doesn't depend on Amazon-shaped metrics (ratings, reviews). It works equally well for vendors, services, and bespoke providers.

---

## 4. Technical Design

### 4.1 Architecture Overview

```
Search results (from all providers)
        │
        ▼
  Classical Scorer (existing scorer.py — price, keyword, quality, diversity)
        │
        ▼
  Embedding Generation (for results that don't have embeddings)
        │
        ▼
  Quantum Re-Ranker (XanaduQuantumReranker — ported from quantum project)
        │
        ├── quantumScore: photonic kernel similarity
        ├── classicalScore: cosine similarity  
        ├── noveltyScore: quantum advantage signal
        ├── coherenceScore: match robustness
        └── blendedScore: final ranking score
        │
        ▼
  Constraint Satisfaction Scorer (uses structured_constraints from Desire Classification)
        │
        ▼
  Final ranked results
```

### 4.2 Porting the Quantum Reranker

**Source**: `HeyLois/eco-system/quantum/backend/app/services/`

Files to port:
- `xanadu_quantum_reranker.py` → `apps/backend/sourcing/quantum/reranker.py`
- `quantum_reranker_service.py` → `apps/backend/sourcing/quantum/service.py`
- `quantum/quantum_device.py` → `apps/backend/sourcing/quantum/device.py`
- `quantum/quantum_utils.py` → `apps/backend/sourcing/quantum/utils.py`
- `quantum/quantum_operations.py` → `apps/backend/sourcing/quantum/operations.py`
- `quantum/quantum_metrics.py` → `apps/backend/sourcing/quantum/metrics.py`

**Key adaptation**: The quantum project uses FAISS for initial retrieval + quantum for reranking. We use pgvector for initial retrieval + quantum for reranking. The reranker interface is the same:

```python
# Input: query embedding + list of results with embeddings
# Output: reranked results with quantum scores
results = await reranker.rerank_results(
    query_embedding=query_emb,    # 1536-dim float list
    search_results=candidates,     # list of dicts with 'embedding' key
    top_k=50,
    enable_novelty=True,
    enable_coherence=True
)
```

### 4.3 Embedding Generation for Web Results

Vendor directory results already have 1536-dim embeddings (from pgvector). Web search results do not.

**Option A: Generate on-the-fly** (simple, higher latency)
```python
async def ensure_embeddings(results):
    """Generate embeddings for results that don't have them."""
    missing = [r for r in results if not r.get('embedding')]
    if missing:
        texts = [f"{r['title']} {r.get('snippet', '')}" for r in missing]
        embeddings = await openrouter_embed_batch(texts)
        for r, emb in zip(missing, embeddings):
            r['embedding'] = emb
    return results
```

**Option B: Skip web results in quantum reranking** (simpler, less powerful)
- Only quantum-rerank vendor directory results (which already have embeddings)
- Use classical scorer for web results
- Merge the two ranked lists with interleaving

**Recommendation**: Start with Option B for MVP. Add Option A when we have budget/latency headroom.

### 4.4 Constraint Satisfaction Scorer

This is new — neither the current scorer nor the quantum reranker handles structured constraints.

```python
def constraint_satisfaction_score(result, constraints):
    """Score how well a result satisfies structured constraints.
    
    Returns 0.0-1.0. Each satisfied constraint adds to the score.
    Unsatisfied hard constraints return 0.0.
    """
    if not constraints:
        return 0.5  # No constraints = neutral
    
    score = 0.0
    total_weight = 0.0
    
    # Route match (for travel/charter)
    if "origin" in constraints:
        total_weight += 1.0
        if result_serves_route(result, constraints["origin"], constraints.get("destination")):
            score += 1.0
    
    # Aircraft class match
    if "aircraft_class" in constraints:
        total_weight += 0.8
        if result_matches_aircraft(result, constraints["aircraft_class"]):
            score += 0.8
    
    # Capacity match
    if "passengers" in constraints:
        total_weight += 0.6
        if result_fits_capacity(result, constraints["passengers"]):
            score += 0.6
    
    # Date availability (soft constraint — we can't always verify)
    if "date" in constraints:
        total_weight += 0.3
        score += 0.3  # Assume available unless we know otherwise
    
    # Feature match (Wi-Fi, etc.)
    if "features" in constraints:
        total_weight += 0.3
        matched = sum(1 for f in constraints["features"] 
                     if feature_present(result, f))
        score += 0.3 * (matched / len(constraints["features"]))
    
    return score / total_weight if total_weight > 0 else 0.5
```

### 4.5 Final Score Blending

The final ranking combines all scoring dimensions:

```python
def compute_final_score(result):
    """Combine all scoring signals into a final rank."""
    
    # Classical signals (from existing scorer.py)
    price_score = result.provenance["score"]["price"]       # 0-1
    keyword_score = result.provenance["score"]["relevance"] # 0-1
    quality_score = result.provenance["score"]["quality"]   # 0-1
    diversity_score = result.provenance["score"]["diversity"] # 0-1
    
    # Quantum signals (from quantum reranker)
    quantum_blended = result.get("blendedScore", 0.0)      # 0-1
    novelty = result.get("noveltyScore", 0.0)              # 0-1
    coherence = result.get("coherenceScore", 0.0)          # 0-1
    
    # Constraint satisfaction (from constraint scorer)
    constraint_fit = result.get("constraintScore", 0.5)    # 0-1
    
    # Has quantum scores?
    has_quantum = result.get("quantum_reranked", False)
    
    if has_quantum:
        # Quantum-enhanced scoring
        final = (
            quantum_blended * 0.30 +    # Semantic fit (quantum)
            constraint_fit  * 0.25 +     # Does it satisfy what the user asked?
            price_score     * 0.15 +     # Price fit
            coherence       * 0.10 +     # Match robustness
            novelty         * 0.10 +     # Serendipity bonus
            quality_score   * 0.05 +     # Classical quality signals
            diversity_score * 0.05       # Provider variety
        )
    else:
        # Classical scoring (web results without embeddings)
        final = (
            keyword_score   * 0.35 +     # Best we have without embeddings
            constraint_fit  * 0.25 +     # Constraint satisfaction
            price_score     * 0.20 +     # Price fit
            quality_score   * 0.15 +     # Ratings, reviews
            diversity_score * 0.05       # Provider variety
        )
    
    return final
```

**Key design choice**: Quantum-enhanced results weight semantic fit (30%) and constraint satisfaction (25%) highest. Classical results weight keyword relevance (35%) highest because that's the best signal available without embeddings.

### 4.6 Simulation Mode vs Hardware Mode

The `XanaduQuantumReranker` supports both:
- **Hardware mode**: Connects to Xanadu X8/X12/X216 photonic quantum hardware via cloud API
- **Simulation mode**: Runs Strawberry Fields simulator locally (NumPy-based)

For BuyAnything MVP, we use **simulation mode**. It's slower than hardware but:
- No quantum cloud API key required
- No per-query costs
- Results are mathematically identical (just slower to compute)
- Latency is acceptable for our use case (reranking 50 results takes ~200ms in simulation)

Hardware mode becomes relevant when we need to rerank 1000+ results in real-time.

---

## 5. Dependencies & Requirements

### Python Packages (add to requirements.txt)

```
strawberryfields>=0.23.0    # Xanadu's quantum computing framework
thewalrus>=0.20.0           # Quantum optics calculations
numpy>=1.24.0               # Already present
```

### Environment Variables

```
QUANTUM_RERANKING_ENABLED=true       # Feature flag
QUANTUM_N_MODES=8                     # Photonic modes (default: 8)
QUANTUM_CUTOFF_DIM=10                 # Fock space cutoff (default: 10)
QUANTUM_BLEND_FACTOR=0.7             # Quantum vs classical blend (default: 0.7)
```

### Graceful Degradation

If Strawberry Fields is not installed or quantum initialization fails:
- Log a warning
- Fall back to classical scoring (existing `scorer.py`)
- Results are still ranked — just without quantum enhancement
- No user-visible error

This is already the pattern in the quantum project's `QuantumRerankerService`:
```python
if not self.is_available():
    return search_results[:top_k]  # Graceful fallback
```

---

## 6. Success Metrics

### Letter Metrics
- Quantum reranking latency (target: < 500ms for 50 results in simulation mode)
- Embedding generation latency for web results (target: < 300ms for batch of 20)
- Feature flag toggle works without restart

### Spirit Metrics
- **Rank inversion rate**: How often does a human reviewer say "result #5 should be #1"? (Baseline: measure with current keyword scorer. Target: 50% reduction.)
- **Serendipity rate**: What % of user-selected results had high `noveltyScore`? (These are results the user *wouldn't have found* with keyword search.)
- **Constraint satisfaction at rank 1**: Does the #1 result actually satisfy the user's stated constraints? (Baseline: unmeasured. Target: > 70% for service tier.)
- **Vendor selection rate**: Do users select vendors more often when results are quantum-reranked? (A/B test once we have enough traffic.)

---

## 7. Rollout Plan

### Phase 1: Port & Integrate (2 weeks)
- Port quantum reranker code from sibling project
- Add Strawberry Fields to requirements
- Wire into `sourcing/service.py` as a post-scoring step
- Feature flag: `QUANTUM_RERANKING_ENABLED`
- Vendor directory results only (already have embeddings)
- Log quantum scores alongside classical scores for comparison
- **Do not change ranking yet** — just log and compare

### Phase 2: A/B Test (1-2 weeks)
- 50/50 split: classical scoring vs quantum-enhanced scoring
- Measure: rank inversion rate, selection rate, constraint satisfaction
- Tune `QUANTUM_BLEND_FACTOR` based on results

### Phase 3: Constraint Satisfaction (1 week)
- Implement constraint satisfaction scorer
- Integrate with `structured_constraints` from Desire Classification PRD
- Add to final score blending

### Phase 4: Web Result Embeddings (1-2 weeks)
- Generate embeddings for web search results on-the-fly
- Quantum-rerank the full result set (not just vendor results)
- Monitor latency and cost impact

### Phase 5: Hardware Mode (future)
- When result volume justifies it, enable Xanadu cloud hardware
- Latency drops from ~200ms to ~50ms for 50 results
- Enables real-time reranking of 1000+ results

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Strawberry Fields dependency is heavy / fragile | Feature flag for graceful degradation; simulation-only in MVP |
| Quantum scores don't improve ranking in practice | Phase 1 logs both scores without changing ranking; Phase 2 A/B tests before committing |
| Embedding generation for web results is too slow/expensive | Start with vendor-only quantum reranking (Option B); add web results later |
| Constraint satisfaction data is sparse (vendors don't have route/aircraft metadata) | Constraints are additive bonuses, not hard filters; score degrades gracefully to quantum-only |
| Quantum reranking adds latency to search | Runs after initial results are displayed; can be async "re-sort" while user browses |

---

## 9. The Spirit Check

Before shipping any milestone, ask:

> If the #1 result is a keyword-stuffed Amazon listing and the perfect vendor is ranked #8 — have we shipped anything of value?

> If a user asks for a "light jet with Wi-Fi" and the top result is a heavy jet without Wi-Fi that happens to contain the word "jet" more times — have we shipped anything of value?

> If we log quantum scores but never use them to change rankings — have we shipped anything of value?

The quantum reranker exists to make the *best* result rank *first* — not the most keyword-dense result. Results should be ranked by how well they satisfy the user's actual desire, measured through semantic similarity, constraint satisfaction, and serendipitous discovery. That's the spirit. Keyword counting is just the letter.
