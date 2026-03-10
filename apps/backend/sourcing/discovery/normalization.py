"""Normalize discovery candidates into NormalizedResult objects."""

from __future__ import annotations

from typing import List

from sourcing.discovery.adapters.base import DiscoveryCandidate
from sourcing.models import NormalizedResult


def normalize_discovery_candidates(candidates: List[DiscoveryCandidate]) -> List[NormalizedResult]:
    normalized: List[NormalizedResult] = []
    for candidate in candidates:
        normalized.append(
            NormalizedResult(
                title=candidate.title,
                url=candidate.url,
                canonical_url=candidate.url,
                source=f"vendor_discovery_{candidate.adapter_id}",
                price=None,
                currency="USD",
                merchant_name=candidate.title,
                merchant_domain=candidate.canonical_domain or "",
                image_url=candidate.image_url,
                raw_data={
                    "snippet": candidate.snippet,
                    "email": candidate.email,
                    "phone": candidate.phone,
                    "location_hint": candidate.location_hint,
                    "source_url": candidate.source_url,
                    "source_type": candidate.source_type,
                    "official_site": candidate.official_site,
                    "first_party_contact": candidate.first_party_contact,
                },
                provenance={
                    "source_provider": candidate.adapter_id,
                    "source_type": candidate.source_type,
                    "official_site": candidate.official_site,
                    "first_party_contact": candidate.first_party_contact,
                    "trust_signals": candidate.trust_signals,
                },
            )
        )
    return normalized
