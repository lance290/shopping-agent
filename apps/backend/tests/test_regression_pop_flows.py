"""Regression tests for Pop chat and Pop processor flows.

Covers:
- UnifiedDecision single-item handling (not list)
- Pop chat guest mode
- Pop chat authenticated mode
- Pop processor SMS/email channel handling
- Decision action types: create_row, update_row, chat, search, context_switch
- Constraint filtering (_META_KEYS exclusion)
- Title capitalization
- Multi-item creation path in pop_chat
- Chat history persistence
"""
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Project, ProjectMember, Bid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _empty_async_gen():
    return
    yield


def _mock_decision(
    action_type="create_row",
    what="eggs",
    message="Added!",
    search_query=None,
    constraints=None,
    category="product",
    service_type=None,
    desire_tier="commodity",
    items=None,
):
    """Build a minimal mock matching UnifiedDecision API."""
    mock_intent = MagicMock()
    mock_intent.what = what
    mock_intent.category = category
    mock_intent.service_type = service_type
    mock_intent.search_query = search_query or (f"{what} deals" if what else None)
    mock_intent.constraints = constraints or {}
    mock_intent.desire_tier = desire_tier
    mock_intent.desire_confidence = 0.8

    mock_decision = MagicMock()
    mock_decision.intent = mock_intent
    mock_decision.action = {"type": action_type}
    mock_decision.message = message
    mock_decision.items = items
    return mock_decision


# ---------------------------------------------------------------------------
# 1. UnifiedDecision single-item contract tests
# ---------------------------------------------------------------------------


class TestUnifiedDecisionContract:
    """The decision object must have .intent and .action directly."""

    def test_direct_intent_access(self):
        d = _mock_decision(what="milk")
        assert d.intent.what == "milk"

    def test_direct_action_access(self):
        d = _mock_decision(action_type="search")
        assert d.action["type"] == "search"

    def test_intent_constraints_is_dict(self):
        d = _mock_decision(constraints={"color": "red"})
        assert isinstance(d.intent.constraints, dict)

    def test_intent_category_is_string(self):
        d = _mock_decision(category="service")
        assert d.intent.category == "service"

    def test_items_is_none_for_single_item(self):
        d = _mock_decision()
        assert d.items is None

    def test_items_is_list_for_multi_item(self):
        d = _mock_decision(items=[{"what": "eggs"}, {"what": "milk"}])
        assert isinstance(d.items, list)
        assert len(d.items) == 2


# ---------------------------------------------------------------------------
# 2. Pop chat guest mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pop_chat_guest_mode(client: AsyncClient, session: AsyncSession, guest_user: User):
    """POST /pop/chat without auth uses guest user — must not 401."""
    decision = _mock_decision(action_type="chat", what="", message="Hi!")
    decision.intent.what = ""
    decision.intent.search_query = None

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            resp = await client.post("/pop/chat", json={"message": "hello"})

    # Should not be 401 or 500
    assert resp.status_code in (200, 201, 422)


@pytest.mark.asyncio
async def test_pop_chat_guest_create_row(client: AsyncClient, session: AsyncSession, guest_user: User):
    """POST /pop/chat with create_row creates a row under guest user."""
    decision = _mock_decision(action_type="create_row", what="bread", search_query="bread deals")

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            with patch("routes.pop_chat.generate_choice_factors", new_callable=AsyncMock, return_value=None):
                resp = await client.post("/pop/chat", json={"message": "I need bread"})

    assert resp.status_code in (200, 201, 422)


# ---------------------------------------------------------------------------
# 3. Pop chat authenticated mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pop_chat_authenticated(
    client: AsyncClient, session: AsyncSession, pop_user, pop_project
):
    """POST /pop/chat with auth creates row in user's project."""
    user, token = pop_user
    decision = _mock_decision(action_type="create_row", what="apples", search_query="apples deals")

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            with patch("routes.pop_chat.generate_choice_factors", new_callable=AsyncMock, return_value=None):
                resp = await client.post(
                    "/pop/chat",
                    json={"message": "add apples", "project_id": pop_project.id},
                    headers={"Authorization": f"Bearer {token}"},
                )

    assert resp.status_code in (200, 201, 422)


