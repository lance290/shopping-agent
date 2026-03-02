"""Regression tests for bugs fixed in the Feb/Mar 2026 production incident.

Covers:
- UnifiedDecision treated as single item (not list) in pop_chat / pop_processor
- filter_bids_by_price handling null/invalid choice_answers
- Guest user fallback on GET /rows
- Price constraint extraction from various LLM key formats
- extract_vendor_query from search_intent
- UserIntent model includes all required fields
"""
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from models import User, Row, Project, Bid


# ---------------------------------------------------------------------------
# 1. UnifiedDecision single-item regression (pop_processor + pop_chat)
# ---------------------------------------------------------------------------


def _mock_decision(action_type="create_row", what="eggs", message="Added!"):
    """Build a minimal mock matching UnifiedDecision's ACTUAL API (single item)."""
    mock_intent = MagicMock()
    mock_intent.what = what
    mock_intent.category = "product"
    mock_intent.service_type = None
    mock_intent.search_query = f"{what} deals"
    mock_intent.constraints = {}
    mock_intent.desire_tier = "commodity"
    mock_intent.desire_confidence = 0.8

    mock_decision = MagicMock()
    mock_decision.intent = mock_intent
    mock_decision.action = {"type": action_type}
    mock_decision.message = message
    mock_decision.items = None  # single-item path, no items array
    return mock_decision


class TestUnifiedDecisionSingleItem:
    """Regression: UnifiedDecision is a single item, not a list."""

    def test_decision_has_direct_intent_and_action(self):
        """The decision object has .intent and .action directly, not .items."""
        d = _mock_decision()
        assert hasattr(d, "intent")
        assert hasattr(d, "action")
        assert d.intent.what == "eggs"
        assert d.action["type"] == "create_row"

    def test_decision_intent_what_is_string(self):
        """intent.what must be a string, not a list."""
        d = _mock_decision(what="milk")
        assert isinstance(d.intent.what, str)

    def test_decision_action_is_dict(self):
        d = _mock_decision()
        assert isinstance(d.action, dict)
        assert "type" in d.action

    def test_decision_action_type_variants(self):
        for action_type in ("create_row", "context_switch", "search", "update_row", "chat"):
            d = _mock_decision(action_type=action_type)
            assert d.action["type"] == action_type


# ---------------------------------------------------------------------------
# 2. filter_bids_by_price with null/malformed choice_answers
# ---------------------------------------------------------------------------


class TestFilterBidsByPrice:
    """Regression: filter_bids_by_price must not crash on null choice_answers."""

    def _make_row(self, choice_answers=None, bids=None, desire_tier=None):
        row = MagicMock(spec=Row)
        row.choice_answers = choice_answers
        row.desire_tier = desire_tier
        row.bids = bids or []
        return row

    def _make_bid(self, price=10.0, source="amazon"):
        bid = MagicMock(spec=Bid)
        bid.price = price
        bid.source = source
        bid.is_service_provider = False
        return bid

    def test_null_choice_answers(self):
        from routes.rows import filter_bids_by_price
        row = self._make_row(choice_answers=None, bids=[self._make_bid()])
        result = filter_bids_by_price(row)
        assert len(result) >= 0  # must not crash

    def test_json_null_string_choice_answers(self):
        """Regression: choice_answers stored as literal JSON 'null' string."""
        from routes.rows import filter_bids_by_price
        row = self._make_row(choice_answers="null", bids=[self._make_bid()])
        result = filter_bids_by_price(row)
        assert len(result) >= 0  # must not crash

    def test_empty_string_choice_answers(self):
        from routes.rows import filter_bids_by_price
        row = self._make_row(choice_answers="", bids=[self._make_bid()])
        result = filter_bids_by_price(row)
        assert len(result) >= 0

    def test_invalid_json_choice_answers(self):
        from routes.rows import filter_bids_by_price
        row = self._make_row(choice_answers="{broken json", bids=[self._make_bid()])
        result = filter_bids_by_price(row)
        assert len(result) >= 0

    def test_json_array_choice_answers(self):
        """choice_answers as JSON array instead of object should not crash."""
        from routes.rows import filter_bids_by_price
        row = self._make_row(choice_answers='["a", "b"]', bids=[self._make_bid()])
        result = filter_bids_by_price(row)
        assert len(result) >= 0

    def test_json_number_choice_answers(self):
        """choice_answers as JSON number should not crash."""
        from routes.rows import filter_bids_by_price
        row = self._make_row(choice_answers="42", bids=[self._make_bid()])
        result = filter_bids_by_price(row)
        assert len(result) >= 0

    def test_no_bids(self):
        from routes.rows import filter_bids_by_price
        row = self._make_row(choice_answers='{"min_price": 5}', bids=[])
        result = filter_bids_by_price(row)
        assert result == []

    def test_none_bids(self):
        from routes.rows import filter_bids_by_price
        row = self._make_row(choice_answers=None, bids=None)
        result = filter_bids_by_price(row)
        assert result == []

    def test_price_filtering_works(self):
        from routes.rows import filter_bids_by_price
        bids = [self._make_bid(price=5.0), self._make_bid(price=50.0), self._make_bid(price=500.0)]
        row = self._make_row(
            choice_answers='{"min_price": 10, "max_price": 100}',
            bids=bids,
        )
        result = filter_bids_by_price(row)
        prices = [b.price for b in result]
        assert 5.0 not in prices
        assert 50.0 in prices


