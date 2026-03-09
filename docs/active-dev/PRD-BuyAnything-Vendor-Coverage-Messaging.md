# PRD: BuyAnything Vendor Coverage Messaging and EA Attribution

## 1. Executive Summary

BuyAnything needs a clearer user experience when the system understands a request but does not yet have enough relevant vendor coverage to fulfill it well.

Today, thin-coverage cases can fall through to a generic empty-response experience. That is misleading. It makes the system look broken when the real issue is that the request was understood, but the vendor base is not yet deep enough.

This PRD defines the MVP behavior for vendor coverage messaging:

1. Detect when a request has inadequate vendor coverage.
2. Tell the user, in plain language, that coverage is currently thin and that the request will be escalated internally.
3. Include the requesting EA’s identity in the vendor coverage report email.
4. If the requester identity is incomplete, ask for the missing information in the conversation.

This is an **email-first operational workflow**, not a dashboard project.

---

## 2. Product Decisions Locked By This PRD

### 2.1 Email-first, not dashboard-first
For MVP, vendor coverage gaps will be routed through email reports to operations.

- No admin dashboard is required for this feature.
- No analyst console is required for this feature.
- The operational handoff is the report email plus the existing vendor sourcing workflow.

### 2.2 Coverage-gap messaging should be explicit and reassuring
When the platform lacks adequate vendor coverage, the user should be told that directly.

- The message must communicate that BuyAnything does not yet have enough coverage for the request.
- The message must communicate that the request has been flagged or escalated internally.
- The tone should be helpful and proactive, not apologetic in a broken-system way.

### 2.3 The requester must be identifiable in the ops report
A vendor coverage report without the requesting EA is operationally weak.

- The report must include the requesting EA when available.
- At minimum, the system should try to include name, company, email, and phone.

### 2.4 Missing requester identity should be recovered conversationally
If the requester identity is incomplete, the system should ask for it in-chat.

- This should not block the search itself.
- This should be asked only when necessary.
- The prompt should be framed as needed to route the sourcing request properly.

### 2.5 Thin coverage is not the same as platform failure
If the issue is a real system error, provider outage, or transport failure, the user should see the relevant failure state.

- The vendor coverage message must not overwrite genuine error handling.
- The vendor coverage message is for understood requests with insufficient vendor supply.

---

## 3. Current Problems

### 3.1 Generic empty-response copy is misleading
The current fallback behavior can imply that the assistant failed to respond, when in reality the platform may have understood the request correctly but lacked strong vendor coverage.

### 3.2 The user is not told what actually happened
In thin-coverage cases, the user does not get a clear explanation that:

- the request was understood
- the vendor directory is not yet sufficient
- the team will act on the coverage gap

### 3.3 Ops reports lack requester context
A vendor coverage signal is less useful if the report does not identify who made the request.

Without requester identity, ops cannot easily:

- prioritize follow-up
- understand the relationship context
- reconnect the newly sourced vendors back to the original EA

### 3.4 There is no clear recovery path for missing EA identity
If the system does not have enough identity data, it should ask for it at the moment the coverage gap is surfaced.

---

## 4. Desired Launch Behavior

### 4.1 When a request is understood but vendor coverage is thin
If BuyAnything recognizes the request and determines that relevant vendor coverage is insufficient, the user should receive a vendor-coverage-aware message.

The message should communicate:

- we do not yet have strong enough vendor coverage for this request
- the request has been flagged internally
- we will work to source or add the needed vendors quickly

### 4.2 When requester identity is missing or incomplete
If the system does not have sufficient requester identity, the assistant should add a short follow-up asking for the missing information.

Examples of missing identity data that may trigger a prompt:

- name
- company
- both name and company

### 4.3 When identity is already known
If the requester identity is already available, the assistant should not ask for it again.

### 4.4 When the system is actually failing
If there is a real system error, timeout, or provider failure state, the normal error handling should remain in place.

### 4.5 Ops email behavior
When a vendor coverage gap is logged for reporting, the email should include:

- canonical need / request summary
- the search query or vendor-discovery hint
- confidence / rationale
- suggested sourcing queries
- requester identity fields
- a note when requester identity is still incomplete

---

## 5. Scope

### In scope
- Detect thin vendor coverage for understood user requests.
- Replace misleading empty-response behavior with coverage-aware messaging.
- Attach requester identity to vendor coverage reporting.
- Ask for missing requester identity in the conversation.
- Keep the workflow email-first for MVP.

### Out of scope
- Building an admin dashboard for vendor coverage gaps.
- Building a full CRM workflow for EA follow-up.
- Building automatic vendor acquisition or outreach automation from this PRD alone.
- Reworking general error handling unrelated to vendor coverage.

---

## 6. Primary User Stories

