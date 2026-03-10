"""Merge and suppress duplicate discovered vendors."""

from __future__ import annotations

from typing import Iterable, List, Set

from sourcing.discovery.adapters.base import DiscoveryCandidate


def dedupe_discovery_candidates(
    candidates: Iterable[DiscoveryCandidate],
    *,
    existing_domains: Set[str] | None = None,
) -> List[DiscoveryCandidate]:
    seen_domains = set(existing_domains or set())
    kept: List[DiscoveryCandidate] = []
    for candidate in candidates:
        domain = (candidate.canonical_domain or "").strip().lower()
        if domain and domain in seen_domains:
            continue
        if domain:
            seen_domains.add(domain)
        kept.append(candidate)
    return kept
