"""
Tests for SDUI Schema Validation (services/sdui_schema.py).

Covers:
- Layout tokens
- All 13 block types with valid/invalid data
- UISchema top-level validation (version, layout, blocks, limits)
- UIHint validation (LLM output contract)
- ActionObject intents
- Value vectors and provenance
- Validation limits (max blocks, max text, max items, max actions)
- Unknown block stripping
- Minimum viable row fallback
- Edge cases (empty, null, oversized)
"""

import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sdui_schema import (
    BLOCK_TYPES,
    GROCERY_BID_CAP,
    LAYOUT_TOKENS,
    MAX_ACTION_ROW_ACTIONS,
    MAX_BLOCKS_PER_ROW,
    MAX_DATAGRID_ITEMS,
    MAX_MARKDOWN_LENGTH,
    RETAIL_BID_CAP,
    VALUE_VECTORS,
    ACTION_INTENTS,
    STATE_DRIVEN_BLOCKS,
    ActionObject,
    ActionRowBlock,
    BadgeListBlock,
    ChoiceFactorFormBlock,
    DataGridBlock,
    DataGridItem,
    EscrowStatusBlock,
    FeatureListBlock,
    LayoutToken,
    MarkdownTextBlock,
    MessageItem,
    MessageListBlock,
    PriceBlock,
    ProductImageBlock,
    ReceiptUploaderBlock,
    TimelineBlock,
    TimelineStep,
    UIBlock,
    UIHint,
    UISchema,
    WalletLedgerBlock,
    get_minimum_viable_row,
    strip_unknown_blocks,
    validate_ui_hint,
    validate_ui_schema,
)


# =========================================================================
# Constants sanity checks
# =========================================================================

class TestConstants:
    def test_layout_tokens_are_three(self):
        assert len(LAYOUT_TOKENS) == 3
        assert "ROW_COMPACT" in LAYOUT_TOKENS
        assert "ROW_MEDIA_LEFT" in LAYOUT_TOKENS
        assert "ROW_TIMELINE" in LAYOUT_TOKENS

    def test_block_types_are_thirteen(self):
        assert len(BLOCK_TYPES) == 13

    def test_action_intents_are_eleven(self):
        assert len(ACTION_INTENTS) == 11
        assert "outbound_affiliate" in ACTION_INTENTS
        assert "claim_swap" in ACTION_INTENTS
        assert "fund_escrow" in ACTION_INTENTS
        assert "send_tip" in ACTION_INTENTS
        assert "contact_vendor" in ACTION_INTENTS
        assert "view_all_bids" in ACTION_INTENTS
        assert "view_raw" in ACTION_INTENTS
        assert "edit_request" in ACTION_INTENTS
        assert "mark_terms_agreed" in ACTION_INTENTS
        assert "continue_negotiation" in ACTION_INTENTS
        assert "invite_vendor_connect" in ACTION_INTENTS

    def test_value_vectors(self):
        assert len(VALUE_VECTORS) == 5
        assert "unit_price" in VALUE_VECTORS
        assert "safety" in VALUE_VECTORS

    def test_state_driven_blocks(self):
        assert "ReceiptUploader" in STATE_DRIVEN_BLOCKS
        assert "WalletLedger" in STATE_DRIVEN_BLOCKS
        assert "EscrowStatus" in STATE_DRIVEN_BLOCKS

    def test_bid_caps(self):
        assert GROCERY_BID_CAP == 5
        assert RETAIL_BID_CAP == 30

    def test_limits(self):
        assert MAX_BLOCKS_PER_ROW == 8
        assert MAX_MARKDOWN_LENGTH == 500
        assert MAX_DATAGRID_ITEMS == 12
        assert MAX_ACTION_ROW_ACTIONS == 3


# =========================================================================
# LayoutToken enum
# =========================================================================

class TestLayoutToken:
    def test_valid_tokens(self):
        assert LayoutToken("ROW_COMPACT") == LayoutToken.ROW_COMPACT
        assert LayoutToken("ROW_MEDIA_LEFT") == LayoutToken.ROW_MEDIA_LEFT
        assert LayoutToken("ROW_TIMELINE") == LayoutToken.ROW_TIMELINE

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError):
            LayoutToken("INVALID_LAYOUT")


# Block type tests extracted to test_sdui_schema_blocks.py


# =========================================================================
# UISchema (Top-Level)
# =========================================================================

