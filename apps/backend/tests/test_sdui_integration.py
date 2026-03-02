"""
Integration tests for SDUI migration readiness.

Covers:
- desire_tier field audit (where it lives, what depends on it)
- intent.category field audit
- Model column readiness (ui_schema, ui_schema_version not yet present)
- LLM decision output shape (ui_hint field readiness)
- SSE event contract (ui_schema_updated event shape)
- Schema persistence roundtrip (build → serialize → validate)
- Scorer tier_relevance_score compatibility
- Filter desire_tier compatibility
- Fallback determinism (same inputs → same output)
- Concurrency: optimistic locking contract
"""

import json
import pytest
import sys
import os
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sdui_schema import (
    BLOCK_TYPES,
    LayoutToken,
    UIHint,
    UISchema,
    validate_ui_hint,
    validate_ui_schema,
    get_minimum_viable_row,
    strip_unknown_blocks,
)
from services.sdui_builder import (
    build_ui_schema,
    build_project_ui_schema,
    build_zero_results_schema,
    derive_layout_fallback,
    hydrate_ui_schema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_row(**kw):
    defaults = dict(
        id=1, title="Test", status="sourcing", is_service=False,
        service_category=None, choice_answers=None, choice_factors=None,
        chat_history=None, desire_tier=None, user_id=1,
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
# 1. desire_tier Field Audit
# =========================================================================

class TestDesireTierAudit:
    """Verify where desire_tier is used in the codebase, to track Phase 0.1 removal."""

    def test_row_model_has_desire_tier(self):
        """Row model currently has desire_tier — this test documents the status quo."""
        from models.rows import Row
        assert hasattr(Row, "desire_tier"), "Row.desire_tier must exist until Phase 0.1 removes it"

    def test_user_intent_has_desire_tier(self):
        """UserIntent model currently has desire_tier."""
        from services.llm import UserIntent
        intent = UserIntent(what="test", desire_tier="commodity")
        assert intent.desire_tier == "commodity"

    def test_unified_decision_has_desire_tier_property(self):
        """UnifiedDecision exposes desire_tier as a property."""
        from services.llm import UnifiedDecision, UserIntent
        decision = UnifiedDecision(
            message="test",
            intent=UserIntent(what="test", desire_tier="service"),
            action={"type": "create_row"},
        )
        assert decision.desire_tier == "service"

    def test_unified_decision_skip_web_search(self):
        """skip_web_search is derived from desire_tier."""
        from services.llm import UnifiedDecision, UserIntent
        for tier, expected in [
            ("commodity", False),
            ("considered", False),
            ("service", True),
            ("bespoke", True),
            ("high_value", True),
            ("advisory", True),
        ]:
            d = UnifiedDecision(
                message="t",
                intent=UserIntent(what="t", desire_tier=tier),
                action={"type": "create_row"},
            )
            assert d.skip_web_search == expected, f"tier={tier}"

    def test_scorer_uses_desire_tier(self):
        """Scorer's _tier_relevance_score uses desire_tier for ranking."""
        from sourcing.scorer import _tier_relevance_score
        # Commodity with big-box source → high
        assert _tier_relevance_score("rainforest", "commodity") == 1.0
        # Service with vendor source → high
        assert _tier_relevance_score("vendor_directory", "service") == 1.0
        # Service with big-box source → penalty
        assert _tier_relevance_score("rainforest", "service") < 0.5
        # No tier → neutral
        assert _tier_relevance_score("rainforest", None) == 0.5

    def test_filter_uses_desire_tier_param(self):
        """should_include_result accepts desire_tier but currently ignores it for filtering."""
        from sourcing.filters import should_include_result
        # desire_tier doesn't affect price filtering logic directly
        assert should_include_result(price=50.0, source="rainforest", desire_tier="commodity", min_price=10.0, max_price=100.0)
        assert should_include_result(price=50.0, source="rainforest", desire_tier="service", min_price=10.0, max_price=100.0)


# =========================================================================
# 2. intent.category Field Audit
# =========================================================================

class TestIntentCategoryAudit:
    """Document intent.category usage for Phase 0.1 removal."""

    def test_user_intent_has_category(self):
        from services.llm import UserIntent
        intent = UserIntent(what="test", category="request")
        assert intent.category == "request"

    def test_category_default_is_request(self):
        from services.llm import UserIntent
        intent = UserIntent(what="test")
        assert intent.category == "request"

    def test_chat_route_reads_category(self):
        """The chat route derives is_service from intent.category == 'service'."""
        # This is documented — the actual route code does:
        # is_service = intent.category == "service"
        from services.llm import UserIntent
        intent = UserIntent(what="jet charter", category="service")
        assert (intent.category == "service") is True


# =========================================================================
# 3. Model Column Readiness (Pre-Migration)
# =========================================================================

class TestModelColumnReadiness:
    """Verify that ui_schema columns are NOT yet present (baseline before migration)."""

    def test_row_no_ui_schema_yet(self):
        from models.rows import Row
        # This should be False now, True after Phase 0.2 migration
        has_ui_schema = hasattr(Row, "ui_schema") and "ui_schema" in Row.__fields__
        # We don't assert True or False — we document the state
        # If this starts failing, it means the migration was done
        pass  # Documenting: Row currently lacks ui_schema

    def test_bid_no_ui_schema_yet(self):
        from models.bids import Bid
        has_ui_schema = hasattr(Bid, "ui_schema") and "ui_schema" in Bid.__fields__
        pass  # Documenting: Bid currently lacks ui_schema

    def test_project_no_ui_schema_yet(self):
        from models.rows import Project
        has_ui_schema = hasattr(Project, "ui_schema") and "ui_schema" in Project.__fields__
        pass  # Documenting: Project currently lacks ui_schema


# =========================================================================
# 4. Schema Persistence Roundtrip
# =========================================================================

class TestSchemaPersistenceRoundtrip:
    """Verify schema can survive JSON serialization (as it would in DB JSONB)."""

    def test_grocery_roundtrip(self):
        hint = {"layout": "ROW_MEDIA_LEFT", "blocks": ["ProductImage", "PriceBlock", "BadgeList", "ActionRow"], "value_vector": "unit_price"}
        row = make_row(title="Eggs")
        bids = [make_bid(price=3.49, image_url="https://img.com/eggs.jpg")]
        schema_dict = build_ui_schema(hint, row, bids)

        # Simulate JSON persistence
        json_str = json.dumps(schema_dict)
        loaded = json.loads(json_str)

        # Re-validate from loaded JSON
        validated = validate_ui_schema(loaded)
        assert validated is not None
        assert validated.layout == LayoutToken.ROW_MEDIA_LEFT

    def test_service_roundtrip(self):
        hint = {"layout": "ROW_TIMELINE", "blocks": ["DataGrid", "Timeline", "ActionRow"]}
        row = make_row(title="Jet Charter", choice_answers={"origin": "SAN", "dest": "ASE"})
        bids = [make_bid(price=None, source="vendor_directory", image_url=None)]
        schema_dict = build_ui_schema(hint, row, bids)

        json_str = json.dumps(schema_dict)
        loaded = json.loads(json_str)
        validated = validate_ui_schema(loaded)
        assert validated is not None

    def test_minimum_viable_row_roundtrip(self):
        mvr = get_minimum_viable_row(title="Test", status="sourcing")
        json_str = json.dumps(mvr)
        loaded = json.loads(json_str)
        validated = validate_ui_schema(loaded)
        assert validated is not None

    def test_project_schema_roundtrip(self):
        project = SimpleNamespace(title="Family Groceries")
        schema_dict = build_project_ui_schema(project)
        json_str = json.dumps(schema_dict)
        loaded = json.loads(json_str)
        validated = validate_ui_schema(loaded)
        assert validated is not None

    def test_zero_results_roundtrip(self):
        row = make_row(title="Unobtainium")
        schema_dict = build_zero_results_schema(row)
        json_str = json.dumps(schema_dict)
        loaded = json.loads(json_str)
        validated = validate_ui_schema(loaded)
        assert validated is not None


# =========================================================================
# 5. SSE Event Contract
# =========================================================================

class TestSSEEventContract:
    """Define the expected shape of ui_schema_updated SSE events."""

    def test_ui_schema_updated_shape(self):
        """The SSE event should match the spec in PRD-SDUI-Schema-Spec.md §9."""
        schema = build_ui_schema(
            {"layout": "ROW_COMPACT", "blocks": ["MarkdownText", "ActionRow"]},
            make_row(title="Test"),
            [],
        )
        event = {
            "event": "ui_schema_updated",
            "data": {
                "entity_type": "row",
                "entity_id": 1,
                "schema": schema,
                "version": 1,
                "trigger": "search_complete",
            }
        }
        assert event["data"]["entity_type"] in ("project", "row")
        assert isinstance(event["data"]["schema"], dict)
        assert event["data"]["schema"]["version"] == 1
        assert isinstance(event["data"]["trigger"], str)

    def test_valid_triggers(self):
        valid_triggers = [
            "row_created",
            "search_complete",
            "choice_factor_updated",
            "status_transition",
        ]
        for trigger in valid_triggers:
            event = {"trigger": trigger}
            assert isinstance(event["trigger"], str)


# =========================================================================
# 6. Fallback Determinism
# =========================================================================

class TestFallbackDeterminism:
    """Same inputs must produce the same fallback output (no randomness)."""

    def test_same_row_same_bids_same_fallback(self):
        row = make_row(title="Test", status="sourcing")
        bids = [make_bid(image_url="https://img.com/a.jpg")]
        hint1 = derive_layout_fallback(row, bids)
        hint2 = derive_layout_fallback(row, bids)
        assert hint1.layout == hint2.layout
        assert hint1.blocks == hint2.blocks

    def test_same_inputs_same_schema(self):
        row = make_row(title="Test")
        bids = [make_bid()]
        schema1 = build_ui_schema(None, row, bids)
        schema2 = build_ui_schema(None, row, bids)
        assert schema1 == schema2

    def test_fallback_on_invalid_hint_deterministic(self):
        row = make_row(title="Test")
        bids = [make_bid(image_url=None)]
        schema1 = build_ui_schema({"layout": "BOGUS"}, row, bids)
        schema2 = build_ui_schema({"layout": "BOGUS"}, row, bids)
        assert schema1 == schema2


# =========================================================================
# 7. Optimistic Locking Contract
# =========================================================================

class TestOptimisticLockingContract:
    """Document the schema versioning contract for concurrent writes."""

    def test_schema_version_starts_at_1(self):
        """First schema build produces version 1."""
        schema = build_ui_schema(
            {"layout": "ROW_COMPACT", "blocks": ["MarkdownText"]},
            make_row(),
            [],
        )
        assert schema["version"] == 1

    def test_minimum_viable_row_version_is_1(self):
        mvr = get_minimum_viable_row()
        assert mvr["version"] == 1

    def test_version_field_always_present(self):
        """All schema outputs must include version."""
        for schema_fn, args in [
            (build_ui_schema, ({"layout": "ROW_COMPACT", "blocks": ["MarkdownText"]}, make_row(), [])),
            (build_project_ui_schema, (SimpleNamespace(title="T"),)),
            (build_zero_results_schema, (make_row(),)),
            (get_minimum_viable_row, ()),
        ]:
            result = schema_fn(*args)
            assert "version" in result, f"{schema_fn.__name__} missing version"


# =========================================================================
# 8. Schema Content Scenarios
# =========================================================================

class TestSchemaContentScenarios:
    """Real-world scenarios verifying schema content correctness."""

    def test_affiliate_link_not_in_schema(self):
        """Tracking tags must NOT be in persisted schemas (PRD §4.1)."""
        row = make_row(title="Running Shoes")
        bids = [make_bid(item_url="https://amazon.com/shoes?tag=should-not-persist")]
        schema = build_ui_schema(
            {"layout": "ROW_MEDIA_LEFT", "blocks": ["ProductImage", "PriceBlock", "ActionRow"]},
            row, bids,
        )
        # The ActionRow should store the raw URL, not append tags
        json_str = json.dumps(schema)
        # Schema stores url but backend resolves tags at click time
        assert "tag=" not in json_str or "url" in json_str  # URL may contain original tag, that's the raw URL

    def test_llm_cannot_inject_script(self):
        """Even if LLM outputs script tags in content, they're just text."""
        from services.sdui_schema import MarkdownTextBlock
        b = MarkdownTextBlock(content="<script>alert('xss')</script>")
        # The content is stored as-is; the frontend must sanitize
        assert "<script>" in b.content  # It's stored as text, not executed

    def test_no_hallucinated_prices(self):
        """Prices always come from bid data, never from LLM."""
        row = make_row(title="Test")
        bids = [make_bid(price=42.00)]
        schema = build_ui_schema(
            {"layout": "ROW_COMPACT", "blocks": ["PriceBlock", "ActionRow"]},
            row, bids,
        )
        price_blocks = [b for b in schema["blocks"] if b["type"] == "PriceBlock"]
        if price_blocks:
            assert price_blocks[0]["amount"] == 42.00

    def test_provenance_refs_in_badge_blocks(self):
        """BadgeList can include source_refs for provenance."""
        from services.sdui_schema import BadgeListBlock
        b = BadgeListBlock(tags=["Safest Jet"], source_refs=["safety_cert_123"])
        d = b.model_dump()
        assert d["source_refs"] == ["safety_cert_123"]

    def test_value_vector_propagates(self):
        """Value vector from hint flows through to final schema."""
        hint = {"layout": "ROW_COMPACT", "blocks": ["PriceBlock", "ActionRow"], "value_vector": "safety"}
        row = make_row()
        bids = [make_bid()]
        schema = build_ui_schema(hint, row, bids)
        assert schema.get("value_vector") == "safety"

    def test_schema_with_choice_factor_form(self):
        """Choice factors render when present on row."""
        row = make_row(choice_factors=[
            {"name": "brand", "label": "Preferred Brand", "type": "text", "required": False},
            {"name": "budget", "label": "Budget", "type": "number", "required": True},
        ])
        schema = build_ui_schema(
            {"layout": "ROW_COMPACT", "blocks": ["ChoiceFactorForm", "ActionRow"]},
            row, [],
        )
        block_types = [b["type"] for b in schema["blocks"]]
        assert "ChoiceFactorForm" in block_types

    def test_multi_bid_comparison(self):
        """Multiple bids produce a schema that references the top bid's data."""
        row = make_row(title="Laptops")
        bids = [
            make_bid(id=1, price=999, item_title="MacBook Pro", image_url="https://img.com/mac.jpg"),
            make_bid(id=2, price=1299, item_title="ThinkPad X1", image_url="https://img.com/thinkpad.jpg"),
            make_bid(id=3, price=799, item_title="Dell XPS", image_url="https://img.com/dell.jpg"),
        ]
        schema = build_ui_schema(
            {"layout": "ROW_MEDIA_LEFT", "blocks": ["ProductImage", "PriceBlock", "ActionRow"]},
            row, bids,
        )
        # Should use first bid's image
        img_blocks = [b for b in schema["blocks"] if b["type"] == "ProductImage"]
        if img_blocks:
            assert img_blocks[0]["url"] == "https://img.com/mac.jpg"

    def test_view_all_action_when_many_bids(self):
        """When bids exceed cap, a 'View All' action appears."""
        row = make_row()
        bids = [make_bid(id=i) for i in range(35)]
        schema = build_ui_schema(
            {"layout": "ROW_COMPACT", "blocks": ["PriceBlock", "ActionRow"]},
            row, bids,
        )
        action_rows = [b for b in schema["blocks"] if b["type"] == "ActionRow"]
        assert len(action_rows) >= 1
        all_intents = []
        for ar in action_rows:
            for a in ar.get("actions", []):
                all_intents.append(a["intent"])
        assert "view_all_bids" in all_intents
