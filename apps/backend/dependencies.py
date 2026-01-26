"""
Centralized FastAPI dependencies to eliminate duplicated auth patterns.

This module consolidates authentication and authorization logic that was
previously scattered across main.py with 18+ HTTPException(401) duplications.
"""

from typing import Optional
from fastapi import Header, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from database import get_session
from models import AuthSession, User, hash_token
from clerk_auth import get_clerk_user_id


async def get_current_session(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> Optional[AuthSession]:
    """
    Extract and validate session from Authorization header.

    Supports both legacy session tokens and Clerk JWTs.
    Returns None if authentication fails.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]

    # First, try Clerk JWT verification
    clerk_user_id = get_clerk_user_id(token)
    if clerk_user_id:
        # Find or create user by Clerk ID
        result = await session.exec(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        user = result.first()

        if not user:
            # Create new user for this Clerk ID
            user = User(clerk_user_id=clerk_user_id, email=None)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"[CLERK] Created new user {user.id} for Clerk ID {clerk_user_id}")

        # Return a synthetic AuthSession for compatibility
        fake_session = AuthSession(
            user_id=user.id,
            session_token_hash="clerk_jwt",
            email=user.email,
        )
        fake_session.id = -1  # Marker for Clerk session
        return fake_session

    # Fallback: try legacy session token lookup
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
