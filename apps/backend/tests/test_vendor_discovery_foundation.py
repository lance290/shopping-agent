import pytest

from models.rows import Row
from sourcing.coverage import evaluate_internal_vendor_coverage
from sourcing.discovery.classifier import classify_search_path, select_discovery_mode
from sourcing.discovery.dedupe import dedupe_discovery_candidates
from sourcing.discovery.adapters.base import DiscoveryCandidate
from sourcing.discovery.query_planner import build_discovery_queries
from sourcing.models import SearchIntent, LocationContext, LocationTargets, NormalizedResult
from sourcing.repository import SearchResult
from sourcing.service import SourcingService


def _intent(raw_input: str, relevance: str = "none") -> SearchIntent:
    return SearchIntent(
        product_category="luxury_real_estate",
        product_name="luxury real estate agent",
        raw_input=raw_input,
        keywords=["luxury", "real estate", "agent"],
        location_context=LocationContext(
            relevance=relevance,
            confidence=0.9,
            targets=LocationTargets(service_location="Nashville, TN"),
        ),
    )


def test_classify_search_path_prefers_vendor_discovery_for_service_rows():
    row = Row(title="Sell mansion", is_service=True, service_category="real_estate", desire_tier="service")
    assert classify_search_path(_intent("sell mansion in nashville", "service_area"), row) == "vendor_discovery_path"


def test_select_discovery_mode_maps_real_estate_to_brokerage():
    row = Row(title="Sell mansion", is_service=True, service_category="real_estate", desire_tier="service")
    assert select_discovery_mode(_intent("sell mansion in nashville", "service_area"), row) == "luxury_brokerage_discovery"


def test_build_discovery_queries_includes_location_variants():
    queries = build_discovery_queries(_intent("sell mansion in nashville", "service_area"), "luxury_brokerage_discovery")
    assert any("nashville" in query.lower() for query in queries)
    assert any("brokerage" in query.lower() or "agent" in query.lower() for query in queries)


def test_coverage_evaluation_marks_borderline_and_insufficient():
    sufficient_results = [
        SearchResult(
            title=f"Vendor {idx}",
            merchant=f"Vendor {idx}",
            url=f"https://vendor{idx}.com",
            merchant_domain=f"vendor{idx}.com",
            source="vendor_directory",
            match_score=0.9,
            metadata={"official_site": True, "location_match": True, "service_category_match": True},
        )
        for idx in range(3)
    ]
    assert evaluate_internal_vendor_coverage(sufficient_results).status == "sufficient"

    weak_results = [
        SearchResult(
            title="Weak Vendor",
            merchant="Weak Vendor",
            url="https://weak.com",
            merchant_domain="weak.com",
            source="vendor_directory",
            match_score=0.3,
            metadata={"official_site": False, "location_match": False, "service_category_match": False},
        )
    ]
    assert evaluate_internal_vendor_coverage(weak_results).status == "insufficient"


def test_dedupe_keeps_same_name_same_geo_when_domains_differ():
    kept = dedupe_discovery_candidates(
        [
            DiscoveryCandidate(
                adapter_id="google_organic",
                query="nashville luxury broker",
                title="Smith Group",
                url="https://smithgroup-one.com",
                source_url="https://smithgroup-one.com",
                source_type="official_site",
                canonical_domain="smithgroup-one.com",
                location_hint="Nashville, TN",
            ),
            DiscoveryCandidate(
                adapter_id="google_organic",
                query="nashville luxury broker",
                title="Smith Group",
                url="https://smithgroup-two.com",
                source_url="https://smithgroup-two.com",
                source_type="official_site",
                canonical_domain="smithgroup-two.com",
                location_hint="Nashville, TN",
            ),
        ]
    )
    assert len(kept) == 2


def test_filter_discovery_results_for_bid_persistence_blocks_high_risk_categories():
    row = Row(title="Buy Gulfstream", desire_tier="high_value", service_category="private_aviation")
    results = [
        NormalizedResult(
            title="Jet Broker Directory",
            url="https://directory.example/gulfstream",
            canonical_url="https://directory.example/gulfstream",
            source="vendor_discovery_google_organic",
            merchant_name="Jet Broker Directory",
            merchant_domain="directory.example",
            image_url=None,
            raw_data={
                "official_site": False,
                "admissibility_status": "admitted",
                "candidate_type": "directory_or_aggregator",
            },
            provenance={"official_site": False, "score": {"combined": 0.92}},
        )
    ]
    allowed = SourcingService._filter_discovery_results_for_bid_persistence(row, results)
    assert allowed == []


def test_filter_discovery_results_for_bid_persistence_allows_high_risk_strong_discovered_vendor():
    row = Row(title="Sell mansion", desire_tier="service", service_category="real_estate")
    results = [
        NormalizedResult(
            title="Belle Meade Estates",
            url="https://bellemeadeestates.example",
            canonical_url="https://bellemeadeestates.example",
            source="vendor_discovery_google_organic",
            merchant_name="Belle Meade Estates",
            merchant_domain="bellemeadeestates.example",
            image_url=None,
            raw_data={
                "official_site": True,
                "admissibility_status": "admitted",
                "candidate_type": "brokerage_or_agent_site",
                "first_party_contact": True,
                "email": "hello@bellemeadeestates.example",
            },
            provenance={
                "official_site": True,
                "first_party_contact": True,
                "candidate_type": "brokerage_or_agent_site",
                "score": {"combined": 0.82},
            },
        )
    ]
    allowed = SourcingService._filter_discovery_results_for_bid_persistence(row, results)
    assert len(allowed) == 1


def test_filter_discovery_results_for_bid_persistence_allows_low_risk_official_site():
    row = Row(title="Find local caterer", desire_tier="service", service_category="catering")
    results = [
        NormalizedResult(
            title="Nashville Catering Co",
            url="https://nashvillecatering.example",
            canonical_url="https://nashvillecatering.example",
            source="vendor_discovery_google_organic",
            merchant_name="Nashville Catering Co",
            merchant_domain="nashvillecatering.example",
            image_url=None,
            raw_data={
                "email": "hello@nashvillecatering.example",
                "official_site": True,
                "admissibility_status": "admitted",
            },
            provenance={"official_site": True, "score": {"combined": 0.72}},
        )
    ]
    allowed = SourcingService._filter_discovery_results_for_bid_persistence(row, results)
    assert len(allowed) == 1
