# PRD 05: Trust & Safety Tooling

**Phase:** 6 — Customer Support & Trust Infrastructure  
**Priority:** P2  
**Status:** Planning  
**Parent:** [Phase 6 Parent](./parent.md)

---

## Problem Statement

The platform has **no moderation or enforcement infrastructure**. There is no way to:

- Review flagged content (spam quotes, abusive messages, fake listings)
- Enforce policies against bad actors (warnings, temporary bans, permanent bans)
- Monitor platform health signals (fraud patterns, abuse trends, content quality)
- Respond to legal or compliance requests (DMCA takedowns, law enforcement requests)
- Protect users from harassment, scams, or deceptive practices

The existing admin routes provide read-only stats and metrics. There are no admin actions for content moderation, user management, or policy enforcement beyond the merchant suspend concept (PRD 04).

---

## Solution Overview

Build a **Trust & Safety admin toolkit** that enables:

1. **Content moderation queue** — Flagged items (quotes, messages, user profiles) reviewed by admins
2. **User enforcement actions** — Warnings, temporary restrictions, permanent bans for both buyers and sellers
3. **Automated safety rules** — Configurable rules that auto-flag content matching patterns
4. **Compliance tools** — DMCA takedowns, data deletion requests, law enforcement response
5. **Safety dashboard** — Real-time view of platform health signals

---

## Scope

### In Scope
- Content flagging: users can report quotes, messages, and profiles
- Admin moderation queue with review/action workflow
- User enforcement: warning, restrict, temporary ban, permanent ban
- Automated rules: profanity filter, spam detection (duplicate content), suspicious URL detection
- Action audit trail (who did what, when, why)
- User-facing: appeal process via support tickets (PRD 01)
- Safety metrics dashboard for admins
- GDPR data deletion request handling
- Blocked user list management

### Out of Scope
- Machine learning-based content classification
- Real-time content scanning (v1 is flag-and-review)
- Legal case management system
- External trust & safety vendor integration (Hive, Spectrum Labs)
- Age verification or child safety (COPPA)

---

## User Stories

**US-01:** As a buyer, I want to report a suspicious seller quote so the platform can investigate.

**US-02:** As a seller, I want to report a buyer who is harassing me through messages.

**US-03:** As an admin, I want to see a queue of flagged content and take action (dismiss, warn, ban).

**US-04:** As an admin, I want to temporarily restrict a user who is behaving badly, with the restriction automatically lifting after a set period.

**US-05:** As a banned user, I want to understand why I was banned and how to appeal.

**US-06:** As an admin, I want to see safety metrics (flags/day, enforcement actions, appeal rate) to monitor platform health.

**US-07:** As a user, I want to request deletion of all my data (GDPR right to erasure).

---

## Business Requirements

### Flagging System

Users can flag:

| Flaggable Content | Flag Reasons |
|-------------------|-------------|
| Seller quote / bid | Spam, misleading price, fake listing, inappropriate content |
| Message (PRD 03) | Harassment, spam, scam attempt, sharing personal info unsolicited |
| User profile | Fake identity, impersonation, offensive content |
| Merchant profile | Fraudulent business, stolen identity, spam registration |

Each flag creates a `ContentFlag` record routed to the moderation queue.

### Enforcement Actions

| Action | Severity | Duration | Effect |
|--------|----------|----------|--------|
| `warning` | Low | N/A | User sees warning notice; recorded in history |
| `restrict_messaging` | Medium | 7-30 days | Cannot send messages; can still quote and buy |
| `restrict_quoting` | Medium | 7-30 days | Seller cannot submit quotes; can still browse |
| `temporary_ban` | High | 14-90 days | Cannot access platform; auto-lifts after period |
| `permanent_ban` | Critical | Permanent | Account disabled; email blocked from re-registration |

All enforcement actions:
- Require a written reason
- Notify the user via email
- Create an audit log entry
- Auto-create an appeal ticket (PRD 01) for bans

### Automated Safety Rules

