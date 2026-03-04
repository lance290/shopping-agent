"""
Tests for individual SDUI block hydrators.
Extracted from test_sdui_builder.py to keep files under 450 lines.
"""

import pytest
import sys
import os
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sdui_builder import (
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
)


# ---------------------------------------------------------------------------
# Helpers: mock Row / Bid objects (duplicated from test_sdui_builder.py)
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
# Individual Block Hydrators
# =========================================================================

class TestHydrateProductImage:
    def test_returns_first_bid_image(self):
        bids = [make_bid(image_url="https://img.com/1.jpg"), make_bid(image_url="https://img.com/2.jpg")]
        block = _hydrate_product_image(make_row(), bids)
        assert block is not None
        assert block.url == "https://img.com/1.jpg"

    def test_skips_bids_without_images(self):
        bids = [make_bid(image_url=None), make_bid(image_url="https://img.com/2.jpg")]
        block = _hydrate_product_image(make_row(), bids)
        assert block.url == "https://img.com/2.jpg"

    def test_returns_none_if_no_images(self):
        bids = [make_bid(image_url=None)]
        block = _hydrate_product_image(make_row(), bids)
        assert block is None

    def test_empty_bids(self):
        block = _hydrate_product_image(make_row(), [])
        assert block is None


class TestHydratePriceBlock:
    def test_returns_top_bid_price(self):
        bids = [make_bid(price=19.99)]
        block = _hydrate_price_block(make_row(), bids)
        assert block is not None
        assert block.amount == 19.99

    def test_quote_based_when_all_none(self):
        bids = [make_bid(price=None)]
        block = _hydrate_price_block(make_row(), bids)
        assert block is not None
        assert block.amount is None
        assert "Quote" in block.label

    def test_empty_bids(self):
        block = _hydrate_price_block(make_row(), [])
        assert block is None


class TestHydrateDataGrid:
    def test_from_choice_answers(self):
        row = make_row(choice_answers={"origin": "SAN", "destination": "ASE", "pax": "4"})
        block = _hydrate_data_grid(row, [])
        assert block is not None
        assert len(block.items) == 3

    def test_no_choice_answers(self):
        row = make_row(choice_answers=None)
        block = _hydrate_data_grid(row, [])
        assert block is None

    def test_empty_dict_choice_answers(self):
        row = make_row(choice_answers={})
        block = _hydrate_data_grid(row, [])
        assert block is None

    def test_max_12_items(self):
        answers = {f"key_{i}": f"val_{i}" for i in range(20)}
        row = make_row(choice_answers=answers)
        block = _hydrate_data_grid(row, [])
        assert block is not None
        assert len(block.items) <= 12


class TestHydrateFeatureList:
    def test_from_provenance(self):
        bid = make_bid(provenance={"matched_features": ["Organic", "Non-GMO"]})
        block = _hydrate_feature_list(make_row(), [bid])
        assert block is not None
        assert "Organic" in block.features

    def test_no_provenance(self):
        bid = make_bid(provenance=None)
        block = _hydrate_feature_list(make_row(), [bid])
        assert block is None

    def test_deduplicates(self):
        bids = [
            make_bid(provenance={"matched_features": ["A", "B"]}),
            make_bid(provenance={"matched_features": ["B", "C"]}),
        ]
        block = _hydrate_feature_list(make_row(), bids)
        assert block is not None
        assert block.features == ["A", "B", "C"]


class TestHydrateBadgeList:
    def test_includes_status(self):
        row = make_row(status="sourcing")
        block = _hydrate_badge_list(row, [])
        assert block is not None
        assert "Sourcing" in block.tags

    def test_includes_source_badges(self):
        bids = [make_bid(source="rainforest"), make_bid(source="ebay_browse")]
        block = _hydrate_badge_list(make_row(), bids)
        assert block is not None
        assert any("Rainforest" in t for t in block.tags)

    def test_includes_pop_swap_badge(self):
        bids = [make_swap_bid()]
        block = _hydrate_badge_list(make_row(), bids)
        assert "Pop Swap" in block.tags

    def test_manual_source_excluded(self):
        bids = [make_bid(source="manual")]
        block = _hydrate_badge_list(make_row(), bids)
        # "manual" should not appear as a badge
        assert not any("Manual" in t for t in block.tags)


class TestHydrateMarkdownText:
    def test_bold_title(self):
        row = make_row(title="Organic Eggs")
        block = _hydrate_markdown_text(row, [])
        assert block is not None
        assert block.content == "**Organic Eggs**"


