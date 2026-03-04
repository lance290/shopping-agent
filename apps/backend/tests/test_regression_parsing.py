"""Regression tests for provider aliases and price parsing utilities.
Extracted from test_regression_null_guards.py to keep files under 450 lines.
"""
import pytest


# ---------------------------------------------------------------------------
# Provider aliases regression
# ---------------------------------------------------------------------------


class TestProviderAliases:
    """Regression: provider key aliases must resolve correctly after rename."""

    def test_amazon_alias(self):
        from sourcing.normalizers import NORMALIZER_REGISTRY
        assert "amazon" in NORMALIZER_REGISTRY

    def test_ebay_alias(self):
        from sourcing.normalizers import NORMALIZER_REGISTRY
        assert "ebay" in NORMALIZER_REGISTRY

    def test_rainforest_still_works(self):
        from sourcing.normalizers import NORMALIZER_REGISTRY
        assert "rainforest" in NORMALIZER_REGISTRY

    def test_ebay_browse_still_works(self):
        from sourcing.normalizers import NORMALIZER_REGISTRY
        assert "ebay" in NORMALIZER_REGISTRY


# ---------------------------------------------------------------------------
# _parse_numeric and _parse_price_value edge cases
# ---------------------------------------------------------------------------


class TestParseNumeric:
    def test_none(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric(None) is None

    def test_int(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric(42) == 42.0

    def test_float(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric(3.14) == 3.14

    def test_dollar_string(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("$99.99") == 99.99

    def test_comma_string(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("$1,500") == 1500.0

    def test_empty_string(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("") is None

    def test_no_numbers(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("no numbers here") is None

    def test_mixed_text(self):
        from sourcing.service import _parse_numeric
        assert _parse_numeric("about $50 or so") == 50.0


class TestParsePriceValue:
    def test_none(self):
        from sourcing.service import _parse_price_value
        assert _parse_price_value(None) == (None, None)

    def test_range(self):
        from sourcing.service import _parse_price_value
        assert _parse_price_value("$50-$200") == (50.0, 200.0)

    def test_greater_than(self):
        from sourcing.service import _parse_price_value
        lo, hi = _parse_price_value(">$100")
        assert lo == 100.0
        assert hi is None

    def test_less_than(self):
        from sourcing.service import _parse_price_value
        lo, hi = _parse_price_value("<$50")
        assert lo is None
        assert hi == 50.0

    def test_plain_number_returns_none_none(self):
        from sourcing.service import _parse_price_value
        assert _parse_price_value(42) == (None, None)

    def test_range_with_commas(self):
        from sourcing.service import _parse_price_value
        assert _parse_price_value("$1,000-$5,000") == (1000.0, 5000.0)