class TestUISchema:
    def test_valid_minimal(self):
        s = UISchema(version=1, layout=LayoutToken.ROW_COMPACT, blocks=[])
        assert s.version == 1
        assert s.layout == LayoutToken.ROW_COMPACT
        assert s.blocks == []

    def test_valid_with_blocks(self):
        s = UISchema(
            version=1,
            layout=LayoutToken.ROW_MEDIA_LEFT,
            value_vector="unit_price",
            blocks=[
                ProductImageBlock(url="https://img.com/a.jpg"),
                PriceBlock(amount=9.99),
                BadgeListBlock(tags=["Organic"]),
            ],
        )
        assert len(s.blocks) == 3
        assert s.value_vector == "unit_price"

    def test_max_blocks_enforced(self):
        blocks = [MarkdownTextBlock(content=f"Block {i}") for i in range(12)]
        s = UISchema(version=1, layout=LayoutToken.ROW_COMPACT, blocks=blocks)
        assert len(s.blocks) == MAX_BLOCKS_PER_ROW

    def test_invalid_value_vector_set_to_none(self):
        s = UISchema(version=1, layout=LayoutToken.ROW_COMPACT, value_vector="nonexistent")
        assert s.value_vector is None

    def test_valid_value_vectors(self):
        for vv in VALUE_VECTORS:
            s = UISchema(version=1, layout=LayoutToken.ROW_COMPACT, value_vector=vv)
            assert s.value_vector == vv

    def test_serialization_roundtrip(self):
        s = UISchema(
            version=1,
            layout=LayoutToken.ROW_COMPACT,
            blocks=[
                MarkdownTextBlock(content="**Test**"),
                ActionRowBlock(actions=[ActionObject(label="Go", intent="view_raw")]),
            ],
        )
        d = s.model_dump()
        assert d["version"] == 1
        assert d["layout"] == "ROW_COMPACT"
        assert len(d["blocks"]) == 2
        assert d["blocks"][0]["type"] == "MarkdownText"
        assert d["blocks"][1]["type"] == "ActionRow"

    def test_invalid_layout_raises(self):
        with pytest.raises(Exception):
            UISchema(version=1, layout="INVALID")

    def test_value_rationale_refs(self):
        s = UISchema(
            version=1,
            layout=LayoutToken.ROW_COMPACT,
            value_vector="safety",
            value_rationale_refs=["ref_1", "ref_2"],
        )
        assert s.value_rationale_refs == ["ref_1", "ref_2"]


# =========================================================================
# UIHint (LLM Output)
# =========================================================================

class TestUIHint:
    def test_valid(self):
        h = UIHint(
            layout=LayoutToken.ROW_MEDIA_LEFT,
            blocks=["ProductImage", "PriceBlock", "BadgeList", "ActionRow"],
            value_vector="unit_price",
        )
        assert h.layout == LayoutToken.ROW_MEDIA_LEFT
        assert len(h.blocks) == 4

    def test_strips_unknown_block_types(self):
        h = UIHint(
            layout=LayoutToken.ROW_COMPACT,
            blocks=["MarkdownText", "UnknownWidget", "ActionRow"],
        )
        assert "UnknownWidget" not in h.blocks
        assert len(h.blocks) == 2

    def test_max_blocks_enforced(self):
        h = UIHint(
            layout=LayoutToken.ROW_COMPACT,
            blocks=list(BLOCK_TYPES) + list(BLOCK_TYPES),  # 26 block types
        )
        assert len(h.blocks) <= MAX_BLOCKS_PER_ROW

    def test_empty_blocks(self):
        h = UIHint(layout=LayoutToken.ROW_COMPACT, blocks=[])
        assert h.blocks == []

    def test_no_value_vector(self):
        h = UIHint(layout=LayoutToken.ROW_COMPACT, blocks=["ActionRow"])
        assert h.value_vector is None

    def test_all_valid_block_types_accepted(self):
        h = UIHint(layout=LayoutToken.ROW_COMPACT, blocks=list(BLOCK_TYPES)[:8])
        assert len(h.blocks) == 8


# =========================================================================
# Validation Helpers
# =========================================================================

class TestValidateUISchema:
    def test_valid_dict(self):
        data = {
            "version": 1,
            "layout": "ROW_COMPACT",
            "blocks": [
                {"type": "MarkdownText", "content": "Hello"},
            ],
        }
        result = validate_ui_schema(data)
        assert result is not None
        assert result.version == 1

    def test_invalid_dict_returns_none(self):
        result = validate_ui_schema({"version": "not_a_number"})
        assert result is None

    def test_empty_dict_returns_none(self):
        result = validate_ui_schema({})
        assert result is None

    def test_missing_layout_returns_none(self):
        result = validate_ui_schema({"version": 1, "blocks": []})
        assert result is None


