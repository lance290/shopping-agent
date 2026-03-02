# PRD Task Discovery Module

**Version:** 1.0  
**Module Type:** Task Identification & Scope Definition  
**Max Lines:** 400

## Module Overview

This module handles Asana task identification, selection, and initial scope definition. It connects to external task management systems and establishes the foundation for PRD creation.

---

## Entry Criteria

- [ ] Session Manager has initialized workflow state
- [ ] User is ready to identify or specify task for PRD creation
- [ ] Asana integration is available (if applicable)

---

## Module Objective

**Primary Goal:** Identify the specific task/feature for PRD creation and define its initial scope boundaries.

**Focus Anchor:**

1. "I am discovering and scoping the task for PRD creation"
2. "My objective is to clearly define what will be built and its boundaries"
3. "I will not proceed to information gathering until task scope is confirmed"

---

## Process Steps

### Step 1: Task Identification Method [Progress: 20%]

#### 1.1 Determine Task Source

```markdown
**Ask User:** "How would you like to specify the task for this PRD?"

**Options:**
A. Search my assigned Asana tasks
B. Provide a specific Asana task ID
C. Describe the task/feature directly
D. Upload task details from another source

**Action Based on Choice:**

- A or B: → Go to Step 1.2 (Asana Integration)
- C: → Go to Step 1.3 (Direct Description)
- D: → Go to Step 1.4 (File Upload)
```

#### 1.2 Asana Task Search & Selection

```markdown
**Search Parameters:**

- assignee: me
- completed: false
- limit: 20
- sort_by: due_date

**Display Format:**
```

| Task ID | Name      | Project   | Due Date   | Priority |
| ------- | --------- | --------- | ---------- | -------- |
| 1234... | Feature X | Project Y | 2024-01-15 | High     |

```

**User Selection:** "Please select the task ID for PRD creation"
**Validation:** Confirm task selection and fetch full details
```

#### 1.3 Direct Task Description

```markdown
**Prompt User:** "Please provide a brief description of the feature/task:"

**Required Information:**

- Feature/task name
- Basic description (1-2 sentences)
- Any known constraints or requirements

**Validation:** Confirm description captures the core intent
```

#### 1.4 File Upload Processing

```markdown
**Supported Formats:** .txt, .md, .doc, .pdf
**Processing:** Extract task name, description, and initial requirements
**Validation:** Confirm extracted information is accurate
```

### Step 2: Task Detail Extraction [Progress: 40%]

#### 2.1 Core Task Information

```markdown
**Extract/Confirm:**

- **Task Name:** [Clear, descriptive name]
- **Task ID:** [If from Asana]
- **Project Context:** [Which product/system this belongs to]
- **Current Status:** [Current state/phase]
- **Assigned Team:** [Who will implement this]

**Generate Sanitized Name:**

- Convert to lowercase, replace spaces with hyphens
- Remove special characters
- Example: "CRM CSV Export" → "crm-csv-export"
```

#### 2.2 Initial Requirements Extraction

```markdown
**From Task Description, Extract:**

- **What:** Core functionality to be built
- **Who:** Target users/stakeholders
- **Why:** Business justification/problem being solved
- **When:** Any timing constraints or deadlines
- **Where:** Systems/platforms affected

**Flag Missing Information:** Note areas requiring clarification in next module
```

### Step 3: Scope Definition [Progress: 60%]

#### 3.1 Boundary Setting

```markdown
**Define Scope Boundaries:**

**In Scope (Confirmed):**

- [ ] Core functionality from task description
- [ ] Primary user workflows
- [ ] Essential integrations mentioned

**Likely In Scope (To Clarify):**

- [ ] Related features mentioned
- [ ] Supporting functionality
- [ ] Edge cases and error handling

**Explicitly Out of Scope:**

- [ ] Future enhancements mentioned
- [ ] Nice-to-have features
- [ ] Complex integrations not required for MVP
```

#### 3.2 Complexity Assessment

