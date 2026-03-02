# PRD Information Gathering Module

**Version:** 1.0  
**Module Type:** Research & Requirements Collection  
**Max Lines:** 400

## Module Overview

This module systematically collects all information needed for comprehensive PRD creation through structured questioning, research, and validation. It prevents PRD gaps by ensuring 80%+ confidence before proceeding.

---

## Entry Criteria

- [ ] Task Discovery module completed (100%)
- [ ] Task scope and boundaries clearly defined
- [ ] Project directory structure exists
- [ ] Workflow mode selected and configured

---

## Module Objective

**Primary Goal:** Gather comprehensive information about user needs, business context, technical constraints, and success criteria to enable confident PRD creation.

**Focus Anchor:**

1. "I am collecting information for the [Task Name] PRD"
2. "My objective is to reach 80%+ confidence in understanding all requirements"
3. "I will not proceed to PRD creation until all critical gaps are addressed"

---

## Process Steps

### Step 1: Confidence Assessment [Progress: 15%]

#### 1.1 Initial Confidence Evaluation

```markdown
**Evaluate Current Understanding:**

- **Problem Definition:** How clearly is the problem understood? (0-100%)
- **User Impact:** How well are affected users identified? (0-100%)
- **Business Context:** How clear are the business goals? (0-100%)
- **Technical Scope:** How well are technical requirements understood? (0-100%)
- **Success Metrics:** How clear are success criteria? (0-100%)

**Overall Confidence:** Average of above scores
**Required Minimum:** 80%

**Decision Point:**

- If ≥ 80%: → Skip to Step 4 (Validation & Research)
- If < 80%: → Proceed to Step 2 (Structured Questioning)
```

#### 1.2 Gap Identification

```markdown
**Flag Areas Below 80%:**

- [ ] Problem definition unclear
- [ ] Target users not well defined
- [ ] Business impact uncertain
- [ ] Technical constraints unknown
- [ ] Success metrics undefined
- [ ] Timeline/resources unclear

**Prioritize Gaps:** Focus on most critical missing information first
```

### Step 2: Essential Questions Generation [Progress: 30%]

#### 2.1 Problem & User Context Questions

```markdown
**Always Ask (Minimum 3 questions):**

**Problem Definition:**

- "What specific problem does this solve for users?"
- "What happens if we don't build this feature?"
- "How do users currently accomplish this task (workarounds)?"

**User Context:**

- "Who are the primary and secondary users?"
- "What user segments/personas will this affect?"
- "How will different user types interact with this feature?"

**Pain Points:**

- "What are the biggest frustrations with the current solution?"
- "Which pain points are most critical to address first?"
- "How severe is the impact of these problems (scale 1-10)?"
```

#### 2.2 Business Context Questions

```markdown
**Business Impact:**

- "What business goals does this feature support?"
- "How does this align with company/product strategy?"
- "What's the expected business impact (revenue, retention, etc.)?"

**Priority & Urgency:**

- "What's driving the timeline for this feature?"
- "What happens if this launches 3 months later?"
- "How does this rank against other priorities?"

**Resources:**

- "What team(s) will work on this?"
- "Are there budget constraints or resource limitations?"
- "What's the expected development timeline?"
```

#### 2.3 Scope & Constraints Questions

```markdown
**Technical Constraints:**

- "Are there specific technologies we must/cannot use?"
- "What existing systems need to integrate with this?"
- "Are there performance requirements (speed, scale, etc.)?"

**Scope Boundaries:**

- "What functionality is explicitly out of scope for V1?"
- "Which edge cases should we handle vs. document as limitations?"
- "Are there regulatory/compliance requirements to consider?"

**Dependencies:**

- "What other features/systems does this depend on?"
- "Are there external dependencies (third-party APIs, etc.)?"
- "What could block or delay this development?"
```

### Step 3: Information Collection [Progress: 50%]

#### 3.1 User Response Processing

```markdown
**For Each Question:**

1. Record detailed response
2. Ask follow-up questions for clarity
3. Update confidence scores for relevant areas
4. Note new questions that emerge from responses

**Follow-up Question Patterns:**

- "Can you give me a specific example of..."
- "How would you measure success for..."
- "What would happen if we..."
- "Who else should I talk to about..."
```

#### 3.2 Response Validation

```markdown
**Quality Checks:**

- [ ] Responses are specific (not vague generalizations)
- [ ] Quantifiable metrics provided where relevant
- [ ] Assumptions are explicitly stated
- [ ] Conflicts or contradictions identified
- [ ] Additional stakeholders mentioned are noted

**Red Flags:**

- Circular reasoning in problem definition
- Vague success metrics ("users will like it")
- Unrealistic timeline expectations
- Missing key stakeholder input
```

### Step 4: Research & Competitive Analysis [Progress: 70%]

#### 4.1 Market Research (When Applicable)