class TestValidateUIHint:
    def test_valid_dict(self):
        data = {
            "layout": "ROW_MEDIA_LEFT",
            "blocks": ["ProductImage", "PriceBlock"],
        }
        result = validate_ui_hint(data)
        assert result is not None
        assert result.layout == LayoutToken.ROW_MEDIA_LEFT

    def test_invalid_dict_returns_none(self):
        result = validate_ui_hint({"layout": "INVALID"})
        assert result is None

    def test_empty_returns_none(self):
        result = validate_ui_hint({})
        assert result is None


class TestStripUnknownBlocks:
    def test_strips_unknown(self):
        data = {
            "blocks": [
                {"type": "MarkdownText", "content": "hi"},
                {"type": "FooWidget", "data": 42},
                {"type": "ActionRow", "actions": []},
            ]
        }
        cleaned = strip_unknown_blocks(data)
        assert len(cleaned["blocks"]) == 2
        types = [b["type"] for b in cleaned["blocks"]]
        assert "FooWidget" not in types

    def test_no_blocks_key(self):
        data = {"version": 1}
        assert strip_unknown_blocks(data) == {"version": 1}

    def test_all_unknown(self):
        data = {"blocks": [{"type": "X"}, {"type": "Y"}]}
        cleaned = strip_unknown_blocks(data)
        assert len(cleaned["blocks"]) == 0

    def test_all_valid(self):
        data = {"blocks": [{"type": "PriceBlock"}, {"type": "BadgeList"}]}
        cleaned = strip_unknown_blocks(data)
        assert len(cleaned["blocks"]) == 2


class TestMinimumViableRow:
    def test_default(self):
        mvr = get_minimum_viable_row()
        assert mvr["version"] == 1
        assert mvr["layout"] == "ROW_COMPACT"
        assert len(mvr["blocks"]) == 3
        assert mvr["blocks"][0]["type"] == "MarkdownText"
        assert "Untitled" in mvr["blocks"][0]["content"]

    def test_custom_title(self):
        mvr = get_minimum_viable_row(title="Eggs", status="searching")
        assert "Eggs" in mvr["blocks"][0]["content"]
        assert "searching" in mvr["blocks"][1]["tags"]

    def test_validates_as_schema(self):
        mvr = get_minimum_viable_row(title="Test")
        result = validate_ui_schema(mvr)
        assert result is not None
        assert result.layout == LayoutToken.ROW_COMPACT


# =========================================================================
# Edge Cases
# =========================================================================

class TestEdgeCases:
    def test_schema_with_all_block_types(self):
        """Ensure schema accepts a mix of different block types."""
        s = UISchema(
            version=1,
            layout=LayoutToken.ROW_MEDIA_LEFT,
            blocks=[
                ProductImageBlock(url="https://img.com/a.jpg"),
                PriceBlock(amount=42.0),
                DataGridBlock(items=[DataGridItem(key="k", value="v")]),
                BadgeListBlock(tags=["X"]),
                MarkdownTextBlock(content="**bold**"),
                ActionRowBlock(actions=[ActionObject(label="Go", intent="view_raw")]),
                TimelineBlock(steps=[TimelineStep(label="Step 1")]),
                FeatureListBlock(features=["F1"]),
            ],
        )
        assert len(s.blocks) == 8

    def test_schema_with_only_action_row(self):
        s = UISchema(
            version=1,
            layout=LayoutToken.ROW_COMPACT,
            blocks=[ActionRowBlock(actions=[ActionObject(label="Edit", intent="edit_request")])],
        )
        assert len(s.blocks) == 1

    def test_schema_model_dump_nested(self):
        """Verify deeply nested structures serialize correctly."""
        s = UISchema(
            version=1,
            layout=LayoutToken.ROW_TIMELINE,
            blocks=[
                DataGridBlock(items=[DataGridItem(key="A", value="1"), DataGridItem(key="B", value="2")]),
                TimelineBlock(steps=[
                    TimelineStep(label="S1", status="done"),
                    TimelineStep(label="S2", status="active"),
                ]),
                ActionRowBlock(actions=[
                    ActionObject(label="Fund", intent="fund_escrow", amount=15000.0),
                ]),
            ],
        )
        d = s.model_dump()
        assert d["blocks"][0]["items"][0]["key"] == "A"
        assert d["blocks"][1]["steps"][1]["status"] == "active"
        assert d["blocks"][2]["actions"][0]["amount"] == 15000.0

    def test_unicode_content(self):
        b = MarkdownTextBlock(content="日本語テスト 🎉")
        assert "日本語" in b.content

    def test_very_long_url_in_product_image(self):
        long_url = "https://example.com/" + "a" * 2000
        b = ProductImageBlock(url=long_url, alt="test")
        assert len(b.url) > 2000
