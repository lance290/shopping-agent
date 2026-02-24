"""Vendor Directory Provider — vector search against our vendor DB.

This is a sourcing provider that runs in parallel with web search providers.
It embeds the query via OpenRouter and does cosine similarity search against
vendor embeddings in the vendor table (pgvector).

Always returns results as SearchResult objects so they merge naturally
with web search results in the sourcing pipeline.
"""
import math
import os
import logging
from typing import List, Optional

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from sourcing.repository import SearchResult, SourcingProvider

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/embeddings"

# Cosine distance threshold: 0 = identical, 2 = opposite
DISTANCE_THRESHOLD = float(os.getenv("VENDOR_DISTANCE_THRESHOLD", "0.45"))


async def _embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """Embed one or more texts via OpenRouter in a single batched call."""
    if not OPENROUTER_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                OPENROUTER_BASE_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": texts,
                    "dimensions": EMBEDDING_DIMENSIONS,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
    except Exception as e:
        logger.warning(f"[VendorProvider] Embedding failed: {e}")
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


class VendorDirectoryProvider(SourcingProvider):
    """Searches our vendor DB using pgvector cosine similarity."""

    def __init__(self, database_url: str):
        self._database_url = database_url
        # Create engine once with a small connection pool
        self._engine = create_async_engine(
            database_url, 
            pool_size=5, 
            max_overflow=10,
            pool_timeout=30
        )

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """Embed query, cosine search vendor table, return SearchResults.

        If a context_query kwarg is provided (the full user query with locations
        etc.), we blend two embeddings:
          - 70% intent query (product_name from LLM, e.g. 'Private jet charter')
          - 30% context query (full query, e.g. 'private jet charter san diego nashville')
        This keeps intent dominant while still boosting vendors that match context.
        """
        context_query = kwargs.get("context_query")

        # 1. Embed — batched if we have both intent + context
        if context_query and context_query.strip().lower() != query.strip().lower():
            vecs = await _embed_texts([query, context_query])
            if not vecs or len(vecs) < 2:
                logger.info("[VendorProvider] No embedding — skipping vector search")
                return []
            embedding = _weighted_blend(vecs, [0.7, 0.3])
            logger.info(f"[VendorProvider] Blended embedding: 70% '{query}' + 30% '{context_query}'")
        else:
            vecs = await _embed_texts([query])
            if not vecs:
                logger.info("[VendorProvider] No embedding — skipping vector search")
                return []
            embedding = vecs[0]

        vec_str = "[" + ",".join(str(f) for f in embedding) + "]"

        # 2. Query vendor table with cosine similarity
        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(
                    sa.text(
                        "SELECT id, name, description, tagline, website, email, phone, "
                        "image_url, category, "
                        "(embedding <=> CAST(:qvec AS vector)) AS distance "
                        "FROM vendor "
                        "WHERE embedding IS NOT NULL "
                        "ORDER BY embedding <=> CAST(:qvec AS vector) "
                        "LIMIT :lim"
                    ),
                    {"qvec": vec_str, "lim": kwargs.get("limit", 15)},
                )
                rows = result.mappings().all()
        except Exception as e:
            logger.warning(f"[VendorProvider] DB query failed: {e}")
            return []

        # 3. Filter by distance threshold and convert to SearchResult
        results: List[SearchResult] = []
        for r in rows:
            if r["distance"] > DISTANCE_THRESHOLD:
                continue

            url = r["website"] or ""
            if not url and r["email"]:
                url = f"mailto:{r['email']}"

            # Extract a meaningful domain — skip aggregator/platform URLs
            raw_domain = ""
            if r["website"]:
                raw_domain = r["website"].replace("https://", "").replace("http://", "").split("/")[0]
            aggregator_domains = {
                "google.com", "www.google.com", "maps.google.com",
                "yelp.com", "www.yelp.com",
                "facebook.com", "www.facebook.com",
                "linkedin.com", "www.linkedin.com",
                "instagram.com", "www.instagram.com",
                "twitter.com", "www.twitter.com", "x.com",
                "youtube.com", "www.youtube.com",
            }
            merchant_domain = raw_domain if raw_domain and raw_domain.lower() not in aggregator_domains else ""

            favicon = ""
            if r["image_url"]:
                favicon = r["image_url"]
            elif merchant_domain:
                favicon = f"https://www.google.com/s2/favicons?domain={merchant_domain}&sz=128"

            results.append(SearchResult(
                title=r["name"],
                price=None,
                currency="USD",
                merchant=r["name"],
                url=url,
                merchant_domain=merchant_domain,
                image_url=favicon,
                source="vendor_directory",
                match_score=1.0 - float(r["distance"]),
                rating=None,
                reviews_count=None,
                shipping_info=f"Category: {r['category'] or 'General'}" if r["category"] else None,
            ))

        logger.info(f"[VendorProvider] Found {len(results)} vendors within distance {DISTANCE_THRESHOLD} (checked {len(rows)} total)")
        return results
