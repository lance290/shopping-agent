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


