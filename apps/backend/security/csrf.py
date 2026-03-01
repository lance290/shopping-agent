"""
CSRF (Cross-Site Request Forgery) Protection Middleware.

Implements double-submit cookie pattern for CSRF protection on state-changing operations.
"""

import secrets
import hmac
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders


# CSRF token configuration
CSRF_TOKEN_LENGTH = 32
CSRF_TOKEN_EXPIRY = timedelta(hours=24)
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_SECRET_KEY = None  # Set from environment variable


def set_csrf_secret(secret: str):
    """Set the CSRF secret key from environment variable."""
    global CSRF_SECRET_KEY
    CSRF_SECRET_KEY = secret


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def sign_csrf_token(token: str, timestamp: int) -> str:
    """
    Create HMAC signature for CSRF token with timestamp.

    Args:
        token: The CSRF token
        timestamp: Unix timestamp when token was created

    Returns:
        HMAC signature (hex)
    """
    if not CSRF_SECRET_KEY:
        raise ValueError("CSRF secret key not configured")

    message = f"{token}:{timestamp}".encode()
    signature = hmac.new(
        CSRF_SECRET_KEY.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature


def create_signed_csrf_token() -> tuple[str, int, str]:
    """
    Create a signed CSRF token with timestamp.

    Returns:
        Tuple of (token, timestamp, signature)
    """
    token = generate_csrf_token()
    timestamp = int(datetime.utcnow().timestamp())
    signature = sign_csrf_token(token, timestamp)
    return token, timestamp, signature


def verify_csrf_token(token: str, timestamp: int, signature: str) -> bool:
    """
    Verify a signed CSRF token.

    Args:
        token: The CSRF token to verify
        timestamp: Unix timestamp when token was created
        signature: HMAC signature to verify

    Returns:
        True if valid, False otherwise
    """
    if not CSRF_SECRET_KEY:
        return False

    # Check if token is expired
    token_time = datetime.fromtimestamp(timestamp)
    if datetime.utcnow() - token_time > CSRF_TOKEN_EXPIRY:
        return False

    # Verify signature
    expected_signature = sign_csrf_token(token, timestamp)
    return hmac.compare_digest(signature, expected_signature)


def encode_csrf_cookie(token: str, timestamp: int, signature: str) -> str:
    """Encode CSRF token data for cookie storage."""
    return f"{token}:{timestamp}:{signature}"


def decode_csrf_cookie(cookie_value: str) -> Optional[tuple[str, int, str]]:
    """
    Decode CSRF token data from cookie.

    Returns:
        Tuple of (token, timestamp, signature) or None if invalid
    """
    try:
        parts = cookie_value.split(":")
        if len(parts) != 3:
            return None
        token, timestamp_str, signature = parts
        timestamp = int(timestamp_str)
        return token, timestamp, signature
    except (ValueError, AttributeError):
        return None


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware using double-submit cookie pattern.

    Protects state-changing operations (POST, PUT, PATCH, DELETE) by requiring:
    1. A CSRF cookie set by the server
    2. A matching CSRF token in request header or form data

    Exempt paths:
    - /auth/* endpoints (need CSRF token to login)
    - /health endpoints
    - /webhooks endpoints (use signature verification instead)
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    EXEMPT_PATHS = [
        "/auth/",
        "/health",
        "/webhooks/",
        "/api/bugs",  # Allow bug reports from unauthenticated users
        "/api/chat",  # Chat SSE endpoint — uses Bearer auth, not cookies
        "/pop/",      # Pop API endpoints (chat, receipt scanning) handle their own auth
    ]

    async def dispatch(self, request: Request, call_next):
        """Process request with CSRF protection."""

        # Skip all CSRF logic when no secret is configured
        if not CSRF_SECRET_KEY:
            return await call_next(request)

        # Skip CSRF check for safe methods
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Always set CSRF cookie on safe requests
            self._set_csrf_cookie(response)
            return response

        # Skip CSRF check for requests using Bearer token auth (not cookie-based)
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            response = await call_next(request)
            return response

        # Skip CSRF check for exempt paths
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            response = await call_next(request)
            return response

        # Verify CSRF token for state-changing operations
        try:
            self._verify_csrf(request)
        except HTTPException as e:
            # Return error response without calling next handler
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )

        response = await call_next(request)
        return response

    def _verify_csrf(self, request: Request):
        """
        Verify CSRF token from cookie and header/form.

        Raises:
            HTTPException: If CSRF verification fails
        """
        # Get CSRF token from cookie
        cookie_value = request.cookies.get(CSRF_COOKIE_NAME)
        if not cookie_value:
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing from cookie"
            )

        # Decode and verify cookie
        csrf_data = decode_csrf_cookie(cookie_value)
        if not csrf_data:
            raise HTTPException(
                status_code=403,
                detail="CSRF token invalid"
            )

        token, timestamp, signature = csrf_data
        if not verify_csrf_token(token, timestamp, signature):
            raise HTTPException(
                status_code=403,
                detail="CSRF token expired or invalid"
            )

        # Get CSRF token from header
        header_token = request.headers.get(CSRF_HEADER_NAME)
        if not header_token:
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing from header"
            )

        # Verify tokens match
        if not hmac.compare_digest(token, header_token):
            raise HTTPException(
                status_code=403,
                detail="CSRF token mismatch"
            )

    def _set_csrf_cookie(self, response: Response):
        """Set CSRF cookie on response."""
        # Only set if not already present
        if CSRF_COOKIE_NAME in response.headers.getlist("set-cookie"):
            return

        token, timestamp, signature = create_signed_csrf_token()
        cookie_value = encode_csrf_cookie(token, timestamp, signature)

        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=cookie_value,
            httponly=False,  # Must be accessible to JavaScript
            secure=True,      # Only send over HTTPS
            samesite="strict",  # Strict same-site policy
            max_age=int(CSRF_TOKEN_EXPIRY.total_seconds())
        )
