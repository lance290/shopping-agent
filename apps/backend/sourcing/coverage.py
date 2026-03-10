"""Strict sufficiency scoring for internal vendor coverage."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from sourcing.repository import SearchResult


@dataclass
class CoverageCandidateScore:
    title: str
    source: str
    semantic_fit: float
    geography_fit: float
    luxury_fit: float
    contactability: float
    specialization_fit: float
    freshness: float
    source_credibility: float
    duplicate_penalty: float
    total_score: float
    missing_signals: List[str]
    reasoning: List[str]

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CoverageEvaluation:
    status: str
    recommended_action: str
    candidates: List[CoverageCandidateScore]
    reasons: List[str]

    def model_dump(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "recommended_action": self.recommended_action,
            "candidates": [candidate.model_dump() for candidate in self.candidates],
            "reasons": list(self.reasons),
        }


def evaluate_internal_vendor_coverage(
    results: List[SearchResult],
    *,
    high_risk: bool = False,
) -> CoverageEvaluation:
    candidates = [_score_candidate(result) for result in results[:8]]
    strong = [candidate for candidate in candidates if candidate.total_score >= 0.75]
    elite = [candidate for candidate in candidates if candidate.total_score >= 0.80]

    reasons: List[str] = []
    if len(strong) >= 3 and (not high_risk or len(elite) >= 2):
        reasons.append("internal vendor coverage met strict sufficiency thresholds")
        return CoverageEvaluation("sufficient", "stop", candidates, reasons)
    if len(strong) >= 2 or len([candidate for candidate in candidates if candidate.total_score >= 0.65]) >= 4:
        reasons.append("internal coverage is usable but not strong enough to skip live discovery")
        return CoverageEvaluation("borderline", "discover_parallel", candidates, reasons)
    reasons.append("internal vendor coverage is insufficient for this request")
    return CoverageEvaluation("insufficient", "discover_now", candidates, reasons)


def _score_candidate(result: SearchResult) -> CoverageCandidateScore:
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    semantic_fit = min(1.0, max(float(result.match_score or 0.0), 0.0))
    geography_fit = 1.0 if metadata.get("location_match") else (0.2 if metadata.get("location_mode") not in (None, "none") else 0.5)
    luxury_fit = 0.7 if any(token in (result.title or "").lower() for token in ("luxury", "estate", "broker", "charter")) else 0.4
    contactability = 0.8 if metadata.get("official_site") else 0.4
    specialization_fit = 0.8 if metadata.get("service_category_match", True) else 0.3
    freshness = 0.5
    source_credibility = 0.9 if metadata.get("official_site") else 0.5
    duplicate_penalty = 0.0
    if "directory" in (result.source or "").lower():
        duplicate_penalty = 0.1

    total_score = (
        semantic_fit * 0.30
        + geography_fit * 0.20
        + specialization_fit * 0.15
        + source_credibility * 0.15
        + contactability * 0.10
        + freshness * 0.05
        + luxury_fit * 0.05
    ) - duplicate_penalty
    missing_signals: List[str] = []
    if not metadata.get("official_site"):
        missing_signals.append("official_site")
    reasoning = [
        f"semantic_fit={semantic_fit:.2f}",
        f"geography_fit={geography_fit:.2f}",
        f"source_credibility={source_credibility:.2f}",
    ]
    return CoverageCandidateScore(
        title=result.title,
        source=result.source,
        semantic_fit=round(semantic_fit, 4),
        geography_fit=round(geography_fit, 4),
        luxury_fit=round(luxury_fit, 4),
        contactability=round(contactability, 4),
        specialization_fit=round(specialization_fit, 4),
        freshness=round(freshness, 4),
        source_credibility=round(source_credibility, 4),
        duplicate_penalty=round(duplicate_penalty, 4),
        total_score=round(max(total_score, 0.0), 4),
        missing_signals=missing_signals,
        reasoning=reasoning,
    )
