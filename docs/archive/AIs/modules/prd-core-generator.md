# PRD Core Generator Module

**Version:** 1.0  
**Module Type:** Document Creation & Content Generation  
**Max Lines:** 400

## Module Overview

This module generates the core business sections of the PRD document using the comprehensive information package from the Information Gathering module. It focuses on problem definition, solution framework, and user requirements.

---

## Entry Criteria

- [ ] Information Gathering module completed (100%)
- [ ] Comprehensive information package available
- [ ] Overall confidence level ≥ 80%
- [ ] PRD template file initialized

---

## Module Objective

**Primary Goal:** Generate the foundational business sections of the PRD that clearly articulate the problem, solution approach, and user requirements.

**Focus Anchor:**

1. "I am generating the core business sections of the [Task Name] PRD"
2. "My objective is to create clear, actionable problem and solution documentation"
3. "I will not proceed to technical details until business foundations are solid"

---

## Process Steps

### Step 1: Document Initialization [Progress: 15%]

#### 1.1 PRD Header Creation

```markdown
**Generate Document Header:**
```

# Product Requirements Document

**Feature/Product:** [Task Name]  
**Company/Team:** [Team/Division]
**Product Manager:** [Name or TBD]  
**Lead Engineer:** [Name or TBD]  
**Designer:** [Name or TBD]  
**Date Created:** [Current Date]  
**Version:** 1.0

```

**Populate Known Values:** Fill in available information, mark unknowns as TBD
```

#### 1.2 TL;DR Section

```markdown
**Create Executive Summary (2-3 sentences):**

- What the feature/product does
- Core value proposition
- Key technologies involved (if known)

**Quality Check:**

- [ ] Can a busy executive understand the value in 30 seconds?
- [ ] Does it capture the essence without jargon?
- [ ] Is it specific enough to differentiate from other features?
```

### Step 2: Problem Definition [Progress: 30%]

#### 2.1 Problem Statement Section

```markdown
**Structure:**

## Problem Statement

**What problem are we solving?**

- [Specific problem statement 1 from information package]
- [Specific problem statement 2]
- [Specific problem statement 3]

**Who is affected?**

- [Primary affected user group with specifics]
- [Secondary affected user group with context]

**Current Impact:**

- [Quantified impact where available]
- [Qualitative impact description]
- [Business cost of not solving]
```

#### 2.2 Problem Validation

```markdown
**Quality Gates:**

- [ ] Problems are specific and measurable
- [ ] User impact is clearly articulated
- [ ] Business case is evident
- [ ] Problems align with gathered information
- [ ] Assumptions are clearly marked
```

### Step 3: Solution Framework [Progress: 45%]

#### 3.1 Solution Overview

```markdown
**Create Solution Section:**

## Solution Overview

**Our Approach:**

- [High-level solution approach]
- [Key solution components]
- [How it addresses each problem]

**Why This Solution:**

- [Reasoning based on research]
- [Advantages over alternatives]
- [Alignment with business goals]

**Solution Boundaries:**

- **In Scope:** [Core functionality from task discovery]
- **Out of Scope:** [Explicitly excluded items]
- **Future Considerations:** [Potential enhancements noted]
```

#### 3.2 Solution Validation

```markdown
**Validation Checks:**

- [ ] Solution directly addresses stated problems
- [ ] Approach is feasible given constraints
- [ ] Scope boundaries are clear and realistic
- [ ] Solution aligns with user needs from research
```

### Step 4: User Requirements [Progress: 60%]

#### 4.1 User Personas & Goals

```markdown
**Generate User Personas Section:**

## User Personas and Goals

### Primary Persona: [Name/Type]

- **Role:** [User role/job title]
- **Goals:** [What they want to accomplish]
- **Pain Points:** [Current frustrations]
- **Context:** [When/where they use this feature]

### Secondary Persona: [Name/Type]

- **Role:** [User role/job title]
- **Goals:** [What they want to accomplish]
- **Pain Points:** [Current frustrations]
- **Context:** [When/where they use this feature]
```

#### 4.2 User Stories Generation

```markdown
**Create User Stories:**

## User Stories

**Epic:** [High-level capability]

**Core User Stories:**

- As a [persona], I want [capability] so that [benefit]
- As a [persona], I want [capability] so that [benefit]
- As a [persona], I want [capability] so that [benefit]

**Supporting User Stories:**

- As a [persona], I want [capability] so that [benefit]
- As a [persona], I want [capability] so that [benefit]

**Quality Standards:**

- [ ] Each story follows "As a... I want... so that..." format
- [ ] Benefits are specific and measurable where possible
- [ ] Stories are independent and testable
- [ ] Coverage spans all primary use cases
```

### Step 5: Business Requirements [Progress: 75%]

#### 5.1 Business Goals & Metrics

