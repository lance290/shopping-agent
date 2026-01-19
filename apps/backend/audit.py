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
            try:
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent", "")[:500]  # Truncate
            except Exception:
                pass
        
        # Redact sensitive info from details if present
        safe_details = None
        if details:
            safe_details = json.dumps(redact_sensitive(details))

        log_entry = AuditLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=safe_details,
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
    sensitive_keys = {'password', 'token', 'secret', 'api_key', 'code', 'session_token'}
    
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
