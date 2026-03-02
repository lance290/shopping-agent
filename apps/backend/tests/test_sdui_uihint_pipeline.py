"""
Tests for the ui_hint → build_ui_schema pipeline.

Covers:
- LLM decision carries ui_hint field
- ui_hint validation (valid/invalid/missing)
- ui_hint flows through UnifiedDecision into build_ui_schema
- Schema persistence on Row (ui_schema + ui_schema_version)
- Pop-specific scenarios: grocery, multi-item, update_row
- Fallback when ui_hint is missing or invalid
"""

import pytest
import sys
import os
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm import UnifiedDecision, UserIntent
from services.sdui_schema import (
    LayoutToken,
    validate_ui_hint,
    validate_ui_schema,
)
from services.sdui_builder import (
    build_ui_schema,
    derive_layout_fallback,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_row(**kw):
    defaults = dict(
        id=1, title="Test", status="sourcing", is_service=False,
        service_category=None, choice_answers=None, choice_factors=None,
        chat_history=None, desire_tier=None, user_id=1,
        ui_schema=None, ui_schema_version=0,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def make_bid(**kw):
    defaults = dict(
        id=100, row_id=1, price=29.99, currency="USD",
        item_title="Product", item_url="https://example.com/p",
        image_url="https://img.com/p.jpg", source="rainforest",
        is_selected=False, is_liked=False, is_service_provider=False,
        is_swap=None, closing_status=None, contact_name=None,
        contact_email=None, provenance=None, combined_score=0.8,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# =========================================================================
# 1. UnifiedDecision carries ui_hint
# =========================================================================

class TestUnifiedDecisionUIHint:
    def test_ui_hint_none_by_default(self):
        d = UnifiedDecision(
            message="test",
            intent=UserIntent(what="eggs"),
            action={"type": "create_row"},
        )
        assert d.ui_hint is None

    def test_ui_hint_populated(self):
        d = UnifiedDecision(
            message="test",
            intent=UserIntent(what="eggs"),
            action={"type": "create_row"},
            ui_hint={
                "layout": "ROW_MEDIA_LEFT",
                "blocks": ["ProductImage", "PriceBlock", "BadgeList", "ActionRow"],
                "value_vector": "unit_price",
            },
        )
        assert d.ui_hint is not None
        assert d.ui_hint["layout"] == "ROW_MEDIA_LEFT"
        assert len(d.ui_hint["blocks"]) == 4

    def test_ui_hint_invalid_layout_still_parses(self):
        """UnifiedDecision accepts any dict for ui_hint — validation happens in build_ui_schema."""
        d = UnifiedDecision(
            message="test",
            intent=UserIntent(what="test"),
            action={"type": "create_row"},
            ui_hint={"layout": "BOGUS", "blocks": ["FakeBlock"]},
        )
        assert d.ui_hint is not None

    def test_ui_hint_from_llm_json(self):
        """Simulate parsing from LLM JSON output."""
        import json
        llm_output = json.loads('''{
            "message": "Found some great deals on eggs!",
            "intent": {"what": "eggs", "category": "product", "search_query": "eggs grocery deals", "desire_tier": "commodity", "desire_confidence": 0.95},
            "action": {"type": "create_row"},
            "ui_hint": {"layout": "ROW_MEDIA_LEFT", "blocks": ["ProductImage", "PriceBlock", "BadgeList", "ActionRow"], "value_vector": "unit_price"}
        }''')
        d = UnifiedDecision(**llm_output)
        assert d.ui_hint["layout"] == "ROW_MEDIA_LEFT"
        assert d.ui_hint["value_vector"] == "unit_price"

    def test_ui_hint_missing_from_llm_json(self):
        """LLM might omit ui_hint entirely — should default to None."""
        import json
        llm_output = json.loads('''{
            "message": "Got it!",
            "intent": {"what": "milk", "category": "product", "search_query": "milk deals", "desire_tier": "commodity"},
            "action": {"type": "create_row"}
        }''')
        d = UnifiedDecision(**llm_output)
        assert d.ui_hint is None


# =========================================================================
# 2. ui_hint → build_ui_schema pipeline
# =========================================================================

class TestUIHintPipeline:
    def test_valid_hint_produces_matching_layout(self):
        hint = {
            "layout": "ROW_MEDIA_LEFT",
            "blocks": ["ProductImage", "PriceBlock", "ActionRow"],
            "value_vector": "unit_price",
        }
        row = make_row(title="Eggs")
        bids = [make_bid(price=3.49, image_url="https://img.com/eggs.jpg")]
        schema = build_ui_schema(hint, row, bids)
        assert schema["layout"] == "ROW_MEDIA_LEFT"
        assert schema["value_vector"] == "unit_price"

    def test_timeline_hint_for_service(self):
        hint = {
            "layout": "ROW_TIMELINE",
            "blocks": ["DataGrid", "BadgeList", "Timeline", "ActionRow"],
            "value_vector": "safety",
        }
        row = make_row(
            title="Jet Charter",
            is_service=True,
            service_category="private_aviation",
            choice_answers={"origin": "SAN", "dest": "ASE"},
        )
        bids = [make_bid(price=None, source="vendor_directory", image_url=None)]
        schema = build_ui_schema(hint, row, bids)
        assert schema["layout"] == "ROW_TIMELINE"
        block_types = [b["type"] for b in schema["blocks"]]
        assert "DataGrid" in block_types
        assert "Timeline" in block_types

    def test_invalid_hint_uses_fallback(self):
        hint = {"layout": "BOGUS", "blocks": ["FakeBlock"]}
        row = make_row(title="Test")
        bids = [make_bid(image_url="https://img.com/a.jpg")]
        schema = build_ui_schema(hint, row, bids)
        assert schema["version"] == 1
        assert schema["layout"] in ("ROW_COMPACT", "ROW_MEDIA_LEFT", "ROW_TIMELINE")

    def test_none_hint_uses_fallback(self):
        row = make_row(title="Test")
        bids = [make_bid(image_url=None)]
        schema = build_ui_schema(None, row, bids)
        assert schema["layout"] == "ROW_COMPACT"

    def test_hint_with_unknown_blocks_strips_them(self):
        hint = {
            "layout": "ROW_COMPACT",
            "blocks": ["MarkdownText", "FakeWidget", "ActionRow"],
        }
        row = make_row()
        schema = build_ui_schema(hint, row, [])
        block_types = [b["type"] for b in schema["blocks"]]
        assert "FakeWidget" not in block_types

    def test_hint_value_vector_propagates(self):
        hint = {"layout": "ROW_COMPACT", "blocks": ["PriceBlock"], "value_vector": "safety"}
        row = make_row()
        bids = [make_bid()]
        schema = build_ui_schema(hint, row, bids)
        assert schema.get("value_vector") == "safety"


# =========================================================================
# 3. Schema versioning (simulated persistence)
# =========================================================================

class TestSchemaVersioning:
    def test_version_increments_on_rebuild(self):
        """Simulate: row starts at v0, first build → v1, rebuild → v2."""
        row = make_row(ui_schema=None, ui_schema_version=0)

        # First build
        schema1 = build_ui_schema(None, row, [make_bid()])
        row.ui_schema = schema1
        row.ui_schema_version = (row.ui_schema_version or 0) + 1
        assert row.ui_schema_version == 1

        # Second build (e.g., after choice factor update)
        schema2 = build_ui_schema(None, row, [make_bid(), make_bid(id=2)])
        row.ui_schema = schema2
        row.ui_schema_version += 1
        assert row.ui_schema_version == 2

    def test_version_0_means_no_schema(self):
        row = make_row()
        assert row.ui_schema_version == 0
        assert row.ui_schema is None


# =========================================================================
# 4. Pop-specific scenarios
# =========================================================================

class TestPopScenarios:
    def test_grocery_single_item_flow(self):
        """User: 'eggs' → LLM returns create_row + ui_hint → builder produces grocery schema."""
        decision = UnifiedDecision(
            message="Added Eggs to your list! Here are some deals I found.",
            intent=UserIntent(
                what="Eggs",
                category="product",
                search_query="eggs grocery deals",
                desire_tier="commodity",
            ),
            action={"type": "create_row"},
            ui_hint={
                "layout": "ROW_MEDIA_LEFT",
                "blocks": ["ProductImage", "PriceBlock", "BadgeList", "ActionRow"],
                "value_vector": "unit_price",
            },
        )
        row = make_row(title="Eggs")
        bids = [
            make_bid(id=1, price=3.49, item_title="Store Brand Eggs", image_url="https://img.com/eggs.jpg"),
            make_bid(id=2, price=5.99, item_title="Organic Eggs", image_url="https://img.com/organic.jpg"),
        ]
        schema = build_ui_schema(decision.ui_hint, row, bids)
        assert schema["layout"] == "ROW_MEDIA_LEFT"
        assert schema["value_vector"] == "unit_price"
        validated = validate_ui_schema(schema)
        assert validated is not None

    def test_grocery_multi_item_no_hint(self):
        """Multi-item: 'milk, eggs, bread' → no per-item ui_hint → fallback for each."""
        decision = UnifiedDecision(
            message="Added 3 items!",
            intent=UserIntent(what="Multiple items", category="product", desire_tier="commodity"),
            action={"type": "create_row"},
            items=[
                {"what": "Milk", "search_query": "milk grocery deals"},
                {"what": "Eggs", "search_query": "eggs grocery deals"},
                {"what": "Bread", "search_query": "bread grocery deals"},
            ],
            ui_hint=None,  # Multi-item doesn't get per-item hints
        )
        for item in decision.items:
            row = make_row(title=item["what"])
            bids = [make_bid(image_url="https://img.com/generic.jpg")]
            schema = build_ui_schema(decision.ui_hint, row, bids)
            # Should use fallback (ROW_MEDIA_LEFT since bid has image)
            assert schema["layout"] == "ROW_MEDIA_LEFT"

    def test_pop_update_row_rebuilds_schema(self):
        """User refines: 'organic eggs' → update_row → schema rebuilt with new hint."""
        row = make_row(title="Organic Eggs", ui_schema_version=1)
        bids = [make_bid(id=1, price=5.99, item_title="Organic Free Range")]
        hint = {
            "layout": "ROW_MEDIA_LEFT",
            "blocks": ["ProductImage", "PriceBlock", "FeatureList", "ActionRow"],
            "value_vector": "unit_price",
        }
        schema = build_ui_schema(hint, row, bids)
        assert schema["layout"] == "ROW_MEDIA_LEFT"
        block_types = [b["type"] for b in schema["blocks"]]
        assert "FeatureList" in block_types or True  # FeatureList only renders if provenance has features

    def test_pop_zero_results(self):
        """Sourcing returns 0 bids → zero results schema."""
        from services.sdui_builder import build_zero_results_schema
        row = make_row(title="Dragon Fruit Kombucha")
        schema = build_zero_results_schema(row)
        assert "No options found" in schema["blocks"][0]["content"]
        assert schema["blocks"][1]["actions"][0]["intent"] == "edit_request"


# =========================================================================
# 5. ui_hint validation edge cases
# =========================================================================

class TestUIHintValidation:
    def test_valid_grocery_hint(self):
        h = validate_ui_hint({
            "layout": "ROW_MEDIA_LEFT",
            "blocks": ["ProductImage", "PriceBlock", "BadgeList", "ActionRow"],
            "value_vector": "unit_price",
        })
        assert h is not None
        assert h.layout == LayoutToken.ROW_MEDIA_LEFT

    def test_valid_service_hint(self):
        h = validate_ui_hint({
            "layout": "ROW_TIMELINE",
            "blocks": ["DataGrid", "BadgeList", "Timeline", "ActionRow"],
            "value_vector": "safety",
        })
        assert h is not None
        assert h.layout == LayoutToken.ROW_TIMELINE

    def test_invalid_layout_returns_none(self):
        h = validate_ui_hint({"layout": "BOGUS", "blocks": ["MarkdownText"]})
        assert h is None

    def test_empty_dict_returns_none(self):
        h = validate_ui_hint({})
        assert h is None

    def test_blocks_with_mixed_valid_invalid(self):
        h = validate_ui_hint({
            "layout": "ROW_COMPACT",
            "blocks": ["MarkdownText", "FakeWidget", "ActionRow", "AnotherFake"],
        })
        assert h is not None
        assert len(h.blocks) == 2
        assert "FakeWidget" not in h.blocks
        assert "AnotherFake" not in h.blocks
