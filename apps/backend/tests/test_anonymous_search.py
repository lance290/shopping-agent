"""Regression tests for anonymous (guest) user search access.

Bug: Anonymous users could trigger chat (which creates rows under the guest user)
but the internal search/stream endpoint required auth, returning 401. This caused
the "Sourcing offers..." spinner to hang forever with no results.

Fix: Both search_row_listings and search_row_listings_stream fall back to the
guest user (guest@buy-anything.com) when no auth session is present.
"""
import pytest
import pytest_asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel.ext.asyncio.session import AsyncSession
from httpx import AsyncClient

from models import Row, User


GUEST_EMAIL = "guest@buy-anything.com"


@pytest_asyncio.fixture
async def guest_user(session: AsyncSession) -> User:
    """Create the guest user that anonymous requests fall back to."""
    user = User(email=GUEST_EMAIL, is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def guest_row(session: AsyncSession, guest_user: User) -> Row:
    """Create a row owned by the guest user (simulates anonymous chat creating a row)."""
    row = Row(
        user_id=guest_user.id,
        title="Roblox gift cards",
        status="sourcing",
        desire_tier="commodity",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@pytest.mark.asyncio
async def test_anonymous_search_returns_200(
    client: AsyncClient, session: AsyncSession, guest_user: User, guest_row: Row
):
    """Regression: POST /rows/{id}/search without auth should use guest user, not 401."""
    from sourcing import SearchResultWithStatus

    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(
                results=[], provider_statuses=[], all_providers_failed=False
            )
        )
        mock_repo.return_value.search_all_with_status = mock_search

        with patch("routes.rate_limit.check_rate_limit", return_value=True):
            response = await client.post(
                f"/rows/{guest_row.id}/search",
                json={"query": "Roblox gift cards"},
                # NO authorization header — anonymous request
            )

    assert response.status_code == 200, (
        f"Anonymous search should succeed via guest user, got {response.status_code}: {response.text}"
    )


@pytest.mark.asyncio
async def test_anonymous_search_stream_returns_200(
    client: AsyncClient, session: AsyncSession, guest_user: User, guest_row: Row
):
    """Regression: POST /rows/{id}/search/stream without auth should use guest user, not 401."""
    from sourcing import ProviderStatusSnapshot

    async def fake_streaming(*args, **kwargs):
        yield (
            "serpapi",
            [],
            ProviderStatusSnapshot(provider_id="serpapi", status="ok", result_count=0, latency_ms=100),
            0,
        )

    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_repo.return_value.search_streaming = fake_streaming

        with patch("routes.rate_limit.check_rate_limit", return_value=True):
            response = await client.post(
                f"/rows/{guest_row.id}/search/stream",
                json={"query": "Roblox gift cards"},
                # NO authorization header — anonymous request
            )

    assert response.status_code == 200, (
        f"Anonymous search/stream should succeed via guest user, got {response.status_code}: {response.text}"
    )


@pytest.mark.asyncio
async def test_anonymous_search_without_guest_user_returns_401(
    client: AsyncClient, session: AsyncSession
):
    """Without a guest user in DB, anonymous search should return 401."""
    response = await client.post(
        "/rows/999/search",
        json={"query": "test"},
        # NO authorization header, NO guest user in DB
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_anonymous_search_cannot_access_other_users_rows(
    client: AsyncClient, session: AsyncSession, guest_user: User, test_user: User
):
    """Anonymous search should only access rows owned by the guest user."""
    # Create a row owned by a different (non-guest) user
    other_row = Row(
        user_id=test_user.id,
        title="Private row",
        status="sourcing",
    )
    session.add(other_row)
    await session.commit()
    await session.refresh(other_row)

    from sourcing import SearchResultWithStatus

    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(
                results=[], provider_statuses=[], all_providers_failed=False
            )
        )
        mock_repo.return_value.search_all_with_status = mock_search

        with patch("routes.rate_limit.check_rate_limit", return_value=True):
            response = await client.post(
                f"/rows/{other_row.id}/search",
                json={"query": "test"},
                # NO authorization header — falls back to guest user
            )

    # Guest user cannot search rows owned by other users → 404
    assert response.status_code == 404, (
        f"Guest user should not access other users' rows, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_authenticated_user_search_still_works(
    client: AsyncClient, session: AsyncSession, auth_user_and_token
):
    """Ensure the guest-user fallback doesn't break authenticated search."""
    user, token = auth_user_and_token

    row = Row(user_id=user.id, title="Auth user row", status="sourcing")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    from sourcing import SearchResultWithStatus

    with patch("routes.rows_search.get_sourcing_repo") as mock_repo:
        mock_search = AsyncMock(
            return_value=SearchResultWithStatus(
                results=[], provider_statuses=[], all_providers_failed=False
            )
        )
        mock_repo.return_value.search_all_with_status = mock_search

        with patch("routes.rate_limit.check_rate_limit", return_value=True):
            response = await client.post(
                f"/rows/{row.id}/search",
                json={"query": "running shoes"},
                headers={"authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200, (
        f"Authenticated search should still work, got {response.status_code}: {response.text}"
    )
