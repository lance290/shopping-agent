# PRD: BuyAnything Trust Metrics and Learning Loop

## 1. Executive Summary

BuyAnything will begin with a small cohort of executive assistants as early adopters.

The product does not earn referral-grade trust from usage volume alone. It earns trust by consistently producing useful, high-conviction outcomes, learning from mistakes, and reducing the amount of manual filtering required from assistants over time.

This PRD defines the trust metrics, feedback loops, instrumentation, and memory write-back mechanisms needed to turn early-adopter usage into a durable product-quality advantage.

The goal is not to maximize clicks or time in app.
The goal is to maximize trusted outcomes.

---

## 2. Product Decisions Locked By This PRD

### 2.1 Trust is measured through outcomes, not vanity activity
The system must prioritize metrics tied to usefulness, confidence, acceptance, and successful completion over raw engagement metrics.

### 2.2 Executive-assistant feedback is a first-class product input
Lightweight feedback from assistants should directly inform ranking, routing, source memory, and quality analysis.

### 2.3 Negative feedback is as important as positive feedback
The system should learn from ignored, dismissed, corrected, or low-confidence results, not only from clicks and saves.

### 2.4 Commodity success and high-touch success must be analyzed separately
Affiliate-driven commodity fulfillment and high-touch sourcing are different trust problems and must not be collapsed into one quality metric.

### 2.5 Existing affiliate query constructors and affiliate-link generation remain intact
Trust instrumentation must sit around the existing affiliate pipeline, not replace it.

---

## 3. Problem Statement

### 3.1 Usage data alone is insufficient
If BuyAnything only measures search volume, click volume, or session frequency, it will not learn what makes results trustworthy for executive assistants.

### 3.2 High-trust users care about embarrassment risk
Executive assistants serving high-net-worth principals will not recommend a system that regularly returns weak leads, poor contact information, irrelevant luxury claims, or noisy result sets.

### 3.3 The product needs a structured learning loop
The system must explicitly capture:

- what was shown
- what was trusted
- what was ignored
- what was rejected
- what led to outreach, shortlist inclusion, booking, or purchase
- what actually solved the request

---

## 4. Goal

Build a trust metrics and learning loop framework that:

1. Measures quality at the request, result, and cohort levels.
2. Captures explicit and implicit assistant feedback.
3. Feeds trusted outcomes back into source memory and ranking.
4. Improves routing decisions over time.
5. Provides operator visibility into whether product quality is compounding.

---

## 5. Scope

### In scope

- trust-oriented instrumentation
- request- and candidate-level feedback capture
- outcome taxonomy
- trust dashboards and reporting requirements
- memory write-back rules for trusted and failed outcomes
- separation of commodity vs sourcing quality measurement
- cohort analysis for early-adopter assistants

### Out of scope

- consumer growth analytics
- affiliate commission reporting
- billing analytics
- full experimentation platform
- replacing existing affiliate query constructors or affiliate link generation

---

## 6. Core Product Principle

BuyAnything should learn from whether assistants trust and use the work product, not merely whether they touched the interface.

---

## 7. What Must Be Measured

## 7.1 Request-level metrics

The system must track:

- request type
- routing mode selected
- providers selected
- time to first useful result
- time to shortlist-worthy result
- whether the request was resolved
- whether the request required fallback to sourcing after affiliate attempts
- whether the assistant overrode or corrected the system

## 7.2 Candidate-level metrics

For each surfaced result, the system should capture:

- shown
- clicked
- saved
- shortlisted
- dismissed
- hidden
- marked irrelevant
- marked not premium enough
- marked missing contact info
- acted on
- contributed to successful outcome

## 7.3 Outcome-level metrics

The system must distinguish between:

- result surfaced
- result trusted
- result acted on
- request partially solved
- request fully solved
- request solved outside the system after failure

## 7.4 Cohort-level metrics

For the early-adopter executive assistant cohort, the system should report:

- trusted-result rate
- save rate
- shortlist rate
- resolution rate
- time-to-trusted-option
- reduction in assistant overrides over time
- routing accuracy trends

---

## 8. Explicit Feedback Model

Assistants should be able to submit lightweight feedback quickly.

### 8.1 Candidate feedback taxonomy

Recommended feedback types:

- good_lead
- irrelevant
- wrong_geography
- not_premium_enough
- too_expensive
- missing_contact_info
- duplicate_of_known_option
- unsafe_or_low_trust
- saved_me_time

### 8.2 Request feedback taxonomy

Recommended request-level feedback:

- solved
- partially_solved
- not_solved
- had_to_search_manually
- routing_was_wrong
- results_were_noisy
- results_were_strong

### 8.3 Design constraints

Feedback must be:

- fast
- low-friction
- optional
- available without long forms
- preservable for later analysis

---

## 9. Implicit Feedback Model

The system should also infer trust from behavior, including:

- save actions
- shortlist actions
- export actions
- clickthrough actions
- dwell on candidate details
- repeated reuse of the same source or vendor
- abandonment after poor results

Implicit signals should be used carefully and never treated as perfect substitutes for explicit feedback.

---

## 10. Trust Metrics That Matter

## 10.1 Primary trust metrics

- trusted_result_rate
- shortlist_rate
- acted_on_rate
- request_resolution_rate
- time_to_trusted_option
- assistant_override_rate
- noisy_result_rate

## 10.2 Secondary trust metrics

- provider usefulness by route type
- source-domain success rate
- contact-readiness rate
- premium-fit score distribution
- hybrid-mode usefulness rate

## 10.3 Vanity metrics to avoid over-prioritizing

- total clicks
- total searches
- total session duration
- total page views

---

## 11. Learning Loop Requirements

## 11.1 Ranking feedback loop

The ranking layer should learn from:

- accepted sources
- dismissed sources
- successful candidate attributes
- repeated low-value result patterns

## 11.2 Routing feedback loop

The router should learn when:

- affiliate-only was sufficient
- sourcing-only was necessary
- hybrid mode produced better outcomes
- the original route was wrong

## 11.3 Memory feedback loop

The memory layer should update trusted-source history using:

- successful outcomes
- repeated saves
- repeated shortlist inclusion
- repeated “good lead” feedback
- repeated negative feedback and failure patterns

---

## 12. Reporting Requirements

The system should provide internal reporting for:

- quality by assistant cohort
- quality by request type
- quality by route type
- quality by provider
- quality by domain/source
- quality trend over time
- top failure modes

---

## 13. Acceptance Criteria

### AC-1 Request and candidate interactions are instrumented
The system records the key user actions required to compute trust metrics.

### AC-2 Explicit feedback can be submitted quickly
Assistants can submit lightweight feedback at both request and result levels.

### AC-3 Trust metrics distinguish route types
Affiliate, sourcing, and hybrid requests can be analyzed separately.

### AC-4 Outcomes feed memory and ranking analysis
Successful and failed outcomes can be tied back to sources, routes, and candidate patterns.

### AC-5 Internal dashboards can identify quality trends
The team can observe whether trust is compounding or degrading over time.

---

## 14. Risks

### 14.1 Measuring the wrong thing
If the system optimizes for clicks or activity rather than trusted outcomes, product quality will drift.

### 14.2 Missing final outcomes
If resolution data is weak, the learning loop may overfit on shallow signals.

### 14.3 Feedback fatigue
If assistants are asked for too much input, they will stop providing it.

### 14.4 Blending heterogeneous request types
If commodity and high-touch requests are analyzed together, the metrics will become misleading.

---

## 15. Final Principle

BuyAnything should become more trusted because it learns which results actually help elite assistants get to confident decisions faster.

The system should optimize for trust earned, not attention captured.
