"""Tests for the unified should_include_result filter (sourcing/filters.py).

Covers all scenarios from PRD_Search_Display_Architecture:
- Nullable price (quote-based) always passes
- No min/max set: everything passes
- min/max price hard filters apply to ALL sources and tiers
- Vendor directory results have price=None, so they always pass naturally
"""

import pytest
from sourcing.filters import should_include_result


class TestQuoteBasedResults:
    """price=None (quote-based) should ALWAYS pass regardless of filters."""

    def test_none_price_passes_with_no_filters(self):
        assert should_include_result(price=None, source="vendor_directory") is True

    def test_none_price_passes_with_min_price(self):
        assert should_include_result(price=None, source="vendor_directory", min_price=50000) is True

    def test_none_price_passes_with_max_price(self):
        assert should_include_result(price=None, source="vendor_directory", max_price=100) is True

    def test_none_price_passes_with_commodity_tier(self):
        assert should_include_result(price=None, source="vendor_directory", desire_tier="commodity", min_price=50000) is True

    def test_none_price_passes_for_any_source(self):
        assert should_include_result(price=None, source="rainforest") is True
        assert should_include_result(price=None, source="unknown_source") is True


class TestSourcesWithConcretePrice:
    """Sources with concrete prices are subject to min/max filtering like any other.
    Vendor directory results have price=None in practice, so they pass via the quote-based rule."""

    def test_vendor_directory_with_concrete_price_filtered(self):
        # Hypothetical: if a vendor_directory result had a concrete price, it gets filtered
        assert should_include_result(price=5.0, source="vendor_directory", min_price=50000) is False

    def test_google_cse_with_concrete_price_filtered(self):
        assert should_include_result(price=10.0, source="google_cse", min_price=50000) is False

    def test_concrete_price_zero_filtered_by_min(self):
        assert should_include_result(price=0.0, source="manual", is_service_provider=True, min_price=50000) is False


class TestTierAwareFiltering:
    """Desire tier determines whether price filters apply."""

    def test_commodity_applies_min_price(self):
        """$148 earrings should be filtered out when min is $50k (commodity tier)."""
        assert should_include_result(price=148, source="rainforest", desire_tier="commodity", min_price=50000) is False

    def test_commodity_applies_max_price(self):
        assert should_include_result(price=200, source="rainforest", desire_tier="commodity", max_price=100) is False

    def test_commodity_passes_within_range(self):
        assert should_include_result(price=75, source="rainforest", desire_tier="commodity", min_price=50, max_price=100) is True

    def test_considered_applies_price_filter(self):
        assert should_include_result(price=10, source="rainforest", desire_tier="considered", min_price=50) is False

    def test_bespoke_applies_price_filter(self):
        """All tiers apply price filters uniformly. Vendor results pass via price=None."""
        assert should_include_result(price=148, source="rainforest", desire_tier="bespoke", min_price=50000) is False

    def test_service_tier_applies_price_filter(self):
        assert should_include_result(price=0.0, source="rainforest", desire_tier="service", min_price=1000) is False

    def test_high_value_applies_price_filter(self):
        assert should_include_result(price=500, source="rainforest", desire_tier="high_value", min_price=50000) is False

    def test_advisory_applies_price_filter(self):
        assert should_include_result(price=0.0, source="rainforest", desire_tier="advisory", min_price=1000) is False


class TestNoFiltersSet:
    """When no min/max price is set, everything passes."""

    def test_no_filters_passes_any_price(self):
        assert should_include_result(price=1.0, source="rainforest") is True
        assert should_include_result(price=1000000.0, source="rainforest") is True
        assert should_include_result(price=0.0, source="rainforest") is True


class TestBoatScenario:
    """The Boat Test from the PRD — refinement from toy to yacht."""

    def test_rubber_duck_filtered_for_yacht_budget(self):
        """When user refines to mega yacht ($5M+), $15 rubber ducks are filtered."""
        assert should_include_result(
            price=15.0, source="rainforest", desire_tier="commodity", min_price=5000000
        ) is False

    def test_yacht_broker_passes_as_vendor(self):
        """Yacht broker (vendor_directory, price=None) always passes."""
        assert should_include_result(
            price=None, source="vendor_directory", desire_tier="high_value", min_price=5000000
        ) is True

    def test_bathtub_toy_passes_for_commodity(self):
        """When user wants commodity toy, $15 item passes with no min."""
        assert should_include_result(
            price=15.0, source="rainforest", desire_tier="commodity"
        ) is True


class TestDiamondEarringsScenario:
    """The Diamond Earrings Test — price filters apply uniformly, vendor results pass via price=None."""

    def test_cheap_amazon_earrings_filtered_by_min_price(self):
        """$148 earrings filtered when min is $50k, regardless of tier."""
        assert should_include_result(
            price=148, source="rainforest", desire_tier="bespoke", min_price=50000
        ) is False

    def test_vendor_always_survives(self):
        """Tiffany (vendor_directory, price=None) always survives."""
        assert should_include_result(
            price=None, source="vendor_directory", desire_tier="bespoke", min_price=50000
        ) is True
