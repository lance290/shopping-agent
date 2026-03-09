from services.location_resolution import build_cache_key, normalize_place_query
from sourcing.location import precision_weight_multiplier


def test_normalize_place_query_trims_and_lowercases():
    assert normalize_place_query("  Nashville,   TN  ") == "nashville, tn"


def test_cache_key_stable_for_normalized_input():
    assert build_cache_key("Nashville, TN") == build_cache_key("  nashville,   tn ")


def test_precision_weight_multiplier_prefers_precise_matches():
    assert precision_weight_multiplier("address") > precision_weight_multiplier("city")
    assert precision_weight_multiplier("city") > precision_weight_multiplier("region")
