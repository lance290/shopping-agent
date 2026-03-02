# Task 06: Production Hardening + Audit Trail

**Priority:** P0  
**Estimated Time:** 3 days  
**Dependencies:** Tasks 01-05 (all prior work)  
**Outcome:** Money-safe, auditable, compliant system

---

## Objective

Harden the system for production use where **real money is involved** (affiliate commissions, potential future transactions):
1. Comprehensive audit logging
2. Error handling + graceful degradation
3. Rate limiting + abuse prevention
4. Admin access controls
5. Compliance infrastructure

---

## Why This Matters

> "This needs to be production grade and WILL be handling people's money (even if second hand)"

- Affiliate networks will audit our click data
- Users may dispute charges/recommendations
- We need forensic capability if something goes wrong
- Compliance with FTC affiliate disclosure rules

---

## Implementation Steps

### Step 6.1: Create AuditLog Model

**File:** `apps/backend/models.py`

```python
class AuditLog(SQLModel, table=True):
    """
    Immutable audit log for all significant system events.
    
    This is append-only. No UPDATE or DELETE operations allowed.
    """
    __tablename__ = "audit_log"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # When
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Who
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    session_id: Optional[int] = Field(default=None)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # What
    action: str = Field(index=True)  # e.g., "row.create", "clickout", "auth.login"
    resource_type: Optional[str] = None  # e.g., "row", "user", "clickout"
    resource_id: Optional[str] = None  # e.g., "123"
    
    # Details
    details: Optional[str] = None  # JSON string with action-specific data
    
    # Outcome
    success: bool = True
    error_message: Optional[str] = None
```

**Audit Actions to Log:**
- `auth.login_start`
- `auth.login_verify`
- `auth.logout`
- `row.create`
- `row.update`
- `row.delete`
- `search.execute`
- `clickout.redirect`
- `admin.access`

- [ ] Add AuditLog model
- [ ] Create Alembic migration
- [ ] Document all audit action types

**Test:** Can insert and query audit logs

---

### Step 6.2: Create Audit Logging Utility

**New File:** `apps/backend/audit.py`

```python
"""
Audit logging utilities.

Usage:
    await audit_log(
        session=db_session,
        action="row.create",
        user_id=user.id,
        resource_type="row",
        resource_id=str(row.id),
        details={"title": row.title},
        request=request,  # Optional FastAPI Request for IP/UA
    )
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Request
import json

from models import AuditLog


async def audit_log(
    session: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    request: Optional[Request] = None,
):
    """
    Create an audit log entry.
    
    This should never raise - failures are logged but not propagated.
    """
    try:
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", "")[:500]  # Truncate
        
        log_entry = AuditLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            success=success,
            error_message=error_message,
        )
        
        session.add(log_entry)
        await session.commit()
        
    except Exception as e:
        # Never let audit logging break the main flow
        print(f"[AUDIT ERROR] Failed to log {action}: {e}")


def redact_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields from audit details."""
    sensitive_keys = {'password', 'token', 'secret', 'api_key', 'code'}
    
    def _redact(obj):
        if isinstance(obj, dict):
            return {
                k: '[REDACTED]' if k.lower() in sensitive_keys else _redact(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_redact(item) for item in obj]
        return obj
    
    return _redact(data)
```

- [ ] Create `audit.py` module
- [ ] Add `audit_log()` function
- [ ] Add `redact_sensitive()` helper
- [ ] Ensure audit logging never raises

**Test:** Audit logs created correctly, sensitive data redacted

---

### Step 6.3: Add Audit Logging to Key Endpoints

**File:** `apps/backend/main.py`

Add audit logging to:

```python
from audit import audit_log, redact_sensitive

# Auth endpoints
@app.post("/auth/start")
async def auth_start(...):
    # ... existing code ...
    await audit_log(
        session=session,
        action="auth.login_start",
        details={"email": email},
        request=request,
    )

# Row endpoints
@app.post("/rows")
async def create_row(...):
    # ... existing code ...
    await audit_log(
        session=session,
        action="row.create",
        user_id=auth_session.user_id,
        resource_type="row",
        resource_id=str(row.id),
        details={"title": row.title},
        request=request,
    )

# Clickout endpoint
@app.get("/api/out")
async def clickout_redirect(...):
    # ... existing code ...
    await audit_log(
        session=session,
        action="clickout.redirect",
        user_id=user_id,
        resource_type="clickout",
        resource_id=str(event.id),
        details={
            "canonical_url": url,
            "merchant_domain": merchant_domain,
            "handler_name": handler_name,
        },
        request=request,
    )
```

