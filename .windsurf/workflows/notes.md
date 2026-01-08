---
allowed-tools: "*"
description: Quick notes to self (effort-level or app-level)
---
allowed-tools: "*"

# Notes to Self Workflow

**Purpose**: Capture quick notes, ideas, technical debt, or deferred work without breaking flow.

---
allowed-tools: "*"

## Step 1: Determine Context

// turbo
1. Check if we're in an effort context:
   - Look for `.cfoi/branches/[branch]/.current-effort`
   - If exists: Use effort-level notes
   - If not: Use app-level notes

2. Determine note file path:
   - **Effort-level**: `.cfoi/branches/[branch]/efforts/[effort-name]/NOTES.md`
   - **App-level**: `.cfoi/branches/[branch]/NOTES.md`

3. Display context: "📝 Adding note to: [effort-name] / [app-level]"

---
allowed-tools: "*"

## Step 2: Capture the Note

// turbo
Ask the user:
```
What would you like to note?

Categories:
1. 💡 Idea / Future Improvement
2. 🐛 Technical Debt
3. ❓ Question / Blocker
4. 📋 TODO (deferred work)
5. 🔍 Discovery / Learning
6. ⚠️  Risk / Concern

Type your note (or just the note without a number):
```

---
allowed-tools: "*"

## Step 3: Append to Notes File

// turbo
1. Create notes file if it doesn't exist (use template below)
2. Append note with:
   - Timestamp (ISO 8601)
   - Category emoji
   - Note content
   - Optional: Current task context

**Format**:
```markdown
- [2025-01-15T14:30:00Z] 💡 **Idea**: Consider adding feature X
- [2025-01-15T15:45:00Z] 🐛 **Tech Debt**: File Y.ts is 380 lines, needs refactoring
- [2025-01-15T16:20:00Z] ❓ **Question**: Need to clarify requirement for Z with PM
```

---
allowed-tools: "*"

## Step 4: Confirm

Display:
```
✅ Note added to [path]

Recent notes:
[show last 5 notes from file]

Continue working? (yes/no)
```

---
allowed-tools: "*"

## Notes File Template

When creating a new NOTES.md file, use this template:

```markdown
# Development Notes

**Branch**: [branch-name]
**Effort**: [effort-name] (or "App-level")
**Created**: [timestamp]

---
allowed-tools: "*"

## Quick Reference

Use `/notes` workflow to add timestamped notes.

**Categories**:
- 💡 Idea / Future Improvement
- 🐛 Technical Debt
- ❓ Question / Blocker
- 📋 TODO (deferred work)
- 🔍 Discovery / Learning
- ⚠️  Risk / Concern

---
allowed-tools: "*"

## Notes

<!-- Notes appear below in reverse chronological order (newest first) -->

```

---
allowed-tools: "*"

## Usage Examples

### During Implementation
```
You: /notes
AI: What would you like to note?
You: File UserService.ts is getting too large, should split into UserService and UserRepository
AI: ✅ Note added to .cfoi/branches/feature-auth/efforts/login/NOTES.md
     - [2025-01-15T14:30:00Z] 🐛 **Tech Debt**: File UserService.ts is getting too large...
```

### Quick Idea
```
You: /notes
AI: What would you like to note?
You: 1. Add password strength indicator to login form
AI: ✅ Note added (Idea)
```

### Blocker
```
You: /notes
AI: What would you like to note?
You: 3. Waiting on API documentation for payment endpoint
AI: ✅ Note added (Question/Blocker)
```

---
allowed-tools: "*"

## Best Practices

### When to Use `/notes`
✅ Quick thoughts during implementation  
✅ Technical debt you discover  
✅ Ideas for future improvements  
✅ Questions that need answering later  
✅ Risks or concerns to address  
✅ Learning discoveries  

### When NOT to Use `/notes`
❌ Actual TODOs in code (use proper task tracking)  
❌ Critical blockers (address immediately or escalate)  
❌ Test failures (fix them, don't note them)  
❌ Constitution violations (fix them, don't defer)  

### Review Your Notes
- **Daily**: Check for quick wins or blockers
- **Weekly**: Convert ideas to tasks in `/plan`
- **Before merge**: Address technical debt notes
- **During `/audit`**: Review accumulated notes

---
allowed-tools: "*"

## Integration with Other Workflows

### With `/plan`
Convert notes to planned tasks:
```
Review NOTES.md → Identify ideas → Add to plan.md → Create tasks
```

### With `/implement`
Reference notes during implementation:
```
Check NOTES.md → Address technical debt → Update note as resolved
```

### With `/audit`
Use notes as audit input:
```
/audit reads NOTES.md → Identifies patterns → Recommends actions
```

### With `/verify`
Include notes in code review:
```
/verify checks NOTES.md → Ensures critical items addressed
```

---
allowed-tools: "*"

## Note Resolution

When you address a note, mark it as resolved:

**Before**:
```markdown
- [2025-01-15T14:30:00Z] 🐛 **Tech Debt**: File UserService.ts is 380 lines
```

**After**:
```markdown
- [2025-01-15T14:30:00Z] 🐛 **Tech Debt**: ~~File UserService.ts is 380 lines~~ 
  ✅ Resolved [2025-01-16T10:00:00Z]: Split into UserService and UserRepository
```

Or simply delete the note if it's no longer relevant.

---
allowed-tools: "*"

## Guardrails

- ✅ Notes are timestamped (traceability)
- ✅ Notes are categorized (easy filtering)
- ✅ Notes are per-effort or app-level (proper scoping)
- ✅ Notes don't replace proper task tracking
- ✅ Notes are reviewed regularly (not forgotten)

**Remember**: Notes are for capturing thoughts, not deferring critical work!

---
allowed-tools: "*"

## File Locations

**Effort-level notes** (preferred when in an effort):
```
.cfoi/branches/[branch]/efforts/[effort-name]/NOTES.md
```

**App-level notes** (for cross-effort or general notes):
```
.cfoi/branches/[branch]/NOTES.md
```

**Both files are gitignored** (personal notes, not committed)

---
allowed-tools: "*"

**Quick capture. Easy review. Never lose a thought.** 📝
