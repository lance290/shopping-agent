"""Cheap structured LLM reranker for high-risk, local, and custom-vendor flows.

Per plan §Phase 3, this supplements (never replaces) the hybrid scoring model.
The reranker is called ONLY when:
  - execution_mode is sourcing_only or affiliate_plus_sourcing
  - desire_tier is high_value, advisory, bespoke, or service
  - OR search_strategies include specialist_first, prestige_first, or local_network_first

The reranker asks a cheap LLM (Gemini Flash) to score the top-N candidates on
relevance, trustworthiness, and actionability.  Results are written into
provenance["llm_rerank"] and blended into the combined score.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from sourcing.models import NormalizedResult, SearchIntent

logger = logging.getLogger(__name__)

# Max candidates to send to the reranker (cost control)
_MAX_RERANK_CANDIDATES = 12

# Weight of reranker score in the final blend
_RERANK_BLEND_WEIGHT = 0.15

# Desire tiers that trigger reranking
_RERANK_TIERS = {"high_value", "advisory", "bespoke", "service"}

# Strategies that trigger reranking
_RERANK_STRATEGIES = {"specialist_first", "prestige_first", "local_network_first"}


def should_rerank(
    intent: Optional[SearchIntent],
    desire_tier: Optional[str],
    execution_mode: Optional[str],
) -> bool:
    """Decide whether to invoke the LLM reranker for this search."""
    if execution_mode and execution_mode in ("sourcing_only", "affiliate_plus_sourcing"):
        return True
    if desire_tier and desire_tier.strip().lower() in _RERANK_TIERS:
        return True
    if intent and intent.search_strategies:
        if set(intent.search_strategies) & _RERANK_STRATEGIES:
            return True
    return False


def _build_rerank_prompt(
    query: str,
    candidates: List[Dict],
    intent: Optional[SearchIntent],
) -> str:
    """Build the structured reranking prompt."""
    intent_summary = ""
    if intent:
        parts = []
        if intent.product_name:
            parts.append(f"Product: {intent.product_name}")
        if intent.brand:
            parts.append(f"Brand: {intent.brand}")
        if intent.location_context and intent.location_context.relevance != "none":
            targets = intent.location_context.targets.non_empty_items()
            if targets:
                parts.append(f"Location: {', '.join(targets.values())}")
        if intent.source_archetypes:
            parts.append(f"Preferred source types: {', '.join(intent.source_archetypes)}")
        intent_summary = "\n".join(parts)

    candidate_lines = []
    for i, c in enumerate(candidates):
        line = f"{i}: title={c['title']!r}, source={c['source']!r}, domain={c['domain']!r}"
        if c.get("price"):
            line += f", price=${c['price']}"
        if c.get("candidate_type"):
            line += f", type={c['candidate_type']}"
        candidate_lines.append(line)

    return f"""You are a search result quality assessor. Score each candidate for a procurement query.

Query: "{query}"
{intent_summary}

Candidates:
{chr(10).join(candidate_lines)}

For EACH candidate (by index), return a JSON array with:
- idx: candidate index
- include: true/false (false ONLY if completely irrelevant or a scam)
- relevance: 0.0-1.0 (does this result match what the user wants?)
- trust: 0.0-1.0 (is this a trustworthy, authoritative source for this kind of request?)
- actionability: 0.0-1.0 (can the user take action — contact, purchase, get a quote?)
- reason_codes: list of short string codes explaining the scores (e.g. ["local_specialist", "no_contact_info", "wrong_category"])

Return ONLY a JSON array, no explanation:
[{{"idx": 0, "include": true, "relevance": 0.9, "trust": 0.8, "actionability": 0.7, "reason_codes": ["high_trust_broker"]}}, ...]"""


async def rerank_candidates(
    query: str,
    results: List[NormalizedResult],
    intent: Optional[SearchIntent] = None,
) -> List[NormalizedResult]:
    """Run the cheap LLM reranker on top candidates and blend scores back.

    Returns the same list with provenance["llm_rerank"] populated and
    provenance["score"]["combined"] adjusted.
    """
    if not results:
        return results

    top_n = results[:_MAX_RERANK_CANDIDATES]
    candidates = []
    for r in top_n:
        raw = r.raw_data if isinstance(r.raw_data, dict) else {}
        prov = r.provenance if isinstance(r.provenance, dict) else {}
        candidates.append({
            "title": r.title[:120],
            "source": r.source,
            "domain": r.merchant_domain[:80],
            "price": r.price,
            "candidate_type": raw.get("candidate_type") or prov.get("candidate_type"),
        })

    prompt = _build_rerank_prompt(query, candidates, intent)

    try:
        from services.llm_core import call_gemini, _extract_json_array
        text = await call_gemini(prompt, timeout=10.0)
        scores = _extract_json_array(text)
        if not isinstance(scores, list):
            logger.warning("[reranker] LLM returned non-list, skipping rerank")
            return results
    except Exception as e:
        logger.warning("[reranker] LLM rerank call failed (graceful degradation): %s", e)
        return results

    score_map: Dict[int, Dict] = {}
    for entry in scores:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("idx")
        if idx is not None and isinstance(idx, int) and 0 <= idx < len(top_n):
            score_map[idx] = {
                "include": bool(entry.get("include", True)),
                "relevance": _clamp(entry.get("relevance", 0.5)),
                "trust": _clamp(entry.get("trust", 0.5)),
                "actionability": _clamp(entry.get("actionability", 0.5)),
                "reason_codes": entry.get("reason_codes", []),
            }

    final_results = []
    for idx, r in enumerate(top_n):
        rerank_data = score_map.get(idx)
        if not rerank_data:
            final_results.append(r)
            continue
        
        if not rerank_data.get("include", True):
            logger.info("[reranker] Excluded candidate: %s due to LLM rerank", r.title)
            continue

        composite = (
            rerank_data["relevance"] * 0.5
            + rerank_data["trust"] * 0.3
            + rerank_data["actionability"] * 0.2
        )
        r.provenance["llm_rerank"] = {
            **rerank_data,
            "composite": round(composite, 4),
        }

        existing_score = r.provenance.get("score", {})
        old_combined = existing_score.get("combined", 0.0)
        new_combined = (
            old_combined * (1.0 - _RERANK_BLEND_WEIGHT)
            + composite * _RERANK_BLEND_WEIGHT
        )
        existing_score["combined"] = round(new_combined, 4)
        existing_score["llm_rerank_composite"] = round(composite, 4)
        r.provenance["score"] = existing_score
        
        final_results.append(r)

    # Append any results that were past top_n
    final_results.extend(results[len(top_n):])
    final_results.sort(key=lambda r: (r.provenance.get("score", {}).get("combined", 0.0)), reverse=True)

    reranked_count = len(score_map)
    logger.info("[reranker] Reranked %d/%d candidates", reranked_count, len(top_n))
    return final_results


def _clamp(v, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return 0.5