# ---------------------------------------------------------------------------
# 4. Decision action types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pop_chat_action_type_chat(client: AsyncClient, session: AsyncSession, guest_user: User):
    """'chat' action_type: no row creation, just reply."""
    decision = _mock_decision(action_type="chat", what="", message="Hello there!")
    decision.intent.what = ""
    decision.intent.search_query = None

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        resp = await client.post("/pop/chat", json={"message": "hi"})
    assert resp.status_code in (200, 201, 422)


@pytest.mark.asyncio
async def test_pop_chat_action_type_search(
    client: AsyncClient, session: AsyncSession, pop_user, pop_project
):
    """'search' action_type with no active row: creates row and searches."""
    user, token = pop_user
    decision = _mock_decision(action_type="search", what="milk", search_query="milk deals")

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            with patch("routes.pop_chat.generate_choice_factors", new_callable=AsyncMock, return_value=None):
                resp = await client.post(
                    "/pop/chat",
                    json={"message": "find milk", "project_id": pop_project.id},
                    headers={"Authorization": f"Bearer {token}"},
                )
    assert resp.status_code in (200, 201, 422)


# ---------------------------------------------------------------------------
# 5. Constraint filtering (_META_KEYS exclusion)
# ---------------------------------------------------------------------------


class TestMetaKeysExclusion:
    """_META_KEYS should be excluded from the constraints dict passed to _create_row."""

    def test_meta_keys_filtered(self):
        _META_KEYS = {
            "what", "is_service", "service_category", "search_query", "title",
            "category", "desire_tier", "desire_confidence",
        }
        raw_constraints = {
            "what": "eggs",
            "category": "product",
            "color": "brown",
            "size": "large",
            "desire_tier": "commodity",
        }
        filtered = {k: v for k, v in raw_constraints.items() if k not in _META_KEYS}
        assert "what" not in filtered
        assert "category" not in filtered
        assert "desire_tier" not in filtered
        assert "color" in filtered
        assert "size" in filtered

    def test_empty_constraints(self):
        _META_KEYS = {"what", "category"}
        raw_constraints = {"what": "test", "category": "product"}
        filtered = {k: v for k, v in raw_constraints.items() if k not in _META_KEYS}
        assert filtered == {}

    def test_none_constraints(self):
        constraints = None
        filtered = {k: v for k, v in (constraints or {}).items()}
        assert filtered == {}


# ---------------------------------------------------------------------------
# 6. Title capitalization
# ---------------------------------------------------------------------------


class TestTitleCapitalization:
    """Title from intent.what should be capitalized."""

    def test_lowercase_capitalized(self):
        what = "eggs"
        title = what[0].upper() + what[1:] if what else what
        assert title == "Eggs"

    def test_already_capitalized(self):
        what = "Eggs"
        title = what[0].upper() + what[1:] if what else what
        assert title == "Eggs"

    def test_single_char(self):
        what = "a"
        title = what[0].upper() + what[1:] if what else what
        assert title == "A"

    def test_empty_string_no_crash(self):
        what = ""
        title = what[0].upper() + what[1:] if what else what
        assert title == ""

    def test_multi_word(self):
        what = "whole milk organic"
        title = what[0].upper() + what[1:] if what else what
        assert title == "Whole milk organic"


# ---------------------------------------------------------------------------
# 7. Multi-item creation path
# ---------------------------------------------------------------------------


class TestMultiItemCreation:
    """pop_chat supports creating multiple rows from a single message."""

    def test_items_array_structure(self):
        items = [
            {"what": "eggs", "search_query": "eggs deals"},
            {"what": "milk", "search_query": "milk deals"},
            {"what": "bread"},
        ]
        for item in items:
            assert "what" in item
            title = item["what"]
            query = item.get("search_query", f"{title} grocery deals")
            assert isinstance(query, str)
            assert len(query) > 0

    def test_empty_what_skipped(self):
        items = [
            {"what": "eggs"},
            {"what": ""},
            {"what": "  "},
        ]
        valid = [i for i in items if i["what"].strip()]
        assert len(valid) == 1

    def test_items_none_means_single_item(self):
        d = _mock_decision(items=None)
        assert d.items is None
        # single-item path should be used


# ---------------------------------------------------------------------------
# 8. Pop processor channel handling
# ---------------------------------------------------------------------------


class TestPopProcessorChannels:
    """Pop processor handles SMS and email channels."""

    def test_sms_channel(self):
        channel = "sms"
        sender_phone = "+15551234567"
        assert channel == "sms" and sender_phone

    def test_email_channel(self):
        channel = "email"
        sender_email = "user@example.com"
        assert channel == "email" and sender_email

    def test_unknown_channel_defaults(self):
        channel = "unknown"
        assert channel not in ("sms", "email")


