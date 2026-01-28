"""
Centralized security utilities for data redaction and sanitization.

This module consolidates redaction logic that was duplicated across
audit.py and sourcing.py, following DRY principles.
"""

from typing import Dict, Any
import re


def redact_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive fields from dictionaries (for audit logs, diagnostics, etc.).

    This replaces sensitive values with '[REDACTED]' to prevent leaking
    credentials, tokens, or other sensitive data in logs.

    Args:
        data: Dictionary potentially containing sensitive data

    Returns:
        New dictionary with sensitive values redacted
    """
    sensitive_keys = {'password', 'token', 'secret', 'api_key', 'code', 'session_token'}

    def _redact(obj):
        if isinstance(obj, dict):
            return {
                k: '[REDACTED]' if k.lower() in sensitive_keys else _redact(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_redact(item) for item in obj]
        return obj

    return _redact(data)


def redact_secrets_from_text(text: str) -> str:
    """
    Redact secrets from plain text using regex patterns.

    This is useful for sanitizing error messages, URLs, or other text
    that might contain sensitive query parameters or headers.

    Args:
        text: String potentially containing secrets in URLs or headers

    Returns:
        String with secrets replaced with '[REDACTED]'
    """
    if not text:
        return text

    redactions = [
        (r"(api_key=)[^&\s]+", r"\1[REDACTED]"),
        (r"(key=)[^&\s]+", r"\1[REDACTED]"),
        (r"(token=)[^&\s]+", r"\1[REDACTED]"),
        (r"(Authorization: Bearer)\s+[^\s]+", r"\1 [REDACTED]"),
    ]

    out = text
    for pattern, repl in redactions:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return out
