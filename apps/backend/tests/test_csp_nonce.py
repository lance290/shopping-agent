"""
Tests for nonce-based Content Security Policy implementation.

Verifies:
- Nonce generation is cryptographically secure
- CSP header is present and correctly formatted
- unsafe-inline and unsafe-eval are NOT present in script-src
- Nonce is unique per request
- X-CSP-Nonce header is exposed to frontend
"""

import pytest
from fastapi.testclient import TestClient
from security.headers import generate_csp_nonce, SecurityHeadersMiddleware
from main import app


client = TestClient(app)


def test_generate_csp_nonce_format():
    """Test that generated nonce has correct format (URL-safe base64)."""
    nonce = generate_csp_nonce()
    assert isinstance(nonce, str)
    assert len(nonce) > 0
    assert all(c.isalnum() or c in ['-', '_'] for c in nonce)


def test_generate_csp_nonce_uniqueness():
    """Test that nonce generation produces unique values."""
    nonces = [generate_csp_nonce() for _ in range(100)]
    assert len(set(nonces)) == 100


def test_csp_header_present():
    """Test that CSP header is present in response."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "Content-Security-Policy" in response.headers


def test_csp_header_no_unsafe_in_script_src():
    """Test that script-src does NOT contain unsafe-inline or unsafe-eval."""
    response = client.get("/health")
    csp_header = response.headers.get("Content-Security-Policy", "")

    if "script-src" in csp_header:
        script_src_part = csp_header.split("script-src")[1].split(";")[0]
        assert "unsafe-inline" not in script_src_part
        assert "unsafe-eval" not in script_src_part


def test_csp_header_contains_nonce():
    """Test that CSP header contains a nonce directive."""
    response = client.get("/health")
    csp_header = response.headers.get("Content-Security-Policy", "")
    assert "nonce-" in csp_header
    assert "script-src" in csp_header


def test_csp_header_allows_self():
    """Test that CSP header allows 'self' for scripts."""
    response = client.get("/health")
    csp_header = response.headers.get("Content-Security-Policy", "")
    assert "'self'" in csp_header


def test_x_csp_nonce_header_present():
    """Test that X-CSP-Nonce header is exposed to frontend."""
    response = client.get("/health")
    assert "X-CSP-Nonce" in response.headers
    nonce = response.headers.get("X-CSP-Nonce")
    assert isinstance(nonce, str)
    assert len(nonce) > 0


def test_nonce_unique_per_request():
    """Test that each request gets a unique nonce."""
    response1 = client.get("/health")
    response2 = client.get("/health")
    nonce1 = response1.headers.get("X-CSP-Nonce")
    nonce2 = response2.headers.get("X-CSP-Nonce")
    assert nonce1 != nonce2


def test_nonce_matches_csp_header():
    """Test that nonce in X-CSP-Nonce matches nonce in CSP header."""
    response = client.get("/health")
    x_nonce = response.headers.get("X-CSP-Nonce")
    csp_header = response.headers.get("Content-Security-Policy", "")
    assert f"nonce-{x_nonce}" in csp_header


def test_additional_security_headers():
    """Test that additional security headers are present."""
    response = client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Referrer-Policy" in response.headers


def test_csp_frame_ancestors_none():
    """Test that CSP prevents clickjacking via frame-ancestors."""
    response = client.get("/health")
    csp_header = response.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp_header


def test_csp_base_uri_restricted():
    """Test that CSP restricts base-uri to prevent base tag injection."""
    response = client.get("/health")
    csp_header = response.headers.get("Content-Security-Policy", "")
    assert "base-uri 'self'" in csp_header
