"""Rate limiting utilities."""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List

# Simple in-memory rate limiter (use Redis in production)
rate_limit_store: dict[str, List[datetime]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = {
    "search": 30,      # 30 searches per minute
    "clickout": 60,    # 60 clicks per minute
    "auth_start": 5,   # 5 login attempts per minute
    "chat_anon": 10,   # 10 anonymous chat requests per minute
}


def check_rate_limit(key: str, limit_type: str) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    
    # Clean old entries
    rate_limit_store[key] = [
        t for t in rate_limit_store[key] if t > window_start
    ]
    
    max_requests = RATE_LIMIT_MAX.get(limit_type, 100)
    if len(rate_limit_store[key]) >= max_requests:
        return False
    
    rate_limit_store[key].append(now)
    return True
