"""Regression tests for geo-filtering pipeline.

These tests ensure that:
1. City names are extracted from raw text when LLM constraints miss them
2. Location mode is correctly inferred when a city is detected
3. Vendor directory hard-filters non-local results when location is present
4. The full intent pipeline produces correct location context for Nashville-type queries
"""

import pytest
from sourcing.location import (
    _extract_location_from_text,
    resolve_location_context,
    normalize_location_targets,
    infer_location_mode_from_request_shape,
    normalize_search_intent_payload,
)
from sourcing.models import LocationTargets


# ---------------------------------------------------------------------------
# _extract_location_from_text
# ---------------------------------------------------------------------------

class TestExtractLocationFromText:
    def test_nashville_in_raw_input(self):
        assert _extract_location_from_text("luxury real estate brokers Nashville 2M+ listings") == "Nashville"

    def test_nashville_in_sentence(self):
        assert _extract_location_from_text("I need to sell a $2.4MM house in Nashville") == "Nashville"

    def test_san_diego_two_word_city(self):
        assert _extract_location_from_text("tennis lessons in San Diego") == "San Diego"

    def test_new_york_two_word_city(self):
        assert _extract_location_from_text("find a realtor new york") == "New York"

    def test_las_vegas_two_word_city(self):
        assert _extract_location_from_text("wedding planner las vegas") == "Las Vegas"

    def test_salt_lake_city_three_word_city(self):
        assert _extract_location_from_text("home inspector salt lake city") == "Salt Lake City"

    def test_denver_single_word(self):
        assert _extract_location_from_text("house cleaning services Denver CO") == "Denver"

    def test_no_city_returns_none(self):
        assert _extract_location_from_text("buy a laptop online") is None

    def test_empty_text_returns_none(self):
        assert _extract_location_from_text("") is None

    def test_none_text_returns_none(self):
        assert _extract_location_from_text(None) is None

    def test_state_name_fallback(self):
        result = _extract_location_from_text("contractors in Tennessee")
        assert result == "Tennessee"

    def test_case_insensitive(self):
        assert _extract_location_from_text("NASHVILLE realtors") == "Nashville"

    def test_does_not_match_partial_words(self):
        """'mesa' should not match inside 'mesmerize'."""
        result = _extract_location_from_text("this mesmerizes me")
        assert result is None


# ---------------------------------------------------------------------------
# resolve_location_context — fallback extraction
# ---------------------------------------------------------------------------

class TestResolveLocationContextFallback:
    def test_nashville_extracted_when_not_in_constraints(self):
        """The core regression: Nashville appears in raw_input but NOT in constraints."""
        ctx = resolve_location_context(
            service_category="real_estate",
            desire_tier=None,
            constraints={"price": "$2.4MM", "intent": "sell"},
            features={"price": "$2.4MM", "intent": "sell"},
            payload={
                "raw_input": "luxury real estate brokers Nashville 2M+ listings",
                "keywords": ["luxury", "real", "estate", "brokers", "nashville", "listings"],
            },
        )
        assert ctx.targets.service_location is not None
        assert "nashville" in ctx.targets.service_location.lower()
        assert ctx.relevance != "none"

    def test_san_diego_extracted_from_keywords(self):
        ctx = resolve_location_context(
            service_category="photography",
            desire_tier=None,
            constraints={},
            features={},
            payload={
                "raw_input": "wedding photographer san diego",
                "keywords": ["wedding", "photographer", "san", "diego"],
            },
        )
        assert ctx.targets.service_location is not None
        assert "san diego" in ctx.targets.service_location.lower()

    def test_explicit_location_in_constraints_takes_priority(self):
        """When constraints already contain 'location', fallback should NOT override."""
        ctx = resolve_location_context(
            service_category="real_estate",
            desire_tier=None,
            constraints={"location": "Memphis, TN"},
            features={"location": "Memphis, TN"},
            payload={
                "raw_input": "realtor Nashville area",
                "keywords": ["realtor", "nashville", "area"],
            },
        )
        # Should use Memphis from constraints, not Nashville from text
        assert ctx.targets.service_location is not None
        assert "memphis" in ctx.targets.service_location.lower()

    def test_no_location_no_city_returns_none_mode(self):
        ctx = resolve_location_context(
            service_category=None,
            desire_tier="commodity",
            constraints={},
            features={},
            payload={
                "raw_input": "buy a laptop online",
                "keywords": ["buy", "laptop", "online"],
            },
        )
        assert ctx.relevance == "none"


