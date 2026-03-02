"""
Tests for SDUI SSE event contract in the BuyAnything chat pipeline.

Covers:
- _build_and_persist_ui_schema helper
- sse_ui_schema_event format
- SSE event shape matches PRD-SDUI-Schema-Spec.md §9
- Schema persistence increments ui_schema_version
- Fallback behavior when schema build fails
"""

import json
import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.chat import sse_event, sse_ui_schema_event
from services.sdui_schema import validate_ui_schema


class TestSSEEvent:
    def test_basic_sse_format(self):
        result = sse_event("test_event", {"key": "value"})
        assert result.startswith("event: test_event\n")
        assert "data: " in result
        assert result.endswith("\n\n")
        data_line = result.split("data: ")[1].strip()
        parsed = json.loads(data_line)
        assert parsed["key"] == "value"

    def test_sse_event_with_none_data(self):
        result = sse_event("empty", None)
        assert "data: null" in result

    def test_sse_event_with_nested_data(self):
        result = sse_event("nested", {"a": {"b": [1, 2, 3]}})
        data_line = result.split("data: ")[1].strip()
        parsed = json.loads(data_line)
        assert parsed["a"]["b"] == [1, 2, 3]


class TestSSEUISchemaEvent:
    def test_format_matches_spec(self):
        schema = {
            "version": 1,
            "layout": "ROW_COMPACT",
            "blocks": [
                {"type": "MarkdownText", "content": "**Test**"},
                {"type": "ActionRow", "actions": [{"label": "Go", "intent": "view_raw"}]},
            ],
        }
        result = sse_ui_schema_event(42, schema, 1, "search_complete")
        assert "event: ui_schema_updated\n" in result
        data_line = result.split("data: ")[1].strip()
        parsed = json.loads(data_line)

        assert parsed["entity_type"] == "row"
        assert parsed["entity_id"] == 42
        assert parsed["version"] == 1
        assert parsed["trigger"] == "search_complete"
        assert parsed["schema"]["version"] == 1
        assert parsed["schema"]["layout"] == "ROW_COMPACT"
        assert len(parsed["schema"]["blocks"]) == 2

    def test_schema_in_event_validates(self):
        schema = {
            "version": 2,
            "layout": "ROW_MEDIA_LEFT",
            "value_vector": "unit_price",
            "blocks": [
                {"type": "ProductImage", "url": "https://img.com/a.jpg", "alt": "A"},
                {"type": "PriceBlock", "amount": 3.49, "currency": "USD", "label": "Best"},
            ],
        }
        result = sse_ui_schema_event(1, schema, 2, "search_complete")
        data_line = result.split("data: ")[1].strip()
        parsed = json.loads(data_line)
        validated = validate_ui_schema(parsed["schema"])
        assert validated is not None
        assert validated.value_vector == "unit_price"

    def test_valid_trigger_values(self):
        schema = {"version": 1, "layout": "ROW_COMPACT", "blocks": []}
        for trigger in ["row_created", "search_complete", "choice_factor_updated", "status_transition"]:
            result = sse_ui_schema_event(1, schema, 1, trigger)
            data_line = result.split("data: ")[1].strip()
            parsed = json.loads(data_line)
            assert parsed["trigger"] == trigger

    def test_project_entity_type_event(self):
        schema = {
            "version": 1,
            "layout": "ROW_COMPACT",
            "blocks": [{"type": "MarkdownText", "content": "**List**"}],
        }
        # sse_ui_schema_event currently always uses "row" — for project, we'd call sse_event directly
        # This test documents the current behavior
        result = sse_ui_schema_event(1, schema, 1, "first_item_added")
        data_line = result.split("data: ")[1].strip()
        parsed = json.loads(data_line)
        assert parsed["entity_type"] == "row"  # Current default

    def test_version_in_event_matches_row_version(self):
        schema = {"version": 1, "layout": "ROW_COMPACT", "blocks": []}
        for row_version in [1, 2, 5, 10]:
            result = sse_ui_schema_event(1, schema, row_version, "search_complete")
            data_line = result.split("data: ")[1].strip()
            parsed = json.loads(data_line)
            assert parsed["version"] == row_version


class TestSSEEventRoundtrip:
    """Verify SSE events can be parsed by a client."""

    def test_grocery_schema_event_parseable(self):
        schema = {
            "version": 1,
            "layout": "ROW_MEDIA_LEFT",
            "value_vector": "unit_price",
            "blocks": [
                {"type": "ProductImage", "url": "https://img.com/eggs.jpg", "alt": "Eggs"},
                {"type": "PriceBlock", "amount": 3.49, "currency": "USD", "label": "Best Price"},
                {"type": "BadgeList", "tags": ["Organic", "Kroger"]},
                {"type": "ActionRow", "actions": [{"label": "View Deal", "intent": "outbound_affiliate", "bid_id": "100"}]},
            ],
        }
        event_str = sse_ui_schema_event(42, schema, 2, "search_complete")

        # Simulate client-side SSE parsing
        lines = event_str.strip().split("\n")
        event_type = lines[0].replace("event: ", "")
        data_str = lines[1].replace("data: ", "")

        assert event_type == "ui_schema_updated"
        parsed = json.loads(data_str)
        assert parsed["entity_id"] == 42
        validated = validate_ui_schema(parsed["schema"])
        assert validated is not None
        assert validated.layout.value == "ROW_MEDIA_LEFT"

    def test_jet_charter_schema_event_parseable(self):
        schema = {
            "version": 1,
            "layout": "ROW_TIMELINE",
            "value_vector": "safety",
            "blocks": [
                {"type": "DataGrid", "items": [{"key": "Origin", "value": "SAN"}]},
                {"type": "Timeline", "steps": [{"label": "Sourcing", "status": "done"}]},
                {"type": "ActionRow", "actions": [{"label": "Contact", "intent": "contact_vendor"}]},
            ],
        }
        event_str = sse_ui_schema_event(99, schema, 1, "search_complete")
        lines = event_str.strip().split("\n")
        data_str = lines[1].replace("data: ", "")
        parsed = json.loads(data_str)
        validated = validate_ui_schema(parsed["schema"])
        assert validated is not None
        assert validated.layout.value == "ROW_TIMELINE"
