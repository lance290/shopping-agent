"""Tests for LLM circuit breaker, fallback logic, and JSON extraction in llm_core.py."""

import json
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from services.llm_core import (
    call_gemini,
    _extract_json,
    _extract_json_array,
    _openrouter_backoff_until,
    _OPENROUTER_BACKOFF_SECS,
)
import services.llm_core as llm_core_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Create a realistic httpx.HTTPStatusError for testing."""
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        message=f"{status_code} Error",
        request=request,
        response=response,
    )


# ---------------------------------------------------------------------------
# Circuit Breaker Tests
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    """Tests for the OpenRouter 402 circuit breaker in call_gemini."""

    @pytest.fixture(autouse=True)
    def reset_circuit_breaker(self):
        """Reset circuit breaker state before each test."""
        llm_core_module._openrouter_backoff_until = 0.0
        yield
        llm_core_module._openrouter_backoff_until = 0.0

    @pytest.mark.asyncio
    async def test_openrouter_success_no_fallback(self):
        """When OpenRouter succeeds, Gemini direct should NOT be called."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"}):
            with patch("services.llm_core._call_openrouter", new_callable=AsyncMock, return_value="openrouter response") as mock_or, \
                 patch("services.llm_core._call_gemini_direct", new_callable=AsyncMock) as mock_gd:
                result = await call_gemini("test prompt")

        assert result == "openrouter response"
        mock_or.assert_called_once()
        mock_gd.assert_not_called()

    @pytest.mark.asyncio
    async def test_openrouter_402_triggers_circuit_breaker(self):
        """A 402 from OpenRouter should activate the circuit breaker and fall back to Gemini."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"}):
            with patch("services.llm_core._call_openrouter", new_callable=AsyncMock, side_effect=_make_http_status_error(402)), \
                 patch("services.llm_core._call_gemini_direct", new_callable=AsyncMock, return_value="gemini response"):
                result = await call_gemini("test prompt")

        assert result == "gemini response"
        # Circuit breaker should now be active
        assert llm_core_module._openrouter_backoff_until > time.monotonic()

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_openrouter_on_subsequent_calls(self):
        """After a 402, subsequent calls should skip OpenRouter entirely."""
        # Activate the circuit breaker
        llm_core_module._openrouter_backoff_until = time.monotonic() + 600

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"}):
            with patch("services.llm_core._call_openrouter", new_callable=AsyncMock) as mock_or, \
                 patch("services.llm_core._call_gemini_direct", new_callable=AsyncMock, return_value="gemini direct") as mock_gd:
                result = await call_gemini("test prompt")

        assert result == "gemini direct"
        mock_or.assert_not_called()  # Skipped due to circuit breaker
        mock_gd.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_expires_and_retries_openrouter(self):
        """After backoff expires, OpenRouter should be tried again."""
        # Set backoff to already expired
        llm_core_module._openrouter_backoff_until = time.monotonic() - 1

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"}):
            with patch("services.llm_core._call_openrouter", new_callable=AsyncMock, return_value="openrouter back") as mock_or:
                result = await call_gemini("test prompt")

        assert result == "openrouter back"
        mock_or.assert_called_once()

    @pytest.mark.asyncio
    async def test_openrouter_500_falls_back_without_circuit_breaker(self):
        """A 500 error should fall back to Gemini but NOT activate the circuit breaker."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"}):
            with patch("services.llm_core._call_openrouter", new_callable=AsyncMock, side_effect=_make_http_status_error(500)), \
                 patch("services.llm_core._call_gemini_direct", new_callable=AsyncMock, return_value="gemini fallback"):
                result = await call_gemini("test prompt")

        assert result == "gemini fallback"
        # Circuit breaker should NOT be activated for non-402 errors
        assert llm_core_module._openrouter_backoff_until == 0.0

    @pytest.mark.asyncio
    async def test_openrouter_timeout_falls_back_without_circuit_breaker(self):
        """A timeout from OpenRouter should fall back without activating circuit breaker."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"}):
            with patch("services.llm_core._call_openrouter", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")), \
                 patch("services.llm_core._call_gemini_direct", new_callable=AsyncMock, return_value="gemini after timeout"):
                result = await call_gemini("test prompt")

        assert result == "gemini after timeout"
        assert llm_core_module._openrouter_backoff_until == 0.0

    @pytest.mark.asyncio
    async def test_no_api_keys_raises_valueerror(self):
        """With no API keys configured, should raise ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("services.llm_core._get_openrouter_api_key", return_value=""), \
                 patch("services.llm_core._get_gemini_api_key", return_value=""):
                with pytest.raises(ValueError, match="No LLM API key"):
                    await call_gemini("test prompt")

    @pytest.mark.asyncio
    async def test_only_gemini_key_skips_openrouter(self):
        """When only Gemini key is set, should go directly to Gemini."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch("services.llm_core._get_openrouter_api_key", return_value=""), \
                 patch("services.llm_core._call_gemini_direct", new_callable=AsyncMock, return_value="gemini only") as mock_gd:
                result = await call_gemini("test prompt")

        assert result == "gemini only"
        mock_gd.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_fail_raises_from_gemini(self):
        """When both OpenRouter and Gemini fail, the Gemini error should propagate."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key", "GEMINI_API_KEY": "test-key"}):
            with patch("services.llm_core._call_openrouter", new_callable=AsyncMock, side_effect=_make_http_status_error(500)), \
                 patch("services.llm_core._call_gemini_direct", new_callable=AsyncMock, side_effect=ValueError("Gemini down")):
                with pytest.raises(ValueError, match="Gemini down"):
                    await call_gemini("test prompt")


# ---------------------------------------------------------------------------
# JSON Extraction Tests
# ---------------------------------------------------------------------------

class TestExtractJson:
    """Tests for _extract_json — handles markdown fences, prose, etc."""

    def test_plain_json(self):
        result = _extract_json('{"action": "search", "query": "laptops"}')
        assert result == {"action": "search", "query": "laptops"}

    def test_json_in_markdown_fence(self):
        text = '```json\n{"action": "search"}\n```'
        result = _extract_json(text)
        assert result == {"action": "search"}

    def test_json_with_surrounding_prose(self):
        text = 'Here is the result:\n{"action": "clarify", "message": "What budget?"}\nHope that helps!'
        result = _extract_json(text)
        assert result == {"action": "clarify", "message": "What budget?"}

    def test_json_in_bare_fence(self):
        text = '```\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_nested_json(self):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = _extract_json(text)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("not json at all")

    def test_empty_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("")


class TestExtractJsonArray:
    """Tests for _extract_json_array — handles arrays in markdown fences."""

    def test_plain_array(self):
        result = _extract_json_array('[{"a": 1}, {"b": 2}]')
        assert result == [{"a": 1}, {"b": 2}]

    def test_array_in_markdown_fence(self):
        text = '```json\n[1, 2, 3]\n```'
        result = _extract_json_array(text)
        assert result == [1, 2, 3]

    def test_array_with_prose(self):
        text = 'Here are the factors:\n["price", "quality", "brand"]\nDone.'
        result = _extract_json_array(text)
        assert result == ["price", "quality", "brand"]

    def test_invalid_array_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json_array("not an array")