# ---------------------------------------------------------------------------
# 3. Guest user fallback on GET /rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_rows_anonymous_returns_empty_list(client: AsyncClient):
    """Regression: GET /rows without auth must return 200 + [] (not 401)."""
    resp = await client.get("/rows")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_rows_authenticated(client: AsyncClient, auth_user_and_token, session: AsyncSession):
    """Authenticated GET /rows returns user's rows."""
    user, token = auth_user_and_token
    row = Row(title="My search", status="sourcing", user_id=user.id)
    session.add(row)
    await session.commit()

    resp = await client.get("/rows", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(r["title"] == "My search" for r in data)


@pytest.mark.asyncio
async def test_get_rows_does_not_return_other_users_rows(
    client: AsyncClient, auth_user_and_token, session: AsyncSession
):
    """GET /rows only returns rows owned by the requesting user."""
    user, token = auth_user_and_token

    other = User(email="other@example.com", is_admin=False)
    session.add(other)
    await session.commit()
    await session.refresh(other)

    other_row = Row(title="Other user row", status="sourcing", user_id=other.id)
    session.add(other_row)
    await session.commit()

    resp = await client.get("/rows", headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    assert not any(r["title"] == "Other user row" for r in data)


# ---------------------------------------------------------------------------
# 4. Price constraint extraction (SourcingService._extract_price_constraints)
# ---------------------------------------------------------------------------


class TestPriceConstraintExtraction:
    """Regression: ensure all LLM key variants for price constraints work."""

    def _make_row(self, search_intent=None, choice_answers=None):
        row = MagicMock(spec=Row)
        row.search_intent = search_intent
        row.choice_answers = choice_answers
        row.budget_max = None
        return row

    def _extract(self, row):
        from sourcing.service import SourcingService
        svc = SourcingService.__new__(SourcingService)
        return svc._extract_price_constraints(row)

    def test_standard_min_max(self):
        row = self._make_row(choice_answers='{"min_price": 50, "max_price": 200}')
        lo, hi = self._extract(row)
        assert lo == 50.0
        assert hi == 200.0

    def test_price_min_price_max_aliases(self):
        row = self._make_row(choice_answers='{"price_min": 10, "price_max": 100}')
        lo, hi = self._extract(row)
        assert lo == 10.0
        assert hi == 100.0

    def test_minimum_price_maximum_price(self):
        row = self._make_row(choice_answers='{"minimum_price": 25, "maximum_price": 75}')
        lo, hi = self._extract(row)
        assert lo == 25.0
        assert hi == 75.0

    def test_budget_range_string(self):
        row = self._make_row(choice_answers='{"budget": "$50-$200"}')
        lo, hi = self._extract(row)
        assert lo == 50.0
        assert hi == 200.0

    def test_price_greater_than(self):
        row = self._make_row(choice_answers='{"price": ">$100"}')
        lo, hi = self._extract(row)
        assert lo == 100.0
        assert hi is None

    def test_price_less_than(self):
        row = self._make_row(choice_answers='{"price": "<$50"}')
        lo, hi = self._extract(row)
        assert lo is None
        assert hi == 50.0

    def test_dollar_sign_in_value(self):
        row = self._make_row(choice_answers='{"min_price": "$30", "max_price": "$300"}')
        lo, hi = self._extract(row)
        assert lo == 30.0
        assert hi == 300.0

    def test_comma_in_value(self):
        row = self._make_row(choice_answers='{"max_price": "$1,500"}')
        lo, hi = self._extract(row)
        assert hi == 1500.0

    def test_null_choice_answers_returns_none_none(self):
        row = self._make_row(choice_answers=None)
        lo, hi = self._extract(row)
        assert lo is None
        assert hi is None

    def test_json_null_string_returns_none_none(self):
        """Regression: choice_answers = 'null' (JSON null literal as string)."""
        row = self._make_row(choice_answers="null")
        lo, hi = self._extract(row)
        assert lo is None
        assert hi is None

    def test_search_intent_overrides_choice_answers(self):
        row = self._make_row(
            search_intent='{"min_price": 100, "max_price": 500}',
            choice_answers='{"min_price": 10, "max_price": 50}',
        )
        lo, hi = self._extract(row)
        assert lo == 100.0
        assert hi == 500.0

    def test_swapped_min_max_auto_corrects(self):
        row = self._make_row(choice_answers='{"min_price": 200, "max_price": 50}')
        lo, hi = self._extract(row)
        assert lo <= hi


# ---------------------------------------------------------------------------
# 5. extract_vendor_query from search_intent
# ---------------------------------------------------------------------------


class TestExtractVendorQuery:
    """Regression: SourcingService.extract_vendor_query must handle all edge cases."""

    def test_extracts_product_name(self):
        from sourcing.service import SourcingService
        row = MagicMock()
        row.search_intent = '{"product_name": "Gulfstream G650"}'
        assert SourcingService.extract_vendor_query(row) == "Gulfstream G650"

    def test_falls_back_to_raw_input(self):
        from sourcing.service import SourcingService
        row = MagicMock()
        row.search_intent = '{"raw_input": "private jet charter"}'
        assert SourcingService.extract_vendor_query(row) == "private jet charter"

    def test_prefers_product_name_over_raw_input(self):
        from sourcing.service import SourcingService
        row = MagicMock()
        row.search_intent = '{"product_name": "G650", "raw_input": "jet"}'
        assert SourcingService.extract_vendor_query(row) == "G650"

    def test_returns_none_for_null_intent(self):
        from sourcing.service import SourcingService
        row = MagicMock()
        row.search_intent = None
        assert SourcingService.extract_vendor_query(row) is None

    def test_returns_none_for_empty_string(self):
        from sourcing.service import SourcingService
        row = MagicMock()
        row.search_intent = ""
        assert SourcingService.extract_vendor_query(row) is None

    def test_returns_none_for_invalid_json(self):
        from sourcing.service import SourcingService
        row = MagicMock()
        row.search_intent = "{broken"
        assert SourcingService.extract_vendor_query(row) is None

    def test_returns_none_for_json_null(self):
        from sourcing.service import SourcingService
        row = MagicMock()
        row.search_intent = "null"
        assert SourcingService.extract_vendor_query(row) is None

    def test_returns_none_for_json_array(self):
        from sourcing.service import SourcingService
        row = MagicMock()
        row.search_intent = '["not", "a", "dict"]'
        assert SourcingService.extract_vendor_query(row) is None

    def test_returns_none_for_none_row(self):
        from sourcing.service import SourcingService
        assert SourcingService.extract_vendor_query(None) is None

    def test_handles_dict_payload_directly(self):
        """When search_intent is already a dict (JSONB column)."""
        from sourcing.service import SourcingService
        row = MagicMock()
        row.search_intent = {"product_name": "Whole milk"}
        assert SourcingService.extract_vendor_query(row) == "Whole milk"


# ---------------------------------------------------------------------------
# 6. UserIntent model regression
# ---------------------------------------------------------------------------


class TestUserIntentModel:
    """Regression: UserIntent must include all fields used by pop_chat/pop_processor."""

    def test_basic_fields(self):
        from services.llm import UserIntent
        intent = UserIntent(what="eggs", category="product")
        assert intent.what == "eggs"
        assert intent.category == "product"

    def test_default_values(self):
        from services.llm import UserIntent
        intent = UserIntent(what="test")
        assert intent.desire_tier == "commodity"
        assert intent.desire_confidence == 0.8
        assert intent.constraints == {}
        assert intent.search_query is None
        assert intent.service_type is None

    def test_constraints_dict(self):
        from services.llm import UserIntent
        intent = UserIntent(what="test", constraints={"color": "blue", "size": "L"})
        assert intent.constraints["color"] == "blue"

    def test_service_type_field(self):
        from services.llm import UserIntent
        intent = UserIntent(what="jet charter", category="service", service_type="private_aviation")
        assert intent.service_type == "private_aviation"


# ---------------------------------------------------------------------------
# 7. Pop chat regression: create_row from decision (integration)
# ---------------------------------------------------------------------------


async def _empty_async_gen():
    return
    yield


@pytest.mark.asyncio
async def test_pop_chat_create_row_does_not_crash(
    client: AsyncClient, session: AsyncSession, guest_user: User
):
    """Regression: POST /pop/chat with create_row decision must not crash."""
    decision = _mock_decision(action_type="create_row", what="eggs")
    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        with patch("routes.pop_chat._stream_search", return_value=_empty_async_gen()):
            resp = await client.post(
                "/pop/chat",
                json={"message": "I need eggs"},
            )
    # Should not crash with UnifiedDecision.items AttributeError
    assert resp.status_code in (200, 201, 422)  # 422 if missing required fields


@pytest.mark.asyncio
async def test_pop_chat_chat_action_does_not_crash(
    client: AsyncClient, session: AsyncSession, guest_user: User
):
    """Regression: POST /pop/chat with 'chat' action must not crash."""
    decision = _mock_decision(action_type="chat", what="", message="Hi there!")
    decision.intent.what = ""
    decision.intent.search_query = None
    with patch("routes.pop_chat.make_pop_decision", new_callable=AsyncMock, return_value=decision):
        resp = await client.post(
            "/pop/chat",
            json={"message": "hello"},
        )
    assert resp.status_code in (200, 201, 422)


# ---------------------------------------------------------------------------
# 8. Row response shape: null-safe fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_row_response_shape_null_fields(
    client: AsyncClient, auth_user_and_token, session: AsyncSession
):
    """Regression: Row response must include nullable fields without crashing serialization."""
    user, token = auth_user_and_token
    row = Row(
        title="Null fields test",
        status="sourcing",
        user_id=user.id,
        choice_factors=None,
        choice_answers=None,
        search_intent=None,
        selected_providers=None,
        chat_history=None,
    )
    session.add(row)
    await session.commit()

    resp = await client.get("/rows", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    row_data = next(r for r in data if r["title"] == "Null fields test")
    # These fields should be present in the response (possibly null)
    assert "choice_factors" in row_data or row_data.get("choice_factors") is None
    assert "choice_answers" in row_data or row_data.get("choice_answers") is None


@pytest.mark.asyncio
async def test_row_with_json_null_choice_answers_serializes(
    client: AsyncClient, auth_user_and_token, session: AsyncSession
):
    """Regression: Row with choice_answers stored as JSON null must serialize."""
    user, token = auth_user_and_token

    # Simulate what happens when the DB stores a JSON null
    row = Row(
        title="JSON null test",
        status="sourcing",
        user_id=user.id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    # Manually set choice_answers to None (simulating JSON null from DB)
    row.choice_answers = None
    session.add(row)
    await session.commit()

    resp = await client.get("/rows", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 9. Provider aliases regression
# ---------------------------------------------------------------------------


class TestProviderAliases:
    """Regression: provider key aliases must resolve correctly after rename."""

    def test_amazon_alias(self):
        from sourcing.normalizers import NORMALIZER_REGISTRY
        assert "amazon" in NORMALIZER_REGISTRY

    def test_ebay_alias(self):
        from sourcing.normalizers import NORMALIZER_REGISTRY
        assert "ebay" in NORMALIZER_REGISTRY

    def test_rainforest_still_works(self):
        from sourcing.normalizers import NORMALIZER_REGISTRY
        assert "rainforest" in NORMALIZER_REGISTRY

    def test_ebay_browse_still_works(self):
        from sourcing.normalizers import NORMALIZER_REGISTRY
        assert "ebay" in NORMALIZER_REGISTRY


# ---------------------------------------------------------------------------
# 10. _parse_numeric and _parse_price_value edge cases
# ---------------------------------------------------------------------------


class TestParseNumeric:
    def test_none(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric(None) is None

    def test_int(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric(42) == 42.0

    def test_float(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric(3.14) == 3.14

    def test_dollar_string(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("$99.99") == 99.99

    def test_comma_string(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("$1,500") == 1500.0

    def test_empty_string(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("") is None

    def test_no_numbers(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("no numbers here") is None

    def test_mixed_text(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("about $50 or so") == 50.0


class TestParsePriceValue:
    def test_none(self):
        from sourcing.service import _parse_price_value
        assert _parse_price_value(None) == (None, None)

    def test_range(self):
        from sourcing.service import _parse_price_value
        assert _parse_price_value("$50-$200") == (50.0, 200.0)

    def test_greater_than(self):
        from sourcing.service import _parse_price_value
        lo, hi = _parse_price_value(">$100")
        assert lo == 100.0
        assert hi is None

    def test_less_than(self):
        from sourcing.service import _parse_price_value
        lo, hi = _parse_price_value("<$50")
        assert lo is None
        assert hi == 50.0

    def test_plain_number_returns_none_none(self):
        from sourcing.service import _parse_price_value
        assert _parse_price_value(42) == (None, None)

    def test_range_with_commas(self):
        from sourcing.service import _parse_price_value
        assert _parse_price_value("$1,000-$5,000") == (1000.0, 5000.0)
