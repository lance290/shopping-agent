# Implementation Plan: PRD 05 — Trust & Safety Tooling

**Status:** Draft — awaiting approval  
**Priority:** P2 (capstone — build last, after all other PRDs)  
**Estimated effort:** 2-3 days  
**Depends on:** PRD 01 (tickets for appeals), PRD 02 (disputes feed enforcement), PRD 03 (message flagging), PRD 04 (merchant suspension)

---

## Goal

Give admins the tools to moderate content, enforce policies, and protect users. Build the flagging system, enforcement actions, automated safety rules, and a safety dashboard.

---

## Current State

- **No moderation tools.** Admin routes provide read-only stats/metrics but no actions on content or users.
- `Merchant` has suspend capability (via PRD 04 plan), but no equivalent for buyers.
- No flagging system — users can't report problematic content.
- No enforcement history — no record of warnings, restrictions, or bans.
- No automated rules — spam bids, duplicate content, and suspicious patterns go undetected.
- Bug reports go to GitHub; there's no content moderation pipeline.

---

## Build Order

### Phase A: Backend Models + Migration (30 min)

**File: `apps/backend/models.py`** — add three models:

```python
class ContentFlag(SQLModel, table=True):
    __tablename__ = "content_flag"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    reporter_user_id: int = Field(foreign_key="user.id", index=True)
    
    content_type: str = Field(index=True)  # bid, message, user_profile, merchant_profile
    content_id: int  # ID of the flagged item
    
    reason: str  # spam, misleading, harassment, scam, fake, inappropriate, other
    description: Optional[str] = None
    
    status: str = "pending"  # pending, reviewed, actioned, dismissed
    reviewed_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    review_notes: Optional[str] = None
    action_taken: Optional[str] = None  # Reference to EnforcementAction
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None


class EnforcementAction(SQLModel, table=True):
    __tablename__ = "enforcement_action"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    target_user_id: int = Field(foreign_key="user.id", index=True)
    
    action_type: str  # warning, restrict_messaging, restrict_quoting, temporary_ban, permanent_ban
    reason: str
    issued_by_user_id: int = Field(foreign_key="user.id")
    related_flag_id: Optional[int] = Field(default=None, foreign_key="content_flag.id")
    
    starts_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # null for permanent
    is_active: bool = True
    
    # Appeal
    appeal_ticket_id: Optional[int] = Field(default=None, foreign_key="support_ticket.id")
    appeal_status: str = "none"  # none, pending, upheld, overturned
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SafetyRule(SQLModel, table=True):
    __tablename__ = "safety_rule"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    rule_type: str  # duplicate_content, suspicious_url, high_flag_rate, rapid_fire, profanity
    enabled: bool = True
    threshold: int = 5  # Trigger threshold (varies by rule)
    action: str = "auto_flag"  # auto_flag, auto_restrict, auto_warn
    cooldown_hours: int = 24
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Migration:** Create three tables + seed default `SafetyRule` rows.

---

### Phase B: Restriction Checking Middleware (30 min)

**File: `apps/backend/dependencies.py`** — add new dependency:

```python
async def check_user_restrictions(
    user_id: int,
    action: str,  # "send_message", "submit_quote", "general"
    session: AsyncSession,
):
    """Check if user has active restrictions blocking this action. Raises 403 if restricted."""
    from models import EnforcementAction
    
    now = datetime.utcnow()
    result = await session.exec(
        select(EnforcementAction).where(
            EnforcementAction.target_user_id == user_id,
            EnforcementAction.is_active == True,
            or_(
                EnforcementAction.expires_at == None,  # permanent
                EnforcementAction.expires_at > now,     # not expired
            ),
        )
    )
    
    for enforcement in result.all():
        if enforcement.action_type == "permanent_ban":
            raise HTTPException(403, "Your account has been permanently suspended.")
        if enforcement.action_type == "temporary_ban":
            raise HTTPException(403, f"Your account is suspended until {enforcement.expires_at.isoformat()}.")
        if enforcement.action_type == "restrict_messaging" and action == "send_message":
            raise HTTPException(403, "Your messaging privileges are temporarily restricted.")
        if enforcement.action_type == "restrict_quoting" and action == "submit_quote":
            raise HTTPException(403, "Your quoting privileges are temporarily restricted.")
```

Wire into:
- `routes/seller.py` → `submit_quote()` — check `"submit_quote"` restriction
- `routes/messages.py` → send message — check `"send_message"` restriction
- General auth flow — check `"general"` for bans

---

### Phase C: Backend Routes (2-3 hours)

**New file: `apps/backend/routes/trust_safety.py`**

#### User-facing:

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /flags` | User | Report content. Body: `{ content_type, content_id, reason, description? }` |
| `GET /flags/mine` | User | My submitted flags |
| `GET /enforcement/mine` | User | My enforcement history (warnings, restrictions) |