- [ ] Add audit logging to `/auth/start`
- [ ] Add audit logging to `/auth/verify`
- [ ] Add audit logging to `/auth/logout`
- [ ] Add audit logging to `POST /rows`
- [ ] Add audit logging to `PATCH /rows/:id`
- [ ] Add audit logging to `DELETE /rows/:id`
- [ ] Add audit logging to `/api/out`
- [ ] Add audit logging to search endpoints

**Test:** All actions create audit log entries

---

### Step 6.4: Add Admin Role Check

**File:** `apps/backend/models.py`

```python
class User(SQLModel, table=True):
    # ... existing fields ...
    is_admin: bool = Field(default=False)
```

**File:** `apps/backend/main.py`

```python
async def require_admin(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Dependency that requires admin role."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await session.get(User, auth_session.user_id)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user

# Use in admin endpoints:
@app.get("/admin/clickouts")
async def list_clickouts(
    admin: User = Depends(require_admin),
    ...
):
    await audit_log(action="admin.access", user_id=admin.id, ...)
    # ... existing code ...
```

- [ ] Add `is_admin` to User model
- [ ] Create Alembic migration
- [ ] Add `require_admin` dependency
- [ ] Apply to all `/admin/*` endpoints

**Test:** Non-admin users get 403 on admin endpoints

---

### Step 6.5: Add Rate Limiting

**File:** `apps/backend/main.py`

Use `slowapi` or implement simple in-memory rate limiting:

```python
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

# Simple in-memory rate limiter (use Redis in production)
rate_limit_store: Dict[str, List[datetime]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = {
    "search": 30,      # 30 searches per minute
    "clickout": 60,    # 60 clicks per minute
    "auth_start": 5,   # 5 login attempts per minute
}

def check_rate_limit(key: str, limit_type: str) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    
    # Clean old entries
    rate_limit_store[key] = [
        t for t in rate_limit_store[key] if t > window_start
    ]
    
    max_requests = RATE_LIMIT_MAX.get(limit_type, 100)
    if len(rate_limit_store[key]) >= max_requests:
        return False
    
    rate_limit_store[key].append(now)
    return True

# Usage in endpoint:
@app.post("/rows/{row_id}/search")
async def search_row_listings(...):
    rate_key = f"search:{auth_session.user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    # ... existing code ...
```

- [ ] Implement rate limiting utility
- [ ] Apply to search endpoints
- [ ] Apply to clickout endpoint
- [ ] Apply to auth endpoints
- [ ] Return 429 with `Retry-After` header

**Test:** Rapid requests get 429 after threshold

---

### Step 6.6: Add Global Error Handler

**File:** `apps/backend/main.py`

```python
from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    
    - Logs full traceback
    - Returns safe error message to client
    - Creates audit log entry
    """
    error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{id(exc)}"
    
    # Log full error (server-side)
    print(f"[ERROR {error_id}] Unhandled exception:")
    traceback.print_exc()
    
    # Audit log (best effort)
    try:
        async with get_session() as session:
            await audit_log(
                session=session,
                action="error.unhandled",
                details={
                    "error_id": error_id,
                    "error_type": type(exc).__name__,
                    "path": str(request.url.path),
                    "method": request.method,
                },
                success=False,
                error_message=str(exc)[:500],
                request=request,
            )
    except:
        pass  # Don't let audit logging fail the error handler
    
    # Safe response to client
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Please try again.",
        }
    )
```

- [ ] Add global exception handler
- [ ] Include error_id for support correlation
- [ ] Log full traceback server-side
- [ ] Return safe message to client

**Test:** Unhandled exceptions return 500 with error_id

---

### Step 6.7: Add Health Check with Dependencies

**File:** `apps/backend/main.py`

```python
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "version": "0.1.0"}

@app.get("/health/ready")
async def readiness_check(session: AsyncSession = Depends(get_session)):
    """
    Readiness check - verifies all dependencies are available.
    
    Returns 503 if any dependency is unavailable.
    """
    checks = {}
    
    # Database check
    try:
        await session.exec(select(1))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"
    
    # Check if any critical dependency failed
    all_ok = all(v == "ok" for v in checks.values())
    
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
```

- [ ] Add `/health/ready` endpoint
- [ ] Check database connectivity
- [ ] Return 503 if degraded

**Test:** `/health/ready` returns correct status

---

### Step 6.8: Add Admin Audit Log Viewer

**File:** `apps/backend/main.py`

```python
@app.get("/admin/audit")
async def list_audit_logs(
    limit: int = 100,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    since: Optional[datetime] = None,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List audit logs (admin only)."""
    query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if since:
        query = query.where(AuditLog.timestamp >= since)
    
    result = await session.exec(query)
    return result.all()
```

- [ ] Add `/admin/audit` endpoint
- [ ] Support filtering by action, user, time
- [ ] Require admin role

**Test:** Admin can query audit logs

---

### Step 6.9: Add FTC Disclosure Compliance

