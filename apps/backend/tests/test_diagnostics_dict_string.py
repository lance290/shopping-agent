"""Tests for diagnostics_utils.py — dict/string dual input handling.

Covers:
- _parse_diagnostics handles dict, string, None, invalid
- validate_and_redact_diagnostics handles dict input (from JSONB), string input, redaction
- generate_diagnostics_summary handles dict input, string input, edge cases
"""

import json
import pytest

from diagnostics_utils import (
    _parse_diagnostics,
    validate_and_redact_diagnostics,
    generate_diagnostics_summary,
)


SAMPLE_DIAG_DICT = {
    "url": "https://dev.buy-anything.com/shop",
    "userAgent": "Mozilla/5.0 (Macintosh)",
    "logs": [
        {"level": "error", "message": "Failed to fetch /api/rows"},
        {"level": "info", "message": "Page loaded"},
    ],
    "network": [
        {"level": "error", "details": {"url": "/api/chat", "status": 500}},
    ],
    "breadcrumbs": [],
}

SAMPLE_DIAG_STRING = json.dumps(SAMPLE_DIAG_DICT)

SENSITIVE_DIAG_DICT = {
    "url": "https://example.com",
    "authorization": "Bearer sk-secret-key-12345",
    "api_key": "AIzaSyVERYsecret",
    "cookie": "session=abc123",
    "normal_field": "this is fine",
}


# ---------------------------------------------------------------------------
# _parse_diagnostics
# ---------------------------------------------------------------------------

class TestParseDiagnostics:

    def test_dict_input_returned_as_is(self):
        result = _parse_diagnostics(SAMPLE_DIAG_DICT)
        assert result == SAMPLE_DIAG_DICT
        assert isinstance(result, dict)

    def test_string_input_parsed_to_dict(self):
        result = _parse_diagnostics(SAMPLE_DIAG_STRING)
        assert result == SAMPLE_DIAG_DICT
        assert isinstance(result, dict)

    def test_none_input_returned_as_is(self):
        result = _parse_diagnostics(None)
        assert result is None

    def test_json_null_string_returns_none(self):
        result = _parse_diagnostics("null")
        assert result is None

    def test_integer_input_returned_as_is(self):
        result = _parse_diagnostics(42)
        assert result == 42

    def test_invalid_json_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_diagnostics("not valid json {{{")

    def test_json_array_string_returns_list(self):
        result = _parse_diagnostics('[1, 2, 3]')
        assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# validate_and_redact_diagnostics
# ---------------------------------------------------------------------------

class TestValidateAndRedact:

    def test_dict_input_returns_json_string(self):
        """JSONB column gives us a dict — should process and return a JSON string."""
        result = validate_and_redact_diagnostics(SAMPLE_DIAG_DICT)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["url"] == "https://dev.buy-anything.com/shop"

    def test_string_input_returns_json_string(self):
        """Regular JSON string input should also work."""
        result = validate_and_redact_diagnostics(SAMPLE_DIAG_STRING)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["url"] == "https://dev.buy-anything.com/shop"

    def test_none_returns_none(self):
        assert validate_and_redact_diagnostics(None) is None

    def test_empty_string_returns_none(self):
        assert validate_and_redact_diagnostics("") is None

    def test_sensitive_keys_redacted_from_dict(self):
        """Sensitive keys (authorization, api_key, cookie) must be redacted."""
        result = validate_and_redact_diagnostics(SENSITIVE_DIAG_DICT)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["authorization"] == "[REDACTED]"
        assert parsed["api_key"] == "[REDACTED]"
        assert parsed["cookie"] == "[REDACTED]"
        assert parsed["normal_field"] == "this is fine"

    def test_sensitive_keys_redacted_from_string(self):
        """Same redaction should work when input is a JSON string."""
        result = validate_and_redact_diagnostics(json.dumps(SENSITIVE_DIAG_DICT))
        assert result is not None
        parsed = json.loads(result)
        assert parsed["authorization"] == "[REDACTED]"
        assert parsed["api_key"] == "[REDACTED]"

    def test_long_strings_truncated(self):
        """Strings over 1000 chars should be truncated."""
        long_diag = {"message": "x" * 2000}
        result = validate_and_redact_diagnostics(long_diag)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed["message"]) < 2000
        assert "[TRUNCATED]" in parsed["message"]

    def test_deeply_nested_object_capped(self):
        """Deeply nested objects should be capped at MAX_DEPTH."""
        nested = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "deep"}}}}}}}
        result = validate_and_redact_diagnostics(nested)
        assert result is not None
        assert "[MAX_DEPTH_REACHED]" in result

    def test_invalid_json_string_returns_none(self):
        """Invalid JSON string should not crash, returns None."""
        result = validate_and_redact_diagnostics("not json {{{")
        assert result is None

    def test_null_json_string_does_not_crash(self):
        """The JSON string 'null' should not crash."""
        result = validate_and_redact_diagnostics("null")
        # May return None or "null" — the key property is no crash
        assert True


# ---------------------------------------------------------------------------
# generate_diagnostics_summary
# ---------------------------------------------------------------------------

class TestGenerateDiagnosticsSummary:

    def test_dict_input_generates_summary(self):
        """JSONB dict input should produce a valid markdown summary."""
        result = generate_diagnostics_summary(SAMPLE_DIAG_DICT)
        assert "https://dev.buy-anything.com/shop" in result
        assert "Mozilla/5.0" in result

    def test_string_input_generates_summary(self):
        """JSON string input should produce the same summary."""
        result = generate_diagnostics_summary(SAMPLE_DIAG_STRING)
        assert "https://dev.buy-anything.com/shop" in result
        assert "Mozilla/5.0" in result

    def test_includes_console_errors(self):
        result = generate_diagnostics_summary(SAMPLE_DIAG_DICT)
        assert "Console Errors" in result
        assert "Failed to fetch /api/rows" in result

    def test_includes_network_failures(self):
        result = generate_diagnostics_summary(SAMPLE_DIAG_DICT)
        assert "Network Failures" in result
        assert "/api/chat" in result

    def test_none_returns_no_diagnostics(self):
        assert generate_diagnostics_summary(None) == "No diagnostics available."

    def test_empty_string_returns_no_diagnostics(self):
        assert generate_diagnostics_summary("") == "No diagnostics available."

    def test_null_json_string_returns_no_diagnostics(self):
        assert generate_diagnostics_summary("null") == "No diagnostics available."

    def test_json_array_returns_no_diagnostics(self):
        """Arrays are not valid diagnostics objects."""
        assert generate_diagnostics_summary("[1, 2, 3]") == "No diagnostics available."

    def test_dict_without_logs_or_network(self):
        """Minimal dict without logs/network should still produce a summary."""
        minimal = {"url": "https://example.com", "userAgent": "TestBot"}
        result = generate_diagnostics_summary(minimal)
        assert "https://example.com" in result
        assert "TestBot" in result
        # No errors section
        assert "Console Errors" not in result