#### Admin:

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /admin/flags` | Admin | Moderation queue. Filters: `?status=`, `?content_type=`, `?reason=` |
| `PATCH /admin/flags/{id}` | Admin | Review flag: dismiss or action. Body: `{ status, review_notes?, action_taken? }` |
| `POST /admin/enforcement` | Admin | Issue enforcement action. Body: `{ target_user_id, action_type, reason, expires_at?, related_flag_id? }` |
| `GET /admin/enforcement` | Admin | List all actions. Filters: `?target_user_id=`, `?action_type=`, `?is_active=` |
| `PATCH /admin/enforcement/{id}` | Admin | Modify action (overturn on appeal). Body: `{ is_active?, appeal_status? }` |
| `GET /admin/safety/rules` | Admin | List automated rules |
| `PATCH /admin/safety/rules/{id}` | Admin | Update rule config. Body: `{ enabled?, threshold?, action? }` |
| `GET /admin/safety/dashboard` | Admin | Safety metrics: flags/day, actions/day, appeal rate, top reasons |

#### Flag creation logic:
1. Validate `content_type` + `content_id` exist
2. Check for duplicate flag (same user, same content) → 409
3. Create flag
4. Check automated rules (Phase D)
5. Notify admin

#### Enforcement action logic:
1. Create action record
2. If `temporary_ban` or `permanent_ban`: auto-create appeal ticket (PRD 01)
3. Send email to target user with reason + appeal instructions
4. Audit log
5. If merchant: also update `Merchant.status` to "suspended" (PRD 04 integration)

---

### Phase D: Automated Safety Rules Engine (1 hour)

**New file: `apps/backend/services/safety_rules.py`**

```python
async def check_safety_rules(
    session: AsyncSession,
    event_type: str,  # "bid_created", "message_sent", "flag_created"
    user_id: int,
    content_id: Optional[int] = None,
) -> list[dict]:
    """Check if any safety rules are triggered. Returns list of triggered actions."""
```

Rules implemented for v1:

| Rule | Event | Check | Action |
|------|-------|-------|--------|
| `duplicate_content` | `bid_created` | Same bid description submitted to 5+ rows by same seller | Auto-flag bid |
| `high_flag_rate` | `flag_created` | User received 3+ flags in 7 days | Auto-flag user profile for review |
| `rapid_fire_quoting` | `bid_created` | Seller submitted 20+ quotes in 1 hour | Auto-restrict quoting for 24h |

Call from:
- `routes/seller.py` → `submit_quote()` after bid creation
- `routes/messages.py` → message send (for future message-based rules)
- `routes/trust_safety.py` → flag creation

---

### Phase E: Enforcement Expiration (30 min)

**New file: `apps/backend/services/enforcement.py`**

```python
async def expire_enforcements(session: AsyncSession) -> int:
    """Deactivate enforcement actions past their expires_at. Returns count expired."""
    now = datetime.utcnow()
    result = await session.exec(
        select(EnforcementAction).where(
            EnforcementAction.is_active == True,
            EnforcementAction.expires_at != None,
            EnforcementAction.expires_at <= now,
        )
    )
    count = 0
    for action in result.all():
        action.is_active = False
        session.add(action)
        count += 1
    await session.commit()
    return count
