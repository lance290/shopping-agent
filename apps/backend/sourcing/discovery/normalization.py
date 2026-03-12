"""Normalize discovery candidates into NormalizedResult objects."""

from __future__ import annotations

from typing import List

from sourcing.discovery.adapters.base import DiscoveryCandidate
from sourcing.models import NormalizedResult


def normalize_discovery_candidates(candidates: List[object]) -> List[NormalizedResult]:
    from sourcing.vendor_provider import AGGREGATOR_DOMAINS
    normalized: List[NormalizedResult] = []
    for item in candidates:
        candidate = item.candidate if hasattr(item, "candidate") else item
        # Skip aggregator/directory domains
        domain = (candidate.canonical_domain or "").lower()
        if domain and (domain in AGGREGATOR_DOMAINS or f"www.{domain}" in AGGREGATOR_DOMAINS):
            continue
        final_score = getattr(item, "final_score", None)
        admissible = getattr(item, "admissible", True)
        rejection_reasons = getattr(item, "rejection_reasons", [])
        heuristic_fit = getattr(item, "heuristic_fit", None)
        trust_score = getattr(item, "trust_score", None)
        location_score = getattr(item, "location_score", None)
        classification = candidate.classification or {}
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
                    "candidate_type": classification.get("candidate_type"),
                    "classification_confidence": classification.get("confidence"),
                    "location_evidence": classification.get("location_evidence", []),
                    "service_category_evidence": classification.get("service_category_evidence", []),
                    "admissibility_status": "admitted" if admissible else "rejected",
                    "rejection_reasons": list(rejection_reasons),
                    "llm_rerank_summary": candidate.trust_signals.get("llm_rerank_summary"),
                },
                provenance={
                    "source_provider": candidate.adapter_id,
                    "source_type": candidate.source_type,
                    "official_site": candidate.official_site,
                    "first_party_contact": candidate.first_party_contact,
                    "trust_signals": candidate.trust_signals,
                    "candidate_type": classification.get("candidate_type"),
                    "classification_confidence": classification.get("confidence"),
                    "location_evidence": classification.get("location_evidence", []),
                    "service_category_evidence": classification.get("service_category_evidence", []),
                    "admissibility_status": "admitted" if admissible else "rejected",
                    "rejection_reasons": list(rejection_reasons),
                    "llm_rerank_summary": candidate.trust_signals.get("llm_rerank_summary"),
                    "score": {
                        "combined": final_score,
                        "relevance": heuristic_fit,
                        "semantic": heuristic_fit,
                        "geo": location_score,
                        "quality": trust_score,
                    } if final_score is not None else {},
                },
            )
        )
    return normalized
