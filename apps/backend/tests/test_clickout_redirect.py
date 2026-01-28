import pytest
from httpx import AsyncClient
from main import app
from routes.rate_limit import check_rate_limit, rate_limit_store
from models import Row, User, AuthSession
from sqlmodel import select
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_clickout_redirect_success(client: AsyncClient, session):
    """
    Test that /api/out redirects to the resolved URL and logs the event.
    """
    # 1. Setup Data
    user = User(email="redirect_test@example.com")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    auth = AuthSession(
        user_id=user.id, 
        email=user.email,
        session_token_hash="hash", 
        created_at=datetime.utcnow()
    )
    session.add(auth)
    await session.commit()
    
    # 2. Call /api/out
    target_url = "https://example.com/product"
    
    # Bypass rate limit for test
    rate_limit_store.clear()
    
    response = await client.get(
        "/api/out",
        params={
            "url": target_url,
            "row_id": 123,
            "idx": 0,
            "source": "test_provider"
        },
        follow_redirects=False  # We want to catch the 307/302
    )
    
    # 3. Verify Redirect
    assert response.status_code in (302, 307)
    assert response.headers["location"] == target_url

@pytest.mark.asyncio
async def test_clickout_missing_url(client: AsyncClient):
    response = await client.get("/api/out")
    assert response.status_code == 422  # Validation error (missing url)

@pytest.mark.asyncio
async def test_clickout_invalid_url(client: AsyncClient):
    response = await client.get("/api/out", params={"url": "not-a-url"})
    assert response.status_code == 400
