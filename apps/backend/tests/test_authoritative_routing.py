"""Regression tests for authoritative LLM routing, adapter-family enforcement,
discovery mode selection, and the cheap LLM reranker.

Covers:
  - Phase 1: LLM execution_mode is authoritative when present and confident
  - Phase 2: Adapter-family isolation (sourcing_only excludes affiliates, affiliate_only excludes vendors)
  - Phase 3: Reranker triggers only for high-risk/specialist/local flows
  - Phase 4: Known bad query replay — routing, locality, source-type regressions
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.rows import Row
from sourcing.models import LocationContext, LocationTargets, SearchIntent
from sourcing.discovery.classifier import (
    classify_search_path,
    execution_mode_for_row,
    select_discovery_mode,
    _llm_execution_mode,
)
from sourcing.reranker import should_rerank, _build_rerank_prompt, _clamp, rerank_candidates
from sourcing.models import NormalizedResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _intent(
    raw_input: str = "",
    execution_mode: str = None,
    search_strategies: list = None,
    source_archetypes: list = None,
    confidence: float = 0.9,
    relevance: str = "none",
    category: str = "general",
    targets: dict = None,
) -> SearchIntent:
    loc_targets = LocationTargets(**(targets or {}))
    return SearchIntent(
        product_category=category,
        raw_input=raw_input,
        keywords=raw_input.split() if raw_input else [],
        confidence=confidence,
        execution_mode=execution_mode,
        search_strategies=search_strategies or [],
        source_archetypes=source_archetypes or [],
        location_context=LocationContext(
            relevance=relevance,
            confidence=confidence,
            targets=loc_targets,
        ),
    )


def _row(
    desire_tier: str = "commodity",
    is_service: bool = False,
    service_category: str = None,
    routing_mode: str = None,
) -> Row:
    r = Row(
        title="test",
        desire_tier=desire_tier,
        is_service=is_service,
        service_category=service_category,
    )
    if routing_mode:
        r.routing_mode = routing_mode
    return r


# ===========================================================================
# Phase 1: LLM execution_mode is authoritative
# ===========================================================================

class TestLLMAuthoritative:
    """LLM execution_mode takes precedence when valid and confident."""

    def test_llm_affiliate_only_overrides_service_tier(self):
        """Even if desire_tier is 'service', LLM affiliate_only wins."""
        intent = _intent(execution_mode="affiliate_only", confidence=0.9)
        row = _row(desire_tier="service", is_service=True)
        assert classify_search_path(intent, row) == "commodity_marketplace_path"

    def test_llm_sourcing_only_overrides_commodity_tier(self):
        """LLM says sourcing_only even though desire_tier is commodity."""
        intent = _intent(execution_mode="sourcing_only", confidence=0.9)
        row = _row(desire_tier="commodity")
        assert classify_search_path(intent, row) == "vendor_discovery_path"

    def test_llm_affiliate_plus_sourcing_routes_to_discovery(self):
        """Hybrid mode routes to vendor_discovery_path (handled specially in service)."""
        intent = _intent(execution_mode="affiliate_plus_sourcing", confidence=0.9)
        row = _row(desire_tier="considered")
        assert classify_search_path(intent, row) == "vendor_discovery_path"

    def test_low_confidence_falls_back_to_heuristics(self):
        """When confidence < threshold, LLM mode is ignored and heuristics run."""
        intent = _intent(execution_mode="affiliate_only", confidence=0.3)
        row = _row(desire_tier="service", is_service=True)
        # Heuristic: service tier -> vendor_discovery_path
        assert classify_search_path(intent, row) == "vendor_discovery_path"

    def test_invalid_execution_mode_falls_back(self):
        """Invalid mode string is ignored."""
        intent = _intent(execution_mode="invalid_mode", confidence=0.9)
        row = _row(desire_tier="commodity")
        assert classify_search_path(intent, row) == "commodity_marketplace_path"

    def test_none_execution_mode_uses_heuristics(self):
        """When no execution_mode, classic heuristics apply."""
        intent = _intent(confidence=0.9)
        row = _row(desire_tier="high_value")
        assert classify_search_path(intent, row) == "vendor_discovery_path"

    def test_execution_mode_for_row_returns_llm_mode(self):
        intent = _intent(execution_mode="affiliate_plus_sourcing", confidence=0.85)
        row = _row(desire_tier="considered")
        assert execution_mode_for_row(intent, row) == "affiliate_plus_sourcing"

    def test_execution_mode_for_row_fallback(self):
        intent = _intent(confidence=0.9)
        row = _row(desire_tier="bespoke")
        assert execution_mode_for_row(intent, row) == "sourcing_only"

    def test_execution_mode_for_row_commodity_fallback(self):
        intent = _intent(confidence=0.9)
        row = _row(desire_tier="commodity")
        assert execution_mode_for_row(intent, row) == "affiliate_only"


# ===========================================================================
# Phase 1: search_strategies drive discovery mode
# ===========================================================================

class TestSearchStrategies:
    """LLM search_strategies steer select_discovery_mode when present."""

    def test_specialist_first_with_aviation_text(self):
        intent = _intent(
            raw_input="private jet charter from SAN to EWR",
            search_strategies=["specialist_first"],
        )
        row = _row(desire_tier="service")
        assert select_discovery_mode(intent, row) == "asset_market_discovery"

    def test_specialist_first_with_real_estate_category(self):
        intent = _intent(
            raw_input="sell my belle meade mansion",
            search_strategies=["specialist_first"],
        )
        row = _row(desire_tier="service", service_category="real_estate")
        assert select_discovery_mode(intent, row) == "luxury_brokerage_discovery"

    def test_local_network_first(self):
        intent = _intent(
            raw_input="HVAC repair near me",
            search_strategies=["local_network_first"],
        )
        row = _row(desire_tier="service")
        assert select_discovery_mode(intent, row) == "local_service_discovery"

    def test_prestige_first_advisory(self):
        intent = _intent(
            raw_input="acquire a SaaS company",
            search_strategies=["prestige_first"],
        )
        row = _row(desire_tier="advisory")
        assert select_discovery_mode(intent, row) == "advisory_discovery"

    def test_prestige_first_non_advisory(self):
        intent = _intent(
            raw_input="luxury watch from trusted dealer",
            search_strategies=["prestige_first"],
        )
        row = _row(desire_tier="high_value")
        assert select_discovery_mode(intent, row) == "uhnw_goods_discovery"

    def test_official_first(self):
        intent = _intent(
            raw_input="FAA registered aircraft broker",
            search_strategies=["official_first"],
        )
        row = _row(desire_tier="high_value")
        assert select_discovery_mode(intent, row) == "advisory_discovery"

    def test_empty_strategies_uses_heuristic(self):
        intent = _intent(raw_input="custom engagement ring")
        row = _row(desire_tier="bespoke")
        # Heuristic: bespoke -> uhnw_goods_discovery
        assert select_discovery_mode(intent, row) == "uhnw_goods_discovery"


# ===========================================================================
# Phase 1: Heuristic fallback — broker token fix
# ===========================================================================

class TestBrokerTokenFix:
    """The bare 'broker' token no longer misclassifies non-aviation requests."""

    def test_insurance_broker_not_asset_market(self):
        """'insurance broker' should NOT route to asset_market_discovery."""
        intent = _intent(raw_input="insurance broker Nashville")
        row = _row(desire_tier="service", service_category="insurance")
        mode = select_discovery_mode(intent, row)
        assert mode != "asset_market_discovery"

    def test_real_estate_broker_routes_correctly(self):
        intent = _intent(raw_input="real estate broker Nashville")
        row = _row(desire_tier="service")
        assert select_discovery_mode(intent, row) == "luxury_brokerage_discovery"

    def test_jet_broker_still_asset_market(self):
        intent = _intent(raw_input="jet broker for Gulfstream G650")
        row = _row(desire_tier="high_value")
        assert select_discovery_mode(intent, row) == "asset_market_discovery"

    def test_yacht_broker_still_asset_market(self):
        intent = _intent(raw_input="yacht broker Mediterranean charter")
        row = _row(desire_tier="high_value")
        assert select_discovery_mode(intent, row) == "asset_market_discovery"


# ===========================================================================
# Phase 2: Adapter-family isolation
# ===========================================================================

class TestAdapterFamilyIsolation:
    """execution_mode controls which provider families run."""

    def test_sourcing_only_excludes_affiliates(self):
        """When mode is sourcing_only, classify_search_path -> vendor_discovery_path."""
        intent = _intent(execution_mode="sourcing_only", confidence=0.9)
        row = _row(desire_tier="service")
        assert classify_search_path(intent, row) == "vendor_discovery_path"

    def test_affiliate_only_excludes_vendor_directory(self):
        """When mode is affiliate_only, classify_search_path -> commodity_marketplace_path."""
        intent = _intent(execution_mode="affiliate_only", confidence=0.9)
        row = _row(desire_tier="commodity")
        assert classify_search_path(intent, row) == "commodity_marketplace_path"


# ===========================================================================
# Phase 3: Reranker trigger logic
# ===========================================================================

class TestRerankerTrigger:
    """should_rerank correctly identifies when to invoke the LLM reranker."""

    def test_sourcing_only_triggers_rerank(self):
        assert should_rerank(None, "service", "sourcing_only") is True

    def test_affiliate_plus_sourcing_triggers_rerank(self):
        assert should_rerank(None, "service", "affiliate_plus_sourcing") is True

    def test_affiliate_only_no_rerank(self):
        assert should_rerank(None, "commodity", "affiliate_only") is False

    def test_high_value_tier_triggers_rerank(self):
        assert should_rerank(None, "high_value", None) is True

    def test_advisory_tier_triggers_rerank(self):
        assert should_rerank(None, "advisory", "affiliate_only") is True

    def test_service_tier_triggers_rerank(self):
        assert should_rerank(None, "service", None) is True

    def test_bespoke_tier_triggers_rerank(self):
        assert should_rerank(None, "bespoke", None) is True

    def test_commodity_affiliate_no_rerank(self):
        assert should_rerank(None, "commodity", None) is False

    def test_specialist_strategy_triggers_rerank(self):
        intent = _intent(search_strategies=["specialist_first"])
        assert should_rerank(intent, "service", None) is True

    def test_local_network_strategy_triggers_rerank(self):
        intent = _intent(search_strategies=["local_network_first"])
        assert should_rerank(intent, "service", None) is True

    def test_prestige_strategy_triggers_rerank(self):
        intent = _intent(search_strategies=["prestige_first"])
        assert should_rerank(intent, "bespoke", None) is True

    def test_market_first_no_rerank(self):
        intent = _intent(search_strategies=["market_first"])
        assert should_rerank(intent, "commodity", None) is False

    def test_commodity_bypasses_rerank_even_in_sourcing_mode(self):
        assert should_rerank(None, "commodity", "sourcing_only") is False


# ===========================================================================
# Phase 3: Reranker prompt and scoring utilities
# ===========================================================================

class TestRerankerPrompt:
    def test_prompt_includes_query_and_candidates(self):
        candidates = [
            {"title": "Vendor A", "source": "vendor_directory", "domain": "a.com", "price": 100, "candidate_type": None},
            {"title": "Vendor B", "source": "vendor_directory", "domain": "b.com", "price": None, "candidate_type": "brokerage"},
        ]
        intent = _intent(raw_input="jet charter", source_archetypes=["brokerage"])
        prompt = _build_rerank_prompt("jet charter SAN to EWR", candidates, intent)
        assert "jet charter SAN to EWR" in prompt
        assert "Vendor A" in prompt
        assert "Vendor B" in prompt
        assert "brokerage" in prompt.lower()

    def test_prompt_includes_strict_brand_rule(self):
        candidates = [
            {
                "title": "Hermès",
                "source": "vendor_directory",
                "domain": "hermes.com",
                "price": None,
                "candidate_type": None,
                "category": "luxury handbags",
                "description": "Official maison for Birkin bags",
                "heuristic_score": 0.91,
            }
        ]
        intent = _intent(raw_input="Birkin bag")
        intent.brand = "Hermes"
        intent.product_name = "Birkin bag"
        prompt = _build_rerank_prompt("Birkin bag", candidates, intent)
        assert "STRICT BRAND MATCH" in prompt
        assert "Official maison for Birkin bags" in prompt

    def test_clamp_normal(self):
        assert _clamp(0.7) == 0.7

    def test_clamp_below(self):
        assert _clamp(-0.5) == 0.0

    def test_clamp_above(self):
        assert _clamp(1.5) == 1.0

    def test_clamp_invalid(self):
        assert _clamp("not_a_number") == 0.5


class TestRerankerExclusion:
    @pytest.mark.asyncio
    async def test_reranker_excludes_wrong_brand_candidate(self):
        results = [
            NormalizedResult(
                title="Hermès",
                url="https://hermes.com",
                source="vendor_directory",
                merchant_name="Hermès",
                merchant_domain="hermes.com",
                raw_data={"description": "Official maison for Birkin bags", "search_metadata": {"vendor_category": "luxury handbags"}},
                provenance={"score": {"combined": 0.91}},
            ),
            NormalizedResult(
                title="Goyard",
                url="https://goyard.com",
                source="vendor_directory",
                merchant_name="Goyard",
                merchant_domain="goyard.com",
                raw_data={"description": "Luxury trunks and handbags", "search_metadata": {"vendor_category": "luxury handbags"}},
                provenance={"score": {"combined": 0.89}},
            ),
        ]
        intent = _intent(raw_input="Birkin bag")
        intent.brand = "Hermes"
        intent.product_name = "Birkin bag"

        mock_response = [
            {"idx": 0, "include": True, "relevance": 0.98, "trust": 0.95, "actionability": 0.90, "reason_codes": ["brand_match"]},
            {"idx": 1, "include": False, "relevance": 0.10, "trust": 0.40, "actionability": 0.20, "reason_codes": ["wrong_brand"]},
        ]

        with patch("services.llm_core.call_gemini", new_callable=AsyncMock) as mock_call:
            with patch("services.llm_core._extract_json_array", return_value=mock_response):
                mock_call.return_value = "[]"
                reranked = await rerank_candidates("Birkin bag", results, intent)

        assert [r.title for r in reranked] == ["Hermès"]


# ===========================================================================
# Phase 4: Known bad query replays — routing regressions
# ===========================================================================

class TestKnownBadQueries:
    """Replay known bad queries that previously routed incorrectly."""

    def test_private_jet_charter_routes_sourcing(self):
        """Private jet charter must NEVER go to affiliate/Amazon path."""
        intent = _intent(
            raw_input="private jet charter from San Diego to Newark",
            execution_mode="sourcing_only",
            search_strategies=["specialist_first"],
            confidence=0.95,
            relevance="endpoint",
        )
        row = _row(desire_tier="service", service_category="private_aviation")
        assert classify_search_path(intent, row) == "vendor_discovery_path"
        assert execution_mode_for_row(intent, row) == "sourcing_only"

    def test_nashville_realtor_routes_sourcing(self):
        """Realtor search is sourcing, not affiliate."""
        intent = _intent(
            raw_input="realtors in Nashville for a $3M mansion",
            execution_mode="sourcing_only",
            search_strategies=["specialist_first", "local_network_first"],
            source_archetypes=["brokerage", "local_directory"],
            confidence=0.92,
            relevance="service_area",
            targets={"search_area": "Nashville, TN"},
        )
        row = _row(desire_tier="service", service_category="real_estate")
        assert classify_search_path(intent, row) == "vendor_discovery_path"
        assert execution_mode_for_row(intent, row) == "sourcing_only"
        assert select_discovery_mode(intent, row) == "luxury_brokerage_discovery"

    def test_running_shoes_routes_affiliate(self):
        """Running shoes is commodity, must NOT trigger vendor discovery."""
        intent = _intent(
            raw_input="running shoes Nike",
            execution_mode="affiliate_only",
            confidence=0.95,
        )
        row = _row(desire_tier="commodity")
        assert classify_search_path(intent, row) == "commodity_marketplace_path"
        assert execution_mode_for_row(intent, row) == "affiliate_only"

    def test_luxury_watch_hybrid_mode(self):
        """Luxury watch benefits from both marketplace and specialist discovery."""
        intent = _intent(
            raw_input="Rolex Submariner pre-owned",
            execution_mode="affiliate_plus_sourcing",
            search_strategies=["market_first", "specialist_first"],
            source_archetypes=["curated_marketplace", "brand_direct"],
            confidence=0.88,
        )
        row = _row(desire_tier="considered")
        assert classify_search_path(intent, row) == "vendor_discovery_path"
        assert execution_mode_for_row(intent, row) == "affiliate_plus_sourcing"

    def test_hvac_repair_local_sourcing(self):
        """HVAC repair is local service, must route to vendor discovery."""
        intent = _intent(
            raw_input="HVAC repair near me",
            execution_mode="sourcing_only",
            search_strategies=["local_network_first"],
            confidence=0.9,
            relevance="vendor_proximity",
            targets={"service_location": "Austin, TX"},
        )
        row = _row(desire_tier="service")
        assert classify_search_path(intent, row) == "vendor_discovery_path"
        assert select_discovery_mode(intent, row) == "local_service_discovery"

    def test_aa_batteries_stays_affiliate(self):
        """Simple commodity must never trigger sourcing."""
        intent = _intent(
            raw_input="AA batteries pack of 24",
            execution_mode="affiliate_only",
            confidence=0.99,
        )
        row = _row(desire_tier="commodity")
        assert classify_search_path(intent, row) == "commodity_marketplace_path"
        assert should_rerank(intent, "commodity", "affiliate_only") is False

    def test_custom_engagement_ring_sourcing(self):
        """Custom/bespoke items require sourcing path."""
        intent = _intent(
            raw_input="custom engagement ring 2 carat diamond",
            execution_mode="sourcing_only",
            search_strategies=["specialist_first", "prestige_first"],
            source_archetypes=["brand_direct", "brokerage"],
            confidence=0.91,
        )
        row = _row(desire_tier="bespoke")
        assert classify_search_path(intent, row) == "vendor_discovery_path"
        assert should_rerank(intent, "bespoke", "sourcing_only") is True

    def test_concert_tickets_hybrid(self):
        """Concert tickets can benefit from both Ticketmaster and broker sources."""
        intent = _intent(
            raw_input="Taylor Swift Eras Tour tickets",
            execution_mode="affiliate_plus_sourcing",
            search_strategies=["market_first"],
            confidence=0.85,
        )
        row = _row(desire_tier="considered")
        assert execution_mode_for_row(intent, row) == "affiliate_plus_sourcing"


# ===========================================================================
# Phase 4: SearchIntent model extensions
# ===========================================================================

class TestSearchIntentExtensions:
    """Verify the new fields on SearchIntent serialize/deserialize correctly."""

    def test_execution_mode_round_trip(self):
        intent = _intent(execution_mode="sourcing_only", search_strategies=["specialist_first"])
        data = intent.model_dump()
        assert data["execution_mode"] == "sourcing_only"
        assert data["search_strategies"] == ["specialist_first"]
        restored = SearchIntent(**data)
        assert restored.execution_mode == "sourcing_only"
        assert restored.search_strategies == ["specialist_first"]

    def test_source_archetypes_round_trip(self):
        intent = _intent(source_archetypes=["brokerage", "local_directory", "registry"])
        data = intent.model_dump()
        assert data["source_archetypes"] == ["brokerage", "local_directory", "registry"]
        restored = SearchIntent(**data)
        assert restored.source_archetypes == ["brokerage", "local_directory", "registry"]

    def test_defaults_are_empty(self):
        intent = SearchIntent(product_category="test")
        assert intent.execution_mode is None
        assert intent.search_strategies == []
        assert intent.source_archetypes == []

    def test_backward_compat_no_new_fields(self):
        """Old JSON payloads without new fields still parse fine."""
        old_payload = {
            "product_category": "electronics",
            "raw_input": "laptop for coding",
            "keywords": ["laptop", "coding"],
        }
        intent = SearchIntent(**old_payload)
        assert intent.execution_mode is None
        assert intent.search_strategies == []
        assert intent.source_archetypes == []


# ===========================================================================
# Phase 4: UserIntent model extensions
# ===========================================================================

class TestUserIntentExtensions:
    """Verify new fields on UserIntent (LLM output model)."""

    def test_user_intent_new_fields(self):
        from services.llm_models import UserIntent
        ui = UserIntent(
            what="private jet charter",
            execution_mode="sourcing_only",
            search_strategies=["specialist_first"],
            source_archetypes=["brokerage"],
        )
        assert ui.execution_mode == "sourcing_only"
        assert ui.search_strategies == ["specialist_first"]
        assert ui.source_archetypes == ["brokerage"]

    def test_user_intent_defaults(self):
        from services.llm_models import UserIntent
        ui = UserIntent(what="AA batteries")
        assert ui.execution_mode is None
        assert ui.search_strategies == []
        assert ui.source_archetypes == []
