"""
Data retention utilities.

Run periodically (e.g., daily cron) to clean up old data.
"""

from datetime import datetime, timedelta
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import AuditLog, ClickoutEvent, BugReport
from pathlib import Path
import os

# Retention periods
AUDIT_LOG_RETENTION_DAYS = 365  # Keep audit logs for 1 year
CLICKOUT_RETENTION_DAYS = 90   # Keep clickouts for 90 days (affiliate reconciliation)
BUG_REPORT_RETENTION_DAYS = int(os.getenv("BUG_REPORT_RETENTION_DAYS", "90")) # Default 90 days

# Check for /data volume (common in Railway) or use env var
if os.path.exists("/data"):
    DEFAULT_UPLOAD_PATH = "/data/uploads/bugs"
else:
    DEFAULT_UPLOAD_PATH = "uploads/bugs"

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", DEFAULT_UPLOAD_PATH))

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

async def cleanup_old_bug_reports(session: AsyncSession):
    """
    Deletes bug reports older than the retention period and removes their attachments.
    """
    cutoff = datetime.utcnow() - timedelta(days=BUG_REPORT_RETENTION_DAYS)
    print(f"[RETENTION] Cleaning up bug reports created before {cutoff.isoformat()}")

    # Find old reports
    statement = select(BugReport).where(BugReport.created_at < cutoff)
    result = await session.exec(statement)
    old_reports = result.all()
    
    count = 0
    for report in old_reports:
        # Delete attachments
        if report.attachments:
            try:
                import json
                paths = json.loads(report.attachments)
                for rel_path in paths:
                    # rel_path is like "/uploads/bugs/filename"
                    # We need to match it to our UPLOAD_DIR
                    filename = os.path.basename(rel_path)
                    file_path = UPLOAD_DIR / filename
                    if file_path.exists():
                        file_path.unlink()
                        print(f"[RETENTION] Deleted file: {file_path}")
            except Exception as e:
                print(f"[RETENTION] Error cleaning files for report {report.id}: {e}")

        # Delete from DB
        await session.delete(report)
        count += 1
    
    if count > 0:
        await session.commit()
        print(f"[RETENTION] Deleted {count} expired bug reports.")
    else:
        print("[RETENTION] No expired bug reports found.")

