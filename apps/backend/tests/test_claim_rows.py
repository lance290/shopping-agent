"""Regression tests for POST /rows/claim — migrating anonymous guest rows to authenticated users.

Flow:
1. Anonymous user searches → row created under guest user (guest@buy-anything.com)
2. User registers/logs in
3. Frontend calls POST /rows/claim with the anonymous row IDs
4. Backend reassigns those rows from guest user → authenticated user
5. GET /rows now returns the claimed rows for the authenticated user
"""
import pytest
import pytest_asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from httpx import AsyncClient

from models import Row, User, Bid, AuthSession, hash_token, generate_session_token


GUEST_EMAIL = "guest@buy-anything.com"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def guest_user(session: AsyncSession) -> User:
    """Create the guest user that anonymous requests fall back to."""
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
async def other_user(session: AsyncSession) -> User:
    """A second real user (not the one logging in) — for security tests."""
    user = User(email="other@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def guest_rows(session: AsyncSession, guest_user: User) -> list[Row]:
    """Create multiple rows owned by the guest user (simulates anonymous searches)."""
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
    """Create a guest row with bids and a selection — the key data that must survive claim."""
    row = Row(user_id=guest_user.id, title="Private jet charter", status="sourcing")
    session.add(row)
    await session.commit()
    await session.refresh(row)

    bid1 = Bid(
        row_id=row.id,
        price=50000.0,
        total_cost=55000.0,
        item_title="NetJets Citation X",
        item_url="https://netjets.com",
        is_selected=True,
        is_liked=True,
    )
    bid2 = Bid(
        row_id=row.id,
        price=45000.0,
        total_cost=48000.0,
        item_title="VistaJet Global 7500",
        item_url="https://vistajet.com",
        is_selected=False,
        is_liked=False,
    )
    session.add_all([bid1, bid2])
    await session.commit()
    await session.refresh(bid1)
    await session.refresh(bid2)

    return row


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_single_guest_row(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str, guest_rows: list[Row],
):
    """Claim a single guest row and verify ownership transfer."""
    target_row = guest_rows[0]

    response = await client.post(
        "/rows/claim",
        json={"row_ids": [target_row.id]},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["claimed"] == 1

    # Verify the row is now owned by real_user
    await session.refresh(target_row)
    assert target_row.user_id == real_user.id

    # Other guest rows remain under guest user
    await session.refresh(guest_rows[1])
    assert guest_rows[1].user_id == guest_user.id


@pytest.mark.asyncio
async def test_claim_multiple_guest_rows(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str, guest_rows: list[Row],
):
    """Claim all guest rows at once."""
    row_ids = [r.id for r in guest_rows]

    response = await client.post(
        "/rows/claim",
        json={"row_ids": row_ids},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["claimed"] == len(guest_rows)

    for row in guest_rows:
        await session.refresh(row)
        assert row.user_id == real_user.id


@pytest.mark.asyncio
async def test_claimed_rows_appear_in_get_rows(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str, guest_rows: list[Row],
):
    """After claiming, GET /rows should include the claimed rows."""
    # Before claim: authenticated user has zero rows
    resp_before = await client.get(
        "/rows",
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert resp_before.status_code == 200
    assert len(resp_before.json()) == 0

    # Claim
    row_ids = [r.id for r in guest_rows]
    await client.post(
        "/rows/claim",
        json={"row_ids": row_ids},
        headers={"authorization": f"Bearer {real_user_token}"},
    )

    # After claim: rows appear
    resp_after = await client.get(
        "/rows",
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert resp_after.status_code == 200
    returned_ids = {r["id"] for r in resp_after.json()}
    for row in guest_rows:
        assert row.id in returned_ids


@pytest.mark.asyncio
async def test_claim_preserves_bids_and_selections(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str,
    guest_row_with_bids: Row,
):
    """Bids, likes, and selections must survive the claim — this is the whole point."""
    row = guest_row_with_bids

    response = await client.post(
        "/rows/claim",
        json={"row_ids": [row.id]},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["claimed"] == 1

    # Verify bids still attached
    result = await session.exec(select(Bid).where(Bid.row_id == row.id))
    bids = result.all()
    assert len(bids) == 2

    # Verify the selected bid is still selected
    selected = [b for b in bids if b.is_selected]
    assert len(selected) == 1
    assert selected[0].item_title == "NetJets Citation X"

    # Verify liked status preserved
    liked = [b for b in bids if b.is_liked]
    assert len(liked) == 1


@pytest.mark.asyncio
async def test_claim_preserves_row_metadata(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str,
):
    """Row title, status, choice_factors, chat_history etc. must survive claim."""
    row = Row(
        user_id=guest_user.id,
        title="Complex search",
        status="sourcing",
        choice_factors='[{"name":"price","label":"Price"}]',
        choice_answers='{"price":"under 500"}',
        chat_history='[{"role":"user","content":"find me a desk"}]',
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    await client.post(
        "/rows/claim",
        json={"row_ids": [row.id]},
        headers={"authorization": f"Bearer {real_user_token}"},
    )

    await session.refresh(row)
    assert row.user_id == real_user.id
    assert row.title == "Complex search"
    assert row.status == "sourcing"
    assert row.choice_factors == '[{"name":"price","label":"Price"}]'
    assert row.choice_answers == '{"price":"under 500"}'
    assert row.chat_history == '[{"role":"user","content":"find me a desk"}]'


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_requires_authentication(
    client: AsyncClient, session: AsyncSession, guest_user: User, guest_rows: list[Row],
):
    """POST /rows/claim without auth token should return 401."""
    response = await client.post(
        "/rows/claim",
        json={"row_ids": [guest_rows[0].id]},
        # NO authorization header
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_claim_cannot_steal_other_users_rows(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str, other_user: User,
):
    """Authenticated user cannot claim rows owned by another real user."""
    other_row = Row(user_id=other_user.id, title="Other user's row", status="sourcing")
    session.add(other_row)
    await session.commit()
    await session.refresh(other_row)

    response = await client.post(
        "/rows/claim",
        json={"row_ids": [other_row.id]},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert response.status_code == 200
    # Should claim 0 rows (the row doesn't belong to guest user)
    assert response.json()["claimed"] == 0

    # Verify the row still belongs to other_user
    await session.refresh(other_row)
    assert other_row.user_id == other_user.id


@pytest.mark.asyncio
async def test_claim_mixed_guest_and_other_rows(
    client: AsyncClient, session: AsyncSession,
    guest_user: User, real_user: User, real_user_token: str, other_user: User,
):
    """When row_ids contain both guest rows and another user's rows, only guest rows are claimed."""
    guest_row = Row(user_id=guest_user.id, title="Guest row", status="sourcing")
    other_row = Row(user_id=other_user.id, title="Other row", status="sourcing")
    session.add_all([guest_row, other_row])
    await session.commit()
    await session.refresh(guest_row)
    await session.refresh(other_row)

    response = await client.post(
        "/rows/claim",
        json={"row_ids": [guest_row.id, other_row.id]},
        headers={"authorization": f"Bearer {real_user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["claimed"] == 1

    await session.refresh(guest_row)
    assert guest_row.user_id == real_user.id

    await session.refresh(other_row)
    assert other_row.user_id == other_user.id


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
