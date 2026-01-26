"""Tests for centralized security utilities."""

import pytest
from utils.security import redact_sensitive, redact_secrets_from_text


def test_redact_sensitive_password():
    """Test that passwords are redacted."""
    data = {
        "username": "john",
        "password": "secret123",
        "email": "john@example.com"
    }
    result = redact_sensitive(data)

    assert result["username"] == "john"
    assert result["password"] == "[REDACTED]"
    assert result["email"] == "john@example.com"


def test_redact_sensitive_api_key():
    """Test that API keys are redacted."""
    data = {
        "service": "stripe",
        "api_key": "sk_test_123456",
        "description": "Payment API"
    }
    result = redact_sensitive(data)

    assert result["service"] == "stripe"
    assert result["api_key"] == "[REDACTED]"
    assert result["description"] == "Payment API"


def test_redact_sensitive_nested():
    """Test that sensitive fields in nested dicts are redacted."""
    data = {
        "user": {
            "name": "Alice",
            "password": "hunter2",
        },
        "settings": {
            "api_key": "abc123",
            "timeout": 30
        }
    }
    result = redact_sensitive(data)

    assert result["user"]["name"] == "Alice"
    assert result["user"]["password"] == "[REDACTED]"
    assert result["settings"]["api_key"] == "[REDACTED]"
    assert result["settings"]["timeout"] == 30


def test_redact_sensitive_list():
    """Test that sensitive fields in lists are redacted."""
    data = {
        "users": [
            {"name": "Alice", "token": "token1"},
            {"name": "Bob", "token": "token2"}
        ]
    }
    result = redact_sensitive(data)

    assert result["users"][0]["name"] == "Alice"
    assert result["users"][0]["token"] == "[REDACTED]"
    assert result["users"][1]["name"] == "Bob"
    assert result["users"][1]["token"] == "[REDACTED]"


def test_redact_sensitive_case_insensitive():
    """Test that redaction is case-insensitive."""
    data = {
        "Password": "abc",
        "API_KEY": "xyz",
        "Secret": "123"
    }
    result = redact_sensitive(data)

    assert result["Password"] == "[REDACTED]"
    assert result["API_KEY"] == "[REDACTED]"
    assert result["Secret"] == "[REDACTED]"


def test_redact_secrets_from_text_api_key():
    """Test redacting API keys from URLs."""
    text = "https://api.example.com/endpoint?api_key=secret123&other=value"
    result = redact_secrets_from_text(text)

    assert "api_key=[REDACTED]" in result
    assert "secret123" not in result
    assert "other=value" in result


def test_redact_secrets_from_text_token():
    """Test redacting tokens from URLs."""
    text = "https://api.example.com/endpoint?token=abc123xyz&id=42"
    result = redact_secrets_from_text(text)

    assert "token=[REDACTED]" in result
    assert "abc123xyz" not in result
    assert "id=42" in result


def test_redact_secrets_from_text_authorization_header():
    """Test redacting Authorization headers."""
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    result = redact_secrets_from_text(text)

    assert "Authorization: Bearer [REDACTED]" in result
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result


def test_redact_secrets_from_text_multiple_params():
    """Test redacting multiple secret parameters."""
    text = "url?api_key=key1&normal=value&token=tok1&key=key2"
    result = redact_secrets_from_text(text)

    assert "api_key=[REDACTED]" in result
    assert "token=[REDACTED]" in result
    assert "key=[REDACTED]" in result
    assert "normal=value" in result
    assert "key1" not in result
    assert "tok1" not in result


def test_redact_secrets_from_text_empty():
    """Test redacting from empty string."""
    assert redact_secrets_from_text("") == ""
    assert redact_secrets_from_text(None) is None


def test_redact_secrets_from_text_no_secrets():
    """Test text without secrets remains unchanged."""
    text = "https://example.com/api?id=123&name=test"
    result = redact_secrets_from_text(text)

    assert result == text