### 6.1 EA requesting a hard-to-source vendor
As an EA, when I ask for something the system understands but does not yet cover well, I want a clear explanation so I know the request is being handled rather than silently failing.

### 6.2 Ops reviewing a coverage-gap report
As an operator, I want to see who made the request so I can understand context and prioritize sourcing work.

### 6.3 EA with incomplete profile
As an EA whose identity details are incomplete, I want the system to ask me for the missing information at the relevant moment so my sourcing request can be routed correctly.

---

## 7. Functional Requirements

### 7.1 Vendor coverage gap detection
The system must determine whether a search/request represents inadequate vendor coverage.

For MVP, the trigger may be based on the existing vendor coverage assessment logic.

A thin-coverage determination should consider signals such as:

- zero or near-zero relevant vendor matches
- low-confidence or weak vendor-directory coverage
- mismatch between recognized intent and available vendor supply

### 7.2 User-facing coverage message
When a thin-coverage condition is detected, the assistant must provide a user-facing message instead of a generic empty-response fallback.

The message must:

- acknowledge insufficient current vendor coverage
- indicate internal follow-up or escalation
- avoid sounding like a generic assistant failure

The exact wording is not locked, but the meaning is.

### 7.3 Do not override real errors
If the system has a genuine error or provider failure that should be exposed, the vendor coverage message must not replace that error state.

### 7.4 Requester identity capture for reports
Each vendor coverage report item should include the requesting EA’s identity when available.

Target fields:

- requester name
- requester company
- requester email
- requester phone

### 7.5 Missing requester identity prompt
If required requester identity fields are missing, the assistant should ask for them in-chat.

MVP requirement:

- ask for missing `name`, `company`, or both
- do not repeatedly ask if the information is already known
- phrase the request as operationally useful, not bureaucratic

### 7.6 Email report content
The vendor coverage report email must include, per gap:

- request summary
- row/request title when available
- search query
- vendor query / sourcing hint when available
- geo hint when available
- rationale
- confidence
- suggested discovery queries
- requester identity fields
- explicit note when requester identity is missing

### 7.7 Deduplication and aggregation remain valid
This PRD does not replace the existing aggregation concept for repeated vendor coverage gaps.

If multiple similar requests map to the same canonical gap, the reporting path may continue to aggregate them, provided requester context remains useful.

### 7.8 Frontend behavior
If search results stream back with a vendor-coverage-aware user message, the chat UI should display that message rather than falling back to a generic empty assistant message.

---

## 8. UX Copy Guidance

The exact copy is flexible, but it must preserve these content elements:

1. We do not currently have adequate or strong vendor coverage for this request.
2. We are notifying the internal team / flagging it for sourcing.
3. We will work to add or source those vendors quickly.
4. If needed, we need the requester’s name and/or company.

The copy should avoid:

- implying the user did something wrong
- implying the assistant crashed
- overpromising a delivery timeline
- sounding robotic or bureaucratic

---

## 9. Acceptance Criteria

### AC-1 Thin coverage produces the correct user message
When a request is understood but vendor coverage is insufficient, the user sees a vendor-coverage-aware message instead of the generic empty-response fallback.

### AC-2 Real errors still surface as errors
When the system encounters a genuine error, the normal error path is preserved and is not overwritten by coverage messaging.

### AC-3 Requester identity is included in reports when known
When requester identity exists, the vendor coverage email includes the requester’s available name, company, email, and phone.

### AC-4 Missing requester identity is flagged and requested
When requester identity is incomplete, the system:

- asks the user for the missing info in-chat
- marks the missing fields in the vendor coverage report

### AC-5 Known requester identity is not redundantly requested
If the requester identity is already present, the system does not ask for it again.

### AC-6 Email-first workflow remains intact
The feature can be operated successfully through email reporting alone, without requiring a new dashboard.

---

## 10. Success Metrics

For MVP, success should be measured by directional operational quality, not a complex analytics program.

Suggested indicators:

- reduction in generic empty-response incidents for thin-coverage cases
- percentage of vendor coverage reports that include requester identity
- percentage of missing-identity cases successfully recovered through chat
- operator confidence that vendor gap emails are actionable

---

## 11. Risks and Open Questions

### 11.1 Over-triggering thin-coverage messaging
If detection is too aggressive, users may be told coverage is thin even when acceptable results exist.

### 11.2 Under-triggering thin-coverage messaging
If detection is too conservative, users may still see confusing empty or weak-response behavior.

### 11.3 Identity policy refinement
MVP focuses on `name` and `company` as the conversationally important missing fields, but this may later expand depending on ops needs.

### 11.4 Follow-up ownership
This PRD assumes internal ops or the founder/vendor sourcing workflow owns follow-up after the email report is generated.
