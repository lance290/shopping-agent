"""Tests for centralized authentication dependencies."""

import pytest
from fastapi import HTTPException
from dependencies import get_current_session, require_auth, require_admin
from models import User, AuthSession, hash_token, generate_session_token


@pytest.mark.asyncio
async def test_get_current_session_no_header(session):
    """Test get_current_session with no authorization header."""
    result = await get_current_session(authorization=None, session=session)
    assert result is None


@pytest.mark.asyncio
async def test_get_current_session_invalid_token(session):
    """Test get_current_session with invalid token."""
    result = await get_current_session(
        authorization="Bearer invalid_token",
        session=session
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_current_session_valid_token(session, test_user):
    """Test get_current_session with valid session token."""
    # Create a session token
    token = generate_session_token()
    auth_session = AuthSession(
        email=test_user.email,
        user_id=test_user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()
    await session.refresh(auth_session)

    # Verify
    result = await get_current_session(
        authorization=f"Bearer {token}",
        session=session
    )
    assert result is not None
    assert result.user_id == test_user.id


@pytest.mark.asyncio
async def test_require_auth_success(session, test_user):
    """Test require_auth with valid authentication."""
    # Create a session token
    token = generate_session_token()
    auth_session = AuthSession(
        email=test_user.email,
        user_id=test_user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()

    # Verify
    result = await require_auth(
        authorization=f"Bearer {token}",
        session=session
    )
    assert result.user_id == test_user.id


@pytest.mark.asyncio
async def test_require_auth_failure(session):
    """Test require_auth raises HTTPException when not authenticated."""
    with pytest.raises(HTTPException) as exc_info:
        await require_auth(authorization=None, session=session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_require_admin_success(session):
    """Test require_admin with admin user."""
    # Create admin user
    admin = User(email="admin@test.com", is_admin=True)
    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    # Create session
    token = generate_session_token()
    auth_session = AuthSession(
        email=admin.email,
        user_id=admin.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()

    # Verify
    result = await require_admin(
        authorization=f"Bearer {token}",
        session=session
    )
    assert result.id == admin.id
    assert result.is_admin is True


@pytest.mark.asyncio
async def test_require_admin_non_admin_user(session, test_user):
    """Test require_admin raises HTTPException for non-admin user."""
    # Create session for non-admin user
    token = generate_session_token()
    auth_session = AuthSession(
        email=test_user.email,
        user_id=test_user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()

    # Verify
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(
            authorization=f"Bearer {token}",
            session=session
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


@pytest.mark.asyncio
async def test_require_admin_not_authenticated(session):
    """Test require_admin raises HTTPException when not authenticated."""
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(authorization=None, session=session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated"
