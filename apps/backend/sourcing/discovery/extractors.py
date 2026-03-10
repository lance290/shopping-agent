"""Best-effort extraction helpers for live discovered vendor pages."""

from __future__ import annotations

import re
from urllib.parse import urlparse


EMAIL_RE = re.compile(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.I)
PHONE_RE = re.compile(r"(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")


def canonical_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower().strip()
    except Exception:
        return ""
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def extract_contact_hints(text: str) -> tuple[str | None, str | None]:
    email_match = EMAIL_RE.search(text or "")
    phone_match = PHONE_RE.search(text or "")
    return (
        email_match.group(1) if email_match else None,
        phone_match.group(1) if phone_match else None,
    )
