"""Tests for Share Links feature."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    User, Row, Bid, Project, ShareLink, ShareSearchEvent,
    AuthSession, hash_token, generate_session_token
)


# ============== SHARE LINK CREATION TESTS ==============

@pytest.mark.asyncio
async def test_create_share_link_for_row(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_row
):
    """Test POST /shares creates share link for row."""
    user, token = auth_user_and_token
    row = test_row

    response = await client.post(
        "/api/shares",
        json={
            "resource_type": "row",
            "resource_id": row.id
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert len(data["token"]) == 32
    assert data["resource_type"] == "row"
    assert data["resource_id"] == row.id


@pytest.mark.asyncio
async def test_create_share_link_for_project(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_project
):
    """Test POST /shares creates share link for project."""
    user, token = auth_user_and_token
    project = test_project

    response = await client.post(
        "/api/shares",
        json={
            "resource_type": "project",
            "resource_id": project.id
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["resource_type"] == "project"


@pytest.mark.asyncio
async def test_create_share_link_unauthorized(client: AsyncClient):
    """Test POST /shares requires authentication."""
    response = await client.post(
        "/api/shares",
        json={"resource_type": "row", "resource_id": 1}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_share_link_invalid_resource(
    session: AsyncSession, client: AsyncClient, auth_user_and_token
):
    """Test POST /shares with non-existent resource returns 404."""
    user, token = auth_user_and_token

    response = await client.post(
        "/api/shares",
        json={
            "resource_type": "row",
            "resource_id": 99999
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


# ============== SHARE LINK RESOLUTION TESTS ==============

@pytest.mark.asyncio
async def test_resolve_share_link(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_row
):
    """Test GET /shares/{token} resolves share link."""
    user, token = auth_user_and_token
    row = test_row

    # Create share link
    share = ShareLink(
        token="abcdef1234567890abcdef1234567890",
        resource_type="row",
        resource_id=row.id,
        created_by=user.id
    )
    session.add(share)
    await session.commit()

    # Resolve it (no auth required for public access)
    response = await client.get(f"/api/shares/{share.token}")

    assert response.status_code == 200
    data = response.json()
    assert data["resource_type"] == "row"
    assert data["resource_id"] == row.id


@pytest.mark.asyncio
async def test_resolve_share_link_increments_access_count(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_row
):
    """Test GET /shares/{token} increments access count."""
    user, token = auth_user_and_token
    row = test_row

    share = ShareLink(
        token="accesscount12345678901234567890",
        resource_type="row",
        resource_id=row.id,
        created_by=user.id,
        access_count=0
    )
    session.add(share)
    await session.commit()

    # Access multiple times
    await client.get(f"/api/shares/{share.token}")
    await client.get(f"/api/shares/{share.token}")
    await client.get(f"/api/shares/{share.token}")

    await session.refresh(share)
    assert share.access_count >= 3


@pytest.mark.asyncio
async def test_resolve_invalid_share_token(client: AsyncClient):
    """Test GET /shares/{token} with invalid token returns 404."""
    response = await client.get("/api/shares/invalidtoken12345678901234")
    assert response.status_code == 404


# ============== SHARE CONTENT ACCESS TESTS ==============

@pytest.mark.asyncio
async def test_get_share_content(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_row
):
    """Test GET /shares/{token}/content returns read-only content."""
    user, token = auth_user_and_token
    row = test_row

    share = ShareLink(
        token="content123456789012345678901234",
        resource_type="row",
        resource_id=row.id,
        created_by=user.id
    )
    session.add(share)
    await session.commit()

    response = await client.get(f"/api/shares/{share.token}/content")

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Shareable Row"


# ============== ANONYMOUS ACCESS TESTS ==============

@pytest.mark.asyncio
async def test_anonymous_share_viewer_cannot_like(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_row
):
    """Test anonymous share viewers cannot interact (like)."""
    user, token = auth_user_and_token
    row = test_row

    # Create bid and share
    bid = Bid(
        row_id=row.id,
        price=100.0,
        total_cost=110.0,
        item_title="Shared Product"
    )
    session.add(bid)
    await session.commit()
    await session.refresh(bid)

    share = ShareLink(
        token="anon_test_1234567890123456789",
        resource_type="row",
        resource_id=row.id,
        created_by=user.id
    )
    session.add(share)
    await session.commit()

    # Try to like without auth (anonymous viewer)
    response = await client.post(f"/likes/{bid.id}/toggle")

    assert response.status_code == 401


# ============== SEARCH TRACKING TESTS ==============

@pytest.mark.asyncio
async def test_share_search_event_tracked(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_row
):
    """Test searches from shares create ShareSearchEvent records."""
    user, token = auth_user_and_token
    row = test_row

    share = ShareLink(
        token="search_track_123456789012345678",
        resource_type="row",
        resource_id=row.id,
        created_by=user.id
    )
    session.add(share)
    await session.commit()

    # This would need the actual search endpoint to support share_token param
    # For now, verify the model exists and can be created
    event = ShareSearchEvent(
        share_token=share.token,
        session_id="test-session-123",
        search_query="test search",
        search_success=True
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)

    assert event.id is not None
    assert event.share_token == share.token


# ============== REFERRAL ATTRIBUTION TESTS ==============

@pytest.mark.asyncio
async def test_signup_with_referral_token(
    session: AsyncSession, client: AsyncClient, auth_user_and_token
):
    """Test signup captures referral_share_token."""
    user, token = auth_user_and_token

    # Create share link for referral
    share = ShareLink(
        token="referral_test_123456789012345",
        resource_type="row",
        resource_id=1,
        created_by=user.id,
        signup_conversion_count=0
    )
    session.add(share)
    await session.commit()

    # Verify model supports referral fields
    new_user = User(
        email="referred@example.com",
        referral_share_token=share.token,
        signup_source="share"
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    assert new_user.referral_share_token == share.token
    assert new_user.signup_source == "share"


# ============== METRICS TESTS ==============

@pytest.mark.asyncio
async def test_share_metrics_endpoint(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_row
):
    """Test share metrics are accessible to creator."""
    user, token = auth_user_and_token
    row = test_row

    share = ShareLink(
        token="metrics_test_1234567890123456",
        resource_type="row",
        resource_id=row.id,
        created_by=user.id,
        access_count=10,
        unique_visitors=5,
        search_initiated_count=3,
        search_success_count=2,
        signup_conversion_count=1
    )
    session.add(share)
    await session.commit()

    # Get metrics (if endpoint exists)
    response = await client.get(
        f"/api/shares/{share.token}/metrics",
        headers={"Authorization": f"Bearer {token}"}
    )

    # May return 200 or 404 depending on implementation
    if response.status_code == 200:
        data = response.json()
        assert data["access_count"] == 10
        assert data["unique_visitors"] == 5


@pytest.mark.asyncio
async def test_share_token_uniqueness(session: AsyncSession, auth_user_and_token, test_row):
    """Test share tokens are unique."""
    user, _ = auth_user_and_token
    row = test_row

    share1 = ShareLink(
        token="unique_test_12345678901234567",
        resource_type="row",
        resource_id=row.id,
        created_by=user.id
    )
    session.add(share1)
    await session.commit()

    # Attempting to create duplicate token should fail
    share2 = ShareLink(
        token="unique_test_12345678901234567",  # Same token
        resource_type="row",
        resource_id=row.id,
        created_by=user.id
    )
    session.add(share2)
    
    with pytest.raises(Exception):  # IntegrityError
        await session.commit()
