from typing import List, Optional
from sourcing import ProviderStatusSnapshot, SearchResult

def determine_search_user_message(
    results: List[SearchResult], 
    statuses: List[ProviderStatusSnapshot]
) -> Optional[str]:
    """
    Determine the appropriate user-facing message based on search results and provider statuses.
    Returns None if no message is needed (e.g., successful search with results).
    """
    if len(results) > 0:
        return None

    exhausted_count = sum(1 for s in statuses if s.status == "exhausted")
    rate_limited_count = sum(1 for s in statuses if s.status == "rate_limited")
    # If no statuses recorded, we consider it failed
    all_failed = all(s.status != "ok" for s in statuses) if statuses else True
    
    if len(statuses) > 0 and exhausted_count == len(statuses):
        return "Search providers have exhausted their quota. Please try again later or contact support."
    
    if rate_limited_count > 0:
        return "Search is temporarily rate-limited. Please wait a moment and try again."
    
    if all_failed:
        return "Unable to search at this time. Please try again later."
        
    return None
