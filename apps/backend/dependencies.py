"""
Centralized FastAPI dependencies to eliminate duplicated auth patterns.

This module consolidates authentication and authorization logic.
"""

from typing import Optional
from fastapi import Header, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from database import get_session
from models import AuthSession, User, hash_token


async def get_current_session(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> Optional[AuthSession]:
    """
    Extract and validate session from Authorization header.

    Returns None if authentication fails.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]

    # Try legacy session token lookup
    token_hash = hash_token(token)

    result = await session.exec(
        select(AuthSession)
        .where(AuthSession.session_token_hash == token_hash, AuthSession.revoked_at == None)
    )
    return result.first()


async def require_auth(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> AuthSession:
    """
    Dependency that requires authentication.

    Raises HTTPException(401) if not authenticated.
    Use this instead of manually checking get_current_session().
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return auth_session


async def require_admin(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Dependency that requires admin role.

    Raises HTTPException(401) if not authenticated.
    Raises HTTPException(403) if not admin.
    """
    from audit import audit_log

    auth_session = await require_auth(authorization, session)

    user = await session.get(User, auth_session.user_id)
    if not user or not user.is_admin:
        # Log unauthorized admin access attempt
        await audit_log(
            session=session,
            action="admin.access_denied",
            user_id=auth_session.user_id,
            details={"reason": "Not an admin"},
        )
        raise HTTPException(status_code=403, detail="Admin access required")

    return user
