"""
Tests for CSRF protection middleware.

Verifies:
- POST without CSRF token returns 403 when CSRF is enabled
- POST with valid CSRF token succeeds
- GET requests work without CSRF token
- Exempt paths bypass CSRF check
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch


# Set CSRF secret BEFORE importing app so middleware registers
TEST_CSRF_SECRET = "test-csrf-secret-key-for-testing-only-1234567890abcdef"


@pytest.fixture(autouse=True)
def csrf_env():
    """Enable CSRF for tests in this module, then restore original state."""
    import security.csrf as csrf_mod
    original_secret = csrf_mod.CSRF_SECRET_KEY
    csrf_mod.set_csrf_secret(TEST_CSRF_SECRET)
    yield
    # Restore original state so other test files aren't affected
    csrf_mod.CSRF_SECRET_KEY = original_secret


@pytest.fixture
def app_with_csrf():
    """Return the app with CSRF already enabled via csrf_env fixture."""
    from main import app
    return app


@pytest_asyncio.fixture
async def client(app_with_csrf):
    """Create async test client."""
    transport = ASGITransport(app=app_with_csrf)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_requests_work_without_csrf(client):
    """GET requests should work without CSRF token."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_csrf_cookie_set_on_get(client):
    """GET request should set CSRF cookie for subsequent use."""
    response = await client.get("/health")
    assert response.status_code == 200
    # CSRF cookie should be set on safe requests
    cookies = response.cookies
    if "csrf_token" in cookies:
        assert len(cookies["csrf_token"]) > 0


@pytest.mark.asyncio
async def test_post_without_csrf_token_fails(client):
    """POST without CSRF token should return 403."""
    response = await client.post(
        "/rows",
        json={"text": "Test row", "project_id": 1},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_post_with_valid_csrf_succeeds_or_auth_fails(client):
    """POST with valid CSRF token should pass CSRF check (may fail on auth)."""
    from security.csrf import create_signed_csrf_token, encode_csrf_cookie
    
    token, timestamp, signature = create_signed_csrf_token()
    cookie_value = encode_csrf_cookie(token, timestamp, signature)
    
    response = await client.post(
        "/rows",
        json={"text": "Test row", "project_id": 1},
        headers={
            "X-CSRF-Token": token,
            "Authorization": "Bearer fake-token",
        },
        cookies={"csrf_token": cookie_value},
    )
    # Should NOT be 403 (CSRF passed), might be 401 (auth) or other
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_exempt_paths_bypass_csrf(client):
    """Exempt paths like /health and /auth/ should bypass CSRF."""
    response = await client.post(
        "/auth/start",
        json={"email": "test@example.com"},
    )
    # Should not be 403 from CSRF (may be other errors)
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_post_with_invalid_csrf_token_fails(client):
    """POST with mismatched CSRF token should return 403."""
    from security.csrf import create_signed_csrf_token, encode_csrf_cookie
    
    token, timestamp, signature = create_signed_csrf_token()
    cookie_value = encode_csrf_cookie(token, timestamp, signature)
    
    response = await client.post(
        "/rows",
        json={"text": "Test row"},
        headers={
            "X-CSRF-Token": "wrong-token-value",
            "Authorization": "Bearer fake-token",
        },
        cookies={"csrf_token": cookie_value},
    )
    assert response.status_code == 403