class TestHydrateTimeline:
    def test_sourcing_state(self):
        row = make_row(status="sourcing")
        block = _hydrate_timeline(row, [])
        assert block is not None
        assert block.steps[0].label == "Sourcing"
        assert block.steps[0].status == "active"

    def test_funded_state(self):
        row = make_row(status="funded")
        block = _hydrate_timeline(row, [])
        assert block is not None
        # Steps before "funded" should be done
        funded_idx = next(i for i, s in enumerate(block.steps) if s.label == "Funded")
        for s in block.steps[:funded_idx]:
            assert s.status == "done"
        assert block.steps[funded_idx].status == "active"

    def test_unknown_status_falls_back(self):
        row = make_row(status="custom_state")
        block = _hydrate_timeline(row, [])
        assert block is not None
        assert len(block.steps) == 1
        assert block.steps[0].status == "active"


class TestHydrateMessageList:
    def test_from_chat_history(self):
        row = make_row(chat_history=[
            {"role": "user", "content": "I need eggs"},
            {"role": "assistant", "content": "I'll find some!"},
        ])
        block = _hydrate_message_list(row, [])
        assert block is not None
        assert len(block.messages) == 2

    def test_no_chat_history(self):
        row = make_row(chat_history=None)
        block = _hydrate_message_list(row, [])
        assert block is None

    def test_empty_chat_history(self):
        row = make_row(chat_history=[])
        block = _hydrate_message_list(row, [])
        assert block is None

    def test_truncates_to_last_3(self):
        row = make_row(chat_history=[
            {"role": "user", "content": f"msg {i}"} for i in range(10)
        ])
        block = _hydrate_message_list(row, [])
        assert block is not None
        assert len(block.messages) == 3


class TestHydrateChoiceFactorForm:
    def test_with_factors(self):
        row = make_row(choice_factors=[
            {"name": "brand", "label": "Brand", "type": "text"},
        ])
        block = _hydrate_choice_factor_form(row, [])
        assert block is not None
        assert len(block.factors) == 1

    def test_no_factors(self):
        row = make_row(choice_factors=None)
        block = _hydrate_choice_factor_form(row, [])
        assert block is None


class TestHydrateActionRow:
    def test_affiliate_action_for_url_bid(self):
        bids = [make_bid(item_url="https://amazon.com/product")]
        block = _hydrate_action_row(make_row(), bids)
        assert block is not None
        assert block.actions[0].intent == "outbound_affiliate"

    def test_contact_action_for_mailto_bid(self):
        bids = [make_vendor_bid(item_url="mailto:vendor@example.com")]
        block = _hydrate_action_row(make_row(), bids)
        assert block is not None
        assert block.actions[0].intent == "contact_vendor"

    def test_view_all_when_over_cap(self):
        row = make_row()
        bids = [make_bid(id=i) for i in range(35)]
        block = _hydrate_action_row(row, bids)
        assert block is not None
        intents = [a.intent for a in block.actions]
        assert "view_all_bids" in intents

    def test_edit_request_when_no_bids(self):
        block = _hydrate_action_row(make_row(), [])
        assert block is not None
        assert block.actions[0].intent == "edit_request"


class TestHydrateReceiptUploader:
    def test_renders_for_claimed_swap(self):
        bid = make_swap_bid(closing_status="pending")
        block = _hydrate_receipt_uploader(make_row(), [bid])
        assert block is not None
        assert block.type == "ReceiptUploader"

    def test_no_render_without_pending_swap(self):
        bid = make_bid(is_swap=False, closing_status="pending")
        block = _hydrate_receipt_uploader(make_row(), [bid])
        assert block is None

    def test_no_render_without_swap(self):
        bid = make_bid()
        block = _hydrate_receipt_uploader(make_row(), [bid])
        assert block is None


class TestHydrateEscrowStatus:
    def test_renders_for_payment_initiated(self):
        bid = make_bid(closing_status="payment_initiated")
        block = _hydrate_escrow_status(make_row(), [bid])
        assert block is not None
        assert block.type == "EscrowStatus"

    def test_renders_for_paid(self):
        bid = make_bid(closing_status="paid")
        block = _hydrate_escrow_status(make_row(), [bid])
        assert block is not None

    def test_no_render_for_pending(self):
        bid = make_bid(closing_status="pending")
        block = _hydrate_escrow_status(make_row(), [bid])
        assert block is None

    def test_no_render_for_none(self):
        bid = make_bid(closing_status=None)
        block = _hydrate_escrow_status(make_row(), [bid])
        assert block is None
