"""Embedding utilities for the Vendor Directory Provider.

Handles OpenRouter API calls, concept weighting, and vector blending
for vendor search queries.
"""

import math
import logging
import os
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/embeddings"


def _get_openrouter_api_key() -> str:
    """Read at call time so dotenv has loaded."""
    return os.getenv("OPENROUTER_API_KEY", "")


def _get_embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")


def _get_embedding_dimensions() -> int:
    return int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))


async def _embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """Embed one or more texts via OpenRouter in a single batched call."""
    api_key = _get_openrouter_api_key()
    if not api_key:
        logger.warning("[VendorProvider] No OPENROUTER_API_KEY — skipping embedding")
        return None
    model = _get_embedding_model()
    dims = _get_embedding_dimensions()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                OPENROUTER_BASE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": texts,
                    "dimensions": dims,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
    except Exception as e:
        logger.warning(f"[VendorProvider] Embedding failed: {type(e).__name__}: {e}")
        return None


def _weighted_blend(vecs: List[List[float]], weights: List[float]) -> List[float]:
    """Blend multiple embedding vectors with weights, then L2-normalize."""
    dim = len(vecs[0])
    blended = [0.0] * dim
    for vec, w in zip(vecs, weights):
        for i in range(dim):
            blended[i] += vec[i] * w
    # L2-normalize so cosine distance works correctly
    norm = math.sqrt(sum(x * x for x in blended))
    if norm > 0:
        blended = [x / norm for x in blended]
    return blended


def _build_embedding_concepts(
    query: str,
    context_query: Optional[str] = None,
    intent_payload: Optional[dict] = None,
) -> List[tuple[str, float]]:
    core_product = (query or "").strip()
    specs_parts: List[str] = []

    if isinstance(intent_payload, dict):
        product_name = intent_payload.get("product_name")
        if product_name and str(product_name).strip():
            core_product = str(product_name).strip()

        constraints = intent_payload.get("features") or intent_payload.get("constraints", {})
        if isinstance(constraints, dict):
            for _, value in constraints.items():
                if value and str(value).lower() not in ("none", "null", "", "not answered"):
                    specs_parts.append(str(value))

        keywords = intent_payload.get("keywords", [])
        if isinstance(keywords, list):
            specs_parts.extend([
                str(keyword)
                for keyword in keywords
                if keyword and str(keyword).strip().lower() != core_product.lower()
            ])

    concepts: List[tuple[str, float]] = [(core_product, 0.60)]
    if specs_parts:
        concepts.append((" ".join(specs_parts[:10]), 0.25))
    else:
        concepts[0] = (concepts[0][0], 0.80)

    cleaned_context = (context_query or "").strip()
    if cleaned_context and cleaned_context.lower() != core_product.lower():
        remaining_weight = 1.0 - sum(weight for _, weight in concepts)
        if remaining_weight > 0.05:
            concepts.append((cleaned_context, remaining_weight))

    total_weight = sum(weight for _, weight in concepts)
    if total_weight <= 0:
        return [(core_product, 1.0)] if core_product else []
    return [(text, weight / total_weight) for text, weight in concepts if text]


async def build_query_embedding(
    query: str,
    context_query: Optional[str] = None,
    intent_payload: Optional[dict] = None,
    pre_computed: Optional[List[float]] = None,
) -> Optional[List[float]]:
    if pre_computed:
        return pre_computed

    concepts = _build_embedding_concepts(query, context_query=context_query, intent_payload=intent_payload)
    if not concepts:
        return None

    texts = [text for text, _ in concepts]
    weights = [weight for _, weight in concepts]
    vecs = await _embed_texts(texts)
    if not vecs or len(vecs) != len(concepts):
        return None
    if len(vecs) == 1:
        return vecs[0]
    return _weighted_blend(vecs, weights)
