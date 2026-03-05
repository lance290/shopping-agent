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
    return float(os.getenv("VENDOR_DISTANCE_THRESHOLD", "0.55"))


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
        final_limit = kwargs.get("limit", 15)

        # Build OR-based tsquery for FTS resilience.
        # plainto_tsquery does AND — "yacht charter San Diego" requires ALL words,
        # killing matches when location/date words are included.
        # We use to_tsquery with OR (|) so any word match counts,
        # but more matching words rank higher via ts_rank_cd.
        fts_words = [w.strip() for w in query.split() if w.strip() and len(w.strip()) > 1]
        if fts_words:
            fts_query_str = " | ".join(fts_words)
        else:
            fts_query_str = query

        # 2. Hybrid query: UNION of vector-nearest + FTS-matched candidates.
        #    We fetch candidates from BOTH paths and merge/dedup in Python
        #    so FTS matches are never crowded out by mediocre vector matches.
        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(
                    sa.text("""
                        WITH
                        -- Top candidates by vector similarity
                        vec_candidates AS (
                            SELECT id, name, description, tagline, website, email, phone,
                                   image_url, category,
                                   (embedding <=> CAST(:qvec AS vector)) AS distance,
                                   CASE
                                     WHEN search_vector IS NOT NULL
                                     THEN ts_rank_cd(search_vector, to_tsquery('english', :fts_query))
                                     ELSE 0
                                   END AS fts_rank
                            FROM vendor
                            WHERE embedding IS NOT NULL
                            ORDER BY embedding <=> CAST(:qvec AS vector)
                            LIMIT :vec_lim
                        ),
                        -- Top candidates by FTS rank (guaranteed inclusion)
                        fts_candidates AS (
                            SELECT id, name, description, tagline, website, email, phone,
                                   image_url, category,
                                   (embedding <=> CAST(:qvec AS vector)) AS distance,
                                   ts_rank_cd(search_vector, to_tsquery('english', :fts_query)) AS fts_rank
                            FROM vendor
                            WHERE embedding IS NOT NULL
                              AND search_vector IS NOT NULL
                              AND search_vector @@ to_tsquery('english', :fts_query)
                            ORDER BY ts_rank_cd(search_vector, to_tsquery('english', :fts_query)) DESC
                            LIMIT :fts_lim
                        ),
                        -- Merge and dedup (FTS row wins on tie)
                        merged AS (
                            SELECT * FROM fts_candidates
                            UNION ALL
                            SELECT * FROM vec_candidates v
                            WHERE NOT EXISTS (SELECT 1 FROM fts_candidates f WHERE f.id = v.id)
                        )
                        SELECT * FROM merged
                    """),
                    {
                        "qvec": vec_str,
                        "fts_query": fts_query_str,
                        "vec_lim": final_limit * 2,
                        "fts_lim": final_limit,
                    },
                )
                rows = result.mappings().all()
                t_db = time.monotonic()
                logger.info(
                    f"[VendorProvider] Hybrid query took {t_db - t_embed:.2f}s, "
                    f"{len(rows)} candidates (weights: vec={vector_weight}, fts={fts_weight})"
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

        # 3. Filter candidates and convert to SearchResult.
        #    - FTS matches (fts_rank > 0) are ALWAYS included regardless of distance.
        #    - Vector-only matches are filtered by distance threshold.
        #    - FTS rank normalized by dividing by FTS_NORM_DIVISOR (not capped at 1.0).
        threshold = _get_distance_threshold()
        FTS_NORM_DIVISOR = 5.0  # ts_rank_cd scores typically range 0-5 for our corpus
        results: List[SearchResult] = []
        for r in rows:
            fts_rank_raw = float(r.get("fts_rank", 0))
            has_fts_match = fts_rank_raw > 0

            # Vector-only candidates must pass distance threshold
            if not has_fts_match and r["distance"] > threshold:
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

            # Blend vector similarity (0-1) with normalized FTS rank (0-1)
            vec_score = 1.0 - float(r["distance"])
            fts_norm = min(fts_rank_raw / FTS_NORM_DIVISOR, 1.0)
            blended = vector_weight * vec_score + fts_weight * fts_norm

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

        # Sort by blended score descending (best matches first)
        results.sort(key=lambda x: x.match_score or 0, reverse=True)
        results = results[:final_limit]

        fts_included = sum(1 for r in rows if float(r.get("fts_rank", 0)) > 0)
        logger.info(
            f"[VendorProvider] Found {len(results)} vendors "
            f"(candidates={len(rows)}, fts_matched={fts_included}, vec_threshold={threshold})"
        )
        return results
