"""Structured debug helpers for discovery session auditability."""

from __future__ import annotations

from typing import Any

from sourcing.discovery.gating import GatedDiscoveryCandidate


def build_discovery_audit_record(
    *,
    discovery_session_id: str,
    discovery_mode: str,
    query: str,
    candidate: GatedDiscoveryCandidate,
    llm_summary: str | None = None,
) -> dict[str, Any]:
    classification = candidate.candidate.classification or {}
    return {
        "discovery_session_id": discovery_session_id,
        "query": query,
        "discovery_mode": discovery_mode,
        "candidate_url": candidate.candidate.url,
        "candidate_domain": candidate.candidate.canonical_domain,
        "candidate_title": candidate.candidate.title,
        "candidate_type": classification.get("candidate_type"),
        "admissible": candidate.admissible,
        "rejection_reasons": list(candidate.rejection_reasons),
        "heuristic_fit": candidate.heuristic_fit,
        "trust_score": candidate.trust_score,
        "location_score": candidate.location_score,
        "final_score": candidate.final_score,
        "llm_rerank_summary": llm_summary,
    }
