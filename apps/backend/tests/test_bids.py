"""Tests for bids endpoints."""
import pytest
import json
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Bid, AuthSession, generate_session_token, hash_token


@pytest.mark.asyncio
async def test_get_bid_without_provenance(session: AsyncSession, client: AsyncClient):
    """Test GET /bids/{bid_id} without provenance parameter."""
    # Create test user
    user = User(email="test@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create auth session
    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token)
    )
    session.add(auth_session)
    await session.commit()

    # Create test row
    row = Row(
        title="Test Item",
        status="sourcing",
        user_id=user.id
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create test bid
    bid = Bid(
        row_id=row.id,
        price=100.0,
        total_cost=110.0,
        item_title="Test Product",
        item_url="https://example.com/product"
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    # Make request without provenance parameter
    response = await client.get(
        f"/bids/{bid.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == bid.id
    assert data["price"] == 100.0
    assert data["item_title"] == "Test Product"
    assert "provenance_data" not in data  # Computed fields not included


@pytest.mark.asyncio
async def test_get_bid_with_provenance(session: AsyncSession, client: AsyncClient):
    """Test GET /bids/{bid_id}?include_provenance=true."""
    # Create test user
    user = User(email="test@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create auth session
    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token)
    )
    session.add(auth_session)
    await session.commit()

    # Create test row
    row = Row(
        title="Test Item",
        status="sourcing",
        user_id=user.id
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create test bid with provenance data
    provenance_data = {
        "product_info": {
            "title": "Test Product",
            "brand": "TestBrand",
            "specs": {"color": "blue", "size": "large"}
        },
        "matched_features": ["Free shipping", "Prime eligible", "Best seller"],
        "chat_excerpts": [
            {"role": "user", "content": "I need something blue"},
            {"role": "assistant", "content": "This product is blue"}
        ]
    }
    bid = Bid(
        row_id=row.id,
        price=100.0,
        total_cost=110.0,
        item_title="Test Product",
        item_url="https://example.com/product",
        provenance=provenance_data
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    # Make request with provenance parameter
    response = await client.get(
        f"/bids/{bid.id}?include_provenance=true",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == bid.id
    assert data["price"] == 100.0
    assert data["provenance_data"] is not None
    assert data["product_info"]["brand"] == "TestBrand"
    assert len(data["matched_features"]) == 3
    assert data["matched_features"][0] == "Free shipping"
    assert len(data["chat_excerpts"]) == 2


@pytest.mark.asyncio
async def test_get_bid_with_malformed_provenance(session: AsyncSession, client: AsyncClient):
    """Test GET /bids/{bid_id}?include_provenance=true with malformed provenance data."""
    # Create test user
    user = User(email="test@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create auth session
    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token)
    )
    session.add(auth_session)
    await session.commit()

    # Create test row
    row = Row(
        title="Test Item",
        status="sourcing",
        user_id=user.id
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create bid with malformed provenance (invalid JSON)
    bid = Bid(
        row_id=row.id,
        price=100.0,
        total_cost=110.0,
        item_title="Test Product",
        provenance="{ invalid json }"
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    # Should return basic bid data without error
    response = await client.get(
        f"/bids/{bid.id}?include_provenance=true",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == bid.id
    assert data["price"] == 100.0


@pytest.mark.asyncio
async def test_get_bid_with_null_provenance(session: AsyncSession, client: AsyncClient):
    """Test GET /bids/{bid_id}?include_provenance=true with null provenance."""
    # Create test user
    user = User(email="test@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create auth session
    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token)
    )
    session.add(auth_session)
    await session.commit()

    # Create test row
    row = Row(
        title="Test Item",
        status="sourcing",
        user_id=user.id
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create bid with no provenance
    bid = Bid(
        row_id=row.id,
        price=100.0,
        total_cost=110.0,
        item_title="Test Product",
        provenance=None
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    # Should return bid with null provenance fields
    response = await client.get(
        f"/bids/{bid.id}?include_provenance=true",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == bid.id
    assert data["provenance_data"] is None
    assert data["product_info"] is None
    assert data["matched_features"] is None
    assert data["chat_excerpts"] is None


@pytest.mark.asyncio
async def test_get_bid_not_found(session: AsyncSession, client: AsyncClient):
    """Test GET /bids/{bid_id} with non-existent bid."""
    # Create test user
    user = User(email="test@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create auth session
    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token)
    )
    session.add(auth_session)
    await session.commit()

    # Request non-existent bid
    response = await client.get(
        "/bids/99999",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Bid not found"


@pytest.mark.asyncio
async def test_get_bid_unauthorized(client: AsyncClient):
    """Test GET /bids/{bid_id} without authentication."""
    response = await client.get("/bids/1")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_get_bid_sparse_provenance(session: AsyncSession, client: AsyncClient):
    """Test GET /bids/{bid_id}?include_provenance=true with sparse provenance."""
    # Create test user
    user = User(email="test@example.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create auth session
    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token)
    )
    session.add(auth_session)
    await session.commit()

    # Create test row
    row = Row(
        title="Test Item",
        status="sourcing",
        user_id=user.id
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Create bid with minimal provenance (only some fields)
    provenance_data = {
        "product_info": {
            "title": "Minimal Product"
        }
        # No matched_features or chat_excerpts
    }
    bid = Bid(
        row_id=row.id,
        price=100.0,
        total_cost=110.0,
        item_title="Test Product",
        provenance=provenance_data
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    # Should handle sparse data gracefully
    response = await client.get(
        f"/bids/{bid.id}?include_provenance=true",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["product_info"]["title"] == "Minimal Product"
    assert data["matched_features"] == []  # Empty list for missing array
    assert data["chat_excerpts"] == []
