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
async def test_anonymous_search_without_guest_user_auto_creates_guest(
    client: AsyncClient, session: AsyncSession
):
    """Without a guest user in DB, anonymous search should auto-create the guest user."""
    response = await client.post(
        "/rows/999/search",
        json={"query": "test"},
        # NO authorization header, NO guest user in DB — guest auto-created
    )
    # Should not be 401 (guest auto-created); 404 for non-existent row is expected
    assert response.status_code != 401


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


@pytest.mark.asyncio
async def test_anonymous_search_stream_cannot_access_other_users_rows(
    client: AsyncClient, session: AsyncSession, guest_user: User, test_user: User
):
    """Regression: Anonymous stream search should not access other users' rows."""
    other_row = Row(
        user_id=test_user.id,
        title="Private streaming row",
        status="sourcing",
    )
    session.add(other_row)
    await session.commit()
    await session.refresh(other_row)

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
                f"/rows/{other_row.id}/search/stream",
                json={"query": "test"},
                # NO authorization — falls back to guest user
            )

    assert response.status_code == 404, (
        f"Guest user should not access other users' rows via stream, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_chat_update_row_with_bid_reset(
    client: AsyncClient, session: AsyncSession, auth_user_and_token
):
    """Regression: chat.py _update_row with reset_bids=True must not crash with 'name Bid is not defined'."""
    user, token = auth_user_and_token

    row = Row(user_id=user.id, title="Test row for bid reset", status="sourcing")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create a bid on this row
    from models import Bid
    bid = Bid(
        row_id=row.id,
        price=50.0,
        total_cost=55.0,
        item_title="Test Product",
        item_url="https://example.com/product",
        is_liked=False,
        is_selected=False,
    )
    session.add(bid)
    await session.commit()

    # Directly test _update_row with reset_bids=True
    from routes.chat import _update_row
    updated = await _update_row(
        session, row, title="Updated title", reset_bids=True
    )

    assert updated.title == "Updated title"

    # Verify the unloved bid was deleted
    from sqlmodel import select as sql_select
    remaining = await session.exec(
        sql_select(Bid).where(Bid.row_id == row.id)
    )
    assert len(remaining.all()) == 0, "Unloved bid should be deleted after reset"


@pytest.mark.asyncio
async def test_chat_update_row_preserves_liked_bids(
    client: AsyncClient, session: AsyncSession, auth_user_and_token
):
    """Regression: reset_bids should preserve liked/selected bids."""
    user, token = auth_user_and_token

    row = Row(user_id=user.id, title="Liked bids test", status="sourcing")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    from models import Bid
    # Liked bid — should survive reset
    liked_bid = Bid(
        row_id=row.id,
        price=100.0,
        total_cost=110.0,
        item_title="Liked Product",
        item_url="https://example.com/liked",
        is_liked=True,
        is_selected=False,
    )
    # Unloved bid — should be deleted
    unloved_bid = Bid(
        row_id=row.id,
        price=200.0,
        total_cost=220.0,
        item_title="Unloved Product",
        item_url="https://example.com/unloved",
        is_liked=False,
        is_selected=False,
    )
    session.add_all([liked_bid, unloved_bid])
    await session.commit()

    from routes.chat import _update_row
    await _update_row(session, row, reset_bids=True)

    from sqlmodel import select as sql_select
    remaining = await session.exec(sql_select(Bid).where(Bid.row_id == row.id))
    remaining_bids = remaining.all()
    assert len(remaining_bids) == 1, f"Only liked bid should survive, got {len(remaining_bids)}"
    assert remaining_bids[0].is_liked is True
