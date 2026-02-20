import pytest
import sys
import os
import json
from httpx import AsyncClient
from sqlmodel import select
from models import Row, AuthSession, User, Bid, Seller

# Add parent directory to path to allow importing models and main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_session
from models import hash_token, generate_session_token
from sourcing import SearchResultWithStatus
import routes.rows_search as rows_search_module

@pytest.mark.asyncio
async def test_rows_authorization(client: AsyncClient, session):
    # Setup: Create two users (A and B) and sessions
    user_a_email = "user_a@example.com"
    user_b_email = "user_b@example.com"
    
    # Create Users
    user_a = User(email=user_a_email)
    user_b = User(email=user_b_email)
    session.add(user_a)
    session.add(user_b)
    await session.commit()
    await session.refresh(user_a)
    await session.refresh(user_b)
    
    # Create Sessions
    token_a = generate_session_token()
    token_b = generate_session_token()
    
    session_a = AuthSession(email=user_a_email, user_id=user_a.id, session_token_hash=hash_token(token_a))
    session_b = AuthSession(email=user_b_email, user_id=user_b.id, session_token_hash=hash_token(token_b))
    session.add(session_a)
    session.add(session_b)
    await session.commit()
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # 1. Unauthenticated access returns empty list (not 401)
    resp = await client.get("/rows")
    assert resp.status_code == 200
    assert resp.json() == []
    
    # 2. User A creates a row
    row_data = {
        "title": "User A Row",
        "status": "sourcing",
        "currency": "USD",
        "request_spec": {
            "item_name": "User A Item",
            "constraints": "{}"
        }
    }
    resp = await client.post("/rows", json=row_data, headers=headers_a)
    assert resp.status_code == 200
    created_row = resp.json()
    row_id_a = created_row["id"]
    assert created_row["title"] == "User A Row"
    
    # Verify DB ownership
    db_row = await session.get(Row, row_id_a)
    assert db_row.user_id == user_a.id
    
    # 3. User A can see their row
    resp = await client.get("/rows", headers=headers_a)
    assert resp.status_code == 200
    rows_a = resp.json()
    assert len(rows_a) == 1
    assert rows_a[0]["id"] == row_id_a
    
    # 4. User B cannot see User A's row
    resp = await client.get("/rows", headers=headers_b)
    assert resp.status_code == 200
    rows_b = resp.json()
    assert len(rows_b) == 0
    
    # 5. User B cannot access User A's row by ID (404 Not Found, not 403 Forbidden to prevent leakage)
    resp = await client.get(f"/rows/{row_id_a}", headers=headers_b)
    assert resp.status_code == 404
    
    # 6. User B cannot update User A's row
    patch_data = {"title": "Hacked by B"}
    resp = await client.patch(f"/rows/{row_id_a}", json=patch_data, headers=headers_b)
    assert resp.status_code == 404
    
    # Verify title unchanged
    await session.refresh(db_row)
    assert db_row.title == "User A Row"
    
    # 7. User B cannot delete User A's row
    resp = await client.delete(f"/rows/{row_id_a}", headers=headers_b)
    assert resp.status_code == 404
    
    # Verify row still exists
    db_row = await session.get(Row, row_id_a)
    assert db_row is not None
    
    # 8. User A can delete their row
    resp = await client.delete(f"/rows/{row_id_a}", headers=headers_a)
    assert resp.status_code == 200
    
    # Verify row archived (soft delete)
    db_row = await session.get(Row, row_id_a)
    assert db_row is not None
    assert db_row.status == "archived"


