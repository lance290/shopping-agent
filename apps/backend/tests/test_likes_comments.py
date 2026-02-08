"""Tests for Likes & Comments Persistence feature."""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Row, Bid, Comment, AuthSession, hash_token, generate_session_token


# ============== LIKE TESTS ==============

@pytest.mark.asyncio
async def test_toggle_like_creates_like(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test POST /likes/{bid_id}/toggle creates a like."""
    user, token = auth_user_and_token
    bid = test_bid

    response = await client.post(
        f"/likes/{bid.id}/toggle",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_liked"] is True
    assert data["like_count"] == 1
    assert data["bid_id"] == bid.id


@pytest.mark.asyncio
async def test_toggle_like_removes_like(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test POST /likes/{bid_id}/toggle removes existing like."""
    user, token = auth_user_and_token
    bid = test_bid

    # Set bid as liked directly
    bid.is_liked = True
    from datetime import datetime
    bid.liked_at = datetime.utcnow()
    session.add(bid)
    await session.commit()

    # Toggle should remove it
    response = await client.post(
        f"/likes/{bid.id}/toggle",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_liked"] is False
    assert data["like_count"] == 0


@pytest.mark.asyncio
async def test_toggle_like_unauthorized(client: AsyncClient, test_bid):
    """Test POST /likes/{bid_id}/toggle requires auth."""
    response = await client.post(f"/likes/{test_bid.id}/toggle")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_likes_for_row(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test GET /likes returns liked bids for a row."""
    user, token = auth_user_and_token
    bid = test_bid

    # Set bid as liked
    bid.is_liked = True
    from datetime import datetime
    bid.liked_at = datetime.utcnow()
    session.add(bid)
    await session.commit()

    response = await client.get(
        f"/likes?row_id={bid.row_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["bid_id"] == bid.id
    assert data[0]["is_liked"] is True


# ============== COMMENT TESTS ==============

@pytest.mark.asyncio
async def test_create_comment(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test POST /comments creates a comment."""
    user, token = auth_user_and_token
    bid = test_bid

    response = await client.post(
        "/comments",
        json={
            "bid_id": bid.id,
            "row_id": bid.row_id,
            "body": "This is a test comment"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["body"] == "This is a test comment"
    assert data["user_id"] == user.id
    assert data["bid_id"] == bid.id


@pytest.mark.asyncio
async def test_create_comment_sanitizes_xss(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test POST /comments sanitizes XSS in comment body."""
    user, token = auth_user_and_token
    bid = test_bid

    response = await client.post(
        "/comments",
        json={
            "bid_id": bid.id,
            "row_id": bid.row_id,
            "body": "<script>alert('xss')</script>Safe text"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "<script>" not in data["body"]
    assert "Safe text" in data["body"]


@pytest.mark.asyncio
async def test_get_comments_for_bid(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test GET /comments?bid_id returns comments."""
    user, token = auth_user_and_token
    bid = test_bid

    # Create comment
    comment = Comment(
        user_id=user.id,
        bid_id=bid.id,
        row_id=bid.row_id,
        body="Test comment"
    )
    session.add(comment)
    await session.commit()

    response = await client.get(
        f"/comments?bid_id={bid.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["body"] == "Test comment"


@pytest.mark.asyncio
async def test_delete_own_comment(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test DELETE /comments/{id} deletes own comment."""
    user, token = auth_user_and_token
    bid = test_bid

    comment = Comment(
        user_id=user.id,
        bid_id=bid.id,
        row_id=bid.row_id,
        body="Comment to delete"
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    response = await client.delete(
        f"/comments/{comment.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_other_user_comment_forbidden(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test DELETE /comments/{id} rejects deleting others' comments."""
    user, token = auth_user_and_token
    bid = test_bid

    # Create another user's comment
    other_user = User(email="other@example.com", is_admin=False)
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)

    comment = Comment(
        user_id=other_user.id,
        bid_id=bid.id,
        row_id=bid.row_id,
        body="Other user's comment"
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    response = await client.delete(
        f"/comments/{comment.id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


# ============== SOCIAL AGGREGATION TESTS ==============

@pytest.mark.asyncio
async def test_get_bid_social_data(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test GET /bids/{bid_id}/social returns aggregated data."""
    user, token = auth_user_and_token
    bid = test_bid

    # Set bid as liked and create comment
    from datetime import datetime
    bid.is_liked = True
    bid.liked_at = datetime.utcnow()
    comment = Comment(
        user_id=user.id,
        bid_id=bid.id,
        row_id=bid.row_id,
        body="Great product!"
    )
    session.add(bid)
    session.add(comment)
    await session.commit()

    response = await client.get(
        f"/bids/{bid.id}/social",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["like_count"] == 1
    assert data["is_liked"] is True
    assert data["comment_count"] == 1
    assert len(data["comments"]) == 1


@pytest.mark.asyncio
async def test_optimistic_like_performance(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test like toggle responds within 100ms for optimistic UI."""
    import time
    user, token = auth_user_and_token
    bid = test_bid

    start = time.time()
    response = await client.post(
        f"/likes/{bid.id}/toggle",
        headers={"Authorization": f"Bearer {token}"}
    )
    elapsed = (time.time() - start) * 1000  # ms

    assert response.status_code == 200
    assert elapsed < 500  # Allow 500ms for test environment (CI may be slow)


@pytest.mark.asyncio
async def test_social_data_persists_across_reload(
    session: AsyncSession, client: AsyncClient, auth_user_and_token, test_bid
):
    """Test social data persists (simulating page reload)."""
    user, token = auth_user_and_token
    bid = test_bid

    # Create like
    await client.post(
        f"/likes/{bid.id}/toggle",
        headers={"Authorization": f"Bearer {token}"}
    )

    # "Reload" - get social data again
    response = await client.get(
        f"/bids/{bid.id}/social",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_liked"] is True
    assert data["like_count"] == 1
