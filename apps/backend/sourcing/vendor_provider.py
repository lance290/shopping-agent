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
import time
from typing import List, Optional

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from sourcing.repository import SearchResult, SourcingProvider

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/embeddings"


def _get_openrouter_api_key() -> str:
    """Read at call time so dotenv has loaded."""
    return os.getenv("OPENROUTER_API_KEY", "")


def _get_embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")


def _get_embedding_dimensions() -> int:
    return int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))

# Cosine distance threshold: 0 = identical, 2 = opposite
# Default read at call time so .env overrides work
def _get_distance_threshold() -> float:
    return float(os.getenv("VENDOR_DISTANCE_THRESHOLD", "0.45"))


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
        t0 = time.monotonic()

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

        t_embed = time.monotonic()
        logger.info(f"[VendorProvider] Embedding took {t_embed - t0:.2f}s")

        vec_str = "[" + ",".join(str(f) for f in embedding) + "]"

        # Hybrid scoring weights
        vector_weight = float(os.getenv("VENDOR_VECTOR_WEIGHT", "0.7"))
        fts_weight = 1.0 - vector_weight

        # 2. Hybrid query: vector cosine + full-text ts_rank, blended
        #    ts_rank returns 0 when search_vector is NULL or no match,
        #    so the query gracefully degrades to vector-only for vendors
        #    without the search_vector column (pre-migration).
        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(
                    sa.text("""
                        SELECT id, name, description, tagline, website, email, phone,
                               image_url, category,
                               (embedding <=> CAST(:qvec AS vector)) AS distance,
                               CASE
                                 WHEN search_vector IS NOT NULL
                                 THEN ts_rank_cd(search_vector, plainto_tsquery('english', :raw_query))
                                 ELSE 0
                               END AS fts_rank
                        FROM vendor
                        WHERE embedding IS NOT NULL
                        ORDER BY (
                            :vec_w * (embedding <=> CAST(:qvec AS vector)) +
                            :fts_w * (1.0 - LEAST(
                                CASE
                                  WHEN search_vector IS NOT NULL
                                  THEN ts_rank_cd(search_vector, plainto_tsquery('english', :raw_query))
                                  ELSE 0
                                END, 1.0))
                        )
                        LIMIT :lim
                    """),
                    {
                        "qvec": vec_str,
                        "raw_query": query,
                        "vec_w": vector_weight,
                        "fts_w": fts_weight,
                        "lim": kwargs.get("limit", 15),
                    },
                )
                rows = result.mappings().all()
                t_db = time.monotonic()
                logger.info(
                    f"[VendorProvider] Hybrid query took {t_db - t_embed:.2f}s, "
                    f"{len(rows)} rows (weights: vec={vector_weight}, fts={fts_weight})"
                )
        except Exception as e:
            # If search_vector column doesn't exist yet, fall back to vector-only
            if "search_vector" in str(e):
                logger.warning("[VendorProvider] search_vector column missing — falling back to vector-only")
                try:
                    async with self._engine.connect() as conn:
                        result = await conn.execute(
                            sa.text(
                                "SELECT id, name, description, tagline, website, email, phone, "
                                "image_url, category, "
                                "(embedding <=> CAST(:qvec AS vector)) AS distance, "
                                "0::float AS fts_rank "
                                "FROM vendor "
                                "WHERE embedding IS NOT NULL "
                                "ORDER BY embedding <=> CAST(:qvec AS vector) "
                                "LIMIT :lim"
                            ),
                            {"qvec": vec_str, "lim": kwargs.get("limit", 15)},
                        )
                        rows = result.mappings().all()
                        t_db = time.monotonic()
                        logger.info(f"[VendorProvider] Vector-only fallback took {t_db - t_embed:.2f}s, {len(rows)} rows")
                except Exception as e2:
                    logger.warning(f"[VendorProvider] Vector-only fallback also failed: {e2}")
                    return []
            else:
                logger.warning(f"[VendorProvider] DB query failed: {e}")
                return []

        # 3. Filter by distance threshold and convert to SearchResult
        #    Boost match_score when FTS also matched (fts_rank > 0)
        results: List[SearchResult] = []
        for r in rows:
            threshold = _get_distance_threshold()
            if r["distance"] > threshold:
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

            # Blend vector similarity (0-1) with FTS rank (0-1 clamped)
            vec_score = 1.0 - float(r["distance"])
            fts_rank = min(float(r.get("fts_rank", 0)), 1.0)
            blended = vector_weight * vec_score + fts_weight * fts_rank

            results.append(SearchResult(
                title=r["name"],
                price=None,
                currency="USD",
                merchant=r["name"],
                url=url,
                merchant_domain=merchant_domain,
                image_url=favicon,
                source="vendor_directory",
                match_score=round(blended, 4),
                rating=None,
                reviews_count=None,
                shipping_info=f"Category: {r['category'] or 'General'}" if r["category"] else None,
                description=r["tagline"] or r["description"] or None,
            ))

        fts_boosted = sum(1 for r in rows if float(r.get("fts_rank", 0)) > 0)
        logger.info(
            f"[VendorProvider] Found {len(results)} vendors within distance {_get_distance_threshold()} "
            f"(checked {len(rows)}, {fts_boosted} had FTS boost)"
        )
        return results
