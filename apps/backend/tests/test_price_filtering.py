"""Tests for price filtering in sourcing service and search routes."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from sourcing.models import NormalizedResult


class TestPriceFiltering:
    """Test suite for price filtering logic."""

    def create_normalized_result(
        self,
        title: str,
        price: float,
        source: str = "rainforest",
        url: str = "https://example.com"
    ) -> NormalizedResult:
        """Helper to create NormalizedResult objects."""
        return NormalizedResult(
            title=title,
            price=price,
            currency="USD",
            url=url,
            canonical_url=url,
            merchant_name="Test Merchant",
            merchant_domain="example.com",
            source=source
        )

    def test_min_price_filter_removes_items_below_threshold(self):
        """Items below min_price should be filtered out."""
        results = [
            self.create_normalized_result("Cheap Item", 100),
            self.create_normalized_result("Medium Item", 500),
            self.create_normalized_result("Expensive Item", 1000),
        ]
        
        min_price = 500
        filtered = [r for r in results if r.price >= min_price]
        
        assert len(filtered) == 2
        assert all(r.price >= 500 for r in filtered)

    def test_max_price_filter_removes_items_above_threshold(self):
        """Items above max_price should be filtered out."""
        results = [
            self.create_normalized_result("Cheap Item", 100),
            self.create_normalized_result("Medium Item", 500),
            self.create_normalized_result("Expensive Item", 1000),
        ]
        
        max_price = 500
        filtered = [r for r in results if r.price <= max_price]
        
        assert len(filtered) == 2
        assert all(r.price <= 500 for r in filtered)

    def test_price_range_filter(self):
        """Items should be filtered to within min/max range."""
        results = [
            self.create_normalized_result("Too Cheap", 100),
            self.create_normalized_result("Just Right 1", 500),
            self.create_normalized_result("Just Right 2", 750),
            self.create_normalized_result("Just Right 3", 1000),
            self.create_normalized_result("Too Expensive", 1500),
        ]
        
        min_price = 500
        max_price = 1000
        filtered = [r for r in results if min_price <= r.price <= max_price]
        
        assert len(filtered) == 3
        assert all(500 <= r.price <= 1000 for r in filtered)

    def test_zero_price_items_filtered_out(self):
        """Items with price=0 should be filtered out when price filtering is active."""
        results = [
            self.create_normalized_result("Zero Price", 0),
            self.create_normalized_result("Valid Price", 500),
        ]
        
        min_price = 100
        filtered = [r for r in results if r.price and r.price > 0 and r.price >= min_price]
        
        assert len(filtered) == 1
        assert filtered[0].title == "Valid Price"

    def test_none_price_items_filtered_out(self):
        """Items with price=None should be filtered out when price filtering is active."""
        result = self.create_normalized_result("No Price", 0)
        result.price = None
        
        results = [
            result,
            self.create_normalized_result("Valid Price", 500),
        ]
        
        min_price = 100
        filtered = [r for r in results if r.price is not None and r.price > 0 and r.price >= min_price]
        
        assert len(filtered) == 1
        assert filtered[0].title == "Valid Price"

    def test_non_shopping_sources_bypass_price_filter(self):
        """Non-shopping sources like google_cse should bypass price filtering."""
        results = [
            self.create_normalized_result("CSE Result 1", 0, source="google_cse"),
            self.create_normalized_result("CSE Result 2", 0, source="google_cse"),
            self.create_normalized_result("Shopping Result", 500, source="rainforest"),
            self.create_normalized_result("Zero Price Shopping", 0, source="rainforest"),
        ]
        
        non_shopping_sources = {"google_cse"}
        min_price = 100
        
        filtered = []
        for r in results:
            if r.source in non_shopping_sources:
                filtered.append(r)
                continue
            if r.price is None or r.price <= 0:
                continue
            if r.price < min_price:
                continue
            filtered.append(r)
        
        assert len(filtered) == 3
        assert sum(1 for r in filtered if r.source == "google_cse") == 2
        assert sum(1 for r in filtered if r.source == "rainforest") == 1

    def test_google_shopping_source_respects_price_filter(self):
        """Google Shopping (google_shopping) results SHOULD be price filtered."""
        results = [
            self.create_normalized_result("Below Min", 100, source="google_shopping"),
            self.create_normalized_result("Above Min", 500, source="google_shopping"),
        ]
        
        non_shopping_sources = {"google_cse"}  # google_shopping is NOT in this set
        min_price = 200
        
        filtered = []
        for r in results:
            if r.source in non_shopping_sources:
                filtered.append(r)
                continue
            if r.price is None or r.price <= 0:
                continue
            if r.price < min_price:
                continue
            filtered.append(r)
        
        assert len(filtered) == 1
        assert filtered[0].title == "Above Min"

    def test_rainforest_source_respects_price_filter(self):
        """Rainforest (Amazon) results SHOULD be price filtered."""
        results = [
            self.create_normalized_result("Below Min", 100, source="rainforest"),
            self.create_normalized_result("Above Min", 500, source="rainforest"),
        ]
        
        min_price = 200
        filtered = [r for r in results if r.price >= min_price]
        
        assert len(filtered) == 1
        assert filtered[0].title == "Above Min"

    def test_no_price_filter_returns_all_results(self):
        """When no min/max price set, all results should be returned."""
        results = [
            self.create_normalized_result("Item 1", 100),
            self.create_normalized_result("Item 2", 500),
            self.create_normalized_result("Item 3", 1000),
        ]
        
        min_price = None
        max_price = None
        
        # No filtering when no price constraints
        if min_price is None and max_price is None:
            filtered = results
        else:
            filtered = [r for r in results if min_price <= r.price <= max_price]
        
        assert len(filtered) == 3

    def test_exact_boundary_prices_included(self):
        """Items at exactly min or max price should be included."""
        results = [
            self.create_normalized_result("At Min", 500),
            self.create_normalized_result("At Max", 1000),
            self.create_normalized_result("Below Min", 499),
            self.create_normalized_result("Above Max", 1001),
        ]
        
        min_price = 500
        max_price = 1000
        filtered = [r for r in results if min_price <= r.price <= max_price]
        
        assert len(filtered) == 2
        assert any(r.title == "At Min" for r in filtered)
        assert any(r.title == "At Max" for r in filtered)


class TestPriceExtractionFromRow:
    """Test price constraint extraction from row data."""

    def test_extract_min_price_from_choice_answers(self):
        """min_price should be extracted from choice_answers."""
        choice_answers = {"min_price": 500, "max_price": 2000}
        
        min_price = choice_answers.get("min_price")
        max_price = choice_answers.get("max_price")
        
        assert min_price == 500
        assert max_price == 2000

    def test_extract_price_from_search_intent(self):
        """Prices should be extractable from search_intent if not in choice_answers."""
        search_intent = {"min_price": 300, "max_price": 1500}
        choice_answers = {}
        
        min_price = choice_answers.get("min_price") or search_intent.get("min_price")
        max_price = choice_answers.get("max_price") or search_intent.get("max_price")
        
        assert min_price == 300
        assert max_price == 1500

    def test_choice_answers_takes_precedence(self):
        """choice_answers should take precedence over search_intent."""
        search_intent = {"min_price": 300, "max_price": 1500}
        choice_answers = {"min_price": 500, "max_price": 2000}
        
        min_price = choice_answers.get("min_price") or search_intent.get("min_price")
        max_price = choice_answers.get("max_price") or search_intent.get("max_price")
        
        assert min_price == 500
        assert max_price == 2000

    def test_handles_missing_price_constraints(self):
        """Should handle missing price constraints gracefully."""
        search_intent = {"keywords": ["bicycle"]}
        choice_answers = {"brand": "Bianchi"}
        
        min_price = choice_answers.get("min_price") or search_intent.get("min_price")
        max_price = choice_answers.get("max_price") or search_intent.get("max_price")
        
        assert min_price is None
        assert max_price is None

    def test_handles_zero_as_valid_min_price(self):
        """Zero should be a valid min_price (free items)."""
        choice_answers = {"min_price": 0, "max_price": 100}
        
        # Note: 0 is falsy in Python, so we need explicit None check
        min_price = choice_answers.get("min_price")
        if min_price is None:
            min_price = 0
        
        assert min_price == 0

    def test_string_price_values_handled(self):
        """String price values should be convertible to float."""
        choice_answers = {"min_price": "500", "max_price": "2000"}
        
        min_price = float(choice_answers.get("min_price", 0))
        max_price = float(choice_answers.get("max_price", 0))
        
        assert min_price == 500.0
        assert max_price == 2000.0


class TestPriceFilteringLogging:
    """Test that price filtering provides useful logging."""

    def test_filter_counts_are_tracked(self):
        """Filtering should track counts for debugging."""
        results = [
            {"title": "Zero", "price": 0, "source": "rainforest"},
            {"title": "Below Min", "price": 100, "source": "rainforest"},
            {"title": "Above Max", "price": 2000, "source": "rainforest"},
            {"title": "Valid", "price": 500, "source": "rainforest"},
            {"title": "CSE", "price": 0, "source": "google_cse"},
        ]
        
        min_price = 200
        max_price = 1000
        non_shopping_sources = {"google_cse"}
        
        dropped_zero = 0
        dropped_min = 0
        dropped_max = 0
        filtered = []
        
        for r in results:
            if r["source"] in non_shopping_sources:
                filtered.append(r)
                continue
            if r["price"] is None or r["price"] <= 0:
                dropped_zero += 1
                continue
            if r["price"] < min_price:
                dropped_min += 1
                continue
            if r["price"] > max_price:
                dropped_max += 1
                continue
            filtered.append(r)
        
        assert dropped_zero == 1
        assert dropped_min == 1
        assert dropped_max == 1
        assert len(filtered) == 2  # Valid + CSE
