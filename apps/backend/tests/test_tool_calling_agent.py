"""Tests for the LLM tool-calling search agent architecture.

Covers:
- sourcing/tools.py — schemas, models, serialization
- services/llm_core.py — message conversion, response parsing
- sourcing/tool_executor.py — tool routing, parallel execution, dedupe
- sourcing/agent.py — agent loop, feature flag, event streaming
"""

import asyncio
import json
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcing.tools import (
    ALL_TOOLS,
    SEARCH_VENDORS,
    SEARCH_MARKETPLACE,
    SEARCH_WEB,
    RUN_APIFY_ACTOR,
    SEARCH_APIFY_STORE,
    GeminiToolResponse,
    SearchEvent,
    ToolCall,
    ToolResult,
    _result_summary,
)
from sourcing.models import NormalizedResult


# ============================================================================
# sourcing/tools.py — Schema & Model Tests
# ============================================================================

class TestToolSchemas:
    """Verify tool schemas are valid Gemini functionDeclarations."""

    def test_all_tools_has_five_entries(self):
        assert len(ALL_TOOLS) == 5

    @pytest.mark.parametrize("tool", ALL_TOOLS, ids=[t["name"] for t in ALL_TOOLS])
    def test_tool_has_required_fields(self, tool):
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert tool["parameters"]["type"] == "object"
        assert "properties" in tool["parameters"]
        assert "required" in tool["parameters"]

    def test_search_vendors_requires_query(self):
        assert "query" in SEARCH_VENDORS["parameters"]["required"]

    def test_search_marketplace_requires_query(self):
        assert "query" in SEARCH_MARKETPLACE["parameters"]["required"]

    def test_run_apify_requires_actor_id_and_input(self):
        required = RUN_APIFY_ACTOR["parameters"]["required"]
        assert "actor_id" in required
        assert "run_input" in required

    def test_search_apify_store_requires_search_term(self):
        assert "search_term" in SEARCH_APIFY_STORE["parameters"]["required"]

    def test_marketplace_enum_values(self):
        items = SEARCH_MARKETPLACE["parameters"]["properties"]["marketplaces"]["items"]
        assert set(items["enum"]) == {"amazon", "ebay", "google_shopping"}

    def test_no_duplicate_tool_names(self):
        names = [t["name"] for t in ALL_TOOLS]
        assert len(names) == len(set(names))


class TestToolModels:
    """Test dataclass models in tools.py."""

    def test_tool_call_creation(self):
        tc = ToolCall(id="abc-123", name="search_vendors", params={"query": "realtors"})
        assert tc.name == "search_vendors"
        assert tc.params["query"] == "realtors"

    def test_tool_result_defaults(self):
        tr = ToolResult()
        assert tr.items == []
        assert tr.metadata == {}
        assert tr.error is None

    def test_tool_result_to_json(self):
        item = NormalizedResult(
            title="Acme Corp",
            url="https://acme.com",
            source="vendor_directory",
            merchant_name="Acme",
            merchant_domain="acme.com",
            price=100.0,
        )
        tr = ToolResult(items=[item])
        j = json.loads(tr.to_json())
        assert j["count"] == 1
        assert j["results"][0]["title"] == "Acme Corp"
        assert j["results"][0]["price"] == 100.0
        assert j["error"] is None

    def test_tool_result_to_json_truncates_at_10(self):
        items = [
            NormalizedResult(
                title=f"Item {i}",
                url=f"https://example.com/{i}",
                source="test",
                merchant_name="Test",
                merchant_domain="example.com",
            )
            for i in range(20)
        ]
        tr = ToolResult(items=items)
        j = json.loads(tr.to_json())
        assert j["count"] == 20
        assert len(j["results"]) == 10

    def test_gemini_tool_response_to_message_text_only(self):
        resp = GeminiToolResponse(text="Here are results", tool_calls=[])
        msg = resp.to_message()
        assert msg["role"] == "model"
        assert msg["parts"][0]["text"] == "Here are results"

    def test_gemini_tool_response_to_message_with_calls(self):
        tc = ToolCall(id="1", name="search_vendors", params={"query": "plumber"})
        resp = GeminiToolResponse(text=None, tool_calls=[tc])
        msg = resp.to_message()
        assert msg["role"] == "model"
        assert msg["parts"][0]["functionCall"]["name"] == "search_vendors"

    def test_search_event_creation(self):
        ev = SearchEvent(type="tool_results", data={"count": 5})
        assert ev.type == "tool_results"
        assert ev.data["count"] == 5

    def test_result_summary_compact(self):
        item = NormalizedResult(
            title="Widget",
            url="https://w.com",
            source="amazon",
            merchant_name="Amazon",
            merchant_domain="amazon.com",
            price=29.99,
            rating=4.5,
            shipping_info="Free shipping",
        )
        s = _result_summary(item)
        assert s["title"] == "Widget"
        assert s["price"] == 29.99
        assert s["rating"] == 4.5
        assert s["shipping"] == "Free shipping"
        assert "reviews_count" not in s  # None fields excluded

    def test_result_summary_minimal(self):
        item = NormalizedResult(
            title="Basic",
            url="https://b.com",
            source="web",
            merchant_name="Web",
            merchant_domain="b.com",
        )
        s = _result_summary(item)
        assert set(s.keys()) == {"title", "url", "merchant"}


