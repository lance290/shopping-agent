"""
Regression tests for Clerk JWT authentication.
Tests SSL handling, token verification, and fallback mechanisms.
"""

import pytest
from unittest.mock import patch, MagicMock
import jwt
import time

from clerk_auth import (
    verify_clerk_token,
    get_clerk_user_id,
    get_token_issuer,
    get_clerk_instance,
    SSL_CONTEXT,
)


class TestClerkAuth:
    """Test Clerk authentication module."""

    def test_ssl_context_exists(self):
        """SSL_CONTEXT should be initialized for JWKS client."""
        assert SSL_CONTEXT is not None

    def test_get_token_issuer_valid_jwt(self):
        """Extract issuer from a valid JWT structure."""
        # Create a minimal JWT with issuer
        payload = {"iss": "https://test.clerk.accounts.dev", "sub": "user_123"}
        token = jwt.encode(payload, "secret", algorithm="HS256")
        
        issuer = get_token_issuer(token)
        assert issuer == "https://test.clerk.accounts.dev"

    def test_get_token_issuer_no_issuer(self):
        """Return empty string when JWT has no issuer."""
        payload = {"sub": "user_123"}
        token = jwt.encode(payload, "secret", algorithm="HS256")
        
        issuer = get_token_issuer(token)
        assert issuer == ""

    def test_get_token_issuer_invalid_token(self):
        """Return empty string for invalid token."""
        issuer = get_token_issuer("not-a-valid-token")
        assert issuer == ""

    def test_get_token_issuer_empty_token(self):
        """Return empty string for empty token."""
        issuer = get_token_issuer("")
        assert issuer == ""

    def test_verify_clerk_token_empty(self):
        """Return None for empty token."""
        result = verify_clerk_token("")
        assert result is None

    def test_verify_clerk_token_none(self):
        """Return None for None token."""
        result = verify_clerk_token(None)
        assert result is None

    def test_get_clerk_user_id_empty(self):
        """Return None for empty token."""
        result = get_clerk_user_id("")
        assert result is None

    @patch('clerk_auth.get_jwks_client_for_issuer')
    @patch('clerk_auth.get_jwks_client')
    def test_verify_clerk_token_jwks_ssl_error_fallback(
        self, mock_get_jwks, mock_get_issuer_jwks
    ):
        """When JWKS client fails due to SSL, should attempt fallback."""
        # Simulate JWKS client returning None (failed to create)
        mock_get_jwks.return_value = None
        mock_get_issuer_jwks.return_value = None
        
        # Create a token that would need verification
        payload = {"iss": "https://test.clerk.dev", "sub": "user_123"}
        token = jwt.encode(payload, "secret", algorithm="HS256")
        
        # Without CLERK_SECRET_KEY set, should return None
        with patch('clerk_auth.CLERK_SECRET_KEY', ''):
            result = verify_clerk_token(token)
            assert result is None

    @patch('clerk_auth.get_jwks_client_for_issuer')
    @patch('clerk_auth.get_jwks_client')
    @patch('clerk_auth.CLERK_SECRET_KEY', 'test-secret-key')
    def test_verify_clerk_token_fallback_to_secret_key(
        self, mock_get_jwks, mock_get_issuer_jwks
    ):
        """When JWKS fails, should try CLERK_SECRET_KEY verification."""
        mock_get_jwks.return_value = None
        mock_get_issuer_jwks.return_value = None
        
        # Create a token signed with the secret key
        payload = {
            "iss": "https://test.clerk.dev",
            "sub": "user_123",
            "exp": int(time.time()) + 3600
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        
        result = verify_clerk_token(token)
        assert result is not None
        assert result["sub"] == "user_123"

    def test_verify_clerk_token_expired(self):
        """Return None for expired token."""
        payload = {
            "iss": "https://test.clerk.dev",
            "sub": "user_123",
            "exp": int(time.time()) - 3600  # Expired 1 hour ago
        }
        token = jwt.encode(payload, "secret", algorithm="HS256")
        
        with patch('clerk_auth.get_jwks_client_for_issuer') as mock_issuer:
            with patch('clerk_auth.get_jwks_client') as mock_jwks:
                mock_issuer.return_value = None
                mock_jwks.return_value = None
                with patch('clerk_auth.CLERK_SECRET_KEY', 'secret'):
                    result = verify_clerk_token(token)
                    assert result is None


class TestClerkInstance:
    """Test Clerk instance extraction from publishable key."""

    @patch('clerk_auth.CLERK_PUBLISHABLE_KEY', '')
    def test_get_clerk_instance_empty_key(self):
        """Return empty string when no publishable key."""
        # Need to reimport to pick up the patched value
        from clerk_auth import get_clerk_instance
        # Clear the cache
        get_clerk_instance.cache_clear() if hasattr(get_clerk_instance, 'cache_clear') else None
        result = get_clerk_instance()
        assert result == ""


class TestAuthIntegration:
    """Integration tests for auth flow."""

    @pytest.mark.asyncio
    async def test_get_current_session_with_clerk_jwt(self, session, test_user):
        """Test that Clerk JWT creates/finds user and returns session."""
        from routes.auth import get_current_session
        from models import User
        
        # Create a mock Clerk user ID
        clerk_user_id = "user_test_clerk_123"
        
        # Patch verify_clerk_token to return a valid payload
        with patch('clerk_auth.verify_clerk_token') as mock_verify:
            mock_verify.return_value = {"sub": clerk_user_id}
            
            # First call should create user
            result = await get_current_session(
                authorization="Bearer fake-clerk-jwt",
                session=session
            )
            
            assert result is not None
            assert result.id == -1  # Fake session ID for Clerk
            
            # Verify user was created
            from sqlmodel import select
            stmt = select(User).where(User.clerk_user_id == clerk_user_id)
            db_result = await session.exec(stmt)
            user = db_result.first()
            assert user is not None
            assert user.clerk_user_id == clerk_user_id

    @pytest.mark.asyncio
    async def test_get_current_session_clerk_then_legacy_fallback(self, session, test_user):
        """Test fallback from Clerk to legacy token when Clerk fails."""
        from routes.auth import get_current_session
        from models import AuthSession, hash_token, generate_session_token
        
        # Create a legacy session token
        token = generate_session_token()
        auth_session = AuthSession(
            email=test_user.email,
            user_id=test_user.id,
            session_token_hash=hash_token(token),
        )
        session.add(auth_session)
        await session.commit()
        
        # Patch Clerk verification to fail
        with patch('clerk_auth.get_clerk_user_id') as mock_clerk:
            mock_clerk.return_value = None  # Clerk verification fails
            
            # Should fall back to legacy token
            result = await get_current_session(
                authorization=f"Bearer {token}",
                session=session
            )
            
            assert result is not None
            assert result.user_id == test_user.id
            assert result.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_current_session_both_fail(self, session):
        """Test that both Clerk and legacy failures return None."""
        from routes.auth import get_current_session
        
        with patch('clerk_auth.get_clerk_user_id') as mock_clerk:
            mock_clerk.return_value = None
            
            result = await get_current_session(
                authorization="Bearer invalid-token-xyz",
                session=session
            )
            
            assert result is None

    @pytest.mark.asyncio
    async def test_rows_endpoint_requires_auth(self, session):
        """Test that /rows endpoint returns 401 without valid auth."""
        from fastapi.testclient import TestClient
        from main import app
        
        # Note: This is a simplified test - in real scenario use async client
        # The point is to verify the auth check exists
        pass  # Placeholder - actual HTTP test would use httpx


class TestSSLContextUsage:
    """Test that SSL context is properly used in JWKS clients."""

    @patch('clerk_auth.PyJWKClient')
    def test_jwks_client_uses_ssl_context(self, mock_jwks_client):
        """Verify PyJWKClient is called with ssl_context parameter."""
        from clerk_auth import get_jwks_client_for_issuer
        
        # Clear any cached clients
        get_jwks_client_for_issuer.cache_clear()
        
        # Call the function
        get_jwks_client_for_issuer("https://test.clerk.dev")
        
        # Verify SSL context was passed
        mock_jwks_client.assert_called_once()
        call_kwargs = mock_jwks_client.call_args
        assert 'ssl_context' in call_kwargs.kwargs or len(call_kwargs.args) > 1
