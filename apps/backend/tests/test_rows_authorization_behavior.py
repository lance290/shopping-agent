"""Extracted rows authorization behavior tests from test_rows_authorization.py."""
import json
import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from models import Row, User, AuthSession, Bid, Seller, generate_session_token, hash_token


@pytest.mark.asyncio
async def test_row_creation_populates_choice_factors_by_default(client: AsyncClient, session):
    user = User(email="choicefactors-default@example.com")
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

    resp = await client.post(
        "/rows",
        json={
            "title": "Nintendo Switch 2",
            "status": "sourcing",
            "currency": "USD",
            "request_spec": {
                "item_name": "Nintendo Switch 2",
                "constraints": "{}",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    created = resp.json()
    assert created.get("choice_factors") is not None

    factors = created["choice_factors"]
    if isinstance(factors, str):
        factors = json.loads(factors)
    assert isinstance(factors, list)
    # Backend returns empty factors — BFF LLM generates proper contextual factors
    assert len(factors) == 0


@pytest.mark.asyncio
async def test_rows_filter_preserves_service_provider_bids(client: AsyncClient, session):
    user = User(email="service-filter@example.com")
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

    row = Row(
        title="Private jet charter",
        status="sourcing",
        user_id=user.id,
        # Both min and max are hard price filters.
        # Vendor directory bids have price=None (quote-based) and pass naturally.
        choice_answers=json.dumps({"min_price": 200, "max_price": 500}),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    seller = Seller(name="JetRight", domain="jetright.com")
    session.add(seller)
    await session.commit()
    await session.refresh(seller)

    service_bid = Bid(
        row_id=row.id,
        vendor_id=seller.id,
        price=None,
        total_cost=None,
        currency="USD",
        item_title="JetRight (Contact: Alexis)",
        item_url="mailto:team@jetright.com",
        source="vendor_directory",
        is_selected=False,
        is_service_provider=True,
        contact_name="Alexis",
        contact_email="team@jetright.com",
        contact_phone="+16505550199",
    )
    too_cheap_bid = Bid(
        row_id=row.id,
        price=50.0,
        total_cost=50.0,
        currency="USD",
        item_title="Cheap poster (under min)",
        item_url="https://example.com/cheap",
        source="rainforest",
        is_selected=False,
    )
    over_budget_bid = Bid(
        row_id=row.id,
        price=999.0,
        total_cost=999.0,
        currency="USD",
        item_title="Luxury poster (over max)",
        item_url="https://example.com/poster",
        source="rainforest",
        is_selected=False,
    )
    in_range_bid = Bid(
        row_id=row.id,
        price=300.0,
        total_cost=300.0,
        currency="USD",
        item_title="Mid-range poster (in budget)",
        item_url="https://example.com/mid",
        source="rainforest",
        is_selected=False,
    )
    session.add(service_bid)
    session.add(too_cheap_bid)
    session.add(over_budget_bid)
    session.add(in_range_bid)
    await session.commit()

    resp = await client.get(
        f"/rows/{row.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    bids = payload.get("bids") or []
    titles = {b["item_title"] for b in bids}
    # Vendor bid (price=None, quote-based) passes price filter naturally
    assert "JetRight (Contact: Alexis)" in titles
    # In-range ($300, between $200-$500) survives
    assert "Mid-range poster (in budget)" in titles
    # Too cheap ($50 < $200 min) filtered out
    assert "Cheap poster (under min)" not in titles
    # Over budget ($999 > $500 max) filtered out
    assert "Luxury poster (over max)" not in titles
    assert len(bids) == 2
    # Verify service provider fields preserved
    svc = next(b for b in bids if b["is_service_provider"])
    assert svc["contact_email"] == "team@jetright.com"
    assert svc["contact_name"] == "Alexis"


@pytest.mark.asyncio
async def test_reset_bids_clears_existing_bids(client: AsyncClient, session):
    user = User(email="reset-bids@example.com")
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

    row = Row(title="Reset test", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    bid = Bid(
        row_id=row.id,
        price=50.0,
        total_cost=50.0,
        currency="USD",
        item_title="Test item",
        item_url="https://example.com/test",
        source="rainforest",
        is_selected=False,
    )
    session.add(bid)
    await session.commit()

    patch = await client.patch(
        f"/rows/{row.id}",
        json={"reset_bids": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch.status_code == 200

    refreshed = await client.get(
        f"/rows/{row.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert refreshed.status_code == 200
    assert refreshed.json().get("bids") == []
