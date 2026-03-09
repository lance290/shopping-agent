# PRD: Quantum Reranker Advancement Program

## 1. Executive Summary

BuyAnything should treat the current quantum reranker as an experimental ranking system that runs in parallel, collects evidence continuously, and gets stronger over time.

The goal of this PRD is not to justify quantum hardware today. The goal is to build a ranking program that:

- improves real search quality materially over the current baseline
- collects the right evidence from live traffic while remaining production-safe
- creates a reusable evaluation corpus from actual BuyAnything usage
- keeps the algorithm portable so that future commercial quantum hardware can be tested without re-architecting the system

This work should begin in shadow mode. The existing ranking path remains user-facing while the quantum reranker runs in parallel, logs its scores, produces counterfactual rankings, and accumulates evaluation data from real user behavior.

Affiliate-heavy searches are a major advantage here. They generate high-volume impressions, clicks, selections, and purchase-proxy events, which gives the system many more examples than a pure bespoke-service-only workflow.

---

## 2. Product Decisions Locked By This PRD

### 2.1 This is an evaluation-first workstream
The first milestone is not “ship quantum ranking to all users.”

The first milestone is:

- run the reranker in parallel
- log its outputs alongside the baseline
- measure whether it would have improved outcomes
- build enough evidence to decide when it should affect ranking

### 2.2 Production ranking must remain stable until the experiment earns promotion
The experimental reranker must not replace the live baseline until it has outperformed the baseline on agreed metrics.

### 2.3 Real user behavior is the core training and evaluation source
The system should learn from actual search behavior, especially high-volume affiliate and marketplace traffic.

Signals should include user actions such as:

- clickouts
- selections
- likes
- comments
- quote requests
- purchases or purchase-proxy events when available
- dwell and revisit behavior when available

### 2.4 The system must support both implicit and explicit evaluation
Implicit behavioral signals are necessary at scale, but they are not enough on their own.

The program must also support sampled human review for:

- top-k relevance
- “best result should have been #1” checks
- novelty that is actually useful rather than merely surprising

### 2.5 Hardware-readiness matters, but hardware dependency does not
The algorithm should be designed so that a future hardware-backed scorer can plug into the same interface.

This PRD does not assume that Xanadu or any commercial quantum provider is economically justified today.

### 2.6 No brittle heuristic ranking layer should be introduced
This work should not devolve into manual keyword patching or category rules.

The advancement path should come from:

- better representations
- better interaction scoring
- better calibration
- better evaluation data
- better learned blending

---

## 3. Problem Statement

The current reranker is now in better shape technically than before, but it is still an experimental signal rather than a proven relevance engine.

The main gaps are:

- there is no systematic shadow-mode evaluation pipeline
- there is no durable corpus of search impressions and rank outcomes for offline replay
- there is no promotion framework from experiment to controlled rollout
- there is no calibrated evidence that the quantum-style score beats simpler baselines
- there is no hardware-ready abstraction and benchmark plan beyond a local simulator

Without that infrastructure, the reranker risks remaining an interesting toy.

---

## 4. Vision

A user searches for something simple, commercial, or affiliate-heavy such as:

- “best noise cancelling headphones under $300”
- “carry on suitcase for frequent business travel”
- “espresso machine for small office”

Or something complex and bespoke such as:

- “light jet charter Teterboro to Aspen for 4 passengers with Wi-Fi”
- “estate jeweler for Art Deco diamond bracelet”
- “private chef for a three-day Napa retreat”

The system should:

1. retrieve candidates normally
2. score them with the current baseline
3. score them in parallel with one or more experimental rerankers
4. store the full candidate slate, features, and rank positions
5. observe downstream user behavior
6. compute counterfactual performance continuously
7. promote only the rerankers that repeatedly outperform the baseline

When commercial quantum hardware becomes viable, BuyAnything should already have:

- a strong ranking dataset
- a strong simulator baseline
- a hardware-compatible scorer interface
- clear success metrics
- a credible reason to test hardware on a real workload

---

## 5. Goals

### 5.1 Build a durable ranking experimentation platform
Create the logging, storage, replay, and evaluation layers required to improve ranking continuously.

### 5.2 Improve the quantum reranker algorithm materially
Advance beyond the current handcrafted scorer into a stronger family of rerankers with better representations, calibration, and blending.

