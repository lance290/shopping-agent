"""URL normalization helpers for the Search Architecture pipeline."""

from __future__ import annotations

import re
from typing import List, Sequence, Tuple
from urllib.parse import parse_qsl, urlsplit, urlunsplit, urlencode

DEFAULT_TRACKING_KEYS: Sequence[str] = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "msclkid",
    "yclid",
    "mc_eid",
    "mc_cid",
    "igshid",
    "spm",
    "ref",
    "affid",
    "affidname",
)

DEFAULT_TRACKING_PREFIXES: Sequence[str] = (
    "utm",
    "ga_",
    "icid",
    "mkt_",
)

_MULTI_SLASH_PATTERN = re.compile(r"/{2,}")


def _ensure_absolute(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    lowered = url.lower()
    if lowered.startswith(("http://", "https://")):
        return url
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("www."):
        return f"https://{url}"
    if url.startswith("/"):
        return f"https://www.google.com{url}"
    if "://" not in url:
        return f"https://{url}"
    return url


def _drop_tracking_params(
    params: List[Tuple[str, str]],
    tracking_keys: Sequence[str],
    tracking_prefixes: Sequence[str],
) -> List[Tuple[str, str]]:
    key_set = {key.lower() for key in tracking_keys}
    cleaned: List[Tuple[str, str]] = []
    for key, value in params:
        key_lower = key.lower()
        if key_lower in key_set:
            continue
        if any(key_lower.startswith(prefix) for prefix in tracking_prefixes):
            continue
        cleaned.append((key, value))
    return cleaned


def _deduplicate_params(params: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    seen: set[Tuple[str, str]] = set()
    deduped: List[Tuple[str, str]] = []
    for key, value in params:
        signature = (key.lower(), value)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append((key, value))
    return deduped


def canonicalize_url(
    raw_url: str,
    *,
    tracking_keys: Sequence[str] = DEFAULT_TRACKING_KEYS,
    tracking_prefixes: Sequence[str] = DEFAULT_TRACKING_PREFIXES,
) -> str:
    """Generate a stable canonical URL for bid deduplication.

    The canonical form enforces https, removes tracking params/fragments,
    normalizes repeated slashes, deduplicates query params, and sorts them.
    """

    absolute = _ensure_absolute(raw_url)
    if not absolute:
        return ""

    split = urlsplit(absolute)
    scheme = "https"

    netloc = split.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    if ":" in netloc:
        host, port = netloc.split(":", 1)
        drop = (scheme == "https" and port == "443") or (scheme == "http" and port == "80")
        netloc = host if drop else netloc

    path = split.path or "/"
    path = _MULTI_SLASH_PATTERN.sub("/", path)
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/":
        path = path.rstrip("/") or "/"

    query_pairs = parse_qsl(split.query, keep_blank_values=False)
    query_pairs = _drop_tracking_params(query_pairs, tracking_keys, tracking_prefixes)
    query_pairs = _deduplicate_params(query_pairs)
    query_pairs.sort(key=lambda pair: pair[0].lower())
    query = urlencode(query_pairs, doseq=True)

    return urlunsplit((scheme, netloc, path, query, ""))


__all__ = ["canonicalize_url"]