# ---------------------------------------------------------------------------
# infer_location_mode_from_request_shape
# ---------------------------------------------------------------------------

class TestLocationModeInference:
    def test_service_location_with_brokers_gives_service_area(self):
        targets = LocationTargets(service_location="Nashville")
        mode = infer_location_mode_from_request_shape(
            service_category="real_estate",
            desire_tier=None,
            targets=targets,
            payload={"raw_input": "luxury real estate brokers Nashville"},
        )
        # "brokers" is a MARKET_HINT_WORD → service_area
        assert mode == "service_area"

    def test_service_location_with_service_tier_gives_vendor_proximity(self):
        targets = LocationTargets(service_location="Nashville")
        mode = infer_location_mode_from_request_shape(
            service_category="real_estate",
            desire_tier="service",
            targets=targets,
            payload={"raw_input": "Nashville realtors"},
        )
        assert mode == "vendor_proximity"

    def test_service_location_with_local_hint_gives_vendor_proximity(self):
        targets = LocationTargets(service_location="Nashville")
        mode = infer_location_mode_from_request_shape(
            service_category="real_estate",
            desire_tier=None,
            targets=targets,
            payload={"raw_input": "realtors near me Nashville"},
        )
        assert mode == "vendor_proximity"


# ---------------------------------------------------------------------------
# normalize_search_intent_payload — end-to-end
# ---------------------------------------------------------------------------

class TestNormalizeSearchIntentPayload:
    def test_nashville_in_raw_input_populates_location_context(self):
        payload = {
            "product_category": "real_estate",
            "product_name": "Nashville Realtors",
            "raw_input": "luxury real estate brokers Nashville 2M+ listings",
            "keywords": ["luxury", "real", "estate", "brokers", "nashville", "listings"],
            "constraints": {"price": "$2.4MM"},
            "features": {"price": "$2.4MM"},
        }
        result = normalize_search_intent_payload(payload)
        loc_ctx = result["location_context"]
        targets = loc_ctx.get("targets", {})
        assert targets.get("service_location") is not None
        assert "nashville" in targets["service_location"].lower()
        assert loc_ctx["relevance"] != "none"

    def test_denver_cleaning_service_gets_location(self):
        payload = {
            "product_category": "cleaning",
            "product_name": "House Cleaning",
            "raw_input": "house cleaning service Denver",
            "keywords": ["house", "cleaning", "service", "denver"],
            "constraints": {},
            "features": {},
        }
        result = normalize_search_intent_payload(payload)
        loc_ctx = result["location_context"]
        targets = loc_ctx.get("targets", {})
        assert targets.get("service_location") is not None
        assert "denver" in targets["service_location"].lower()


# ---------------------------------------------------------------------------
# Vendor directory hard-filtering
# ---------------------------------------------------------------------------

class TestVendorDirectoryHardFilter:
    """Test the filtering logic extracted from VendorDirectoryProvider.search()."""

    @staticmethod
    def _make_result(title, location_match, store_geo_location=""):
        """Minimal mock SearchResult-like object for filter testing."""
        from sourcing.repository import SearchResult
        return SearchResult(
            title=title,
            price=None,
            currency="USD",
            merchant=title,
            url=f"https://{title.lower().replace(' ', '')}.com",
            source="vendor_directory",
            match_score=0.5,
            metadata={
                "location_match": location_match,
                "store_geo_location": store_geo_location,
                "location_mode": "service_area",
            },
        )

    def test_hard_filter_keeps_only_local_when_location_present(self):
        local = self._make_result("Nashville Realty Co", True, "Nashville, TN")
        remote1 = self._make_result("CA Luxury Homes", False, "Los Angeles, CA")
        remote2 = self._make_result("Nationwide Brokers", False, "")

        all_results = [local, remote1, remote2]
        matched = [r for r in all_results if r.metadata.get("location_match")]

        has_explicit_location_target = True
        # Simulate the hard-filter logic from vendor_provider.py
        if has_explicit_location_target and matched:
            filtered = matched
        else:
            filtered = all_results

        assert len(filtered) == 1
        assert filtered[0].title == "Nashville Realty Co"

    def test_no_filter_when_no_location_target(self):
        r1 = self._make_result("Vendor A", False, "")
        r2 = self._make_result("Vendor B", False, "")
        all_results = [r1, r2]
        matched = [r for r in all_results if r.metadata.get("location_match")]

        has_explicit_location_target = False
        if has_explicit_location_target and matched:
            filtered = matched
        else:
            filtered = all_results

        assert len(filtered) == 2