| Rule | Trigger | Action |
|------|---------|--------|
| Duplicate content | Same bid description submitted to 5+ rows | Auto-flag for review |
| Suspicious URLs | Bid URL matches known phishing domains | Auto-flag + hide from buyer |
| High flag rate | User receives 3+ flags in 7 days | Auto-flag profile for review |
| Rapid-fire quoting | Seller submits 20+ quotes in 1 hour | Auto-restrict quoting for 24h |
| Profanity | Message contains profanity (configurable word list) | Warn sender; deliver message with content warning |

Rules are configurable by admins (enable/disable, adjust thresholds).

### Data Requirements

**ContentFlag model:**
```
id
reporter_user_id (FK user)
content_type: bid | message | user_profile | merchant_profile
content_id: int — ID of the flagged item
reason: spam | misleading | harassment | scam | fake | inappropriate | other
description (text, nullable) — reporter's explanation
status: pending | reviewed | actioned | dismissed
reviewed_by_user_id (FK user, nullable)
review_notes (text, nullable)
action_taken (str, nullable) — reference to enforcement action
created_at, reviewed_at
```

**EnforcementAction model:**
```
id
target_user_id (FK user)
action_type: warning | restrict_messaging | restrict_quoting | temporary_ban | permanent_ban
reason (text)
issued_by_user_id (FK user) — admin
related_flag_id (FK content_flag, nullable)

# Duration
starts_at: datetime
expires_at: datetime (nullable — null for permanent)
is_active: bool (default true)

# Appeal
appeal_ticket_id (FK support_ticket, nullable)
appeal_status: none | pending | upheld | overturned

created_at
```

**SafetyRule model:**
```
id
name: str
rule_type: duplicate_content | suspicious_url | high_flag_rate | rapid_fire | profanity
enabled: bool (default true)
threshold: int — configurable trigger threshold
action: auto_flag | auto_restrict | auto_warn
cooldown_hours: int (default 24)
created_at, updated_at
```

### Authentication & Authorization
- **Flag content:** Authenticated users
- **Moderation queue:** Admin only
- **Enforcement actions:** Admin only
- **View own enforcement history:** Authenticated user (own records only)
- **Safety rules config:** Admin only
- **Safety dashboard:** Admin only

### Performance
- Flag submission < 300ms
- Moderation queue load < 500ms
- Enforcement action application < 500ms
- Automated rule check (per action) < 100ms

---

## Technical Design

### Backend

**New file:** `routes/trust_safety.py`

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /flags` | User | Report content |
| `GET /flags/mine` | User | My submitted flags |
| `GET /admin/flags` | Admin | Moderation queue (filter by status, type, date) |
| `PATCH /admin/flags/{id}` | Admin | Review flag (dismiss or action) |
| `POST /admin/enforcement` | Admin | Issue enforcement action against user |
| `GET /admin/enforcement` | Admin | List enforcement actions (filter by user, type, status) |
| `PATCH /admin/enforcement/{id}` | Admin | Modify action (e.g., overturn on appeal) |
| `GET /admin/safety/rules` | Admin | List automated rules |
| `PATCH /admin/safety/rules/{id}` | Admin | Update rule config |
| `GET /admin/safety/dashboard` | Admin | Safety metrics summary |
| `GET /enforcement/mine` | User | My enforcement history |

**New file:** `services/safety_rules.py`
- Rule engine: check incoming actions against configured rules
- Called from: bid creation, message send, flag creation
- Returns: list of triggered rules and their actions

**New file:** `services/enforcement.py`
- Apply enforcement action (update user restrictions)
- Check if user is currently restricted (middleware/dependency)
- Auto-expire temporary bans (cron job)

**New dependency:** `dependencies.py` update
- `check_user_restrictions(user)` — called before protected actions
- Returns 403 with restriction details if user is banned/restricted

### Frontend

| Page | Description |
|------|-------------|
| Flag button (component) | Reusable "Report" button on quotes, messages, profiles |
| Flag modal | Select reason + optional description |
| `/admin/safety` | Safety dashboard: metrics, recent flags, active enforcements |
| `/admin/safety/flags` | Moderation queue with bulk actions |
| `/admin/safety/flags/[id]` | Flag detail: content preview, reporter info, action buttons |
| `/admin/safety/enforcement` | Enforcement action list |
| `/admin/safety/rules` | Rule configuration panel |
| `/account/safety` | User-facing: view my restrictions, appeal link |

### Middleware Integration

```python
async def check_restrictions(user: User, action: str, session: AsyncSession):
    """Check if user has active restrictions blocking this action."""
    active = await get_active_enforcements(session, user.id)
    for enforcement in active:
        if enforcement.action_type == "permanent_ban":
            raise HTTPException(403, "Your account has been permanently suspended.")
        if enforcement.action_type == "temporary_ban":
            raise HTTPException(403, f"Your account is temporarily suspended until {enforcement.expires_at}.")
        if enforcement.action_type == "restrict_messaging" and action == "send_message":
            raise HTTPException(403, "Your messaging privileges are temporarily restricted.")
        if enforcement.action_type == "restrict_quoting" and action == "submit_quote":
            raise HTTPException(403, "Your quoting privileges are temporarily restricted.")