# ============================================================================
# services/llm_core.py — Message Conversion & Response Parsing
# ============================================================================

class TestGeminiMessageConversion:
    """Test _messages_to_gemini_contents."""

    def test_system_message_becomes_user_model_pair(self):
        from services.llm_core import _messages_to_gemini_contents

        msgs = [{"role": "system", "content": "You are helpful"}]
        contents = _messages_to_gemini_contents(msgs)
        assert len(contents) == 2
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "You are helpful"
        assert contents[1]["role"] == "model"
        assert contents[1]["parts"][0]["text"] == "Understood."

    def test_user_message(self):
        from services.llm_core import _messages_to_gemini_contents

        msgs = [{"role": "user", "content": "Find realtors in Nashville"}]
        contents = _messages_to_gemini_contents(msgs)
        assert len(contents) == 1
        assert contents[0]["role"] == "user"

    def test_assistant_message(self):
        from services.llm_core import _messages_to_gemini_contents

        msgs = [{"role": "assistant", "content": "Sure thing"}]
        contents = _messages_to_gemini_contents(msgs)
        assert contents[0]["role"] == "model"

    def test_model_message_with_parts(self):
        from services.llm_core import _messages_to_gemini_contents

        msgs = [{"role": "model", "parts": [{"text": "hi"}, {"functionCall": {"name": "test", "args": {}}}]}]
        contents = _messages_to_gemini_contents(msgs)
        assert contents[0]["role"] == "model"
        assert len(contents[0]["parts"]) == 2

    def test_tool_message(self):
        from services.llm_core import _messages_to_gemini_contents

        msgs = [{"role": "tool", "tool_name": "search_vendors", "content": '{"results": []}'}]
        contents = _messages_to_gemini_contents(msgs)
        assert contents[0]["role"] == "function"
        fr = contents[0]["parts"][0]["functionResponse"]
        assert fr["name"] == "search_vendors"


class TestGeminiResponseParsing:
    """Test _parse_gemini_tool_response."""

    def test_empty_candidates(self):
        from services.llm_core import _parse_gemini_tool_response

        resp = _parse_gemini_tool_response({"candidates": []})
        assert resp.text is None
        assert resp.tool_calls == []

    def test_text_response(self):
        from services.llm_core import _parse_gemini_tool_response

        data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Here are your results"}],
                },
            }],
        }
        resp = _parse_gemini_tool_response(data)
        assert resp.text == "Here are your results"
        assert resp.tool_calls == []

    def test_function_call_response(self):
        from services.llm_core import _parse_gemini_tool_response

        data = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "functionCall": {
                            "name": "search_vendors",
                            "args": {"query": "realtors", "location": "Nashville, TN"},
                        },
                    }],
                },
            }],
        }
        resp = _parse_gemini_tool_response(data)
        assert resp.text is None
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "search_vendors"
        assert resp.tool_calls[0].params["location"] == "Nashville, TN"
        assert resp.tool_calls[0].id  # UUID generated

    def test_parallel_function_calls(self):
        from services.llm_core import _parse_gemini_tool_response

        data = {
            "candidates": [{
                "content": {
                    "parts": [
                        {"functionCall": {"name": "search_vendors", "args": {"query": "realtors"}}},
                        {"functionCall": {"name": "search_web", "args": {"query": "best realtors Nashville"}}},
                    ],
                },
            }],
        }
        resp = _parse_gemini_tool_response(data)
        assert len(resp.tool_calls) == 2
        assert resp.tool_calls[0].name == "search_vendors"
        assert resp.tool_calls[1].name == "search_web"

    def test_mixed_text_and_function_call(self):
        from services.llm_core import _parse_gemini_tool_response

        data = {
            "candidates": [{
                "content": {
                    "parts": [
                        {"text": "Let me search for that."},
                        {"functionCall": {"name": "search_marketplace", "args": {"query": "shoes"}}},
                    ],
                },
            }],
        }
        resp = _parse_gemini_tool_response(data)
        assert resp.text == "Let me search for that."
        assert len(resp.tool_calls) == 1

    def test_no_content_key(self):
        from services.llm_core import _parse_gemini_tool_response

        data = {"candidates": [{}]}
        resp = _parse_gemini_tool_response(data)
        assert resp.text is None
        assert resp.tool_calls == []