```

Add admin endpoint: `POST /admin/safety/expire-enforcements` — triggers expiration check.

---

### Phase F: Frontend — Flag Button Component (30 min)

**New file: `apps/frontend/app/components/FlagButton.tsx`**

Reusable "Report" button. Props: `contentType`, `contentId`.
- Click → modal with reason selector + optional description
- Submit → `POST /api/flags`
- Confirmation: "Thank you for reporting. We'll review this."

Add to:
- `OfferTile.tsx` — report a bid/quote (kebab menu)
- `MessagePanel.tsx` — report a message
- User profile (if one exists)

---

### Phase G: Frontend — Admin Safety Pages (1-2 hours)

**New file: `apps/frontend/app/admin/safety/page.tsx`**

Safety dashboard:
- Key metrics cards: flags today, open flags, active enforcements, appeal rate
- Recent flags table (quick actions: dismiss, escalate)
- Active enforcements table

**New file: `apps/frontend/app/admin/safety/flags/page.tsx`**

Moderation queue:
- Table: content preview, reporter, reason, status, age
- Click → flag detail with full content preview
- Actions: dismiss, issue warning, restrict, ban

**New file: `apps/frontend/app/admin/safety/rules/page.tsx`**

Rule configuration:
- Toggle enable/disable per rule
- Adjust thresholds
- View trigger history

**New file: `apps/frontend/app/account/safety/page.tsx`**

User-facing enforcement history:
- List of any warnings, restrictions, bans
- Appeal status if applicable
- Link to support ticket for active appeals

---

### Phase H: Frontend Proxy Routes (15 min)

| Route file | Proxies to |
|-----------|-----------|
| `app/api/flags/route.ts` | `GET, POST /flags` |
| `app/api/enforcement/mine/route.ts` | `GET /enforcement/mine` |
| `app/api/admin/flags/route.ts` | `GET /admin/flags` |
| `app/api/admin/flags/[id]/route.ts` | `PATCH /admin/flags/{id}` |
| `app/api/admin/enforcement/route.ts` | `GET, POST /admin/enforcement` |
| `app/api/admin/enforcement/[id]/route.ts` | `PATCH /admin/enforcement/{id}` |
| `app/api/admin/safety/rules/route.ts` | `GET /admin/safety/rules` |
| `app/api/admin/safety/rules/[id]/route.ts` | `PATCH /admin/safety/rules/{id}` |
| `app/api/admin/safety/dashboard/route.ts` | `GET /admin/safety/dashboard` |

---

### Phase I: Tests (1 hour)

**New file: `apps/backend/tests/test_trust_safety.py`**

| # | Test | Expected |
|---|------|----------|
| 1 | Flag content (happy path) | 200, flag created |
| 2 | Flag duplicate (same user, same content) | 409 |
| 3 | Flag requires auth | 401 |
| 4 | Admin moderation queue | 200, pending flags |
| 5 | Admin dismiss flag | 200, status=dismissed |
| 6 | Admin issue warning | 200, enforcement created |
| 7 | Admin issue temporary ban | 200, user blocked, appeal ticket created |
| 8 | Banned user gets 403 on general actions | 403 |
| 9 | Messaging-restricted user can still buy | 200 on non-message actions |
| 10 | Enforcement expires automatically | Action deactivated after expiry |
| 11 | Appeal overturn reactivates user | 200, is_active=false |
| 12 | Safety rule: duplicate content detection | Auto-flag triggered |
| 13 | Safety rule: rapid-fire quoting | Auto-restrict triggered |
| 14 | Non-admin can't access admin endpoints | 403 |
| 15 | User can see own enforcement history | 200, own records only |

---

## Files Changed Summary

| File | Change Type | Lines Est. |
|------|------------|-----------|
| `apps/backend/models.py` | Add `ContentFlag`, `EnforcementAction`, `SafetyRule` | +55 |
| `apps/backend/routes/trust_safety.py` | **New file** — 11 endpoints | ~400 |
| `apps/backend/services/safety_rules.py` | **New file** — rule engine | ~100 |
| `apps/backend/services/enforcement.py` | **New file** — expiration logic | ~40 |
| `apps/backend/dependencies.py` | Add `check_user_restrictions()` | +30 |
| `apps/backend/routes/seller.py` | Wire restriction check into quote submission | ~5 modified |
| `apps/backend/routes/messages.py` | Wire restriction check into message send | ~5 modified |
| `apps/backend/main.py` | Register trust_safety router | +2 |
| `apps/backend/services/email.py` | Add `send_enforcement_email()` | +50 |
| `apps/backend/alembic/versions/p6_trust_safety.py` | **New file** — create tables + seed rules | ~50 |
| `apps/backend/tests/test_trust_safety.py` | **New file** — 15 tests | ~350 |
| `apps/frontend/app/components/FlagButton.tsx` | **New file** | ~80 |
| `apps/frontend/app/components/OfferTile.tsx` | Add report button | ~10 modified |
| Frontend admin pages (3 files) | **New files** | ~400 |
| `apps/frontend/app/account/safety/page.tsx` | **New file** | ~100 |
| Frontend proxy routes (9 files) | **New files** | ~135 |

**Total:** ~1,810 lines across 23 files (17 new, 6 modified)

---

## Open Questions

1. **Should flagging be rate-limited?** (Recommendation: Yes — max 10 flags per user per day to prevent flag abuse.)
2. **Should we notify the target when they're flagged?** (Recommendation: No — only notify on enforcement action, not on raw flag. Prevents retaliation.)
3. **Seed safety rules:** Should rules be database-seeded or hardcoded? (Recommendation: Database-seeded via migration for admin configurability, with sensible defaults.)
4. **GDPR data deletion:** Include in this PRD or separate? (Recommendation: Separate micro-PRD, but note it here as a dependency. The `check_user_restrictions` function should also check for deletion-requested accounts.)
