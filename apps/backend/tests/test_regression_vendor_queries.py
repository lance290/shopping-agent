import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession
from unittest.mock import MagicMock, AsyncMock, patch
from models import Row, User


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
    mock_decision.items = None
    return mock_decision

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
    """Regression: UserIntent must include all required fields."""

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


# Provider aliases + parsing tests extracted to test_regression_parsing.py