**File:** `apps/frontend/app/components/RowsPane.tsx` (or Board)

Ensure disclosure is prominent:

```tsx
<div className="text-xs text-gray-500 mb-3 p-2 bg-gray-100 rounded">
  <strong>Disclosure:</strong> We may earn a commission from qualifying purchases. 
  This does not affect our recommendations or the prices you pay.
  <a href="/disclosure" className="ml-1 text-blue-500 underline">Learn more</a>
</div>
```

**New File:** `apps/frontend/app/disclosure/page.tsx`

```tsx
export default function DisclosurePage() {
  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4">Affiliate Disclosure</h1>
      
      <p className="mb-4">
        BuyAnything.ai participates in affiliate marketing programs. When you 
        click on links to products and make a purchase, we may earn a commission 
        from the retailer at no additional cost to you.
      </p>
      
      <h2 className="text-xl font-semibold mb-2">How It Works</h2>
      <p className="mb-4">
        When you search for products through our platform, we display results 
        from various retailers. If you click through to a retailer and make a 
        purchase, that retailer may pay us a referral fee.
      </p>
      
      <h2 className="text-xl font-semibold mb-2">Our Commitment</h2>
      <ul className="list-disc pl-6 mb-4">
        <li>Our product rankings are not influenced by affiliate relationships</li>
        <li>We disclose our affiliate relationships transparently</li>
        <li>You pay the same price whether you use our links or not</li>
      </ul>
      
      <p className="text-sm text-gray-500">
        Last updated: January 2026
      </p>
    </div>
  );
}
```

- [ ] Add prominent disclosure on main page
- [ ] Create `/disclosure` page with full details
- [ ] Ensure disclosure is visible before any product links

**Test:** Disclosure visible on page load

---

### Step 6.10: Data Retention Policy

**New File:** `apps/backend/retention.py`

```python
"""
Data retention utilities.

Run periodically (e.g., daily cron) to clean up old data.
"""

from datetime import datetime, timedelta
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import AuditLog, ClickoutEvent

# Retention periods
AUDIT_LOG_RETENTION_DAYS = 365  # Keep audit logs for 1 year
CLICKOUT_RETENTION_DAYS = 90   # Keep clickouts for 90 days (affiliate reconciliation)


async def cleanup_old_audit_logs(session: AsyncSession):
    """Delete audit logs older than retention period."""
    cutoff = datetime.utcnow() - timedelta(days=AUDIT_LOG_RETENTION_DAYS)
    # Note: In production, archive before delete
    await session.exec(
        select(AuditLog).where(AuditLog.timestamp < cutoff)
    )
    # Actually delete (careful!)
    # For now, just log what would be deleted
    print(f"[RETENTION] Would delete audit logs before {cutoff}")


async def cleanup_old_clickouts(session: AsyncSession):
    """Delete clickout events older than retention period."""
    cutoff = datetime.utcnow() - timedelta(days=CLICKOUT_RETENTION_DAYS)
    print(f"[RETENTION] Would delete clickouts before {cutoff}")
```

- [ ] Create retention policy module
- [ ] Document retention periods
- [ ] Create cleanup job (or document manual process)

---

## Acceptance Criteria

- [ ] All significant actions create audit log entries
- [ ] Audit logs include user, IP, timestamp, action, details
- [ ] Admin endpoints require `is_admin` role
- [ ] Rate limiting prevents abuse
- [ ] Unhandled errors return safe messages with error_id
- [ ] `/health/ready` checks all dependencies
- [ ] FTC disclosure prominently displayed
- [ ] Disclosure page explains affiliate relationships
- [ ] Data retention policy documented

---

## Audit Checklist (Pre-Launch)

Before handling real affiliate revenue:

- [ ] All clickouts logged in `clickout_event` table
- [ ] Affiliate handler names recorded for each click
- [ ] Admin can query clickouts by date, merchant, handler
- [ ] Audit logs capture all row CRUD operations
- [ ] Rate limiting prevents click fraud
- [ ] Error handling doesn't leak internal details
- [ ] Disclosure complies with FTC guidelines
- [ ] Data retention policy reviewed by legal (if applicable)

---

## Files Changed

| File | Action |
|------|--------|
| `apps/backend/models.py` | Add `AuditLog`, `User.is_admin` |
| `apps/backend/audit.py` | **New** — Audit logging utilities |
| `apps/backend/retention.py` | **New** — Data retention utilities |
| `apps/backend/main.py` | Add audit logging, rate limiting, error handling |
| `apps/frontend/app/components/RowsPane.tsx` | Add disclosure |
| `apps/frontend/app/disclosure/page.tsx` | **New** — Disclosure page |
| `alembic/versions/` | Migrations for AuditLog, User.is_admin |
