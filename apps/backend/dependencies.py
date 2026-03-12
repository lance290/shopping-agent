"""
Centralized FastAPI dependencies to eliminate duplicated auth patterns.

This module consolidates authentication and authorization logic.
"""

from typing import Optional, Tuple
from fastapi import Header, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from database import get_session
from models import AuthSession, User, hash_token


async def get_current_session(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> Optional[AuthSession]:
    """
    Extract and validate session from Authorization header.

    Returns None if authentication fails or if the session is expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]

    # Try legacy session token lookup
    token_hash = hash_token(token)

    result = await session.exec(
        select(AuthSession)
        .where(
            AuthSession.session_token_hash == token_hash,
            AuthSession.revoked_at == None,
            (AuthSession.expires_at == None) | (AuthSession.expires_at > datetime.utcnow())
        )
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


GUEST_EMAIL = "guest@buy-anything.com"


async def resolve_user_id(
    authorization: Optional[str],
    session: AsyncSession,
) -> int:
    """
    Resolve user_id from auth header, falling back to guest user for anonymous requests.

    Use this when an endpoint should work for both authenticated and anonymous users.
    """
    user_id, _ = await resolve_user_id_and_guest_flag(authorization, session)
    return user_id


async def resolve_user_id_and_guest_flag(
    authorization: Optional[str],
    session: AsyncSession,
) -> Tuple[int, bool]:
    """
    Like resolve_user_id but also returns whether the user is the guest.

    Returns (user_id, is_guest).
    """
    auth_session = await get_current_session(authorization, session)
    if auth_session:
        return auth_session.user_id, False

    guest_result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
    guest_user = guest_result.first()
    if not guest_user:
        guest_user = User(email=GUEST_EMAIL)
        session.add(guest_user)
        await session.commit()
        await session.refresh(guest_user)
    return guest_user.id, True


async def resolve_accessible_row(
    session: AsyncSession,
    row_id: int,
    user_id: int,
    is_guest: bool,
    anonymous_session_id: Optional[str],
) -> "Row":
    """Single source of truth for row ownership resolution.

    Guest users are scoped by anonymous_session_id.
    Authenticated users are scoped by user_id.
    Raises 404 if the row is not found or not accessible.
    """
    from models import Row

    clauses = [Row.id == row_id]
    if is_guest:
        if not anonymous_session_id:
            raise HTTPException(status_code=404, detail="Row not found")
        clauses.append(Row.anonymous_session_id == anonymous_session_id)
    else:
        clauses.append(Row.user_id == user_id)

    result = await session.exec(select(Row).where(*clauses))
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    return row


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
