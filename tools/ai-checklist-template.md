# Implementation Completion Checklist

**Date:** [YYYY-MM-DD]  
**Task:** [Task name from /task]  
**Branch:** [branch-name]  
**Implementer:** [AI Assistant Name]

---

## 📋 Code Completeness

- [ ] **All planned files created/modified**
  - List files:
    - `path/to/file1.js` (150 lines)
    - `path/to/file2.py` (200 lines)
- [ ] **No TODO or FIXME comments**
  - Verified with: `grep -r "TODO:\|FIXME:" src/`
  - Result: [0 matches / show output]

- [ ] **No placeholder implementations**
  - No empty functions
  - No `pass` / `raise NotImplementedError`
  - All functions have real logic
- [ ] **All imports at top of files**
  - Show first 10 lines of each new file
- [ ] **Error handling implemented**
  - List error scenarios handled:
    1. [Error type] → [How it's handled]
    2. [Error type] → [How it's handled]
  - Show code snippet:
    ```javascript
    try {
      // your code
    } catch (error) {
      // error handling
    }
    ```

- [ ] **Edge cases from /clarify are handled**
  - List edge cases from plan:
    1. [Edge case] → ✅ Handled in [file:line]
    2. [Edge case] → ✅ Handled in [file:line]

---

## 🧪 Testing

- [ ] **Unit tests written**
  - Test file: `path/to/file.test.js`
  - Line count: [XX lines]
  - Show test file contents (first 30 lines):
    ```javascript
    // paste test code here
    ```

- [ ] **Tests actually test the code**
  - Not just imports
  - Tests verify behavior
  - List test cases:
    1. [Test name] - Tests [behavior]
    2. [Test name] - Tests [behavior]

- [ ] **Tests pass locally**
  - Command run: `npm test` / `pytest` / etc.
  - Show output:
    ```
    [paste test output here]
    ```

- [ ] **Coverage is adequate**
  - Coverage %: [XX%]
  - Command: `npm run test:coverage`
  - Critical paths covered: Yes/No

---

## 📚 Documentation

- [ ] **env.example updated**
  - New environment variables added:
    ```bash
    # New variables added:
    NEW_VAR_NAME=description
    ANOTHER_VAR=description
    ```

- [ ] **README updated**
  - Section updated: [section name]
  - What changed: [brief description]

- [ ] **Code comments added**
  - Complex logic explained
  - "Why" not "what"
  - Show examples:
    ```javascript
    // Explain WHY this approach was chosen
    // Not just what it does
    ```

---

## 🔗 Integration

- [ ] **Integrates with existing codebase**
  - No breaking changes (or documented if intentional)
  - Follows existing patterns
  - Uses established conventions

- [ ] **Database changes handled**
  - [ ] N/A - No database changes
  - [ ] Migration created: [migration file]
  - [ ] Schema updated: [describe changes]
  - [ ] Seed data updated: [describe changes]

- [ ] **API contracts match /plan**
  - Endpoints implemented:
    - `POST /api/endpoint` - ✅ Matches plan
    - `GET /api/endpoint` - ✅ Matches plan
  - Request/response format verified

---

## ✅ Verification Proof

### File Contents Proof

Show relevant code sections (not just "I created it"):

**File: `path/to/main-file.js`**

```javascript
// Lines 1-20
[paste actual code here]
```

**File: `path/to/test-file.test.js`**

```javascript
// Lines 1-30
[paste actual test code here]
```

### Test Output Proof

```bash
$ npm test
[paste full test output]

✓ All tests passing
✓ Coverage: XX%
```

### Working Demo Proof

One of:

- [ ] Screenshot of working feature
- [ ] cURL command showing API working:

  ```bash
  $ curl -X POST http://localhost:8080/api/endpoint \
    -H "Content-Type: application/json" \
    -d '{"data": "value"}'

  Response: {"success": true}
  ```

- [ ] Logs showing feature working:
  ```
  [paste relevant logs]
  ```

### Verification Script Output

```bash
$ ./tools/verify-implementation.sh
[paste output]

✅ Implementation verification PASSED
```

---

## 🎯 Original Goal Verification

**Original task from /plan:**

```markdown
[paste original task description]
```

**How this implementation addresses it:**

- [Point 1] → Implemented in [file/function]
- [Point 2] → Implemented in [file/function]
- [Point 3] → Implemented in [file/function]

**Acceptance criteria met:**

- ✅ [Criterion 1]
- ✅ [Criterion 2]
- ✅ [Criterion 3]

---

## 📊 Self-Assessment

**Completeness:** [1-10] / 10  
**Code Quality:** [1-10] / 10  
**Test Coverage:** [1-10] / 10  
**Documentation:** [1-10] / 10

**Time Estimate vs Actual:**

- Estimated: [XX minutes]
- Actual: [XX minutes]
- Variance: [+/- XX minutes]

**Challenges encountered:**

1. [Challenge] - Resolved by [solution]
2. [Challenge] - Resolved by [solution]

**What could be better:**

1. [Improvement area]
2. [Improvement area]

---

## 🖊️ Sign-Off

**AI Confirmation:**
I confirm that:

- All checklist items above are complete
- I have provided proof for each item
- The code is production-ready
- Tests pass and prove correctness
- Documentation is updated
- No shortcuts were taken

**AI Signature:** [AI Name] - [Date/Time]

---

**Human Verification:**

- [ ] ✅ Approved - Ready to commit
- [ ] ⚠️ Needs work - See comments below

**Comments:**
[Human feedback here]

**Human Signature:** **\*\*\*\***\_**\*\*\*\*** - [Date]

---

## 📝 Notes

[Any additional notes, gotchas, or important context]

---

**Filing:** Save this checklist in `.cfoi/branches/[branch]/proof/[task-id]/checklist.md`
