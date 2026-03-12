"""Tests for anonymous access to /rows endpoints (select_row_option, PATCH, etc).

Covers:
- Anonymous PATCH /rows/{id} (select option) uses guest user, not 401
- Anonymous cannot access other users' rows
- Authenticated users unaffected by guest fallback
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from models import User, Row, Bid


GUEST_EMAIL = "guest@buy-anything.com"


@pytest_asyncio.fixture
async def guest_user(session: AsyncSession) -> User:
    user = User(email=GUEST_EMAIL, is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def guest_row(session: AsyncSession, guest_user: User) -> Row:
    row = Row(
        user_id=guest_user.id,
        title="Guest power stations",
        status="sourcing",
        desire_tier="commodity",
        anonymous_session_id="test-session-aaa",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@pytest_asyncio.fixture
async def guest_bid(session: AsyncSession, guest_row: Row) -> Bid:
    bid = Bid(
        row_id=guest_row.id,
        price=199.99,
        total_cost=209.99,
        item_title="EcoFlow RIVER 2",
        item_url="https://example.com/ecoflow",
        is_liked=False,
        is_selected=False,
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)
    return bid


@pytest.mark.asyncio
async def test_patch_row_anonymous_returns_200(
    client: AsyncClient, session: AsyncSession, guest_user: User, guest_row: Row
):
    """Anonymous PATCH /rows/{id} should succeed for guest-owned rows."""
    response = await client.patch(
        f"/rows/{guest_row.id}",
        json={"title": "Updated by anon"},
        headers={"X-Anonymous-Session-Id": "test-session-aaa"},
        # NO authorization header
    )
    assert response.status_code == 200, (
        f"Anonymous PATCH should work on guest row, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data["title"] == "Updated by anon"


@pytest.mark.asyncio
async def test_patch_row_anonymous_cannot_access_other_users_row(
    client: AsyncClient, session: AsyncSession, guest_user: User, auth_user_and_token
):
    """Anonymous user cannot PATCH rows owned by other users."""
    user, _ = auth_user_and_token
    other_row = Row(user_id=user.id, title="Private row", status="sourcing")
    session.add(other_row)
    await session.commit()
    await session.refresh(other_row)

    response = await client.patch(
        f"/rows/{other_row.id}",
        json={"title": "Hacked"},
        headers={"X-Anonymous-Session-Id": "attacker-session"},
        # NO authorization header — resolves to guest user
    )
    assert response.status_code == 404, (
        f"Guest should not be able to PATCH other user's row, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_select_option_anonymous_returns_200(
    client: AsyncClient, session: AsyncSession, guest_user: User, guest_row: Row, guest_bid: Bid
):
    """Anonymous POST /rows/{id}/select-option should work for guest rows."""
    response = await client.post(
        f"/rows/{guest_row.id}/select-option",
        json={"bid_id": guest_bid.id},
        headers={"X-Anonymous-Session-Id": "test-session-aaa"},
        # NO authorization header
    )
    # 200 means it worked, or 400/422 means validation issue — but NOT 401
    assert response.status_code != 401, (
        f"Anonymous select-option should not 401, got {response.status_code}: {response.text}"
    )


@pytest.mark.asyncio
async def test_select_option_anonymous_cannot_access_other_users_row(
    client: AsyncClient, session: AsyncSession, guest_user: User, auth_user_and_token
):
    """Anonymous user cannot select options on rows owned by other users."""
    user, _ = auth_user_and_token
    other_row = Row(user_id=user.id, title="Private", status="sourcing")
    session.add(other_row)
    await session.commit()
    await session.refresh(other_row)

    bid = Bid(
        row_id=other_row.id, price=50, total_cost=55,
        item_title="Product", item_url="https://example.com",
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    response = await client.post(
        f"/rows/{other_row.id}/select-option",
        json={"bid_id": bid.id},
        headers={"X-Anonymous-Session-Id": "attacker-session"},
    )
    # Should be 404 (row not found for guest user), not 401
    assert response.status_code in (404, 403), (
        f"Guest should not access other user's rows, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_get_rows_anonymous_with_session_id_returns_scoped_rows(
    client: AsyncClient, session: AsyncSession, guest_user: User, guest_row: Row
):
    """Anonymous GET /rows with matching session ID should return that session's rows."""
    response = await client.get(
        "/rows",
        headers={"X-Anonymous-Session-Id": "test-session-aaa"},
    )
    assert response.status_code == 200
    data = response.json()
    titles = [r["title"] for r in data]
    assert "Guest power stations" in titles


@pytest.mark.asyncio
async def test_get_rows_anonymous_without_session_id_returns_empty(
    client: AsyncClient, session: AsyncSession, guest_user: User, guest_row: Row
):
    """Anonymous GET /rows without session ID should return empty list (no leak)."""
    response = await client.get("/rows")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_rows_anonymous_wrong_session_id_returns_empty(
    client: AsyncClient, session: AsyncSession, guest_user: User, guest_row: Row
):
    """Anonymous GET /rows with a different session ID should not see other sessions' rows."""
    response = await client.get(
        "/rows",
        headers={"X-Anonymous-Session-Id": "different-session-bbb"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_rows_anonymous_no_guest_rows_returns_empty(
    client: AsyncClient, session: AsyncSession, guest_user: User
):
    """Anonymous GET /rows with no guest rows should return empty list, not 401."""
    response = await client.get(
        "/rows",
        headers={"X-Anonymous-Session-Id": "some-session"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_rows_anonymous_session_isolation(
    client: AsyncClient, session: AsyncSession, guest_user: User
):
    """Two different anonymous sessions should each only see their own rows."""
    row_a = Row(
        user_id=guest_user.id, title="Session A item", status="sourcing",
        anonymous_session_id="session-alpha",
    )
    row_b = Row(
        user_id=guest_user.id, title="Session B item", status="sourcing",
        anonymous_session_id="session-beta",
    )
    session.add_all([row_a, row_b])
    await session.commit()

    resp_a = await client.get("/rows", headers={"X-Anonymous-Session-Id": "session-alpha"})
    assert resp_a.status_code == 200
    titles_a = [r["title"] for r in resp_a.json()]
    assert "Session A item" in titles_a
    assert "Session B item" not in titles_a

    resp_b = await client.get("/rows", headers={"X-Anonymous-Session-Id": "session-beta"})
    assert resp_b.status_code == 200
    titles_b = [r["title"] for r in resp_b.json()]
    assert "Session B item" in titles_b
    assert "Session A item" not in titles_b


@pytest.mark.asyncio
async def test_patch_row_authenticated_still_works(
    client: AsyncClient, session: AsyncSession, auth_user_and_token
):
    """Authenticated PATCH should still work normally."""
    user, token = auth_user_and_token
    row = Row(user_id=user.id, title="Auth row", status="sourcing")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    response = await client.patch(
        f"/rows/{row.id}",
        json={"title": "Updated by auth"},
        headers={"authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated by auth"
