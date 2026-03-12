"""Tests for the SSE streaming + vendor search + project creation fixes.

Covers this session's changes:
- tool_executor.py: DDG HTML fallback in search_web, fallback chain
- vendor_provider.py: distance threshold raised to 0.65
- chat_helpers.py: _stream_search forwards anonymous_session_id
- models/rows.py: Project.ui_schema is sa.JSON (not str)
- agent.py: updated system prompt (vendors=services, web=products)
"""

import asyncio
import json
import os
from typing import List, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcing.models import NormalizedResult
from sourcing.tools import ToolResult


# ============================================================================
# tool_executor.py — DDG HTML scraper
# ============================================================================

class TestDDGHtmlSearch:
    """Test the _ddg_html_search helper that scrapes DuckDuckGo HTML."""

    @pytest.mark.asyncio
    async def test_ddg_html_search_parses_results(self):
        """Given valid DDG HTML, parser extracts titles and URLs."""
        from sourcing.tool_executor import _ddg_html_search

        fake_html = """
        <div class="result">
          <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fpriveporter.com%2F&rut=abc">
            Privé Porter
          </a>
          <a class="result__snippet" href="#">
            Authenticated Hermès Birkin bags for sale.
          </a>
        </div>
        <div class="result">
          <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Ftherealreal.com%2Fbirkin&rut=def">
            The RealReal - Birkin
          </a>
          <a class="result__snippet" href="#">
            Consignment luxury handbags.
          </a>
        </div>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = fake_html
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await _ddg_html_search("Birkin bag resellers", max_results=5)

        assert len(results) == 2
        assert results[0]["title"].strip() == "Privé Porter"
        assert "priveporter.com" in results[0]["url"]
        assert "Authenticated" in results[0]["snippet"]
        assert "therealreal.com" in results[1]["url"]

    @pytest.mark.asyncio
    async def test_ddg_html_search_empty_html(self):
        """DDG returning no results → empty list."""
        from sourcing.tool_executor import _ddg_html_search

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body>No results</body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await _ddg_html_search("xyzzy nonexistent", max_results=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_ddg_html_search_respects_max_results(self):
        """Parser respects max_results limit."""
        from sourcing.tool_executor import _ddg_html_search

        # Build HTML with 5 results
        result_blocks = []
        for i in range(5):
            result_blocks.append(f"""
            <div class="result">
              <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fsite{i}.com%2F&rut=x">
                Site {i}
              </a>
              <a class="result__snippet" href="#">Snippet {i}</a>
            </div>
            """)
        fake_html = "\n".join(result_blocks)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = fake_html
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await _ddg_html_search("test", max_results=2)

        assert len(results) == 2


# ============================================================================
# tool_executor.py — search_web fallback chain
# ============================================================================

class TestSearchWebFallbackChain:
    """Test that search_web tries SerpAPI → SearchAPI → CSE → DDG in order."""

    @pytest.mark.asyncio
    async def test_search_web_falls_through_to_ddg(self):
        """When SerpAPI/SearchAPI/CSE all fail, DDG fallback is used."""
        from sourcing.tool_executor import _tool_search_web

        ddg_results = [
            {"url": "https://example.com", "title": "Example", "snippet": "Test"},
        ]

        with patch.dict(os.environ, {
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            with patch("sourcing.tool_executor._ddg_html_search", new_callable=AsyncMock) as mock_ddg:
                mock_ddg.return_value = ddg_results
                result = await _tool_search_web(query="test query", max_results=5)

        assert len(result.items) == 1
        assert result.items[0].source == "web_duckduckgo"
        assert result.items[0].title == "Example"
        mock_ddg.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_web_serpapi_success_skips_fallbacks(self):
        """When SerpAPI succeeds, no other providers are called."""
        from sourcing.tool_executor import _tool_search_web

        mock_serp_resp = MagicMock()
        mock_serp_resp.status_code = 200
        mock_serp_resp.raise_for_status = MagicMock()
        mock_serp_resp.json.return_value = {
            "organic_results": [
                {"title": "SerpAPI Result", "link": "https://serp.com", "snippet": "From SerpAPI"},
            ]
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_serp_resp)

        with patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"}, clear=False):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await _tool_search_web(query="test", max_results=5)

        assert len(result.items) == 1
        assert result.items[0].source == "web_serpapi"

    @pytest.mark.asyncio
    async def test_search_web_all_fail_returns_error(self):
        """When all providers fail (including DDG), returns error."""
        from sourcing.tool_executor import _tool_search_web

        with patch.dict(os.environ, {
            "SERPAPI_API_KEY": "",
            "SEARCHAPI_API_KEY": "",
            "GOOGLE_CSE_API_KEY": "",
            "GOOGLE_CSE_CX": "",
        }, clear=False):
            with patch("sourcing.tool_executor._ddg_html_search", new_callable=AsyncMock) as mock_ddg:
                mock_ddg.return_value = []
                result = await _tool_search_web(query="test", max_results=5)

        assert result.error is not None
        assert "failed" in result.error.lower()


# ============================================================================
# vendor_provider.py — distance threshold
# ============================================================================

class TestVendorDistanceThreshold:
    """Test the vendor distance threshold configuration."""

    def test_default_threshold_is_0_65(self):
        from sourcing.vendor_provider import _get_distance_threshold

        with patch.dict(os.environ, {}, clear=False):
            # Remove env var if set
            os.environ.pop("VENDOR_DISTANCE_THRESHOLD", None)
            threshold = _get_distance_threshold()
            assert threshold == 0.65

    def test_threshold_respects_env_override(self):
        from sourcing.vendor_provider import _get_distance_threshold

        with patch.dict(os.environ, {"VENDOR_DISTANCE_THRESHOLD": "0.70"}, clear=False):
            threshold = _get_distance_threshold()
            assert threshold == 0.70

    def test_hermes_birkin_distance_passes_threshold(self):
        """Hermès at distance 0.5599 should pass the 0.65 threshold."""
        from sourcing.vendor_provider import _get_distance_threshold

        hermes_distance = 0.5599
        threshold = _get_distance_threshold()
        assert hermes_distance <= threshold, (
            f"Hermès distance {hermes_distance} should pass threshold {threshold}"
        )


# ============================================================================
# chat_helpers.py — _stream_search header forwarding
# ============================================================================

class TestStreamSearchHeaders:
    """Test that _stream_search forwards anonymous_session_id."""

    @pytest.mark.asyncio
    async def test_stream_search_includes_anon_session_header(self):
        from routes.chat_helpers import _stream_search

        captured_headers = {}

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "text/event-stream"}

            def raise_for_status(self):
                pass

            async def aiter_text(self):
                yield 'data: {"provider": "test", "results": [], "status": "done", "more_incoming": false}\n\n'

            async def aclose(self):
                pass

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, method, url, **kwargs):
                captured_headers.update(kwargs.get("headers", {}))

                class StreamCtx:
                    async def __aenter__(self_inner):
                        return FakeResponse()
                    async def __aexit__(self_inner, *args):
                        pass
                return StreamCtx()

        with patch("httpx.AsyncClient", return_value=FakeClient()):
            with patch("routes.chat_helpers._get_self_base_url", return_value="http://localhost:8000"):
                batches = []
                async for batch in _stream_search(
                    row_id=1,
                    query="test",
                    authorization="Bearer token123",
                    anonymous_session_id="anon-uuid-abc",
                ):
                    batches.append(batch)

        assert captured_headers.get("X-Anonymous-Session-Id") == "anon-uuid-abc"
        assert captured_headers.get("Authorization") == "Bearer token123"

    @pytest.mark.asyncio
    async def test_stream_search_omits_anon_header_when_none(self):
        from routes.chat_helpers import _stream_search

        captured_headers = {}

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "text/event-stream"}
            def raise_for_status(self): pass
            async def aiter_text(self):
                yield 'data: {"provider": "test", "results": [], "status": "done", "more_incoming": false}\n\n'
            async def aclose(self): pass

        class FakeClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def stream(self, method, url, **kwargs):
                captured_headers.update(kwargs.get("headers", {}))
                class StreamCtx:
                    async def __aenter__(self_inner): return FakeResponse()
                    async def __aexit__(self_inner, *args): pass
                return StreamCtx()

        with patch("httpx.AsyncClient", return_value=FakeClient()):
            with patch("routes.chat_helpers._get_self_base_url", return_value="http://localhost:8000"):
                async for _ in _stream_search(row_id=1, query="test", authorization=None):
                    pass

        assert "X-Anonymous-Session-Id" not in captured_headers


# ============================================================================
# models/rows.py — Project.ui_schema type
# ============================================================================

class TestProjectUiSchemaType:
    """Verify Project.ui_schema is JSON-compatible, not VARCHAR."""

    def test_project_ui_schema_column_type_is_json(self):
        import sqlalchemy as sa
        from models.rows import Project

        col = Project.__table__.columns["ui_schema"]
        assert isinstance(col.type, sa.JSON), (
            f"Project.ui_schema column should be sa.JSON, got {type(col.type)}"
        )

    def test_project_ui_schema_accepts_dict(self):
        from models.rows import Project

        p = Project(title="test", status="active")
        p.ui_schema = {"layout": "grid", "version": 1}
        assert p.ui_schema["layout"] == "grid"

    def test_project_ui_schema_accepts_none(self):
        from models.rows import Project

        p = Project(title="test", status="active")
        assert p.ui_schema is None


# ============================================================================
# agent.py — updated system prompt
# ============================================================================

class TestAgentPromptRules:
    """Verify the agent prompt correctly routes product vs service queries."""

    def test_prompt_says_no_vendors_for_products(self):
        from sourcing.agent import AGENT_SYSTEM_PROMPT

        assert "Do NOT call search_vendors for products" in AGENT_SYSTEM_PROMPT

    def test_prompt_says_search_web_for_luxury(self):
        from sourcing.agent import AGENT_SYSTEM_PROMPT

        assert "search_web" in AGENT_SYSTEM_PROMPT
        assert "authenticated resellers" in AGENT_SYSTEM_PROMPT

    def test_prompt_says_vendors_for_services(self):
        from sourcing.agent import AGENT_SYSTEM_PROMPT

        assert "SERVICES" in AGENT_SYSTEM_PROMPT
        assert "search_vendors" in AGENT_SYSTEM_PROMPT
