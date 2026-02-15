"""Vendor Directory Provider — vector search against our vendor DB.

This is a sourcing provider that runs in parallel with web search providers.
It embeds the query via OpenRouter and does cosine similarity search against
vendor embeddings in the vendor table (pgvector).

Always returns results as SearchResult objects so they merge naturally
with web search results in the sourcing pipeline.
"""
import os
import logging
from typing import List, Optional

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as SAAsyncSession
from sqlalchemy.pool import NullPool

from sourcing.repository import SearchResult, SourcingProvider

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/embeddings"

# Cosine distance threshold: 0 = identical, 2 = opposite
DISTANCE_THRESHOLD = float(os.getenv("VENDOR_DISTANCE_THRESHOLD", "0.55"))


async def _embed_query(text: str) -> Optional[List[float]]:
    """Embed a single query string via OpenRouter."""
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
                    "input": [text],
                    "dimensions": EMBEDDING_DIMENSIONS,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"[VendorProvider] Embedding failed: {e}")
        return None


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
        """Embed query, cosine search vendor table, return SearchResults."""
        # 1. Embed the query
        embedding = await _embed_query(query)
        if not embedding:
            logger.info("[VendorProvider] No embedding — skipping vector search")
            return []

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

            favicon = ""
            if r["image_url"]:
                favicon = r["image_url"]
            elif r["website"]:
                domain = r["website"].replace("https://", "").replace("http://", "").split("/")[0]
                favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

            results.append(SearchResult(
                title=r["name"],
                price=0.0,
                currency="USD",
                merchant=r["name"],
                url=url,
                merchant_domain=r["website"].replace("https://", "").replace("http://", "").split("/")[0] if r["website"] else "",
                image_url=favicon,
                source="vendor_directory",
                rating=None,
                reviews_count=None,
                shipping_info=f"Category: {r['category'] or 'General'}" if r["category"] else None,
            ))

        logger.info(f"[VendorProvider] Found {len(results)} vendors within distance {DISTANCE_THRESHOLD} (checked {len(rows)} total)")
        return results
