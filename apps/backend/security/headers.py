"""
Security Headers Middleware.

Adds security headers to all responses:
- HSTS (HTTP Strict Transport Security)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Content-Security-Policy
- Referrer-Policy
"""

import secrets

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


def generate_csp_nonce() -> str:
    """Generate a cryptographically secure nonce for CSP."""
    return secrets.token_urlsafe(16)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Headers added:
    - Strict-Transport-Security: Force HTTPS for 1 year
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter (legacy browsers)
    - Content-Security-Policy: Restrict resource loading
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Disable unnecessary browser features
    """

    def __init__(self, app, *, is_production: bool = False):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application
            is_production: Whether running in production (enables stricter policies)
        """
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)

        # HSTS - Force HTTPS for 1 year (only in production)
        if self.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS Protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy with nonce-based script protection
        nonce = generate_csp_nonce()
        request.state.csp_nonce = nonce

        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' https://s.skimresources.com",
            "style-src 'self' 'unsafe-inline'",  # Tailwind requires inline styles
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' https://s.skimresources.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Expose nonce to frontend via custom header
        response.headers["X-CSP-Nonce"] = nonce

        # Referrer Policy - Don't leak referrer to external sites
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy - Disable unnecessary features
        permissions = [
            "camera=()",
            "microphone=()",
            "geolocation=()",
            "interest-cohort=()",  # Disable FLoC
            "payment=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)

        return response
