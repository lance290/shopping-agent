import pytest
from sourcing.messaging import determine_search_user_message
from sourcing import ProviderStatusSnapshot, SearchResult

def test_determine_search_user_message_success():
    """If we have results, no error message should be returned even if some providers failed."""
    results = [SearchResult(title="Item 1", price=10.0, currency="USD", merchant="Test", url="http://test.com", source="test")]
    statuses = [
        ProviderStatusSnapshot(provider_id="p1", status="ok", result_count=1),
        ProviderStatusSnapshot(provider_id="p2", status="error", result_count=0)
    ]
    msg = determine_search_user_message(results, statuses)
    assert msg is None

def test_determine_search_user_message_all_exhausted():
    """If no results and all providers exhausted, return exhausted message."""
    results = []
    statuses = [
        ProviderStatusSnapshot(provider_id="p1", status="exhausted", result_count=0),
        ProviderStatusSnapshot(provider_id="p2", status="exhausted", result_count=0)
    ]
    msg = determine_search_user_message(results, statuses)
    assert msg == "Search providers have exhausted their quota. Please try again later or contact support."

def test_determine_search_user_message_rate_limited():
    """If no results and at least one provider rate limited, return rate limit message."""
    results = []
    statuses = [
        ProviderStatusSnapshot(provider_id="p1", status="rate_limited", result_count=0),
        ProviderStatusSnapshot(provider_id="p2", status="ok", result_count=0) # Maybe ok but 0 results?
    ]
    msg = determine_search_user_message(results, statuses)
    assert msg == "Search is temporarily rate-limited. Please wait a moment and try again."

def test_determine_search_user_message_generic_failure():
    """If no results and all failed (but not specific reasons), return generic message."""
    results = []
    statuses = [
        ProviderStatusSnapshot(provider_id="p1", status="error", result_count=0),
        ProviderStatusSnapshot(provider_id="p2", status="timeout", result_count=0)
    ]
    msg = determine_search_user_message(results, statuses)
    assert msg == "Unable to search at this time. Please try again later."

def test_determine_search_user_message_no_results_no_error():
    """If no results but status is OK (just empty), return None (handled by UI 'No offers found')."""
    results = []
    statuses = [
        ProviderStatusSnapshot(provider_id="p1", status="ok", result_count=0)
    ]
    # In this case all_failed is False.
    # exhausted_count = 0
    # rate_limited_count = 0
    # Returns None.
    msg = determine_search_user_message(results, statuses)
    assert msg is None
