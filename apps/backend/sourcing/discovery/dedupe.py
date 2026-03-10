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
    kept_by_domain: dict[str, DiscoveryCandidate] = {}
    passthrough: List[DiscoveryCandidate] = []
    for candidate in candidates:
        domain = (candidate.canonical_domain or "").strip().lower()
        if domain and domain in seen_domains:
            continue
        if not domain:
            passthrough.append(candidate)
            continue
        existing = kept_by_domain.get(domain)
        if existing is None or _candidate_strength(candidate) > _candidate_strength(existing):
            kept_by_domain[domain] = candidate
        seen_domains.add(domain)
    return list(kept_by_domain.values()) + passthrough


def _candidate_strength(candidate: DiscoveryCandidate) -> float:
    classification = candidate.classification or {}
    candidate_type = str(classification.get("candidate_type") or "")
    type_bonus = {
        "official_vendor_site": 0.35,
        "brokerage_or_agent_site": 0.35,
        "brand_site": 0.25,
        "marketplace_or_exchange": 0.20,
        "directory_or_aggregator": 0.10,
        "listing_or_inventory_page": 0.05,
        "editorial_or_irrelevant": 0.0,
    }.get(candidate_type, 0.0)
    trust_signals = candidate.trust_signals or {}
    confidence = float(classification.get("confidence") or 0.0)
    contact_bonus = 0.15 if (candidate.first_party_contact or classification.get("first_party_contact")) else 0.0
    official_bonus = 0.2 if (candidate.official_site or classification.get("official_site")) else 0.0
    location_bonus = 0.1 if classification.get("location_evidence") else 0.0
    rank_bonus = max(0.0, 0.1 - (float(trust_signals.get("result_rank") or 99) * 0.01))
    return type_bonus + confidence + contact_bonus + official_bonus + location_bonus + rank_bonus
