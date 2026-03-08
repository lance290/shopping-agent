import pytest
import sys
import os
import json
from httpx import AsyncClient
from sqlmodel import select
from models import Row, AuthSession, User, Bid, Seller, VendorBookmark, ItemBookmark

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
    
    # 1. Verify Unauthenticated Access returns empty list (guest user flow)
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
async def test_row_read_includes_vendor_and_item_bookmark_state(client: AsyncClient, session):
    user = User(email="bookmark-row@example.com")
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

    vendor = Seller(name="Saved Vendor", email="saved-vendor@example.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    row = Row(title="Need options", status="sourcing", currency="USD", user_id=user.id)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    vendor_bid = Bid(
        row_id=row.id,
        vendor_id=vendor.id,
        price=100.0,
        currency="USD",
        item_title="Vendor Option",
        item_url="https://vendor.example.com/offer",
        source="vendor_directory",
    )
    item_bid = Bid(
        row_id=row.id,
        price=49.0,
        currency="USD",
        item_title="Saved Product",
        item_url="https://www.amazon.com/dp/ABC123?tag=oldtag&utm_source=test",
        canonical_url="https://amazon.com/dp/ABC123",
        source="amazon",
    )
    session.add(vendor_bid)
    session.add(item_bid)
    await session.commit()
    await session.refresh(vendor_bid)
    await session.refresh(item_bid)

    session.add(VendorBookmark(user_id=user.id, vendor_id=vendor.id, source_row_id=row.id))
    session.add(ItemBookmark(user_id=user.id, canonical_url="https://amazon.com/dp/ABC123", source_row_id=row.id))
    await session.commit()

    resp = await client.get(f"/rows/{row.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    bids = resp.json()["bids"]

    vendor_payload = next(b for b in bids if b["id"] == vendor_bid.id)
    assert vendor_payload["is_vendor_bookmarked"] is True
    assert vendor_payload["is_item_bookmarked"] is False
    assert vendor_payload["is_liked"] is True

    item_payload = next(b for b in bids if b["id"] == item_bid.id)
    assert item_payload["canonical_url"] == "https://amazon.com/dp/ABC123"
    assert item_payload["is_vendor_bookmarked"] is False
    assert item_payload["is_item_bookmarked"] is True
    assert item_payload["is_liked"] is True


@pytest.mark.asyncio
async def test_search_preserves_global_bookmarks_and_emits_bookmark_flags(client: AsyncClient, session):
    user = User(email="bookmark-search@example.com")
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

    create_resp = await client.post(
        "/rows",
        json={
            "title": "Search bookmark row",
            "status": "sourcing",
            "currency": "USD",
            "request_spec": {"item_name": "Search bookmark row", "constraints": "{}"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    row_id = create_resp.json()["id"]

    vendor = Seller(name="Search Saved Vendor", email="search-saved-vendor@example.com")
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    vendor_bid = Bid(
        row_id=row_id,
        vendor_id=vendor.id,
        price=200.0,
        currency="USD",
        item_title="Saved Vendor Search Option",
        item_url="https://vendor.example.com/search-option",
        source="vendor_directory",
    )
    item_bid = Bid(
        row_id=row_id,
        price=59.0,
        currency="USD",
        item_title="Saved Product Search Option",
        item_url="https://www.ebay.com/itm/999?utm_source=test",
        canonical_url="https://ebay.com/itm/999",
        source="ebay",
    )
    session.add(vendor_bid)
    session.add(item_bid)
    await session.commit()
    await session.refresh(vendor_bid)
    await session.refresh(item_bid)

    session.add(VendorBookmark(user_id=user.id, vendor_id=vendor.id, source_row_id=row_id))
    session.add(ItemBookmark(user_id=user.id, canonical_url="https://ebay.com/itm/999", source_row_id=row_id))
    await session.commit()

    async def fake_search_all_with_status(self, query: str, **kwargs):
        return SearchResultWithStatus(results=[], provider_statuses=[], all_providers_failed=False)

    rows_search_module._sourcing_repo = type('MockRepo', (), {'search_all_with_status': fake_search_all_with_status})()

    resp = await client.post(
        f"/rows/{row_id}/search",
        json={"query": "Search bookmark row"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2

    vendor_result = next(r for r in results if r["bid_id"] == vendor_bid.id)
    assert vendor_result["is_vendor_bookmarked"] is True
    assert vendor_result["is_liked"] is True

    item_result = next(r for r in results if r["bid_id"] == item_bid.id)
    assert item_result["canonical_url"] == "https://ebay.com/itm/999"
    assert item_result["is_item_bookmarked"] is True
    assert item_result["is_liked"] is True


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
    assert captured["query"] == long_query


@pytest.mark.asyncio
async def test_provider_query_map_persists_on_row(client: AsyncClient, session):
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
        json={"provider_query_map": {"some_provider": {"query": "Roblox gift cards"}}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch.status_code == 200
    assert patch.json().get("provider_query_map") == {"some_provider": {"query": "Roblox gift cards"}}

    get = await client.get(
        f"/rows/{row_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get.status_code == 200
    assert get.json().get("provider_query_map") == {"some_provider": {"query": "Roblox gift cards"}}


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
    assert captured["query"] == "Nintendo Switch 2"
