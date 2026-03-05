"""Tests for resolve_user_id — anonymous/guest fallback used across rows, projects, chat.

Covers:
- Authenticated user returns correct user_id
- Anonymous request falls back to guest user
- Guest user auto-created if not in DB
- Guest user reused across multiple calls
"""

import pytest
import pytest_asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from dependencies import resolve_user_id, GUEST_EMAIL
from models import User, AuthSession, hash_token, generate_session_token


@pytest_asyncio.fixture
async def regular_user(session: AsyncSession) -> tuple:
    """Create an authenticated regular user with a session token."""
    user = User(email="regular@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()
    return user, token


class TestResolveUserId:

    @pytest.mark.asyncio
    async def test_authenticated_user_returns_their_id(self, session, regular_user):
        """With a valid Bearer token, resolve_user_id returns the authenticated user's ID."""
        user, token = regular_user
        user_id = await resolve_user_id(f"Bearer {token}", session)
        assert user_id == user.id

    @pytest.mark.asyncio
    async def test_no_auth_header_returns_guest_id(self, session):
        """With no authorization header, should return the guest user's ID."""
        user_id = await resolve_user_id(None, session)

        # Verify it's the guest user
        result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
        guest = result.first()
        assert guest is not None
        assert user_id == guest.id

    @pytest.mark.asyncio
    async def test_empty_auth_header_returns_guest_id(self, session):
        """With an empty authorization header, should return the guest user's ID."""
        user_id = await resolve_user_id("", session)

        result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
        guest = result.first()
        assert guest is not None
        assert user_id == guest.id

    @pytest.mark.asyncio
    async def test_invalid_token_returns_guest_id(self, session):
        """With an invalid Bearer token, should fall back to guest user."""
        user_id = await resolve_user_id("Bearer totally-invalid-token", session)

        result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
        guest = result.first()
        assert guest is not None
        assert user_id == guest.id

    @pytest.mark.asyncio
    async def test_guest_user_auto_created_when_missing(self, session):
        """If guest user doesn't exist in DB, it should be auto-created."""
        # Verify no guest user exists
        result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
        assert result.first() is None

        user_id = await resolve_user_id(None, session)

        # Now guest should exist
        result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
        guest = result.first()
        assert guest is not None
        assert guest.email == GUEST_EMAIL
        assert user_id == guest.id

    @pytest.mark.asyncio
    async def test_guest_user_reused_across_calls(self, session):
        """Multiple anonymous calls should reuse the same guest user."""
        id1 = await resolve_user_id(None, session)
        id2 = await resolve_user_id(None, session)
        id3 = await resolve_user_id("Bearer bad-token", session)

        assert id1 == id2 == id3

        # Only one guest user should exist
        result = await session.exec(select(User).where(User.email == GUEST_EMAIL))
        guests = result.all()
        assert len(guests) == 1

    @pytest.mark.asyncio
    async def test_existing_guest_user_is_found(self, session):
        """If guest user already exists, it should be found — not duplicated."""
        existing_guest = User(email=GUEST_EMAIL, is_admin=False)
        session.add(existing_guest)
        await session.commit()
        await session.refresh(existing_guest)

        user_id = await resolve_user_id(None, session)
        assert user_id == existing_guest.id

    @pytest.mark.asyncio
    async def test_auth_user_not_affected_by_guest(self, session, regular_user):
        """Authenticated requests should never return guest ID even if guest exists."""
        # Create guest user first
        guest = User(email=GUEST_EMAIL, is_admin=False)
        session.add(guest)
        await session.commit()
        await session.refresh(guest)

        user, token = regular_user
        user_id = await resolve_user_id(f"Bearer {token}", session)
        assert user_id == user.id
        assert user_id != guest.id
