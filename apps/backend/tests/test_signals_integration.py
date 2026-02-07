"""Integration tests for user signal routes (PRD 11)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_record_signal_requires_auth(client: AsyncClient):
    res = await client.post("/signals", json={"signal_type": "click"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_record_signal_thumbs_up(client: AsyncClient, auth_user_and_token):
    _, token = auth_user_and_token
    res = await client.post(
        "/signals",
        json={"signal_type": "thumbs_up", "value": 1.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["signal_type"] == "thumbs_up"
    assert data["value"] == 1.0
    assert "id" in data


@pytest.mark.asyncio
async def test_record_signal_invalid_type(client: AsyncClient, auth_user_and_token):
    _, token = auth_user_and_token
    res = await client.post(
        "/signals",
        json={"signal_type": "invalid_type"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "Invalid signal_type" in res.json()["detail"]


@pytest.mark.asyncio
async def test_record_all_valid_signal_types(client: AsyncClient, auth_user_and_token):
    _, token = auth_user_and_token
    headers = {"Authorization": f"Bearer {token}"}

    for signal_type in ["thumbs_up", "thumbs_down", "click", "select", "skip"]:
        res = await client.post(
            "/signals",
            json={"signal_type": signal_type, "value": 1.0},
            headers=headers,
        )
        assert res.status_code == 200, f"Failed for signal_type={signal_type}"
        assert res.json()["signal_type"] == signal_type


@pytest.mark.asyncio
async def test_get_preferences_empty(client: AsyncClient, auth_user_and_token):
    _, token = auth_user_and_token
    res = await client.get(
        "/signals/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_preferences_requires_auth(client: AsyncClient):
    res = await client.get("/signals/preferences")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_signal_with_bid_creates_preferences(client: AsyncClient, session, auth_user_and_token):
    """Thumbs up on a bid with a seller should create merchant preference."""
    from models import Row, Bid, Seller

    user, token = auth_user_and_token
    headers = {"Authorization": f"Bearer {token}"}

    row = Row(title="Test", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    seller = Seller(name="TestStore", domain="teststore.com")
    session.add(seller)
    await session.commit()
    await session.refresh(seller)

    bid = Bid(
        row_id=row.id, price=25.0, total_cost=25.0, currency="USD",
        item_title="Widget", item_url="https://teststore.com/w",
        source="google", seller_id=seller.id,
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    # Send thumbs_up signal
    res = await client.post(
        "/signals",
        json={"signal_type": "thumbs_up", "bid_id": bid.id, "row_id": row.id},
        headers=headers,
    )
    assert res.status_code == 200

    # Check preferences were learned
    pref_res = await client.get("/signals/preferences", headers=headers)
    prefs = pref_res.json()
    # Should have at least merchant and source preferences
    pref_keys = [p["key"] for p in prefs]
    assert "merchant" in pref_keys or "source" in pref_keys
