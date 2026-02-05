<!-- PLAN_APPROVAL: approved by Lance at 2026-02-05T17:51:00Z -->

# Plan: Bug Report Triage (v2026-02-05)

## User Story
As a product owner, I want incoming bug reports to be automatically classified as "bug" or "feature request" so that:
- Bugs continue through the existing AI Bug Fixer pipeline (GitHub issue → Claude fix)
- Feature requests are emailed to me for later review
- Low-confidence classifications are flagged via email while still being processed as bugs

## Architecture Decision

**Where triage runs:** Inside the existing `create_github_issue_task` background task in `bugs.py`, BEFORE the GitHub issue is created.

**LLM integration:** Extend the existing diagnostics summary generation to also classify the report. This keeps triage within the same LLM call context (no new round-trip).

**Flow:**
```
User submits report
    ↓
BugReport saved to DB (status: "captured")
    ↓
Background task: create_github_issue_task
    ↓
[NEW] LLM classifies report → { type: "bug" | "feature_request", confidence: 0-1 }
    ↓
┌─────────────────────────────────────────────────────────────┐
│ DECISION MATRIX                                             │
├─────────────────────────────────────────────────────────────┤
│ type=bug, confidence≥0.7        → GitHub issue (existing)   │
│ type=feature_request, conf≥0.7  → Email only, no GH issue   │
│ confidence<0.7 (either type)    → Treat as bug + Email      │
└─────────────────────────────────────────────────────────────┘
```

## Technical Spec

### 1. New Function: `classify_report()` in `bugs.py`

```python
async def classify_report(notes: str, expected: str | None, actual: str | None, diagnostics_summary: str) -> dict:
    """
    Use LLM to classify report as bug or feature request.
    Returns: { "type": "bug" | "feature_request", "confidence": 0.0-1.0, "reasoning": str }
    """
    prompt = f"""Classify this user report as either a BUG or a FEATURE REQUEST.

REPORT:
- Description: {notes}
- Expected: {expected or 'Not provided'}
- Actual: {actual or 'Not provided'}
- Diagnostics: {diagnostics_summary}

DEFINITIONS:
- BUG: Something is broken, not working as expected, causes errors, crashes, or incorrect behavior.
- FEATURE REQUEST: User wants new functionality, improvements, enhancements, or changes to existing behavior that isn't broken.

IMPORTANT: When uncertain, classify as BUG. It's safer to process a feature request as a bug than to miss a real bug.

Respond in JSON format:
{{"type": "bug" or "feature_request", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}
"""
    # Call existing LLM client (Anthropic/OpenAI)
```

### 2. New Function: `send_triage_notification_email()` in `services/email.py`

```python
async def send_triage_notification_email(
    to_email: str,
    report_id: int,
    report_notes: str,
    report_url: str | None,
    classification: str,  # "bug" | "feature_request"
    confidence: float,
    reasoning: str,
    screenshot_urls: list[str],
) -> EmailResult:
    """Send notification email for feature requests or low-confidence classifications."""
```

Email content:
- Subject: `[Triage] {classification}: {notes[:50]}...`
- Body: report summary, classification result, confidence, reasoning, screenshot links, diagnostics URL

### 3. Modify `create_github_issue_task()` in `bugs.py`

```python
async def create_github_issue_task(bug_id: int):
    # ... existing setup ...
    
    # NEW: Classify the report
    summary = generate_diagnostics_summary(bug.diagnostics) if bug.diagnostics else ""
    classification = await classify_report(bug.notes, bug.expected, bug.actual, summary)
    
    report_type = classification.get("type", "bug")
    confidence = classification.get("confidence", 0.0)
    reasoning = classification.get("reasoning", "")
    
    # Store classification on bug record
    bug.classification = report_type
    bug.classification_confidence = confidence
    
    # Decision logic
    is_low_confidence = confidence < 0.7
    is_feature_request = report_type == "feature_request" and not is_low_confidence
    
    # Send email if feature request OR low confidence
    if is_feature_request or is_low_confidence:
        await send_triage_notification_email(
            to_email="masseyl@gmail.com",
            report_id=bug.id,
            report_notes=bug.notes,
            report_url=extract_url_from_diagnostics(bug.diagnostics),
            classification=report_type,
            confidence=confidence,
            reasoning=reasoning,
            screenshot_urls=json.loads(bug.attachments) if bug.attachments else [],
        )
    
    # Create GitHub issue ONLY if bug (high or low confidence)
    if not is_feature_request:
        # ... existing GitHub issue creation ...
        bug.status = "sent"
    else:
        bug.status = "feature_request"
    
    session.add(bug)
    await session.commit()
```

### 4. Database Migration: Add fields to `BugReport` model

```python
# In models.py, add to BugReport:
classification: Optional[str] = Field(default=None)  # "bug" | "feature_request"
classification_confidence: Optional[float] = Field(default=None)  # 0.0-1.0
```

## File Changes Summary

| File | Change |
|------|--------|
| `apps/backend/routes/bugs.py` | Add `classify_report()`, modify `create_github_issue_task()` |
| `apps/backend/services/email.py` | Add `send_triage_notification_email()` |
| `apps/backend/models.py` | Add `classification`, `classification_confidence` fields |
| `apps/backend/tests/test_bug_triage.py` | New test file for triage logic |

## E2E Test Steps

1. **Bug report (high confidence):**
   - Submit: "App crashes when clicking search button"
   - Expect: GitHub issue created, no email sent

2. **Feature request (high confidence):**
   - Submit: "Would be nice to have dark mode"
   - Expect: Email sent to masseyl@gmail.com, NO GitHub issue

3. **Low confidence (ambiguous):**
   - Submit: "Search results aren't what I expected"
   - Expect: GitHub issue created AND email sent

## Success Criteria

- [ ] Classification accuracy ≥85% on sample reports (sampled)
- [ ] Bug flow unchanged — existing integration test passes (measured)
- [ ] Email delivery rate = 100% for feature requests/low confidence (measured)
- [ ] Triage latency <2 seconds (measured)
- [ ] Features-as-bugs rate <10% (sampled, acceptable)

## Assumptions

1. **LLM availability:** Existing LLM client (Anthropic) is available in bugs.py context
2. **Resend configured:** RESEND_API_KEY env var is set in production
3. **Confidence threshold:** 0.7 is appropriate; may need tuning based on real data
4. **Email hardcoded:** masseyl@gmail.com is acceptable for MVP; can add env var later

## Risks

1. **LLM latency:** Classification adds ~1-2 seconds to background task (acceptable)
2. **Classification accuracy:** May need prompt tuning after seeing real reports
3. **Email deliverability:** Resend should handle, but monitor for bounces

## Out of Scope

- User-facing classification feedback
- Feature request tracking/voting system
- Changing existing bug fix flow
- Configurable email recipients (future enhancement)