```markdown
**Generate Business Section:**

## Business Goals and Success Metrics

**Primary Business Goals:**

- [Quantified goal from information package]
- [Quantified goal from information package]
- [Quantified goal from information package]

**Success Metrics:**

- **Primary KPI:** [Main success indicator with target]
- **Secondary KPIs:** [Supporting metrics with targets]
- **Health Metrics:** [Quality/performance indicators]

**Measurement Plan:**

- **Baseline:** [Current state metrics]
- **Timeline:** [When to measure progress]
- **Ownership:** [Who tracks these metrics]
```

#### 5.2 Constraints & Assumptions

```markdown
**Document Constraints:**

## Constraints and Assumptions

**Technical Constraints:**

- [Limitation from information package]
- [Platform/technology restriction]
- [Performance requirement]

**Business Constraints:**

- [Timeline constraint with reasoning]
- [Resource limitation]
- [Budget consideration]

**Assumptions:**

- [Key assumption from information gathering]
- [User behavior assumption]
- [Technical capability assumption]

**Risk Mitigation:**

- **High Risk:** [Assumption] → [Mitigation plan]
- **Medium Risk:** [Assumption] → [Mitigation plan]
```

### Step 6: Content Validation & Review [Progress: 100%]

#### 6.1 Internal Consistency Check

```markdown
**Validation Matrix:**

- [ ] Problem → Solution alignment verified
- [ ] User stories → Business goals alignment confirmed
- [ ] Success metrics → User value alignment checked
- [ ] Constraints → Solution feasibility validated
- [ ] Assumptions → Risk assessment completed
```

#### 6.2 Completeness Assessment

```markdown
**Section Completeness:**

- [ ] TL;DR: Clear and compelling
- [ ] Problem Statement: Specific and quantified
- [ ] Solution Overview: Comprehensive and feasible
- [ ] User Personas: Detailed and research-backed
- [ ] User Stories: Complete coverage of use cases
- [ ] Business Goals: Quantified and measurable
- [ ] Constraints: All limitations documented
- [ ] Assumptions: Risks identified and mitigated

**Quality Gates:**

- [ ] No major gaps or TBDs in business sections
- [ ] All content traces back to information package
- [ ] Document is ready for technical specification
```

---

## Exit Criteria

- [ ] All core business sections completed and validated
- [ ] Internal consistency verified across sections
- [ ] Content quality meets PRD standards
- [ ] No critical business gaps remain
- [ ] Document ready for technical specification module
- [ ] User feedback incorporated (if workflow includes review breakpoint)

---

## Data Outputs

### Generated PRD Sections

```markdown
**Completed Sections:**

1. Document Header (with metadata)
2. TL;DR (executive summary)
3. Problem Statement (specific, quantified)
4. Solution Overview (approach and boundaries)
5. User Personas and Goals (research-backed)
6. User Stories (comprehensive coverage)
7. Business Goals and Success Metrics (measurable)
8. Constraints and Assumptions (documented risks)
```

### Content Quality Metrics

```json
{
  "sectionsCompleted": 8,
  "totalSections": 8,
  "qualityScore": {
    "problemClarity": "number (0-100)",
    "solutionFeasibility": "number (0-100)",
    "userValueAlignment": "number (0-100)",
    "businessAlignment": "number (0-100)",
    "overallQuality": "number (0-100)"
  },
  "gapsIdentified": ["array of remaining gaps"],
  "assumptionsCount": "number",
  "userStoriesCount": "number"
}
```

---

## Troubleshooting

### Common Issues

1. **Vague Problem Statements**: Return to information package, ask for specifics
2. **Solution-Problem Misalignment**: Revisit solution approach with user
3. **Incomplete User Stories**: Use persona-driven story generation
4. **Unmeasurable Success Metrics**: Work with user to define quantifiable goals

### Quality Recovery Actions

```markdown
**Problem Clarity Issues:**

- Break down complex problems into specific components
- Add concrete examples and use cases
- Quantify impact where possible

**Solution Feasibility Concerns:**

- Validate against technical constraints
- Consider simpler alternative approaches
- Document assumptions requiring validation

**User Story Gaps:**

- Map stories to each persona's journey
- Ensure edge cases are covered
- Validate stories with information package
```

### Content Templates

```markdown
**Problem Statement Template:**
"Users currently experience [specific problem] when [context]. This results in [quantified impact] and prevents [business goal]. Without solving this, [business consequence]."

**User Story Template:**
"As a [specific persona], I want to [specific capability] so that I can [specific benefit that maps to business value]."

**Success Metric Template:**
"Increase [specific metric] from [baseline] to [target] within [timeframe], measured by [method]."
```

---

## Next Module: Technical Specification

**Module File:** `prd-technical-specification.md`
**Entry Requirements:** Core PRD sections complete, business foundation solid
**Expected Duration:** 20-30 minutes
