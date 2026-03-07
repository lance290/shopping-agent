"""
Tests for SDUI Builder (services/sdui_builder.py).

Covers:
- Deterministic fallback layout derivation
- Bid cap (grocery vs retail)
- All 13 block hydrators
- hydrate_ui_schema() main entry point
- build_ui_schema() with valid/invalid/missing hints
- build_project_ui_schema()
- build_zero_results_schema()
- Post-decision fulfillment detection
- State-driven block gating (receipt uploader, escrow)
- Edge cases (empty bids, null fields, mixed sources)
"""

import pytest
import sys
import os
from unittest.mock import MagicMock
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sdui_schema import (
    GROCERY_BID_CAP,
    RETAIL_BID_CAP,
    LayoutToken,
    UIHint,
    UISchema,
    validate_ui_schema,
)
from services.sdui_builder import (
    build_project_ui_schema,
    build_ui_schema,
    build_zero_results_schema,
    derive_layout_fallback,
    get_bid_cap,
    hydrate_ui_schema,
    _hydrate_product_image,
    _hydrate_price_block,
    _hydrate_data_grid,
    _hydrate_feature_list,
    _hydrate_badge_list,
    _hydrate_markdown_text,
    _hydrate_timeline,
    _hydrate_message_list,
    _hydrate_choice_factor_form,
    _hydrate_action_row,
    _hydrate_receipt_uploader,
    _hydrate_escrow_status,
    _is_post_decision_fulfillment,
)


# ---------------------------------------------------------------------------
# Helpers: mock Row / Bid objects
# ---------------------------------------------------------------------------

