"""Vendor Directory Provider — vector search against our vendor DB.

This is a sourcing provider that runs in parallel with web search providers.
It embeds the query via OpenRouter and does cosine similarity search against
vendor embeddings in the vendor table (pgvector).

Always returns results as SearchResult objects so they merge naturally
with web search results in the sourcing pipeline.
"""
import os
import re
import logging
import time
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from sourcing.location import location_weight_profile
from sourcing.repository import SearchResult, SourcingProvider
from sourcing.vendor_embedding import (  # noqa: F401 — re-exported
    _build_embedding_concepts,
    _embed_texts,
    _get_embedding_dimensions,
    _get_embedding_model,
    _get_openrouter_api_key,
    _weighted_blend,
    build_query_embedding,
)
from sourcing.vendor_result_processing import (  # noqa: F401 — re-exported
    AGGREGATOR_DOMAINS,
    CATEGORY_MAPPINGS,
    _extract_location_search_state,
    _get_distance_threshold,
    _vendor_matches_service_category,
    _vendor_result_sort_key,
    process_vendor_rows,
)

logger = logging.getLogger(__name__)


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

        If query_embedding is provided via kwargs, uses it directly (avoids
        duplicate API call — the orchestration layer already computed it).

        If a context_query kwarg is provided (the full user query with locations
        etc.), we blend two embeddings:
          - 70% intent query (product_name from LLM, e.g. 'Private jet charter')
          - 30% context query (full query, e.g. 'private jet charter san diego nashville')
        This keeps intent dominant while still boosting vendors that match context.
        """
        context_query = kwargs.get("context_query")
        pre_computed = kwargs.get("query_embedding")
        intent_payload = kwargs.get("intent_payload")
        t0 = time.monotonic()

        # 1. Embed — reuse pre-computed if available, otherwise call API
        embedding = await build_query_embedding(
            query,
            context_query=context_query,
            intent_payload=intent_payload,
            pre_computed=pre_computed,
        )
        if pre_computed:
            logger.info(f"[VendorProvider] Using pre-computed query embedding (skipped API call)")
        if not embedding:
            logger.info("[VendorProvider] No embedding — skipping vector search")
            return []

        t_embed = time.monotonic()
        logger.info(f"[VendorProvider] Embedding took {t_embed - t0:.2f}s")

        vec_str = "[" + ",".join(str(f) for f in embedding) + "]"

        final_limit = kwargs.get("limit", 15)
        location_state = _extract_location_search_state(intent_payload)
        location_mode = str(location_state["mode"])
        location_terms = location_state["terms"] if isinstance(location_state["terms"], list) else []
        geo_resolution = location_state["geo_resolution"] if isinstance(location_state["geo_resolution"], dict) else None
        weight_profile = location_weight_profile(location_mode)

        # PHASE 3.1: Log constraint propagation
        constraints = {}
        if intent_payload and isinstance(intent_payload, dict):
            constraints = intent_payload.get("constraints") or intent_payload.get("features") or {}
        logger.info(
            f"[VendorProvider] Search with location_mode={location_mode}, "
            f"geo_resolution={'resolved' if geo_resolution else 'unresolved'}, "
            f"location_terms={location_terms}, "
            f"constraints={list(constraints.keys())}, "
            f"weights={weight_profile}"
        )

        # Build AND-based tsquery for FTS precision.
        # Previously we used OR (|), but that caused "house cleaning in Denver" 
        # to match any vendor with "Denver" in the name (e.g. Denver Art Museum).
        # Vector search handles fuzzy semantic matches; FTS should handle precise keyword overlap.
        stop_words = {"in", "the", "for", "a", "an", "and", "or", "with", "at", "to", "of", "on"}
        _fts_sanitize = re.compile(r"[^a-zA-Z0-9]")
        fts_words = []
        for w in query.split():
            cleaned = _fts_sanitize.sub("", w)
            if cleaned and len(cleaned) > 1 and cleaned.lower() not in stop_words:
                fts_words.append(cleaned)
        if fts_words:
            fts_query_str = " & ".join(fts_words)
        else:
            fts_query_str = query

        service_category = str(location_state.get("service_category") or "").strip()
        geo_lat = geo_resolution.get("lat") if geo_resolution else None
        geo_lon = geo_resolution.get("lon") if geo_resolution else None
        geo_radius_miles = float(os.getenv("VENDOR_PROXIMITY_RADIUS_MILES", "75"))
        geo_term_1 = location_terms[0] if len(location_terms) > 0 else ""
        geo_term_2 = location_terms[1] if len(location_terms) > 1 else ""
        geo_term_3 = location_terms[2] if len(location_terms) > 2 else ""
        location_mode_for_query = location_mode if location_mode in {"service_area", "vendor_proximity"} else "none"

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
                                   trust_score, image_url, category, embedding::text AS embedding_text,
                                   store_geo_location, latitude, longitude,
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
                                   trust_score, image_url, category, embedding::text AS embedding_text,
                                   store_geo_location, latitude, longitude,
                                   (embedding <=> CAST(:qvec AS vector)) AS distance,
                                   ts_rank_cd(search_vector, to_tsquery('english', :fts_query)) AS fts_rank
                            FROM vendor
                            WHERE embedding IS NOT NULL
                              AND search_vector IS NOT NULL
                              AND search_vector @@ to_tsquery('english', :fts_query)
                            ORDER BY ts_rank_cd(search_vector, to_tsquery('english', :fts_query)) DESC
                            LIMIT :fts_lim
                        ),
                        geo_candidates AS (
                            SELECT id, name, description, tagline, website, email, phone,
                                   trust_score, image_url, category, embedding::text AS embedding_text,
                                   store_geo_location, latitude, longitude,
                                   (embedding <=> CAST(:qvec AS vector)) AS distance,
                                   CASE
                                     WHEN search_vector IS NOT NULL
                                     THEN ts_rank_cd(search_vector, to_tsquery('english', :fts_query))
                                     ELSE 0
                                   END AS fts_rank
                            FROM vendor
                            WHERE :location_mode = 'vendor_proximity'
                             AND (
                                (
                                  :geo_lat IS NOT NULL AND :geo_lon IS NOT NULL
                                  AND latitude IS NOT NULL AND longitude IS NOT NULL
                                  AND (
                                    3959 * acos(
                                      least(1.0, greatest(-1.0,
                                        cos(radians(:geo_lat)) * cos(radians(latitude))
                                        * cos(radians(longitude) - radians(:geo_lon))
                                        + sin(radians(:geo_lat)) * sin(radians(latitude))
                                      ))
                                    )
                                  ) <= :geo_radius_miles
                                )
                                OR (
                                  store_geo_location IS NOT NULL
                                  AND (
                                    (:geo_term_1 <> '' AND lower(store_geo_location) LIKE ('%%' || lower(:geo_term_1) || '%%'))
                                    OR (:geo_term_2 <> '' AND lower(store_geo_location) LIKE ('%%' || lower(:geo_term_2) || '%%'))
                                    OR (:geo_term_3 <> '' AND lower(store_geo_location) LIKE ('%%' || lower(:geo_term_3) || '%%'))
                                  )
                                )
                              )
                              AND (:service_category = '' OR lower(category) LIKE ('%%' || lower(:service_category) || '%%'))
                            ORDER BY
                              CASE
                                WHEN :geo_lat IS NOT NULL AND :geo_lon IS NOT NULL
                                     AND latitude IS NOT NULL AND longitude IS NOT NULL
                                THEN (
                                  3959 * acos(
                                    least(1.0, greatest(-1.0,
                                      cos(radians(:geo_lat)) * cos(radians(latitude))
                                      * cos(radians(longitude) - radians(:geo_lon))
                                      + sin(radians(:geo_lat)) * sin(radians(latitude))
                                    ))
                                  )
                                )
                                ELSE 1000000
                              END ASC,
                              fts_rank DESC,
                              distance ASC
                            LIMIT :geo_lim
                        ),
                        service_area_candidates AS (
                            SELECT id, name, description, tagline, website, email, phone,
                                   trust_score, image_url, category, embedding::text AS embedding_text,
                                   store_geo_location, latitude, longitude,
                                   (embedding <=> CAST(:qvec AS vector)) AS distance,
                                   CASE
                                     WHEN search_vector IS NOT NULL
                                     THEN ts_rank_cd(search_vector, to_tsquery('english', :fts_query))
                                     ELSE 0
                                   END AS fts_rank
                            FROM vendor
                            WHERE :location_mode = 'service_area'
                              AND store_geo_location IS NOT NULL
                              AND (
                                (:geo_term_1 <> '' AND lower(store_geo_location) LIKE ('%%' || lower(:geo_term_1) || '%%'))
                                OR (:geo_term_2 <> '' AND lower(store_geo_location) LIKE ('%%' || lower(:geo_term_2) || '%%'))
                                OR (:geo_term_3 <> '' AND lower(store_geo_location) LIKE ('%%' || lower(:geo_term_3) || '%%'))
                              )
                              AND (:service_category = '' OR lower(category) LIKE ('%%' || lower(:service_category) || '%%'))
                            ORDER BY fts_rank DESC, distance ASC
                            LIMIT :geo_lim
                        ),
                        -- Merge and dedup (FTS row wins on tie)
                        merged AS (
                            SELECT * FROM fts_candidates
                            UNION ALL
                            SELECT * FROM vec_candidates v
                            WHERE NOT EXISTS (SELECT 1 FROM fts_candidates f WHERE f.id = v.id)
                            UNION ALL
                            SELECT * FROM geo_candidates g
                            WHERE NOT EXISTS (SELECT 1 FROM fts_candidates f WHERE f.id = g.id)
                              AND NOT EXISTS (SELECT 1 FROM vec_candidates v WHERE v.id = g.id)
                            UNION ALL
                            SELECT * FROM service_area_candidates s
                            WHERE NOT EXISTS (SELECT 1 FROM fts_candidates f WHERE f.id = s.id)
                              AND NOT EXISTS (SELECT 1 FROM vec_candidates v WHERE v.id = s.id)
                              AND NOT EXISTS (SELECT 1 FROM geo_candidates g WHERE g.id = s.id)
                        )
                        SELECT * FROM merged
                    """),
                    {
                        "qvec": vec_str,
                        "fts_query": fts_query_str,
                        "vec_lim": final_limit * 2,
                        "fts_lim": final_limit,
                        "geo_lim": final_limit,
                        "location_mode": location_mode_for_query,
                        "geo_lat": geo_lat,
                        "geo_lon": geo_lon,
                        "geo_radius_miles": geo_radius_miles,
                        "geo_term_1": geo_term_1,
                        "geo_term_2": geo_term_2,
                        "geo_term_3": geo_term_3,
                        "service_category": service_category,
                    },
                )
                rows = result.mappings().all()
                t_db = time.monotonic()
                logger.info(
                    f"[VendorProvider] Hybrid query took {t_db - t_embed:.2f}s, "
                    f"{len(rows)} candidates (mode={location_mode}, weights={weight_profile})"
                )
        except Exception as e:
            # If search_vector column doesn't exist yet, fall back to vector-only
            if "search_vector" in str(e):
                logger.warning(f"[VendorProvider] search_vector error — falling back to vector-only: {e}")
                try:
                    async with self._engine.connect() as conn:
                        result = await conn.execute(
                            sa.text(
                                "SELECT id, name, description, tagline, website, email, phone, "
                                "trust_score, "
                                "image_url, category, store_geo_location, latitude, longitude, "
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

        # 3. Score, filter, and convert to SearchResult objects.
        return process_vendor_rows(
            rows,
            location_state=location_state,
            intent_payload=intent_payload,
            final_limit=final_limit,
        )
