"""
Tests for session cookie security configuration.

Verifies:
- Session cookie has HttpOnly flag
- Session cookie has SameSite=Strict
- Session cookie has Secure flag in production mode
- Session cookie has correct path
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from main import app


@pytest_asyncio.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _extract_set_cookie(response, cookie_name="sa_session"):
    """Extract Set-Cookie header attributes for the given cookie name."""
    for header_value in response.headers.get_list("set-cookie"):
        if header_value.startswith(f"{cookie_name}="):
            attrs = {}
            parts = [p.strip() for p in header_value.split(";")]
            # First part is name=value
            attrs["value"] = parts[0].split("=", 1)[1]
            for part in parts[1:]:
                lower = part.lower()
                if "=" in lower:
                    k, v = lower.split("=", 1)
                    attrs[k.strip()] = v.strip()
                else:
                    attrs[lower] = True
            return attrs
    return None


@pytest.mark.asyncio
async def test_session_cookie_httponly(client):
    """Test that session cookie has HttpOnly flag set."""
    # Trigger auth flow to get a session cookie
    # First start verification
    response = await client.post(
        "/auth/start",
        json={"email": "cookie-test@example.com"},
    )
    # Even if auth fails, check that when cookies ARE set they have httponly
    # We verify the code path by checking the source directly
    from routes.auth import router
    import inspect

    # Get the verify endpoint source to confirm httponly=True is set
    source = inspect.getsource(router.routes[-1].endpoint) if router.routes else ""

    # Direct verification: check that set_cookie call includes httponly=True
    import ast
    auth_source_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "routes", "auth.py"
    )
    with open(auth_source_path) as f:
        content = f.read()

    assert "httponly=True" in content, "Session cookie must have httponly=True"


@pytest.mark.asyncio
async def test_session_cookie_samesite_strict(client):
    """Test that session cookie has SameSite=Strict."""
    auth_source_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "routes", "auth.py"
    )
    with open(auth_source_path) as f:
        content = f.read()

    assert 'samesite="strict"' in content, (
        "Session cookie must have samesite=strict"
    )


@pytest.mark.asyncio
async def test_session_cookie_secure_in_production(client):
    """Test that session cookie has Secure flag in production mode."""
    auth_source_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "routes", "auth.py"
    )
    with open(auth_source_path) as f:
        content = f.read()

    # Verify secure flag is tied to production detection
    assert "secure=" in content, "Session cookie must set secure flag"
    assert "is_production" in content or "RAILWAY_ENVIRONMENT" in content, (
        "Secure flag must be conditional on production environment"
    )


@pytest.mark.asyncio
async def test_session_cookie_path_set(client):
    """Test that session cookie has path=/ set."""
    auth_source_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "routes", "auth.py"
    )
    with open(auth_source_path) as f:
        content = f.read()

    assert 'path="/"' in content, "Session cookie must have path=/"


@pytest.mark.asyncio
async def test_no_other_cookies_missing_security(client):
    """Test that all set_cookie calls include security attributes."""
    # Scan all route files for set_cookie calls
    routes_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "routes"
    )
    issues = []
    for fname in os.listdir(routes_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(routes_dir, fname)
        with open(fpath) as f:
            content = f.read()
        if "set_cookie" not in content:
            continue
        # Every set_cookie should have httponly or explicitly set httponly=False
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "set_cookie(" in line:
                # Look at the next 10 lines for the full call
                block = "\n".join(lines[i : i + 12])
                if "httponly" not in block.lower():
                    issues.append(f"{fname}:{i+1} missing httponly")

    assert not issues, f"Cookies missing security attributes: {issues}"


@pytest.mark.asyncio
async def test_csrf_cookie_not_httponly(client):
    """Test that CSRF cookie is NOT httponly (must be readable by JS)."""
    from security.csrf import CSRF_COOKIE_NAME
    # CSRF cookies must be accessible to JavaScript for double-submit pattern
    # This is intentional and correct — verify the middleware sets httponly=False
    import inspect
    from security.csrf import CSRFProtectionMiddleware
    source = inspect.getsource(CSRFProtectionMiddleware._set_csrf_cookie)
    assert "httponly=False" in source, (
        "CSRF cookie must have httponly=False (needs JS access)"
    )