### 5.3 Harvest live examples from real search traffic
Use affiliate and marketplace searches as a high-volume source of examples while still supporting bespoke service searches.

### 5.4 Establish measurable promotion criteria
Define exactly what a reranker must beat before it is allowed to influence live ranking.

### 5.5 Be ready for future hardware experiments
Keep the scoring interface abstract enough that simulator and hardware backends can be compared on the same queries and candidate sets.

---

## 6. Non-Goals

- committing today to paid quantum hardware usage
- claiming quantum advantage before measurement
- replacing the entire retrieval stack with a hardware-dependent architecture
- building manual ranking rules for categories, brands, or search terms
- shipping a user-visible “quantum” feature purely for marketing

---

## 7. Current State

### 7.1 What exists now
The codebase already has:

- a `QuantumReranker` in `apps/backend/sourcing/quantum/reranker.py`
- simulator-only scoring in NumPy
- per-result signals such as `quantum_score`, `classical_score`, `novelty_score`, `coherence_score`, and `blended_score`
- integration into streaming search and sourcing service paths

### 7.2 What is still missing
The codebase does not yet have:

- a ranking experiment registry
- shadow-run storage of alternative rank orders
- a reusable offline replay dataset
- a labeled or weakly-labeled evaluation corpus
- a promotion gate for experiment rollout
- a hardware adapter boundary beyond the current simulator implementation

---

## 8. Users and Beneficiaries

### 8.1 End users
Users benefit when the best result appears earlier, especially for high-intent searches.

### 8.2 Internal product and engineering
The team benefits from having a rigorous way to improve ranking rather than tuning blindly.

### 8.3 Future research and platform strategy
If quantum hardware becomes commercially viable, the company benefits from having a real-world workload, comparison framework, and evidence base ready.

---

## 9. Core Product Requirements

### 9.1 Shadow-mode parallel reranking
Every eligible search should support running one or more experimental rerankers in parallel with the live ranking path.

Required behavior:

- baseline ranking remains authoritative for the user by default
- experimental rerankers receive the same query and candidate set
- each experiment produces its own ordered list and per-result scores
- the experiment output is stored even when it does not affect the UI

### 9.2 Ranking experiment identity
Each experiment must be versioned and attributable.

Each scored search should record:

- experiment name
- experiment version
- scoring mode (`shadow`, `interleaving`, `partial-rollout`, `live`)
- timestamp
- query and row identifiers
- candidate slate identifier

### 9.3 Candidate slate capture
For replay and auditability, the system must store the candidate slate that each reranker saw.

At minimum, record:

- query text and normalized query text
- row id when available
- candidate ids or stable keys
- provider source
- original baseline rank
- experimental rank
- scoring features used by the reranker when feasible

### 9.4 Outcome capture
The system must tie downstream user behavior back to the candidate slate and rank positions.

Target outcomes include:

- clickout
- selected offer
- like
- comment
- quote request
- purchase or purchase-proxy event
- share behavior when relevant
- return-to-row or revisit behavior when relevant

### 9.5 Counterfactual evaluation
The platform must support analysis such as:

- did the clicked result move up or down under the experiment?
- was the selected result ranked higher by the experiment than by baseline?
- would the experiment have improved MRR, NDCG, or top-k hit rate?
- did novelty correlate with good outcomes or bad surprises?

### 9.6 Explicit review dataset
The system must support sampled manual review of saved result slates.

Reviewers should be able to judge:

- top-1 quality
- top-3 ordering quality
- whether a result is relevant
- whether a result is a useful novel discovery
- whether the experiment improved or degraded the ranking

### 9.7 Algorithm family expansion
The reranker program must support multiple algorithm variants rather than one monolith.

Initial variants should include:

- current simulator-based quantum reranker
- improved quantum-inspired reranker with better reduction and calibration
- cosine-only baseline reranker
- learned blend variant using observed outcomes
- optional lightweight neural reranker for comparison

### 9.8 Hardware adapter boundary
The scoring system must expose a backend interface that allows the same reranker contract to be implemented by:

- local simulator
- future Xanadu-compatible cloud hardware
- other future experimental backends

The surrounding pipeline should not need to change when swapping scoring backends.

---

