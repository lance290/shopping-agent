"""Discovery-mode admissibility gates for classified discovery candidates."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Iterable

from models.rows import Row
from sourcing.discovery.adapters.base import DiscoveryCandidate
from sourcing.models import SearchIntent

PREFERRED_TYPES = {
    "local_service_discovery": {"official_vendor_site", "brokerage_or_agent_site"},
    "luxury_brokerage_discovery": {"brokerage_or_agent_site", "official_vendor_site"},
    "uhnw_goods_discovery": {"official_vendor_site", "marketplace_or_exchange", "brand_site"},
    "asset_market_discovery": {"brokerage_or_agent_site", "marketplace_or_exchange", "official_vendor_site"},
    "destination_service_discovery": {"official_vendor_site", "brokerage_or_agent_site"},
    "advisory_discovery": {"official_vendor_site", "brokerage_or_agent_site"},
}
FALLBACK_TYPES = {
    "local_service_discovery": {"directory_or_aggregator"},
    "luxury_brokerage_discovery": {"marketplace_or_exchange"},
    "uhnw_goods_discovery": {"directory_or_aggregator"},
    "asset_market_discovery": {"directory_or_aggregator"},
    "destination_service_discovery": {"marketplace_or_exchange", "directory_or_aggregator"},
    "advisory_discovery": {"directory_or_aggregator"},
}
REJECT_TYPES = {
    "local_service_discovery": {"editorial_or_irrelevant"},
    "luxury_brokerage_discovery": {"listing_or_inventory_page", "editorial_or_irrelevant"},
    "uhnw_goods_discovery": {"editorial_or_irrelevant"},
    "asset_market_discovery": {"editorial_or_irrelevant"},
    "destination_service_discovery": {"editorial_or_irrelevant"},
    "advisory_discovery": {"listing_or_inventory_page", "editorial_or_irrelevant"},
}


@dataclass
class GatedDiscoveryCandidate:
    candidate: DiscoveryCandidate
    admissible: bool
    heuristic_fit: float
    trust_score: float
    location_score: float
    final_score: float
    rejection_reasons: list[str] = field(default_factory=list)

    def model_dump(self) -> dict[str, object]:
        data = asdict(self)
        data["candidate"] = self.candidate
        return data


def visibility_threshold() -> float:
    try:
        return float(os.getenv("DISCOVERY_ROW_VISIBILITY_THRESHOLD", "0.55"))
    except Exception:
        return 0.55


def _high_risk_mode(discovery_mode: str) -> bool:
    return discovery_mode in {"luxury_brokerage_discovery", "asset_market_discovery", "advisory_discovery"}


def gate_discovery_candidates(
    candidates: Iterable[DiscoveryCandidate],
    *,
    discovery_mode: str,
    intent: SearchIntent | None,
    row: Row | None,
) -> list[GatedDiscoveryCandidate]:
    gated: list[GatedDiscoveryCandidate] = []
    row_visibility_threshold = visibility_threshold()
    relevance = intent.location_context.relevance if intent else "none"
    requires_location = relevance in {"service_area", "vendor_proximity"}
    preferred = PREFERRED_TYPES.get(discovery_mode, {"official_vendor_site"})
    fallback = FALLBACK_TYPES.get(discovery_mode, set())
    rejected = REJECT_TYPES.get(discovery_mode, {"editorial_or_irrelevant"})

    for candidate in candidates:
        classification = candidate.classification or {}
        candidate_type = str(classification.get("candidate_type") or "editorial_or_irrelevant")
        location_evidence = classification.get("location_evidence") or []
        service_evidence = classification.get("service_category_evidence") or []

        reasons: list[str] = []
        admissible = True
        type_score = 1.0 if candidate_type in preferred else 0.65 if candidate_type in fallback else 0.2
        if candidate_type in rejected:
            admissible = False
            reasons.append(f"type_rejected:{candidate_type}")

        trust_score = 0.35
        if classification.get("official_site"):
            trust_score += 0.3
        if classification.get("first_party_contact"):
            trust_score += 0.2
        if candidate.canonical_domain:
            trust_score += 0.1
        if candidate_type == "directory_or_aggregator":
            trust_score -= 0.15
        trust_score = max(0.0, min(trust_score, 1.0))

        location_score = 0.5
        if location_evidence:
            location_score = 0.95
        elif requires_location:
            location_score = 0.2
            reasons.append("missing_location_evidence")

        specialization_score = 0.55 if service_evidence else 0.35
        if candidate_type in {"brokerage_or_agent_site", "official_vendor_site", "marketplace_or_exchange"} and service_evidence:
            specialization_score = 0.85

        if requires_location and not location_evidence and candidate_type not in fallback:
            admissible = False

        if _high_risk_mode(discovery_mode) and trust_score < 0.55:
            admissible = False
            reasons.append("trust_floor_failed")

        final_score = (
            type_score * 0.45
            + specialization_score * 0.25
            + trust_score * 0.20
            + location_score * 0.10
        )

        if not admissible or final_score < row_visibility_threshold:
            if final_score < row_visibility_threshold:
                reasons.append("below_row_visibility_threshold")
            admissible = False

        gated.append(
            GatedDiscoveryCandidate(
                candidate=candidate,
                admissible=admissible,
                heuristic_fit=round(type_score * 0.6 + specialization_score * 0.4, 4),
                trust_score=round(trust_score, 4),
                location_score=round(location_score, 4),
                final_score=round(final_score, 4),
                rejection_reasons=reasons,
            )
        )

    if requires_location:
        has_local_admissible = any(item.admissible and item.location_score >= 0.9 for item in gated)
        if has_local_admissible:
            for item in gated:
                if item.admissible and item.location_score < 0.9:
                    item.admissible = False
                    if "suppressed_by_local_matches" not in item.rejection_reasons:
                        item.rejection_reasons.append("suppressed_by_local_matches")

    return gated