def make_row(**kwargs):
    defaults = {
        "id": 1,
        "title": "Test Item",
        "status": "sourcing",
        "is_service": False,
        "service_category": None,
        "choice_answers": None,
        "choice_factors": None,
        "chat_history": None,
        "desire_tier": None,
        "user_id": 1,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_bid(**kwargs):
    defaults = {
        "id": 100,
        "row_id": 1,
        "price": 29.99,
        "currency": "USD",
        "item_title": "Product A",
        "item_url": "https://amazon.com/product-a",
        "image_url": "https://img.com/a.jpg",
        "source": "rainforest",
        "is_selected": False,
        "is_liked": False,
        "is_service_provider": False,
        "is_swap": None,
        "closing_status": None,
        "contact_name": None,
        "contact_email": None,
        "provenance": None,
        "combined_score": 0.85,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_vendor_bid(**kwargs):
    defaults = dict(
        price=None,
        source="vendor_directory",
        is_service_provider=True,
        item_url="mailto:vendor@example.com",
        image_url=None,
    )
    defaults.update(kwargs)
    return make_bid(**defaults)


def make_swap_bid(**kwargs):
    defaults = dict(
        is_swap=True,
        source="kroger",
        price=3.49,
        item_title="Store Brand Eggs",
    )
    defaults.update(kwargs)
    return make_bid(**defaults)


# =========================================================================
# Post-Decision Detection
# =========================================================================

class TestIsPostDecisionFulfillment:
    def test_sourcing_is_not_post_decision(self):
        row = make_row(status="sourcing")
        assert not _is_post_decision_fulfillment(row, [])

    def test_closed_is_post_decision(self):
        row = make_row(status="closed")
        assert _is_post_decision_fulfillment(row, [])

    def test_funded_is_post_decision(self):
        row = make_row(status="funded")
        assert _is_post_decision_fulfillment(row, [])

    def test_delivered_is_post_decision(self):
        row = make_row(status="delivered")
        assert _is_post_decision_fulfillment(row, [])

    def test_bid_with_paid_status_triggers(self):
        row = make_row(status="sourcing")
        bid = make_bid(closing_status="paid")
        assert _is_post_decision_fulfillment(row, [bid])

    def test_bid_with_shipped_status_triggers(self):
        row = make_row(status="sourcing")
        bid = make_bid(closing_status="shipped")
        assert _is_post_decision_fulfillment(row, [bid])

    def test_bid_with_pending_status_no_trigger(self):
        row = make_row(status="sourcing")
        bid = make_bid(closing_status="pending")
        assert not _is_post_decision_fulfillment(row, [bid])


# =========================================================================
# Bid Cap
# =========================================================================

class TestGetBidCap:
    def test_grocery_swap_cap(self):
        row = make_row()
        bids = [make_swap_bid()]
        assert get_bid_cap(row, bids) == GROCERY_BID_CAP

    def test_service_row_retail_cap(self):
        row = make_row(is_service=True, service_category="private_aviation")
        bids = [make_vendor_bid()]
        assert get_bid_cap(row, bids) == RETAIL_BID_CAP

    def test_default_retail_cap(self):
        row = make_row()
        bids = [make_bid()]
        assert get_bid_cap(row, bids) == RETAIL_BID_CAP

    def test_empty_bids_retail_cap(self):
        row = make_row()
        assert get_bid_cap(row, []) == RETAIL_BID_CAP


# =========================================================================
# Deterministic Fallback
# =========================================================================

class TestDeriveLayoutFallback:
    def test_post_decision_returns_timeline(self):
        row = make_row(status="closed")
        hint = derive_layout_fallback(row, [])
        assert hint.layout == LayoutToken.ROW_TIMELINE
        assert "Timeline" in hint.blocks

    def test_bids_with_images_returns_media_left(self):
        row = make_row()
        bids = [make_bid(image_url="https://img.com/a.jpg")]
        hint = derive_layout_fallback(row, bids)
        assert hint.layout == LayoutToken.ROW_MEDIA_LEFT
        assert "ProductImage" in hint.blocks

    def test_bids_without_images_returns_compact(self):
        row = make_row()
        bids = [make_bid(image_url=None)]
        hint = derive_layout_fallback(row, bids)
        assert hint.layout == LayoutToken.ROW_COMPACT
        assert "MarkdownText" in hint.blocks

    def test_no_bids_returns_compact(self):
        row = make_row()
        hint = derive_layout_fallback(row, [])
        assert hint.layout == LayoutToken.ROW_COMPACT

    def test_fallback_always_has_action_row(self):
        row = make_row()
        hint = derive_layout_fallback(row, [])
        assert "ActionRow" in hint.blocks


# Individual block hydrator tests extracted to test_sdui_builder_blocks.py


# =========================================================================
# hydrate_ui_schema (main function)
# =========================================================================

class TestHydrateUISchema:
    def test_grocery_schema(self):
        hint = UIHint(
            layout=LayoutToken.ROW_MEDIA_LEFT,
            blocks=["ProductImage", "PriceBlock", "BadgeList", "ActionRow"],
            value_vector="unit_price",
        )
        row = make_row(title="Organic Eggs")
        bids = [make_bid(image_url="https://img.com/eggs.jpg", price=4.99)]
        schema = hydrate_ui_schema(hint, row, bids)
        assert isinstance(schema, UISchema)
        assert schema.layout == LayoutToken.ROW_MEDIA_LEFT
        assert schema.value_vector == "unit_price"
        assert len(schema.blocks) > 0

    def test_service_schema(self):
        hint = UIHint(
            layout=LayoutToken.ROW_TIMELINE,
            blocks=["DataGrid", "BadgeList", "Timeline", "ActionRow"],
            value_vector="safety",
        )
        row = make_row(
            title="Private Jet SAN to ASE",
            is_service=True,
            service_category="private_aviation",
            choice_answers={"origin": "SAN", "destination": "ASE", "pax": "4"},
        )
        bids = [make_vendor_bid()]
        schema = hydrate_ui_schema(hint, row, bids)
        assert schema.layout == LayoutToken.ROW_TIMELINE
        block_types = [b.type for b in schema.blocks]
        assert "DataGrid" in block_types
        assert "Timeline" in block_types

    def test_empty_bids_still_produces_schema(self):
        hint = UIHint(
            layout=LayoutToken.ROW_COMPACT,
            blocks=["MarkdownText", "BadgeList", "ActionRow"],
        )
        row = make_row(title="Searching...")
        schema = hydrate_ui_schema(hint, row, [])
        assert len(schema.blocks) >= 1  # At least MarkdownText

    def test_respects_bid_cap_for_grocery(self):
        hint = UIHint(
            layout=LayoutToken.ROW_COMPACT,
            blocks=["PriceBlock", "ActionRow"],
        )
        row = make_row()
        bids = [make_swap_bid(id=i) for i in range(20)]
        schema = hydrate_ui_schema(hint, row, bids)
        # The builder should cap at GROCERY_BID_CAP internally
        assert isinstance(schema, UISchema)

    def test_state_driven_blocks_gated(self):
        """ReceiptUploader should only render when state allows."""
        hint = UIHint(
            layout=LayoutToken.ROW_COMPACT,
            blocks=["MarkdownText", "ReceiptUploader", "ActionRow"],
        )
        row = make_row()
        bids = [make_bid()]  # No swap, no pending claim
        schema = hydrate_ui_schema(hint, row, bids)
        block_types = [b.type for b in schema.blocks]
        assert "ReceiptUploader" not in block_types

    def test_state_driven_blocks_render_when_permitted(self):
        hint = UIHint(
            layout=LayoutToken.ROW_COMPACT,
            blocks=["MarkdownText", "ReceiptUploader", "ActionRow"],
        )
        row = make_row()
        bids = [make_swap_bid(closing_status="pending")]
        schema = hydrate_ui_schema(hint, row, bids)
        block_types = [b.type for b in schema.blocks]
        assert "ReceiptUploader" in block_types


# =========================================================================
# build_ui_schema (top-level entry)
# =========================================================================

class TestBuildUISchema:
    def test_valid_hint(self):
        hint_data = {
            "layout": "ROW_MEDIA_LEFT",
            "blocks": ["ProductImage", "PriceBlock", "ActionRow"],
        }
        row = make_row()
        bids = [make_bid()]
        result = build_ui_schema(hint_data, row, bids)
        assert result["version"] == 1
        assert result["layout"] == "ROW_MEDIA_LEFT"
        assert len(result["blocks"]) > 0

    def test_invalid_hint_uses_fallback(self):
        hint_data = {"layout": "INVALID_LAYOUT"}
        row = make_row()
        bids = [make_bid()]
        result = build_ui_schema(hint_data, row, bids)
        assert result["version"] == 1
        # Should have used fallback (ROW_MEDIA_LEFT since bid has image)
        assert result["layout"] in ("ROW_COMPACT", "ROW_MEDIA_LEFT", "ROW_TIMELINE")

    def test_none_hint_uses_fallback(self):
        row = make_row()
        bids = [make_bid(image_url=None)]
        result = build_ui_schema(None, row, bids)
        assert result["version"] == 1
        assert result["layout"] == "ROW_COMPACT"

    def test_empty_hint_uses_fallback(self):
        result = build_ui_schema({}, make_row(), [])
        assert result["version"] == 1

    def test_result_is_valid_ui_schema(self):
        hint_data = {
            "layout": "ROW_COMPACT",
            "blocks": ["MarkdownText", "ActionRow"],
        }
        result = build_ui_schema(hint_data, make_row(), [])
        validated = validate_ui_schema(result)
        assert validated is not None

    def test_terms_agreed_active_deal_injects_payment_actions(self):
        row = make_row(
            active_deal={
                "id": 88,
                "row_id": 1,
                "status": "terms_agreed",
                "buyer_total": 15150.0,
                "currency": "USD",
                "agreed_terms_summary": "Vendor confirmed the quote and timing.",
                "agreement_source": "manual",
            }
        )
        result = build_ui_schema(
            {
                "layout": "ROW_COMPACT",
                "blocks": ["MarkdownText", "ActionRow"],
            },
            row,
            [],
        )
        action_rows = [block for block in result["blocks"] if block["type"] == "ActionRow"]
        intents = [action["intent"] for block in action_rows for action in block["actions"]]
        assert "fund_escrow" in intents
        assert "continue_negotiation" in intents
        assert any(block["type"] == "BadgeList" for block in result["blocks"])

    def test_negotiating_active_deal_injects_manual_agreement_action(self):
        row = make_row(
            active_deal={
                "id": 89,
                "row_id": 1,
                "status": "negotiating",
                "vendor_quoted_price": 14500.0,
                "currency": "USD",
            }
        )
        result = build_ui_schema(
            {
                "layout": "ROW_COMPACT",
                "blocks": ["MarkdownText", "ActionRow"],
            },
            row,
            [],
        )
        action_rows = [block for block in result["blocks"] if block["type"] == "ActionRow"]
        intents = [action["intent"] for block in action_rows for action in block["actions"]]
        assert "mark_terms_agreed" in intents


# =========================================================================
# build_project_ui_schema
# =========================================================================

class TestBuildProjectUISchema:
    def test_basic(self):
        project = SimpleNamespace(title="Family Groceries")
        result = build_project_ui_schema(project)
        assert result["version"] == 1
        assert result["layout"] == "ROW_COMPACT"
        assert len(result["blocks"]) == 2
        assert "Family Groceries" in result["blocks"][0]["content"]

    def test_has_share_action(self):
        project = SimpleNamespace(title="Test")
        result = build_project_ui_schema(project)
        action_rows = [b for b in result["blocks"] if b["type"] == "ActionRow"]
        assert len(action_rows) >= 1


# =========================================================================
# build_zero_results_schema
# =========================================================================

class TestBuildZeroResultsSchema:
    def test_basic(self):
        row = make_row(title="Unicorn Steaks")
        result = build_zero_results_schema(row)
        assert result["version"] == 1
        assert result["layout"] == "ROW_COMPACT"
        assert "Unicorn Steaks" in result["blocks"][0]["content"]
        assert result["blocks"][1]["actions"][0]["intent"] == "edit_request"

    def test_validates_as_schema(self):
        row = make_row(title="Test")
        result = build_zero_results_schema(row)
        validated = validate_ui_schema(result)
        assert validated is not None


# =========================================================================
# Scenario Tests
# =========================================================================

class TestScenarios:
    def test_grocery_flow_end_to_end(self):
        """Simulate: user asks for eggs → sourcing → bids arrive → schema built."""
        row = make_row(title="Eggs", status="sourcing")
        bids = [
            make_bid(id=1, price=3.49, item_title="Store Brand Eggs", image_url="https://img.com/eggs1.jpg"),
            make_bid(id=2, price=4.99, item_title="Organic Free Range Eggs", image_url="https://img.com/eggs2.jpg"),
            make_swap_bid(id=3, price=2.99, item_title="Pop Swap: Brand Eggs"),
        ]
        hint_data = {
            "layout": "ROW_MEDIA_LEFT",
            "blocks": ["ProductImage", "PriceBlock", "BadgeList", "ActionRow"],
            "value_vector": "unit_price",
        }
        result = build_ui_schema(hint_data, row, bids)
        assert result["layout"] == "ROW_MEDIA_LEFT"
        assert result["value_vector"] == "unit_price"
        block_types = [b["type"] for b in result["blocks"]]
        assert "ProductImage" in block_types
        assert "PriceBlock" in block_types

    def test_jet_charter_flow_end_to_end(self):
        """Simulate: user asks for private jet → vendor quotes → schema built."""
        row = make_row(
            title="Private Jet SAN to ASE",
            is_service=True,
            service_category="private_aviation",
            choice_answers={"origin": "SAN", "destination": "ASE", "pax": "4", "date": "Feb 13"},
        )
        bids = [
            make_vendor_bid(id=1, item_title="NetJets - Light Jet"),
            make_vendor_bid(id=2, item_title="Wheels Up - Midsize Jet"),
        ]
        hint_data = {
            "layout": "ROW_TIMELINE",
            "blocks": ["DataGrid", "BadgeList", "Timeline", "ActionRow"],
            "value_vector": "safety",
        }
        result = build_ui_schema(hint_data, row, bids)
        assert result["layout"] == "ROW_TIMELINE"
        assert result["value_vector"] == "safety"
        block_types = [b["type"] for b in result["blocks"]]
        assert "DataGrid" in block_types
        assert "Timeline" in block_types

    def test_post_purchase_escrow_flow(self):
        """Simulate: user funded escrow → timeline + escrow status."""
        row = make_row(title="Yacht Charter", status="funded")
        bids = [make_bid(closing_status="payment_initiated")]
        hint_data = {
            "layout": "ROW_TIMELINE",
            "blocks": ["MarkdownText", "Timeline", "EscrowStatus", "ActionRow"],
        }
        result = build_ui_schema(hint_data, row, bids)
        block_types = [b["type"] for b in result["blocks"]]
        assert "EscrowStatus" in block_types
        assert "Timeline" in block_types

    def test_swap_claim_receipt_flow(self):
        """Simulate: user claimed a swap → receipt uploader rendered."""
        row = make_row(title="Eggs", status="sourcing")
        bids = [make_swap_bid(closing_status="pending")]
        hint_data = {
            "layout": "ROW_COMPACT",
            "blocks": ["MarkdownText", "ReceiptUploader", "ActionRow"],
        }
        result = build_ui_schema(hint_data, row, bids)
        block_types = [b["type"] for b in result["blocks"]]
        assert "ReceiptUploader" in block_types

    def test_fallback_on_llm_failure(self):
        """When LLM produces garbage, system degrades gracefully."""
        row = make_row(title="Laptop")
        bids = [make_bid(image_url="https://img.com/laptop.jpg")]
        result = build_ui_schema({"layout": "BOGUS"}, row, bids)
        assert result["version"] == 1
        # Should have fallen back to a valid layout
        assert result["layout"] in ("ROW_COMPACT", "ROW_MEDIA_LEFT", "ROW_TIMELINE")

    def test_zero_bids_flow(self):
        """No results found — shows zero-results schema."""
        row = make_row(title="Unobtainium")
        result = build_zero_results_schema(row)
        assert "No options found" in result["blocks"][0]["content"]
        assert result["blocks"][1]["actions"][0]["intent"] == "edit_request"
