"""Anti-Fraud detection service (PRD 10).

Simple heuristic-based fraud detection for clickout events.
Flags suspicious activity based on rate, IP patterns, and user behavior.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory rate tracking (production would use Redis)
_ip_click_counts: dict[str, list[datetime]] = defaultdict(list)
_user_click_counts: dict[int, list[datetime]] = defaultdict(list)

# Thresholds
MAX_CLICKS_PER_IP_PER_MINUTE = 10
MAX_CLICKS_PER_USER_PER_MINUTE = 5
SUSPICIOUS_PATTERNS = {"headless", "bot", "crawler", "spider", "scraper"}


def assess_clickout(
    ip_address: Optional[str],
    user_agent: Optional[str],
    user_id: Optional[int],
) -> bool:
    """
    Assess whether a clickout is suspicious.

    Returns True if the clickout appears fraudulent.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=1)
    is_suspicious = False

    # Check user agent for bot patterns
    if user_agent:
        ua_lower = user_agent.lower()
        if any(pattern in ua_lower for pattern in SUSPICIOUS_PATTERNS):
            logger.warning(f"[FRAUD] Bot-like user agent detected: {user_agent[:80]}")
            is_suspicious = True

    # Check IP rate
    if ip_address:
        clicks = _ip_click_counts[ip_address]
        # Prune old entries
        _ip_click_counts[ip_address] = [t for t in clicks if t > cutoff]
        _ip_click_counts[ip_address].append(now)
        if len(_ip_click_counts[ip_address]) > MAX_CLICKS_PER_IP_PER_MINUTE:
            logger.warning(
                f"[FRAUD] IP rate exceeded: {ip_address} "
                f"({len(_ip_click_counts[ip_address])} clicks/min)"
            )
            is_suspicious = True

    # Check user rate
    if user_id:
        clicks = _user_click_counts[user_id]
        _user_click_counts[user_id] = [t for t in clicks if t > cutoff]
        _user_click_counts[user_id].append(now)
        if len(_user_click_counts[user_id]) > MAX_CLICKS_PER_USER_PER_MINUTE:
            logger.warning(
                f"[FRAUD] User rate exceeded: user_id={user_id} "
                f"({len(_user_click_counts[user_id])} clicks/min)"
            )
            is_suspicious = True

    return is_suspicious
