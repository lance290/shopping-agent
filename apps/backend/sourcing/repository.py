from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import httpx
import os
import re
from urllib.parse import urlparse, urlencode
import asyncio
import time
import base64

from utils.security import redact_secrets_from_text
from sourcing.executors import run_provider_with_status
from sourcing.models import NormalizedResult, ProviderStatusSnapshot
from sourcing.metrics import log_provider_result


def extract_merchant_domain(url: str) -> str:
    """Extract the merchant domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return "unknown"


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("/"):
        return f"https://www.google.com{url}"
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("www."):
        return f"https://{url}"
    return url


# Redaction moved to utils.security.redact_secrets_from_text
# Keeping this alias for backward compatibility
redact_secrets = redact_secrets_from_text

class SearchResult(BaseModel):
    title: str
    price: Optional[float] = None
    currency: str = "USD"
    merchant: str
    url: str
    merchant_domain: str = ""
    click_url: str = ""
    match_score: float = 0.0
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    shipping_info: Optional[str] = None
    source: str
    bid_id: Optional[int] = None
    is_selected: bool = False
    is_liked: bool = False
    liked_at: Optional[str] = None


class SearchResultWithStatus(BaseModel):
    """Search results with provider status information."""
    results: List[SearchResult] = []
    normalized_results: List[NormalizedResult] = []
    provider_statuses: List[ProviderStatusSnapshot] = []
    all_providers_failed: bool = False
    user_message: Optional[str] = None

def compute_match_score(result: SearchResult, query: str) -> float:
    """
    Compute a basic relevance score for a search result.
    
    Factors:
        - Title contains query words
        - Has image
        - Has rating
        - Has reviews
        - Price is present
    
    Returns: 0.0 - 1.0
    """
    score = 0.0
    query_words = set(query.lower().split())
    title_words = set(result.title.lower().split())
    
    # Title relevance (0-0.4)
    if query_words:
        overlap = len(query_words & title_words)
        score += 0.4 * (overlap / len(query_words))
    
    # Has image (0.15)
    if result.image_url:
        score += 0.15
    
    # Has rating (0.15)
    if result.rating and result.rating > 0:
        score += 0.15
    
    # Has reviews (0.15)
    if result.reviews_count and result.reviews_count > 0:
        score += 0.15
    
    # Has price (0.15)
    if result.price and result.price > 0:
        score += 0.15
    
    return min(score, 1.0)


