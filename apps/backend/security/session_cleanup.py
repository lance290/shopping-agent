"""
Session cleanup job to remove expired sessions.

This background task runs periodically to clean up:
- Expired sessions
- Old revoked sessions
- Inactive verification codes

Run this as a cron job or background worker.
"""

import asyncio
from datetime import datetime, timedelta
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import AuthSession, AuthLoginCode


async def cleanup_expired_sessions(
    session: AsyncSession,
    retention_days: int = 30
) -> dict:
    """
    Clean up expired and old revoked sessions.

    Args:
        session: Database session
        retention_days: How many days to keep revoked sessions for audit trail

    Returns:
        Dictionary with cleanup statistics
    """
    now = datetime.utcnow()
    retention_cutoff = now - timedelta(days=retention_days)

    # Find expired sessions
    expired_result = await session.exec(
        select(AuthSession)
        .where(AuthSession.expires_at < now)
        .where(AuthSession.revoked_at == None)
    )
    expired_sessions = expired_result.all()

    # Revoke expired sessions
    expired_count = 0
    for auth_session in expired_sessions:
        auth_session.revoked_at = now
        session.add(auth_session)
        expired_count += 1

    # Delete old revoked sessions (beyond retention period)
    old_revoked_result = await session.exec(
        select(AuthSession)
        .where(AuthSession.revoked_at < retention_cutoff)
    )
    old_revoked_sessions = old_revoked_result.all()

    deleted_count = 0
    for auth_session in old_revoked_sessions:
        await session.delete(auth_session)
        deleted_count += 1

    await session.commit()

    return {
        "expired_sessions_revoked": expired_count,
        "old_sessions_deleted": deleted_count,
        "timestamp": now.isoformat()
    }


async def cleanup_old_login_codes(
    session: AsyncSession,
    max_age_hours: int = 24
) -> dict:
    """
    Clean up old login verification codes.

    Args:
        session: Database session
        max_age_hours: Maximum age for inactive codes

    Returns:
        Dictionary with cleanup statistics
    """
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

    # Delete old inactive codes
    old_codes_result = await session.exec(
        select(AuthLoginCode)
        .where(AuthLoginCode.created_at < cutoff)
        .where(AuthLoginCode.is_active == False)
    )
    old_codes = old_codes_result.all()

    deleted_count = 0
    for code in old_codes:
        await session.delete(code)
        deleted_count += 1

    await session.commit()

    return {
        "old_codes_deleted": deleted_count,
        "timestamp": datetime.utcnow().isoformat()
    }


async def run_security_cleanup():
    """
    Run all security cleanup tasks.

    This is the main entry point for the cleanup job.
    """
    print("[SECURITY] Starting security cleanup job...")

    async for session in get_session():
        try:
            # Clean up sessions
            session_stats = await cleanup_expired_sessions(session)
            print(f"[SECURITY] Session cleanup: {session_stats}")

            # Clean up login codes
            code_stats = await cleanup_old_login_codes(session)
            print(f"[SECURITY] Login code cleanup: {code_stats}")
        finally:
            # Session is managed by the async generator, no need to close
            pass

    print("[SECURITY] Security cleanup job completed")


async def run_cleanup_loop(interval_hours: int = 1):
    """
    Run cleanup job in a loop with specified interval.

    Args:
        interval_hours: Hours between cleanup runs
    """
    while True:
        try:
            await run_security_cleanup()
        except Exception as e:
            print(f"[SECURITY] Cleanup job error: {e}")

        # Wait for next run
        await asyncio.sleep(interval_hours * 3600)


if __name__ == "__main__":
    # Run cleanup immediately when executed directly
    asyncio.run(run_security_cleanup())