```

---

## GDPR Data Deletion

### Flow
1. User submits deletion request via `/account/delete` or support ticket
2. Admin reviews (5-day cooling-off period)
3. System anonymizes: replace PII with `[deleted_user_XXXX]`, null out emails, phones
4. Preserve: transaction records (legal requirement), anonymized flags, anonymized messages
5. Delete: sessions, preferences, signals, bookmarks, notification records
6. Confirm deletion to user via email (last email sent)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Flag-to-review time (median) | < 24 hours |
| False positive rate (dismissed flags / total) | < 40% |
| Enforcement appeal rate | < 15% |
| Appeal overturn rate | < 20% |
| Repeat offender rate (same user flagged again after action) | < 10% |
| User reports per 1000 active users | < 5 (healthy platform) |

---

## Acceptance Criteria

- [ ] Users can flag quotes, messages, and profiles with a reason
- [ ] Admin moderation queue shows all pending flags with content preview
- [ ] Admin can dismiss a flag or take enforcement action from the queue
- [ ] Enforcement actions: warning, restrict_messaging, restrict_quoting, temporary_ban, permanent_ban
- [ ] Temporary bans auto-expire after configured duration
- [ ] Banned users cannot access protected endpoints (403 with explanation)
- [ ] Restricted users blocked from specific actions (messaging or quoting) per restriction type
- [ ] All enforcement actions are audit-logged with admin, reason, and timestamp
- [ ] Email sent to user on every enforcement action with reason and appeal instructions
- [ ] Automated rules configurable by admin (enable/disable, thresholds)
- [ ] At least one automated rule functional: duplicate content detection
- [ ] Safety dashboard shows flag volume, action count, and resolution metrics
- [ ] GDPR data deletion request flow implemented with cooling-off period
- [ ] User can view their own enforcement history at `/account/safety`

---

## Dependencies
- **PRD 01 (Support Tickets):** Appeals create support tickets
- **PRD 02 (Disputes):** Dispute outcomes may trigger enforcement
- **PRD 03 (Messaging):** Message flagging and messaging restrictions
- **PRD 04 (Seller Verification):** Merchant suspension is a special case of enforcement
- **Phase 4 PRD 10 (Anti-Fraud):** Fraud detection feeds into safety rules

## Risks
- **Over-moderation** — Aggressive rules alienate legitimate users → start conservative, tune based on data
- **Under-moderation** — Lax rules erode trust → monitor flag volume and resolution quality
- **Admin abuse** — Single admin makes bad calls → require reason for all actions; track admin action patterns
- **Scale** — Manual review doesn't scale past ~100 flags/day → plan for automated classification (ML) in future
- **Legal complexity** — GDPR, CDA §230, varying jurisdictions → consult legal before launch; document policies clearly
