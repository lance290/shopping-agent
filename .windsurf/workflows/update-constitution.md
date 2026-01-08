---
allowed-tools: "*"
description: Update the workspace constitution with project-specific enhancements
---
allowed-tools: "*"

## Constitution Update Process

### 1. Analyze Current State

The `/update-constitution` workflow will:

- Read the existing `.windsurf/constitution.md` file
- Analyze the current codebase structure and patterns
- Identify technology stack and architectural decisions
- Understand team workflow patterns from repository structure

### 2. Intelligent Enhancement

The workflow intelligently adds value by:

- **Preserving existing content** - Never removes or contradicts current rules
- **Adding project-specific rules** - Based on detected technologies and patterns
- **Enhancing existing sections** - With more specific guidance for the current context
- **Filling gaps** - Adding missing principles that would benefit the codebase

### 3. Areas of Enhancement

#### **Technology Stack Specific**

- Framework-specific best practices (React, Next.js, Express, etc.)
- Database patterns (MongoDB, PostgreSQL, Redis usage)
- Deployment and infrastructure considerations
- Package manager and dependency management rules

#### **Architecture Patterns**

- Microservices vs monolith considerations
- API design patterns specific to the current setup
- State management approaches
- Error handling and logging standards

#### **Team Workflow**

- Git branching strategies based on repository structure
- Code review requirements
- Testing strategies appropriate for the tech stack
- Documentation standards

#### **Security & Compliance**

- Authentication and authorization patterns
- Data handling requirements
- API security considerations
- Environment variable and secrets management

### 4. Usage Examples

#### **Basic Update**

```bash
/update-constitution
```

This analyzes the current codebase and suggests comprehensive updates.

#### **Focus Areas**

```bash
/update-constitution focus on security and API design patterns
/update-constitution enhance testing and deployment guidelines
/update-constitution add microservices communication patterns
```

### 5. Review and Apply Process

1. **Run the workflow** - Generate the constitution update analysis
2. **Review proposed changes** - Examine the `ProposedAdditions` and `Enhancements`
3. **Validate against team needs** - Ensure suggestions align with team practices
4. **Apply selectively** - Use the `UpdatedConstitution` content or pick specific additions
5. **Update the file** - Replace `.windsurf/constitution.md` with enhanced version
6. **Team review** - Have team members review and approve the updated constitution

### 6. Example Output Structure

```yaml
# cfoi.constitution-update.v1
CurrentConstitution: "Existing priorities, code organization, and guardrails"
ProposedAdditions:
  - section: "API Security"
    content: "JWT token validation, rate limiting, input sanitization"
    rationale: "Express.js API detected with authentication middleware"
  - section: "Database Patterns"
    content: "Connection pooling, transaction management, migration strategies"
    rationale: "PostgreSQL and MongoDB usage detected"
Enhancements:
  - section: "Code Organization"
    current: "Use repositories and adapters"
    enhanced: "Use repositories and adapters with connection pooling and retry logic"
    rationale: "Database reliability patterns needed for production"
TechStackSpecific:
  - "Next.js: Use App Router, avoid Pages Router for new features"
  - "TypeScript: Strict mode enabled, no any types in production code"
  - "Docker: Multi-stage builds, non-root user, minimal base images"
ProjectContext: "E-commerce platform with microservices architecture"
UpdatedConstitution: "Complete enhanced constitution content..."
```

### 7. Best Practices

- **Run periodically** - Update constitution as the codebase evolves
- **Team consensus** - Ensure team agrees with proposed changes
- **Document rationale** - Keep track of why specific rules were added
- **Version control** - Commit constitution updates with clear commit messages
- **Gradual adoption** - Implement new rules incrementally rather than all at once

### 8. Integration with Other Workflows

- **`/audit`** - Use updated constitution for more accurate compliance checking
- **`/plan`** - New slices automatically follow enhanced constitution principles
- **Git hooks** - Updated rules are automatically enforced in pre-commit checks
- **`/implement`** - Code generation follows the enhanced architectural guidelines