## 10. Technical Requirements

### 10.1 Ranking experiment data model
Create a durable way to store ranking experiments and outcomes.

Recommended entities:

- `RankingExperiment`
- `RankingRun`
- `RankingRunCandidate`
- `RankingOutcome`
- `RankingLabel` for explicit human judgments

If implementation chooses different names, the capability requirements still apply.

### 10.2 Stable candidate identity
Each result in a candidate slate must have a stable identity suitable for replay and attribution.

Acceptable examples include:

- `bid_id` when persisted
- canonical URL or stable item URL normalization
- provider-specific stable key when canonical URL is absent

### 10.3 Feature logging
Each candidate should log the features needed for offline analysis when feasible.

Examples:

- baseline relevance/price/quality/diversity scores
- quantum score outputs
- provider type
- position in original ranking
- whether the result had an embedding
- desire tier and structured constraints when present

### 10.4 Replay harness
Build a replay tool that can:

- load historical ranking runs
- re-run one or more rerankers on the saved candidate slates
- compare rank movements and evaluation metrics
- export analysis for product review

### 10.5 Metrics pipeline
Support at least the following evaluation metrics:

- MRR
- NDCG@k
- Recall@k where labels exist
- click-weighted MRR
- selected-result uplift
- quote-request uplift
- purchase-proxy uplift
- novelty-success rate
- bad-surprise rate

### 10.6 Eligibility rules for shadow mode
Not every search must run every experiment.

Eligibility can be based on operational constraints such as:

- candidate count threshold
- embedding availability
- provider mix
- latency budget

These eligibility rules should be operational, not manual category heuristics.

### 10.7 Latency isolation
Experimental reranking must not materially degrade user-perceived search responsiveness during shadow mode.

If needed, shadow scoring may complete after initial results are shown, provided the run is still fully logged.

### 10.8 Configurability
The platform must allow:

- enabling/disabling experiments independently
- per-experiment rollout percentages
- per-experiment shadow vs live mode
- score logging verbosity controls

---

## 11. Algorithm Advancement Requirements

### 11.1 Improve representation reduction
The reranker must support richer embedding-to-mode reduction strategies.

The progression should include:

- chunked full-vector pooling
- fixed seeded projection
- optional learned projection trained offline
- comparative evaluation of reduction methods

### 11.2 Preserve signed interaction signals
Raw similarity signals should retain their signed meaning where appropriate.

If downstream ranking requires normalization, normalization should happen explicitly and transparently.

### 11.3 Calibrate the final score
The system should move beyond a fixed handcrafted blend where possible.

Later phases should support:

- learned blending from observed outcomes
- calibration against explicit relevance labels
- per-surface calibration when evidence justifies it

### 11.4 Support novelty without rewarding weirdness
Novelty should be treated as valuable only when it also correlates with useful outcomes.

The system should explicitly measure:

- good novelty
- neutral novelty
- bad novelty

### 11.5 Separate research and production scoring
Research variants may emit many diagnostic signals.

Production promotion should require:

- a stable score contract
- documented semantics
- reproducible evaluation wins

---

## 12. Launch and Rollout Plan

### Phase 1: Instrumentation and shadow infrastructure
Build the experiment registry, run logging, candidate slate capture, and outcome attribution.

Acceptance for Phase 1:

- experimental reranker can run in parallel with no user-facing ranking change
- runs are stored with candidate slates and scores
- downstream click/select signals can be joined back to rank positions

### Phase 2: Offline replay and evaluation
Build replay tooling and metric dashboards or reports.

Acceptance for Phase 2:

- historical runs can be replayed
- baseline vs experiment metrics can be compared on the same corpus
- sampled review workflow exists for explicit judgments

### Phase 3: Algorithm improvement program
Implement multiple reranker variants and compare them.

Acceptance for Phase 3:

- at least three reranker variants can be scored on the same slate
- reduction strategy comparisons are measurable
- novelty and coherence behavior are analyzed, not just logged

### Phase 4: Controlled live influence
Allow winning experiments to influence ranking in narrow rollouts.

Acceptance for Phase 4:

- experiment can control a limited percentage of live ranking
- rollback is immediate via configuration
- promotion gates are documented and enforced

### Phase 5: Hardware-ready backend abstraction
Create or refine the scorer backend interface for simulator vs future hardware.