```markdown
**Initial Complexity Indicators:**

- **Low:** Single feature, clear requirements, existing patterns
- **Medium:** Multiple components, some unknowns, new patterns
- **High:** System-wide changes, many unknowns, novel functionality

**Time Estimation (Rough):**

- Low: 1-3 days development
- Medium: 1-2 weeks development
- High: 2+ weeks development

**Impact on Workflow:** Higher complexity = more thorough information gathering needed
```

### Step 4: Project Structure Setup [Progress: 80%]

#### 4.1 Create Project Directories

```markdown
**Directory Structure:**
```

docs/PRDs/{sanitized-task-name}/
├── prd*{sanitized-task-name}.md
├── workflow-state*{sanitized-task-name}.json  
├── changelog*{sanitized-task-name}.md
├── tasks*{sanitized-task-name}.json (if TaskMaster used)
└── artifacts/ (for screenshots, mockups, etc.)

```

**Validation:** Confirm all directories created successfully
```

#### 4.2 Initialize Project Files

```markdown
**Create Placeholder Files:**

- **PRD File:** Header with task name, date, version
- **Changelog:** Initial entry with task discovery completion
- **State File:** Update with task details and current progress

**File Naming Convention:**

- All lowercase
- Hyphens instead of spaces
- Descriptive but concise
```

### Step 5: Workflow Mode Selection [Progress: 100%]

#### 5.1 Recommend Workflow Mode

```markdown
**Based on Complexity Assessment:**

**Express Mode** (Low complexity):

- Simplified PRD template
- Combined breakpoints
- Faster iteration cycles

**Regular Mode** (Medium complexity):

- Standard PRD template
- All standard breakpoints
- Balanced depth and speed

**Deep Dive Mode** (High complexity):

- Comprehensive PRD template
- Additional research phases
- Extensive technical documentation

**Dev Mode** (Implementation focus):

- Technical-heavy PRD
- Direct TaskMaster integration
- Code-generation optimized
```

#### 5.2 Mode Confirmation

```markdown
**Present Recommendation:**
"Based on the task complexity, I recommend [MODE] workflow because [REASONING].

**User Options:**

- Accept recommendation
- Choose different mode
- Customize mode settings

**Update State File:** Record selected mode and configuration
```

---

## Exit Criteria

- [ ] Task clearly identified and described
- [ ] Scope boundaries defined (in/out of scope)
- [ ] Project directory structure created
- [ ] Workflow mode selected and configured
- [ ] State file updated with task details
- [ ] Next module (Information Gathering) prerequisites prepared

---

## Data Outputs

### Task Definition Object

```json
{
  "taskName": "string",
  "sanitizedTaskName": "string",
  "taskId": "string | null",
  "source": "asana | direct | upload",
  "description": "string",
  "projectContext": "string",
  "assignedTeam": "string",
  "complexity": "low | medium | high",
  "estimatedDuration": "string",
  "scopeBoundaries": {
    "inScope": ["array of strings"],
    "outOfScope": ["array of strings"],
    "clarificationNeeded": ["array of strings"]
  },
  "workflowMode": "express | regular | deep-dive | dev"
}
```

---

## Troubleshooting

### Common Issues

1. **Asana Connection Failed**: Fallback to direct description mode
2. **Vague Task Description**: Flag for extensive information gathering
3. **Scope Too Broad**: Help user narrow focus to core functionality
4. **Conflicting Requirements**: Document conflicts for resolution in next module

### Quality Checks

```markdown
**Before Module Exit:**

- [ ] Can task be summarized in 1-2 clear sentences?
- [ ] Is it obvious what the end result will be?
- [ ] Are scope boundaries logical and defensible?
- [ ] Does workflow mode match complexity assessment?
```

### Recovery Actions

- **Unclear Task**: Return to Step 1, try different identification method
- **Scope Confusion**: Use progressive scope refinement technique
- **Mode Selection Issues**: Provide detailed mode comparison

---

## Next Module: Information Gathering

**Module File:** `prd-info-gathering.md`
**Entry Requirements:** Task defined, scope set, project structure created
**Expected Duration:** 10-20 minutes (varies by task complexity)