@pytest.mark.asyncio
async def test_search_query_uses_explicit_query_when_provided(client: AsyncClient, session, monkeypatch):
    user = User(email="searcher@example.com")
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

    row_data = {
        "title": "Roblox gift cards",
        "status": "sourcing",
        "currency": "USD",
        "choice_answers": json.dumps({"quantity": 3, "is_gift": True}),
        "request_spec": {
            "item_name": "Roblox gift cards",
            "constraints": json.dumps({"card_value": "$100"}),
        },
    }

    resp = await client.post(
        "/rows",
        json=row_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    row_id = resp.json()["id"]

    captured = {}

    async def fake_search_all_with_status(self, query: str, **kwargs):
        captured["query"] = query
        return SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)

    rows_search_module._sourcing_repo = type('MockRepo', (), {'search_all_with_status': fake_search_all_with_status})()

    search_resp = await client.post(
        f"/rows/{row_id}/search",
        json={"query": "Roblox gift cards"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert search_resp.status_code == 200
    assert captured["query"] == "Roblox gift cards"


@pytest.mark.asyncio
async def test_search_query_uses_constraints_when_query_missing(client: AsyncClient, session, monkeypatch):
    user = User(email="constraints@example.com")
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

    row_data = {
        "title": "Roblox gift cards",
        "status": "sourcing",
        "currency": "USD",
        "choice_answers": json.dumps({"quantity": 3, "is_gift": True}),
        "request_spec": {
            "item_name": "Roblox gift cards",
            "constraints": json.dumps({"card_value": "$100"}),
        },
    }

    resp = await client.post(
        "/rows",
        json=row_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    row_id = resp.json()["id"]

    captured = {}

    async def fake_search_all_with_status(self, query: str, **kwargs):
        captured["query"] = query
        return SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)

    rows_search_module._sourcing_repo = type('MockRepo', (), {'search_all_with_status': fake_search_all_with_status})()

    search_resp = await client.post(
        f"/rows/{row_id}/search",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert search_resp.status_code == 200
    # provider_query / title is used as-is — no appending of constraints or choice_answers
    assert captured["query"].strip() == "Roblox gift cards"


@pytest.mark.asyncio
async def test_search_query_sanitizes_long_query(client: AsyncClient, session, monkeypatch):
    user = User(email="sanitize@example.com")
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

    row_data = {
        "title": "Long Query Row",
        "status": "sourcing",
        "currency": "USD",
        "request_spec": {
            "item_name": "Long Query Row",
            "constraints": "{}",
        },
    }

    resp = await client.post(
        "/rows",
        json=row_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    row_id = resp.json()["id"]

    captured = {}

    async def fake_search_all_with_status(self, query: str, **kwargs):
        captured["query"] = query
        return SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)

    rows_search_module._sourcing_repo = type('MockRepo', (), {'search_all_with_status': fake_search_all_with_status})()

    long_query = "one two three four five six seven eight nine ten eleven"
    search_resp = await client.post(
        f"/rows/{row_id}/search",
        json={"query": long_query},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert search_resp.status_code == 200
    # Explicit user queries should not be truncated; only auto-constructed queries are limited.
    assert captured["query"] == long_query


@pytest.mark.asyncio
async def test_provider_query_persists_on_row(client: AsyncClient, session):
    user = User(email="provider_query@example.com")
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
            "title": "Roblox gift cards $50 and up",
            "status": "sourcing",
            "currency": "USD",
            "request_spec": {
                "item_name": "Roblox gift cards",
                "constraints": "{}",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    row_id = resp.json()["id"]

    patch = await client.patch(
        f"/rows/{row_id}",
        json={"provider_query": "Roblox gift cards"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch.status_code == 200
    assert patch.json().get("provider_query") == "Roblox gift cards"

    get = await client.get(
        f"/rows/{row_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get.status_code == 200
    assert get.json().get("provider_query") == "Roblox gift cards"


@pytest.mark.asyncio
async def test_search_defaults_to_row_title(client: AsyncClient, session, monkeypatch):
    user = User(email="defaults@example.com")
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

    row_data = {
        "title": "Nintendo Switch 2",
        "status": "sourcing",
        "currency": "USD",
        "request_spec": {
            "item_name": "Nintendo Switch 2",
            "constraints": "{}",
        },
    }

    resp = await client.post(
        "/rows",
        json=row_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    row_id = resp.json()["id"]

    captured = {}

    async def fake_search_all_with_status(self, query: str, **kwargs):
        captured["query"] = query
        return SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)

    rows_search_module._sourcing_repo = type('MockRepo', (), {'search_all_with_status': fake_search_all_with_status})()

    search_resp = await client.post(
        f"/rows/{row_id}/search",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert search_resp.status_code == 200
    assert captured["query"].startswith("Nintendo Switch 2")


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

    factors = json.loads(created["choice_factors"])
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
    # No filtering — all bids returned regardless of price
    assert "JetRight (Contact: Alexis)" in titles
    assert "Mid-range poster (in budget)" in titles
    assert "Cheap poster (under min)" in titles
    assert "Luxury poster (over max)" in titles
    assert len(bids) == 4
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
    bids_in_response = [b for b in refreshed.json().get("bids", []) if not b.get("is_superseded")]
    assert bids_in_response == []




