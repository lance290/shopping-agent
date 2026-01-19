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
    # Note: In production, archive before delete would be better
    # For now, just logging the intent to prevent accidental data loss during dev
    print(f"[RETENTION] Checking for audit logs older than {cutoff}...")
    
    # Example logic (commented out for safety until production cron is set up)
    # statement = select(AuditLog).where(AuditLog.timestamp < cutoff)
    # results = await session.exec(statement)
    # to_delete = results.all()
    # for item in to_delete:
    #     await session.delete(item)
    # await session.commit()


async def cleanup_old_clickouts(session: AsyncSession):
    """Delete clickout events older than retention period."""
    cutoff = datetime.utcnow() - timedelta(days=CLICKOUT_RETENTION_DAYS)
    print(f"[RETENTION] Checking for clickouts older than {cutoff}...")
    
    # Example logic
    # statement = select(ClickoutEvent).where(ClickoutEvent.created_at < cutoff)
    # results = await session.exec(statement)
    # to_delete = results.all()
    # for item in to_delete:
    #     await session.delete(item)
    # await session.commit()