```markdown
**Research Areas:**

- **Competitive Features:** How do competitors solve this problem?
- **Industry Standards:** What are common patterns/best practices?
- **User Expectations:** What do users expect based on other tools?
- **Technical Approaches:** How are similar features typically implemented?

**Research Methods:**

- Web search for competitive analysis
- Best practices documentation
- Technical implementation patterns
- User experience standards
```

#### 4.2 Internal Knowledge Validation

```markdown
**Check Against:**

- Existing product patterns and conventions
- Technical architecture constraints
- Brand guidelines and UX standards
- Previous similar features and their outcomes

**Document:**

- Consistency requirements with existing features
- Reusable components or patterns
- Known technical limitations or preferences
```

### Step 5: Information Synthesis [Progress: 85%]

#### 5.1 Confidence Re-evaluation

```markdown
**Re-assess Understanding:**

- **Problem Definition:** [Updated score] (Target: 80%+)
- **User Impact:** [Updated score] (Target: 80%+)
- **Business Context:** [Updated score] (Target: 80%+)
- **Technical Scope:** [Updated score] (Target: 80%+)
- **Success Metrics:** [Updated score] (Target: 80%+)

**Overall Confidence:** [Updated average]

**Decision Point:**

- If ≥ 80%: → Proceed to Step 6 (Documentation)
- If < 80%: → Return to Step 2 with focused questions
```

#### 5.2 Gap Documentation

```markdown
**Remaining Gaps (For PRD Documentation):**

- **Assumptions:** List all assumptions made due to missing information
- **Open Questions:** Questions that couldn't be answered
- **Research Needed:** Areas requiring further investigation
- **Dependencies:** External factors that could affect requirements

**Risk Assessment:**

- High-risk assumptions that could invalidate the solution
- Medium-risk gaps that could affect implementation
- Low-risk unknowns that can be resolved during development
```

### Step 6: Information Package Creation [Progress: 100%]

#### 6.1 Structured Information Summary

```markdown
**Create Comprehensive Information Package:**

**Core Requirements:**

- Problem statement (clear, specific)
- Target users (personas, use cases)
- Business objectives (measurable goals)
- Success metrics (quantifiable KPIs)

**Context & Constraints:**

- Technical requirements and limitations
- Timeline and resource constraints
- Integration requirements
- Compliance/regulatory needs

**Research Insights:**

- Competitive landscape findings
- Best practices identified
- User expectation benchmarks
- Technical implementation patterns
```

#### 6.2 PRD Readiness Validation

```markdown
**Final Checklist:**

- [ ] All essential questions answered satisfactorily
- [ ] Business case clearly articulated
- [ ] User needs well understood
- [ ] Technical approach feasible
- [ ] Success metrics defined and measurable
- [ ] Scope boundaries confirmed
- [ ] Major assumptions documented
- [ ] Open questions cataloged for PRD

**Quality Gate:** Must achieve 80%+ confidence to proceed
```

---

## Exit Criteria

- [ ] Overall confidence level ≥ 80%
- [ ] All critical information gaps addressed
- [ ] Comprehensive information package created
- [ ] Assumptions and open questions documented
- [ ] Research findings consolidated
- [ ] Next module (Core PRD Generator) inputs prepared

---

## Data Outputs

### Information Package Schema

```json
{
  "confidenceScores": {
    "problemDefinition": "number (0-100)",
    "userImpact": "number (0-100)",
    "businessContext": "number (0-100)",
    "technicalScope": "number (0-100)",
    "successMetrics": "number (0-100)",
    "overall": "number (0-100)"
  },
  "coreRequirements": {
    "problemStatement": "string",
    "targetUsers": ["array of personas"],
    "businessObjectives": ["array of goals"],
    "successMetrics": ["array of KPIs"]
  },
  "contextConstraints": {
    "technicalRequirements": ["array of requirements"],
    "timeline": "string",
    "resources": "string",
    "integrations": ["array of systems"],
    "compliance": ["array of requirements"]
  },
  "researchInsights": {
    "competitiveFindings": ["array of insights"],
    "bestPractices": ["array of practices"],
    "userExpectations": ["array of expectations"],
    "technicalPatterns": ["array of patterns"]
  },
  "gaps": {
    "assumptions": ["array of assumptions"],
    "openQuestions": ["array of questions"],
    "researchNeeded": ["array of topics"],
    "dependencies": ["array of dependencies"]
  }
}
```

---

## Troubleshooting

### Common Issues

1. **Low Response Quality**: Ask for specific examples, use "5 Whys" technique
2. **Conflicting Information**: Document conflicts, identify decision maker
3. **Stakeholder Unavailable**: Work with available info, flag as assumption
4. **Scope Creep During Questions**: Gently redirect to defined scope

### Quality Recovery

- **Vague Responses**: "Can you give me a concrete example?"
- **Missing Metrics**: "How would we know this feature succeeded?"
- **Technical Unknowns**: "Who on the team would know about [technical aspect]?"

---

## Next Module: Core PRD Generator

**Module File:** `prd-core-generator.md`
**Entry Requirements:** 80%+ confidence, comprehensive information package ready
**Expected Duration:** 15-25 minutes