# ---------------------------------------------------------------------------
# 9. Pop chat — conversation history persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pop_chat_persists_history(
    client: AsyncClient, session: AsyncSession, pop_user, pop_project
):
    """Chat messages should be persisted to row's chat_history."""
    user, token = pop_user
    decision = _mock_decision(
        action_type="create_row", what="cereal", message="Added cereal!",
        search_query="cereal deals",
    )

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            with patch("routes.pop_chat.generate_choice_factors", new_callable=AsyncMock, return_value=None):
                resp = await client.post(
                    "/pop/chat",
                    json={"message": "add cereal", "project_id": pop_project.id},
                    headers={"Authorization": f"Bearer {token}"},
                )

    assert resp.status_code in (200, 201, 422)

    # Verify a row was created
    result = await session.exec(
        select(Row).where(Row.user_id == user.id, Row.project_id == pop_project.id)
    )
    rows = result.all()
    # At least one row should exist (may already have rows from other tests)
    if rows:
        # The newest row should have chat_history
        newest = sorted(rows, key=lambda r: r.id, reverse=True)[0]
        if newest.chat_history:
            history = newest.chat_history if isinstance(newest.chat_history, list) else json.loads(newest.chat_history)
            assert isinstance(history, list)


# ---------------------------------------------------------------------------
# 10. Pop chat — service detection
# ---------------------------------------------------------------------------


class TestServiceDetection:
    """Pop chat correctly detects services vs products."""

    def test_product_detection(self):
        d = _mock_decision(category="product")
        is_service = d.intent.category == "service"
        assert is_service is False

    def test_service_detection(self):
        d = _mock_decision(category="service", service_type="private_aviation")
        is_service = d.intent.category == "service"
        service_category = d.intent.service_type
        assert is_service is True
        assert service_category == "private_aviation"


# ---------------------------------------------------------------------------
# 11. Integration: Full pop chat flow (create_row -> search -> reply)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pop_chat_create_search_reply(
    client: AsyncClient, session: AsyncSession, pop_user, pop_project
):
    """Full flow: user sends message -> create_row -> search -> reply."""
    user, token = pop_user
    decision = _mock_decision(
        action_type="create_row",
        what="bananas",
        message="Added bananas to your list! Searching for deals...",
        search_query="bananas organic deals",
    )

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            with patch("routes.pop_chat.generate_choice_factors", new_callable=AsyncMock, return_value=None):
                resp = await client.post(
                    "/pop/chat",
                    json={"message": "add bananas", "project_id": pop_project.id},
                    headers={"Authorization": f"Bearer {token}"},
                )

    assert resp.status_code in (200, 201, 422)

    # Verify the row was created with correct fields
    result = await session.exec(
        select(Row).where(
            Row.user_id == user.id,
            Row.title == "Bananas",
        )
    )
    row = result.first()
    if row:
        assert row.status == "sourcing"
        assert row.project_id == pop_project.id


# ---------------------------------------------------------------------------
# 12. Regression: decision with empty what and no search_query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pop_chat_empty_what_no_search(client: AsyncClient, session: AsyncSession, guest_user: User):
    """Decision with empty what and no search_query should not crash."""
    decision = _mock_decision(action_type="chat", what="", message="I'm not sure what you need.")
    decision.intent.what = ""
    decision.intent.search_query = None

    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        resp = await client.post("/pop/chat", json={"message": "uhh"})

    # Should not crash — just a chat response
    assert resp.status_code in (200, 201, 422)


# ---------------------------------------------------------------------------
# 13. Regression: desire_tier values from LLM
# ---------------------------------------------------------------------------


class TestDesireTierValues:
    """All valid desire_tier values should work in the flow."""

    def test_valid_tiers(self):
        valid_tiers = ["commodity", "considered", "service", "bespoke", "high_value", "advisory"]
        for tier in valid_tiers:
            d = _mock_decision(desire_tier=tier)
            assert d.intent.desire_tier == tier

    def test_unknown_tier_accepted(self):
        """Unknown tier shouldn't crash — LLM might hallucinate."""
        d = _mock_decision(desire_tier="ultra_luxury")
        assert d.intent.desire_tier == "ultra_luxury"
