"""
Tests for individual SDUI schema block types.
Extracted from test_sdui_schema.py to keep files under 450 lines.
"""

import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sdui_schema import (
    MAX_ACTION_ROW_ACTIONS,
    MAX_DATAGRID_ITEMS,
    MAX_MARKDOWN_LENGTH,
    ACTION_INTENTS,
    ActionObject,
    ActionRowBlock,
    BadgeListBlock,
    ChoiceFactorFormBlock,
    DataGridBlock,
    DataGridItem,
    EscrowStatusBlock,
    FeatureListBlock,
    MarkdownTextBlock,
    MessageItem,
    MessageListBlock,
    PriceBlock,
    ProductImageBlock,
    ReceiptUploaderBlock,
    TimelineBlock,
    TimelineStep,
    WalletLedgerBlock,
)


# =========================================================================
# Display Primitives
# =========================================================================

class TestProductImageBlock:
    def test_valid(self):
        b = ProductImageBlock(url="https://img.com/a.jpg", alt="Product A")
        assert b.type == "ProductImage"
        assert b.url == "https://img.com/a.jpg"
        assert b.alt == "Product A"

    def test_default_alt(self):
        b = ProductImageBlock(url="https://img.com/b.jpg")
        assert b.alt == ""


class TestPriceBlock:
    def test_valid(self):
        b = PriceBlock(amount=29.99, currency="USD", label="Total")
        assert b.type == "PriceBlock"
        assert b.amount == 29.99

    def test_null_price_quote_based(self):
        b = PriceBlock(amount=None, label="Request Quote")
        assert b.amount is None

    def test_zero_price_free(self):
        b = PriceBlock(amount=0.0, label="Free")
        assert b.amount == 0.0

    def test_defaults(self):
        b = PriceBlock()
        assert b.currency == "USD"
        assert b.label == "Total"


class TestDataGridBlock:
    def test_valid(self):
        items = [DataGridItem(key="Origin", value="SAN"), DataGridItem(key="Dest", value="ASE")]
        b = DataGridBlock(items=items)
        assert b.type == "DataGrid"
        assert len(b.items) == 2

    def test_empty_items(self):
        b = DataGridBlock(items=[])
        assert len(b.items) == 0

    def test_max_items_enforced(self):
        items = [DataGridItem(key=f"k{i}", value=f"v{i}") for i in range(20)]
        b = DataGridBlock(items=items)
        assert len(b.items) == MAX_DATAGRID_ITEMS


class TestFeatureListBlock:
    def test_valid(self):
        b = FeatureListBlock(features=["Organic", "Non-GMO", "Gluten Free"])
        assert b.type == "FeatureList"
        assert len(b.features) == 3

    def test_empty(self):
        b = FeatureListBlock()
        assert b.features == []


class TestBadgeListBlock:
    def test_valid(self):
        b = BadgeListBlock(tags=["Pop Swap", "Organic"])
        assert b.type == "BadgeList"
        assert "Pop Swap" in b.tags

    def test_source_refs(self):
        b = BadgeListBlock(tags=["Safest Jet"], source_refs=["vendor_safety_db_44"])
        assert b.source_refs == ["vendor_safety_db_44"]

    def test_no_source_refs(self):
        b = BadgeListBlock(tags=["Tag"])
        assert b.source_refs is None


class TestMarkdownTextBlock:
    def test_valid(self):
        b = MarkdownTextBlock(content="**Hello**")
        assert b.type == "MarkdownText"
        assert b.content == "**Hello**"

    def test_truncates_at_500(self):
        long_text = "x" * 600
        b = MarkdownTextBlock(content=long_text)
        assert len(b.content) == MAX_MARKDOWN_LENGTH

    def test_empty(self):
        b = MarkdownTextBlock()
        assert b.content == ""


# =========================================================================
# Interactive Primitives
# =========================================================================

class TestTimelineBlock:
    def test_valid(self):
        steps = [
            TimelineStep(label="Sourcing", status="done"),
            TimelineStep(label="Comparing", status="active"),
            TimelineStep(label="Negotiating", status="pending"),
        ]
        b = TimelineBlock(steps=steps)
        assert b.type == "Timeline"
        assert len(b.steps) == 3
        assert b.steps[0].status == "done"

    def test_invalid_status_raises(self):
        with pytest.raises(Exception):
            TimelineStep(label="X", status="invalid_status")

    def test_empty_steps(self):
        b = TimelineBlock()
        assert b.steps == []


class TestMessageListBlock:
    def test_valid(self):
        msgs = [
            MessageItem(sender="user", text="I need a jet"),
            MessageItem(sender="assistant", text="Let me find options"),
        ]
        b = MessageListBlock(messages=msgs)
        assert b.type == "MessageList"
        assert len(b.messages) == 2

    def test_empty(self):
        b = MessageListBlock()
        assert b.messages == []


class TestChoiceFactorFormBlock:
    def test_valid(self):
        factors = [
            {"name": "brand", "label": "Preferred Brand", "type": "text"},
            {"name": "budget", "label": "Budget", "type": "number"},
        ]
        b = ChoiceFactorFormBlock(factors=factors)
        assert b.type == "ChoiceFactorForm"
        assert len(b.factors) == 2


class TestActionRowBlock:
    def test_valid(self):
        actions = [
            ActionObject(label="Buy on Amazon", intent="outbound_affiliate", bid_id="123"),
        ]
        b = ActionRowBlock(actions=actions)
        assert b.type == "ActionRow"
        assert len(b.actions) == 1

    def test_max_actions_enforced(self):
        actions = [
            ActionObject(label=f"Action {i}", intent="view_raw") for i in range(5)
        ]
        b = ActionRowBlock(actions=actions)
        assert len(b.actions) == MAX_ACTION_ROW_ACTIONS

    def test_empty_actions(self):
        b = ActionRowBlock()
        assert b.actions == []


class TestActionObject:
    def test_valid_intents(self):
        for intent in ACTION_INTENTS:
            a = ActionObject(label="Test", intent=intent)
            assert a.intent == intent

    def test_invalid_intent_raises(self):
        with pytest.raises(Exception):
            ActionObject(label="Test", intent="invalid_intent")

    def test_affiliate_with_bid_id(self):
        a = ActionObject(
            label="Buy",
            intent="outbound_affiliate",
            bid_id="uuid-123",
            url="https://amazon.com/product",
            merchant_id="amazon",
            product_id="ASIN123",
        )
        assert a.bid_id == "uuid-123"
        assert a.url == "https://amazon.com/product"

    def test_tip_with_amount(self):
        a = ActionObject(label="Tip $5", intent="send_tip", amount=5.0)
        assert a.amount == 5.0

    def test_view_all_with_count(self):
        a = ActionObject(label="View All (42)", intent="view_all_bids", count=42)
        assert a.count == 42


# =========================================================================
# State-Driven Primitives
# =========================================================================

class TestReceiptUploaderBlock:
    def test_valid(self):
        b = ReceiptUploaderBlock(campaign_id="camp_123")
        assert b.type == "ReceiptUploader"
        assert b.campaign_id == "camp_123"


class TestWalletLedgerBlock:
    def test_valid(self):
        b = WalletLedgerBlock()
        assert b.type == "WalletLedger"


class TestEscrowStatusBlock:
    def test_valid(self):
        b = EscrowStatusBlock(deal_id="deal_456")
        assert b.type == "EscrowStatus"
        assert b.deal_id == "deal_456"
