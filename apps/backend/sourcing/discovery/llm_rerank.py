"""LLM-assisted reranking for already-gated discovery candidates."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Sequence

from models.rows import Row
from services.llm import _extract_json_array, call_gemini
from sourcing.discovery.gating import GatedDiscoveryCandidate
from sourcing.models import SearchIntent

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryRerankDecision:
    candidate_id: str
    llm_score: float
    fit_summary: str
    specialization_score: float
    trust_adjustment: float
    should_demote: bool
    should_exclude: bool
    exclusion_reason: str | None = None

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


async def rerank_gated_candidates(
    candidates: Sequence[GatedDiscoveryCandidate],
    *,
    intent: SearchIntent | None,
    row: Row | None,
) -> tuple[list[GatedDiscoveryCandidate], dict[str, DiscoveryRerankDecision]]:
    admissible = [candidate for candidate in candidates if candidate.admissible]
    if len(admissible) <= 1:
        return list(candidates), {}

    prompt = _build_prompt(admissible, intent=intent, row=row)
    try:
        response = await call_gemini(prompt, timeout=12.0)
        parsed = _extract_json_array(response)
        decisions = _parse_decisions(parsed)
    except Exception as exc:
        logger.warning("[VendorDiscovery] LLM rerank unavailable, falling back to heuristic ranking only: %s", exc)
        return sorted(candidates, key=lambda item: item.final_score, reverse=True), {}

    decision_map = {decision.candidate_id: decision for decision in decisions}
    reranked: list[GatedDiscoveryCandidate] = []
    for item in candidates:
        candidate_id = _candidate_id(item)
        decision = decision_map.get(candidate_id)
        llm_score = decision.llm_score if decision else item.heuristic_fit
        trust_adjustment = decision.trust_adjustment if decision else 0.0
        final_score = (
            item.heuristic_fit * 0.45
            + llm_score * 0.35
            + item.trust_score * 0.10
            + item.location_score * 0.10
        ) + trust_adjustment
        item.final_score = round(max(0.0, min(final_score, 1.0)), 4)
        if decision and decision.should_exclude:
            item.admissible = False
            if decision.exclusion_reason:
                item.rejection_reasons.append(decision.exclusion_reason)
        reranked.append(item)

    reranked.sort(key=lambda item: item.final_score, reverse=True)
    return reranked, decision_map


def _candidate_id(candidate: GatedDiscoveryCandidate) -> str:
    return candidate.candidate.canonical_domain or candidate.candidate.url


def _build_prompt(
    candidates: Sequence[GatedDiscoveryCandidate],
    *,
    intent: SearchIntent | None,
    row: Row | None,
) -> str:
    request_text = (intent.raw_input if intent else "") or getattr(row, "title", "") or ""
    payload = []
    for item in candidates[:8]:
        classification = item.candidate.classification or {}
        payload.append(
            {
                "candidate_id": _candidate_id(item),
                "title": item.candidate.title,
                "url": item.candidate.url,
                "snippet": item.candidate.snippet,
                "candidate_type": classification.get("candidate_type"),
                "official_site": classification.get("official_site"),
                "first_party_contact": classification.get("first_party_contact"),
                "location_evidence": classification.get("location_evidence", []),
                "service_category_evidence": classification.get("service_category_evidence", []),
                "heuristic_fit": item.heuristic_fit,
                "trust_score": item.trust_score,
                "location_score": item.location_score,
            }
        )
    return (
        "You are reranking already-vetted discovery candidates for BuyAnything.\n"
        "The candidates have already passed deterministic gating. Your job is to assess nuanced fit, not to invent facts.\n"
        f"User request: {request_text}\n"
        "Return ONLY a JSON array. One object per candidate with keys:\n"
        "candidate_id, llm_score (0-1), fit_summary, specialization_score (0-1), trust_adjustment (-0.1 to 0.1), "
        "should_demote (bool), should_exclude (bool), exclusion_reason.\n"
        "Do not exclude a candidate unless it appears semantically wrong even after gating.\n"
        f"Candidates: {json.dumps(payload)}"
    )


def _parse_decisions(parsed: object) -> list[DiscoveryRerankDecision]:
    if not isinstance(parsed, list):
        return []
    decisions: list[DiscoveryRerankDecision] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("candidate_id") or "").strip()
        if not candidate_id:
            continue
        try:
            llm_score = max(0.0, min(float(item.get("llm_score", 0.5)), 1.0))
        except Exception:
            llm_score = 0.5
        try:
            specialization_score = max(0.0, min(float(item.get("specialization_score", llm_score)), 1.0))
        except Exception:
            specialization_score = llm_score
        try:
            trust_adjustment = max(-0.1, min(float(item.get("trust_adjustment", 0.0)), 0.1))
        except Exception:
            trust_adjustment = 0.0
        decisions.append(
            DiscoveryRerankDecision(
                candidate_id=candidate_id,
                llm_score=llm_score,
                fit_summary=str(item.get("fit_summary") or "")[:240],
                specialization_score=specialization_score,
                trust_adjustment=trust_adjustment,
                should_demote=bool(item.get("should_demote")),
                should_exclude=bool(item.get("should_exclude")),
                exclusion_reason=str(item.get("exclusion_reason") or "") or None,
            )
        )
    return decisions