Acceptance for Phase 5:

- simulator and alternate backends conform to the same scorer contract
- a benchmark harness can compare latency and ranking quality across backends
- no production dependency on hardware is introduced by default

---

## 13. Success Metrics

### 13.1 Product metrics
- increase in selected-result rate for searched rows
- increase in clickout-to-selection efficiency
- increase in quote-request conversion on relevant rows
- increase in purchase-proxy conversion where trackable

### 13.2 Ranking metrics
- better MRR than baseline
- better NDCG@5 and NDCG@10 than baseline
- higher rate that the selected result appears in top 3
- lower rate of obvious rank inversions in human review

### 13.3 Novelty quality metrics
- percentage of positive outcomes involving high-novelty results
- bad-surprise rate for high-novelty results
- percentage of high-novelty results later judged relevant by humans

### 13.4 Operational metrics
- shadow scoring success rate
- reranker latency distribution
- percentage of runs with complete slate capture
- percentage of runs with attributable downstream outcome data

### 13.5 Strategic metrics
- number of replayable ranking examples collected
- number of explicitly labeled ranking examples collected
- readiness to benchmark simulator vs hardware on the same workload

---

## 14. Promotion Criteria

An experiment must not affect live ranking broadly until it demonstrates all of the following:

- statistically credible improvement on agreed ranking metrics
- no unacceptable regression in user outcomes
- no unacceptable latency or reliability regression
- no evidence that novelty is increasing low-quality surprises
- reproducible wins across more than one search surface or query segment

---

## 15. Risks and Mitigations

### 15.1 Risk: We collect lots of data but no usable labels
Mitigation:

- define clear join paths from ranking run to downstream outcome
- sample explicit review sets regularly
- prioritize surfaces with rich user actions first

### 15.2 Risk: The reranker overfits affiliate traffic and underperforms on bespoke searches
Mitigation:

- segment evaluation by surface and query type
- maintain separate reports for affiliate-heavy and bespoke-service traffic
- do not promote globally from one segment alone

### 15.3 Risk: Novelty becomes a gimmick signal
Mitigation:

- track good-novelty vs bad-novelty outcomes
- require human review on high-novelty samples
- do not reward novelty independent of usefulness

### 15.4 Risk: Hardware abstraction adds complexity before it matters
Mitigation:

- keep the backend interface minimal
- do not add a hardware dependency until there is evidence and budget approval

### 15.5 Risk: Experiment logging adds too much operational weight
Mitigation:

- start with compact run/candidate storage
- sample where necessary
- make logging and rollout configurable

---

## 16. Open Questions

- Which existing event models can be reused directly for ranking outcome attribution, and which require new experiment-specific tables?
- What is the minimum viable replay corpus size before promotion decisions become trustworthy?
- Which explicit-review workflow is lightest-weight but still rigorous enough for ranking judgment?
- Should affiliate surfaces and bespoke-service surfaces share one promotion gate or separate gates?
- At what latency and quality thresholds would a future hardware-backed experiment become worth paying for?

---

## 17. Acceptance Criteria

### AC-1 Parallel shadow reranking exists
A search can run baseline ranking and one or more experimental rerankers in parallel without changing user-visible order by default.

### AC-2 Ranking runs are replayable
The system stores enough slate and scoring data to rerun and compare experiments offline.

### AC-3 Outcomes can be attributed back to ranking positions
Clicks, selections, quotes, and related user actions can be joined back to baseline and experimental rank positions.

### AC-4 Multiple reranker variants can be evaluated side by side
The platform supports comparing at least three reranker variants on the same query/candidate slate.

### AC-5 Promotion gates are explicit
There is a documented standard for moving an experiment from shadow mode to live influence.

### AC-6 Hardware-readiness is real but optional
The scoring system exposes a backend contract that can support future hardware experiments without making hardware mandatory.

---

## 18. Recommended Immediate Next Steps

1. Design the ranking experiment data model.
2. Wire shadow-mode logging into the current search path.
3. Connect clickout/selection outcomes back to logged rank positions.
4. Build a first offline replay report for affiliate-heavy searches.
5. Add at least two additional reranker variants for comparison.
6. Review the first 100-500 real examples before allowing any live ranking influence.