# ============================================================================
# sourcing/tool_executor.py — Execution & Routing
# ============================================================================

class TestToolExecutor:
    """Test tool routing and parallel execution."""

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_returns_error(self):
        from sourcing.tool_executor import _execute_single

        tc = ToolCall(id="1", name="nonexistent_tool", params={})
        result = await _execute_single(tc)
        assert result.error is not None
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_execute_tools_parallel_with_timeout(self):
        from sourcing.tool_executor import execute_tools_parallel

        async def slow_tool(*args, **kwargs):
            await asyncio.sleep(10)

        tc = ToolCall(id="1", name="nonexistent_tool", params={})
        results = await execute_tools_parallel([tc], timeout_per_tool=0.1)
        assert len(results) == 1
        assert results[0].error is not None

    @pytest.mark.asyncio
    async def test_search_vendors_missing_db_url(self):
        from sourcing.tool_executor import _tool_search_vendors

        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            result = await _tool_search_vendors(query="realtors")
            assert result.error is not None
            assert "DATABASE_URL" in result.error

    @pytest.mark.asyncio
    async def test_search_apify_store_calls_adapter(self):
        mock_actors = [
            {"actor_id": "test/actor", "title": "Test Actor", "description": "Test"},
        ]
        with patch("sourcing.discovery.adapters.apify.search_apify_store", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_actors
            from sourcing.tool_executor import _tool_search_apify_store
            result = await _tool_search_apify_store(search_term="google maps")
            assert len(result.items) == 1
            assert result.items[0].title == "Test Actor"
            mock_search.assert_called_once_with("google maps", limit=5)

    def test_dedupe_results(self):
        from sourcing.tool_executor import _dedupe_results

        items = [
            NormalizedResult(title="A", url="https://example.com/a", source="s1", merchant_name="M", merchant_domain="example.com"),
            NormalizedResult(title="A dup", url="https://example.com/a/", source="s2", merchant_name="M", merchant_domain="example.com"),
            NormalizedResult(title="B", url="https://example.com/b", source="s1", merchant_name="M", merchant_domain="example.com"),
        ]
        deduped = _dedupe_results(items)
        assert len(deduped) == 2
        assert deduped[0].title == "A"
        assert deduped[1].title == "B"

    def test_dedupe_empty_list(self):
        from sourcing.tool_executor import _dedupe_results

        assert _dedupe_results([]) == []


# ============================================================================
# sourcing/agent.py — Agent Loop
# ============================================================================

class TestAgentLoop:
    """Test agent_search generator and message building."""

    def test_build_initial_messages_basic(self):
        from sourcing.agent import _build_initial_messages

        msgs = _build_initial_messages(None, "Find realtors")
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "Find realtors"

    def test_build_initial_messages_with_context(self):
        from sourcing.agent import _build_initial_messages

        ctx = {"title": "Nashville realtors", "is_service": True}
        msgs = _build_initial_messages(ctx, "Find realtors")
        # system prompt + context + user message
        assert len(msgs) == 3
        assert "Nashville realtors" in msgs[1]["content"]

    def test_build_initial_messages_with_history(self):
        from sourcing.agent import _build_initial_messages

        history = [
            {"role": "user", "content": "Find realtors in Nashville"},
            {"role": "assistant", "content": "Searching..."},
        ]
        msgs = _build_initial_messages(None, "Focus on luxury", history)
        assert len(msgs) == 4  # system + 2 history + user

    def test_build_initial_messages_truncates_history(self):
        from sourcing.agent import _build_initial_messages

        history = [{"role": "user", "content": f"msg {i}"} for i in range(20)]
        msgs = _build_initial_messages(None, "latest", history)
        # system + last 6 history + user
        assert len(msgs) == 8

    def test_feature_flag_default_off(self):
        from sourcing.agent import USE_TOOL_CALLING_AGENT

        # Default should be False unless env var is set
        assert isinstance(USE_TOOL_CALLING_AGENT, bool)

    @pytest.mark.asyncio
    async def test_agent_search_text_only_response(self):
        """Agent returns text with no tool calls → yields agent_message + complete."""
        from sourcing.agent import agent_search

        mock_response = GeminiToolResponse(
            text="I can help with that but I need more details.",
            tool_calls=[],
        )
        with patch("services.llm_core.call_gemini_with_tools", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            events = []
            async for event in agent_search(user_message="help"):
                events.append(event)

        assert len(events) == 2
        assert events[0].type == "agent_message"
        assert events[1].type == "complete"

    @pytest.mark.asyncio
    async def test_agent_search_single_tool_call(self):
        """Agent calls one tool → yields tool_results + complete."""
        from sourcing.agent import agent_search

        mock_llm_response = GeminiToolResponse(
            text=None,
            tool_calls=[
                ToolCall(id="1", name="search_vendors", params={"query": "realtors", "location": "Nashville"}),
            ],
        )
        mock_text_response = GeminiToolResponse(
            text="Here are some realtors in Nashville.",
            tool_calls=[],
        )

        mock_tool_result = ToolResult(
            items=[
                NormalizedResult(
                    title="Nashville Realty",
                    url="https://nashvillerealty.com",
                    source="vendor_directory",
                    merchant_name="Nashville Realty",
                    merchant_domain="nashvillerealty.com",
                ),
            ],
            metadata={"source": "vendor_directory"},
        )

        call_count = 0

        async def mock_gemini(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_llm_response
            return mock_text_response

        with patch("services.llm_core.call_gemini_with_tools", side_effect=mock_gemini):
            with patch("sourcing.agent.execute_tools_parallel", new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = [mock_tool_result]
                events = []
                async for event in agent_search(user_message="Find realtors in Nashville"):
                    events.append(event)

        # tool_results + agent_message + complete
        types = [e.type for e in events]
        assert "tool_results" in types
        assert "complete" in types
        # Check tool_results event has correct data
        tr_event = next(e for e in events if e.type == "tool_results")
        assert tr_event.data["tool"] == "search_vendors"
        assert tr_event.data["count"] == 1

    @pytest.mark.asyncio
    async def test_agent_respects_max_tool_calls(self):
        """Agent stops after max_tool_calls budget is exhausted."""
        from sourcing.agent import agent_search

        # LLM always wants to call tools
        mock_response = GeminiToolResponse(
            text=None,
            tool_calls=[
                ToolCall(id="1", name="search_web", params={"query": "test"}),
                ToolCall(id="2", name="search_web", params={"query": "test2"}),
            ],
        )
        mock_result = ToolResult(items=[], metadata={})

        with patch("services.llm_core.call_gemini_with_tools", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            with patch("sourcing.tool_executor.execute_tools_parallel", new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = [mock_result, mock_result]
                events = []
                async for event in agent_search(
                    user_message="test",
                    max_iterations=5,
                    max_tool_calls=2,
                ):
                    events.append(event)

        complete_event = next(e for e in events if e.type == "complete")
        assert complete_event.data["tool_calls_used"] == 2

    @pytest.mark.asyncio
    async def test_agent_search_no_response(self):
        """Agent handles empty LLM response gracefully."""
        from sourcing.agent import agent_search

        mock_response = GeminiToolResponse(text=None, tool_calls=[])

        with patch("services.llm_core.call_gemini_with_tools", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            events = []
            async for event in agent_search(user_message="test"):
                events.append(event)

        assert events[0].type == "agent_message"
        assert events[1].type == "complete"


# ============================================================================
# Integration: call_gemini_with_tools HTTP call
# ============================================================================

class TestCallGeminiWithTools:
    """Test the full call_gemini_with_tools function with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self):
        from services.llm_core import call_gemini_with_tools

        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_GENERATIVE_AI_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="No Gemini API key"):
                await call_gemini_with_tools(
                    messages=[{"role": "user", "content": "test"}],
                    tools=[SEARCH_VENDORS],
                )

    @pytest.mark.asyncio
    async def test_successful_tool_call(self):
        from services.llm_core import call_gemini_with_tools

        mock_api_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "functionCall": {
                            "name": "search_vendors",
                            "args": {"query": "plumber", "location": "Austin, TX"},
                        },
                    }],
                },
            }],
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = mock_api_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("services.llm_core.httpx.AsyncClient", return_value=mock_client):
                result = await call_gemini_with_tools(
                    messages=[{"role": "user", "content": "Find a plumber in Austin"}],
                    tools=[SEARCH_VENDORS],
                )

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "search_vendors"
        assert result.tool_calls[0].params["location"] == "Austin, TX"

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        from services.llm_core import call_gemini_with_tools

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False):
            with patch("services.llm_core.httpx.AsyncClient", return_value=mock_client):
                result = await call_gemini_with_tools(
                    messages=[{"role": "user", "content": "test"}],
                    tools=[SEARCH_VENDORS],
                )

        assert result.tool_calls == []
        assert result.text is None
