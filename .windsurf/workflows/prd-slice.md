---
allowed-tools: "*"
description: Slice a parent PRD into child PRDs with cross-cutting concerns integrated
---
allowed-tools: "*"

# Purpose
Create independently-executable child PRDs from a single parent PRD, explicitly embedding cross-cutting business concerns (authentication, monitoring, billing, data requirements, performance expectations, UX consistency, accessibility, privacy/compliance, operational visibility). Each child PRD is tightly scoped, aligned to the Product North Star, defines WHAT needs to be achieved (not HOW), and is ready to flow into efforts (/effort-new → /plan → /task → /implement) where technical decisions are made.

# Philosophy: Stack-Agnostic Business Requirements

**PRDs define WHAT, not HOW:**
- ✅ Business outcomes and user capabilities
- ✅ Performance expectations and constraints
- ✅ Compliance and regulatory requirements
- ✅ User experience standards
- ❌ Technology stack choices (Python vs Node, SQL vs NoSQL)
- ❌ Architecture patterns (microservices, serverless, etc.)
- ❌ Implementation details (database schemas, API designs)

**When technical decisions happen:**
- PRD (this workflow) → Business requirements only
- /plan → Technical architecture, stack selection, implementation approach
- /task → Detailed technical specifications
- /implement → Code execution

**Why separate them:**
- Business requirements are stable; technology choices evolve
- Same PRD can be implemented with different tech stacks
- Product managers can write PRDs without technical expertise
- Technical teams have flexibility to choose optimal solutions

# Inputs
- Parent PRD path (Markdown)
- PRD folder slug (e.g., checkout-v2)
- Output root for PRDs (default: docs/prd/)
- Product North Star reference (path)

# Outputs
- Folder at docs/prd/<slug>/ containing:
  - parent.md (copy of the parent PRD)
  - prd-<child>.md files (one per slice)
- Optional: effort stubs created for each child PRD
- Traceability matrix linking parent → child PRDs (docs/prd/TRACEABILITY.md)

# Steps
1) Collect inputs
- Parent PRD path (e.g., docs/prd/prd-core.md)
- PRD folder slug (e.g., checkout-v2)
- Output root (default: docs/prd/). Do not place PRDs in .cfoi — .cfoi is for per-branch evidence and ephemeral artifacts, while PRDs are durable product docs.
- Product North Star path (e.g., docs/north-star/PRODUCT_NORTH_STAR.md)

2) Extract candidate slices
- Identify functional seams and user outcomes
- Identify business domains and data ownership boundaries
- Inventory cross-cutting business requirements that must be embedded, not appended later:
  - Authentication/authorization: Who can access what?
  - Monitoring & visibility: What business metrics need tracking?
  - Billing/entitlements: How is this monetized or entitled?
  - Data requirements: What information needs to persist?
  - Performance expectations: What are acceptable response times and throughput?
  - UX consistency and accessibility: What user experience standards apply?
  - Privacy/security/compliance: What regulations and policies govern this?

3) Define slicing strategy
- For each candidate slice, ensure it can ship independently and drives a measurable movement in the product north star.
- Write a one-line value statement and acceptance criteria per slice.
- Note explicit dependencies between slices when unavoidable.

4) Generate child PRD skeletons
- Create folder docs/prd/<slug>/ (auto-create if missing).
- Copy the parent PRD into docs/prd/<slug>/parent.md.
- For each slice, create a new file named: prd-<short-slug>.md under docs/prd/<slug>/.
- Use this template:

```
# PRD: <Title>

## Business Outcome
- Measurable impact: <metric tied to Product North Star>
- Success criteria: <quantitative business thresholds>
- Target users: <who benefits>

## Scope
- In-scope: <business capabilities>
- Out-of-scope: <explicitly excluded>

## User Flow
_Brief step sequence showing how users accomplish the outcome:_
1. <trigger/entry point — what initiates this flow?>
2. <user action or system response>
3. <...additional steps as needed...>
4. <outcome/exit point — what does success look like?>

_Optional: Link to flow diagram at docs/diagrams/<slug>.png_

## Business Requirements

### Authentication & Authorization
- Who needs access? <user roles/personas>
- What actions are permitted? <business operations>
- What data is restricted? <data sensitivity levels>

### Monitoring & Visibility
- What business metrics matter? <KPIs, conversion rates, etc.>
- What operational visibility is needed? <error rates, uptime, etc.>
- What user behavior needs tracking? <analytics requirements>

### Billing & Entitlements
- How is this monetized? <pricing model>
- What entitlement rules apply? <access tiers, feature flags>
- What usage limits exist? <quotas, rate limits>

### Data Requirements
- What information must persist? <business entities>
- How long must data be retained? <retention policies>
- What data relationships exist? <business domain model>

### Performance Expectations
- What response times are acceptable? <user-facing targets>
- What throughput is expected? <volume projections>
- What availability is required? <uptime expectations>

### UX & Accessibility
- What user experience standards apply? <design system, patterns>
- What accessibility requirements? <WCAG level, screen readers>
- What devices/browsers must be supported? <compatibility>

### Privacy, Security & Compliance
- What regulations apply? <GDPR, HIPAA, SOC2, etc.>
- What data protection is required? <PII handling, encryption>
- What audit trails are needed? <compliance logging>

## Dependencies
- Upstream: <prerequisite business capabilities>
- Downstream: <dependent business capabilities>

## Risks & Mitigations
- <business risk> → <mitigation strategy>

## Acceptance Criteria (Business Validation)
_Each criterion MUST have a quantitative threshold OR binary test. Values must be realistic and grounded in real-world data (baseline metrics, industry benchmarks, user research) — never invented._

- [ ] <metric>: <current baseline> → <target threshold> (source: <where this number comes from>)
- [ ] <user can accomplish X in Y time/steps> (baseline: <current state>)
- [ ] <% of users complete flow> ≥ <threshold>% (benchmark: <source>)
- [ ] <binary test — user can/cannot do specific action>

**Examples of GOOD vs BAD criteria:**
- ❌ BAD: "Users find the flow intuitive" (untestable, no threshold)
- ❌ BAD: "≥90% satisfaction" (where does 90% come from?)
- ✅ GOOD: "Task completion rate ≥75% (current baseline: 52%, industry avg: 70%)"
- ✅ GOOD: "Time to complete ≤45s (current: 2m10s, competitor benchmark: 50s)"

## Traceability
- Parent PRD: <path>
- Product North Star: <path>

---
allowed-tools: "*"
**Note:** Technical implementation decisions (stack, architecture, database choice, etc.) are made during /plan and /task phases, not in this PRD.
```

5) Create traceability matrix with prioritization
- Create/append docs/prd/TRACEABILITY.md with a table mapping Parent PRD folder (slug) → Child PRDs.
- **Required columns:**
  - Child PRD name
  - Priority (P0 = must-have MVP, P1 = near-term, P2 = future)
  - Phase (MVP / v1.1 / v2.0 / Future)
  - Ship Order (1, 2, 3... — explicit sequencing)
  - Status (Draft / Ready / In Progress / Done)
  - Dependencies (which other child PRDs must ship first)
- The parent PRD owner defines prioritization; child PRDs inherit their assigned priority.
- **Prioritization must be justified** — tie each P0 to north star impact or user research.

6) Review for cross-cutting completeness
- Check each child PRD includes specific business requirements for every cross-cutting area.
- Ensure requirements are framed as business outcomes, not technical implementation.
- Verify all requirements are testable from a user/business perspective.
- Ensure no concern is deferred "to a future phase" unless explicitly justified.

7) Optional: create efforts from child PRDs
- For each child PRD, you may create a corresponding effort (kept per-branch under .cfoi) after human confirmation.
- Suggested flow per child PRD:
  - /effort-new → define effort north star tied to the Product North Star
  - /plan → THIS is where technical decisions are made (stack, architecture, database, etc.)
  - /task and /implement → execute with chosen technology

8) Governance checks
- **Acceptance criteria quality:**
  - Every criterion has a quantitative threshold OR binary pass/fail test
  - Thresholds are grounded in real data (current baseline, benchmark, user research) — reject made-up numbers
  - If no baseline exists, criterion must include "Baseline TBD: measure in first 2 weeks"
- **Prioritization completeness:**
  - Every child PRD has Priority (P0/P1/P2) and Phase assigned
  - MVP scope (P0s) is explicitly defined and justified
  - Ship order is explicit with dependency sequencing
- **User flow clarity:**
  - Each child PRD includes a step sequence showing user journey
  - Entry points and exit points are explicit
- Verify dependencies are explicit and sequencing is feasible.
- Confirm PRD contains ZERO technical specifications (no stack choices, no architecture diagrams, no database schemas).

# Notes on storage location
- PRDs are long-lived product artifacts. Recommended location: docs/prd/<slug>/ (or a product docs folder you designate).
- .cfoi is reserved for per-branch execution evidence (tests, coverage, proofs) and should not store PRDs.

# Helper script
- Run the assisted slicer: `bash tools/prd-slice.sh`
  - Prompts for parent PRD, PRD slug, child slice names.
  - Ensures docs/prd/ and docs/prd/<slug>/ exist.
  - Copies parent to parent.md and scaffolds child PRDs.
  - Updates docs/prd/TRACEABILITY.md.

# Rollback
- If slicing produced too many or overlapping PRDs, collapse adjacent slices by merging documents and updating the traceability matrix accordingly.
