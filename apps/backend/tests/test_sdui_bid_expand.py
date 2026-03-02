"""
Tests for lazy bid-expand schema endpoint and schema invalidation.

Covers:
- GET /bids/{id}/schema endpoint (lazy hydration + caching)
- Schema invalidation when bids are reset via _update_row
- Bid-level schema is valid UISchema
- Cached schema returned on second request
- 404 on missing bid
- 401 without auth
"""

import pytest
import pytest_asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_bid_schema_endpoint_401_without_auth(client):
    """GET /bids/1/schema without auth returns 401."""
    response = await client.get("/bids/1/schema")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bid_schema_endpoint_404_missing_bid(client, auth_user_and_token):
    """GET /bids/99999/schema with valid auth returns 404 for nonexistent bid."""
    _, token = auth_user_and_token
    response = await client.get(
        "/bids/99999/schema",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bid_schema_endpoint_returns_valid_schema(client, session, auth_user_and_token, test_bid):
    """GET /bids/{id}/schema returns a valid ui_schema dict."""
    _, token = auth_user_and_token
    response = await client.get(
        f"/bids/{test_bid.id}/schema",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "ui_schema" in data
    assert "bid_id" in data
    assert data["bid_id"] == test_bid.id
    schema = data["ui_schema"]
    assert schema["version"] == 1
    assert schema["layout"] in ("ROW_COMPACT", "ROW_MEDIA_LEFT", "ROW_TIMELINE")
    assert "blocks" in schema
    assert isinstance(schema["blocks"], list)


@pytest.mark.asyncio
async def test_bid_schema_cached_on_second_request(client, session, auth_user_and_token, test_bid):
    """Second GET /bids/{id}/schema returns cached version without re-hydrating."""
    _, token = auth_user_and_token
    headers = {"Authorization": f"Bearer {token}"}

    # First request — hydrates
    r1 = await client.get(f"/bids/{test_bid.id}/schema", headers=headers)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["ui_schema_version"] == 1

    # Second request — should return cached
    r2 = await client.get(f"/bids/{test_bid.id}/schema", headers=headers)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["ui_schema_version"] == 1
    assert d2["ui_schema"] == d1["ui_schema"]


@pytest.mark.asyncio
async def test_schema_invalidation_on_update_row(session, auth_user_and_token):
    """When _update_row resets bids, Row.ui_schema should be set to None."""
    from models import Row
    from routes.chat import _update_row

    user, _ = auth_user_and_token
    row = Row(
        title="Test Item",
        status="sourcing",
        user_id=user.id,
        ui_schema={"version": 1, "layout": "ROW_COMPACT", "blocks": []},
        ui_schema_version=1,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    assert row.ui_schema is not None
    assert row.ui_schema_version == 1

    # Update with reset_bids=True should invalidate ui_schema
    updated = await _update_row(
        session, row,
        title="New Title",
        reset_bids=True,
    )
    assert updated.ui_schema is None


@pytest.mark.asyncio
async def test_schema_preserved_on_update_without_reset(session, auth_user_and_token):
    """When _update_row does NOT reset bids, Row.ui_schema should be preserved."""
    from models import Row
    from routes.chat import _update_row

    user, _ = auth_user_and_token
    original_schema = {"version": 1, "layout": "ROW_COMPACT", "blocks": []}
    row = Row(
        title="Test Item",
        status="sourcing",
        user_id=user.id,
        ui_schema=original_schema,
        ui_schema_version=1,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Update without reset_bids — schema should be preserved
    updated = await _update_row(
        session, row,
        constraints={"color": "blue"},
        reset_bids=False,
    )
    assert updated.ui_schema is not None
    assert updated.ui_schema == original_schema
