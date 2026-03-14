import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from models import User, Row, Bid, AuthSession, hash_token, generate_session_token


GUEST_EMAIL = "guest@buy-anything.com"


@pytest_asyncio.fixture
async def guest_user(session: AsyncSession) -> User:
    """The shared guest user used by anonymous browsing."""
    user = User(email=GUEST_EMAIL, is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def real_user(session: AsyncSession) -> User:
    """Create a real authenticated user (the one logging in)."""
    user = User(email="buyer@example.com", phone_number="+15551234567", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def real_user_token(session: AsyncSession, real_user: User) -> str:
    """Create a session token for the real user."""
    token = generate_session_token()
    auth_session = AuthSession(
        email=real_user.email,
        phone_number=real_user.phone_number,
        user_id=real_user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()
    return token


@pytest_asyncio.fixture
async def guest_rows(session: AsyncSession, guest_user: User) -> list[Row]:
    """Create multiple rows owned by the guest user."""
    rows = []
    for title in ["Standing desk", "Wireless earbuds", "Running shoes"]:
        row = Row(user_id=guest_user.id, title=title, status="sourcing")
        session.add(row)
        rows.append(row)
    await session.commit()
    for r in rows:
        await session.refresh(r)
    return rows


@pytest_asyncio.fixture
async def guest_row_with_bids(session: AsyncSession, guest_user: User) -> Row:
    """Create a guest row with bids — data that must survive claim."""
    row = Row(user_id=guest_user.id, title="Private jet charter", status="sourcing")
    session.add(row)
    await session.commit()
    await session.refresh(row)
    bid1 = Bid(row_id=row.id, price=50000.0, total_cost=55000.0,
               item_title="NetJets Citation X", item_url="https://netjets.com",
               is_selected=True, is_liked=True)
    bid2 = Bid(row_id=row.id, price=45000.0, total_cost=48000.0,
               item_title="VistaJet Global 7500", item_url="https://vistajet.com",
               is_selected=False, is_liked=False)
    session.add_all([bid1, bid2])
    await session.commit()
    return row


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_empty_row_ids(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str,
):
    """Claiming with empty row_ids list should succeed with 0 claimed."""
    response = await client.post(
        "/rows/claim",
        json={"row_ids": []},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["claimed"] == 0


@pytest.mark.asyncio
async def test_claim_nonexistent_row_ids(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str,
):
    """Claiming nonexistent row IDs should succeed with 0 claimed (no crash)."""
    response = await client.post(
        "/rows/claim",
        json={"row_ids": [999999, 888888]},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["claimed"] == 0


@pytest.mark.asyncio
async def test_claim_idempotent(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str, guest_rows: list[Row],
):
    """Calling claim twice with the same row IDs should be safe (idempotent)."""
    row_ids = [guest_rows[0].id]

    # First claim
    resp1 = await client.post(
        "/rows/claim",
        json={"row_ids": row_ids},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert resp1.json()["claimed"] == 1

    # Second claim — row already belongs to real_user, not guest → 0 claimed
    resp2 = await client.post(
        "/rows/claim",
        json={"row_ids": row_ids},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert resp2.json()["claimed"] == 0

    # Row still belongs to real_user
    await session.refresh(guest_rows[0])
    assert guest_rows[0].user_id == real_user.id


@pytest.mark.asyncio
async def test_claim_without_guest_user_in_db(
    client: AsyncClient, session: AsyncSession,
    real_user: User, real_user_token: str,
):
    """If guest user doesn't exist in DB, claim should not crash."""
    response = await client.post(
        "/rows/claim",
        json={"row_ids": [1, 2, 3]},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["claimed"] == 0


@pytest.mark.asyncio
async def test_claim_does_not_affect_archived_guest_rows(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str,
):
    """Archived guest rows should still be claimable (they're still guest-owned)."""
    row = Row(user_id=guest_user.id, title="Archived search", status="archived")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    response = await client.post(
        "/rows/claim",
        json={"row_ids": [row.id]},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["claimed"] == 1

    await session.refresh(row)
    assert row.user_id == real_user.id
    assert row.status == "archived"


# ---------------------------------------------------------------------------
# Integration: anonymous GET /rows before/after claim
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anonymous_get_rows_returns_empty(
    client: AsyncClient, session: AsyncSession, guest_user: User, guest_rows: list[Row],
):
    """GET /rows without auth should return empty list (not guest rows)."""
    response = await client.get("/rows")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_full_claim_flow_end_to_end(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str,
    guest_row_with_bids: Row,
):
    """
    Full end-to-end flow:
    1. Anonymous user has rows (not visible in GET /rows)
    2. User logs in and claims rows
    3. GET /rows returns claimed rows with bids preserved
    """
    row = guest_row_with_bids

    # Step 1: Anonymous GET /rows → empty
    anon_resp = await client.get("/rows")
    assert anon_resp.json() == []

    # Step 2: Authenticated GET /rows → empty (hasn't claimed yet)
    auth_resp = await client.get(
        "/rows",
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert len(auth_resp.json()) == 0

    # Step 3: Claim
    claim_resp = await client.post(
        "/rows/claim",
        json={"row_ids": [row.id]},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert claim_resp.json()["claimed"] == 1

    # Step 4: Authenticated GET /rows → row appears with bids
    final_resp = await client.get(
        "/rows",
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert final_resp.status_code == 200
    rows_data = final_resp.json()
    assert len(rows_data) == 1
    assert rows_data[0]["id"] == row.id
    assert rows_data[0]["title"] == "Private jet charter"
    assert len(rows_data[0]["bids"]) == 2

    # Verify selected bid survived
    selected_bids = [b for b in rows_data[0]["bids"] if b["is_selected"]]
    assert len(selected_bids) == 1
    assert selected_bids[0]["item_title"] == "NetJets Citation X"
