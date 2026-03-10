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
from typing import Dict, List, Optional

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from sourcing.location import location_weight_profile, neutral_geo_score, precision_weight_multiplier
from sourcing.repository import SearchResult, SourcingProvider

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/embeddings"

# PHASE 1.4: Category matching semantic mappings
CATEGORY_MAPPINGS = {
    "cleaning": ["cleaning", "house", "maid", "janitorial", "home service", "housekeeping"],
    "roofing": ["roofing", "roof", "contractor", "construction", "roofer"],
    "hvac": ["hvac", "heating", "cooling", "air conditioning", "furnace", "ac repair"],
    "jewelry": ["jewelry", "jeweler", "diamond", "engagement", "ring", "gemstone"],
    "real_estate": ["real estate", "realtor", "broker", "property", "homes", "housing"],
    "private_aviation": ["private jet", "aviation", "charter", "aircraft", "flight"],
    "catering": ["catering", "caterer", "food service", "event", "banquet"],
    "photography": ["photography", "photographer", "photo", "videography"],
    "interior_design": ["interior design", "designer", "decorator", "home staging"],
    "yacht_charter": ["yacht", "boat", "charter", "marine", "vessel"],
}


def _vendor_matches_service_category(
    vendor_category: str,
    request_category: str,
    vendor_name: str,
    vendor_description: str
) -> bool:
    """Check if vendor category reasonably matches the service request."""
    # Extract category hint from vendor
    vc_lower = vendor_category.lower()
    vn_lower = vendor_name.lower()
    vd_lower = vendor_description.lower()
    rc_lower = request_category.lower()

    # Exact match
    if rc_lower in vc_lower or rc_lower in vn_lower:
        return True

    # Semantic mapping
    request_keywords = CATEGORY_MAPPINGS.get(rc_lower, [rc_lower])
    vendor_text = f"{vc_lower} {vn_lower} {vd_lower}"

    return any(kw in vendor_text for kw in request_keywords)


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


def _extract_location_search_state(intent_payload: Optional[dict]) -> Dict[str, object]:
    if not isinstance(intent_payload, dict):
        return {"mode": "none", "terms": [], "geo_resolution": None, "service_category": None}
    location_context = intent_payload.get("location_context") or {}
    location_resolution = intent_payload.get("location_resolution") or {}
    targets = location_context.get("targets") or {}
    mode = str(location_context.get("relevance") or "none")
    terms = [str(value).strip() for value in targets.values() if isinstance(value, str) and value.strip()]
    geo_resolution = None
    for field_name in ("service_location", "search_area", "vendor_market", "origin", "destination"):
        resolved = location_resolution.get(field_name)
        if isinstance(resolved, dict) and resolved.get("status") == "resolved":
            geo_resolution = resolved
            break
    return {
        "mode": mode,
        "terms": terms[:3],
        "geo_resolution": geo_resolution,
        "service_category": intent_payload.get("product_category"),
    }


def _vendor_result_sort_key(result: SearchResult) -> tuple[float, float, float]:
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    location_mode = str(metadata.get("location_mode") or "none")
    location_match = bool(metadata.get("location_match"))
    distance = metadata.get("geo_distance_miles")
    numeric_distance = float(distance) if isinstance(distance, (int, float)) else None
    match_score = float(result.match_score or 0.0)

    if location_mode == "vendor_proximity":
        if location_match and numeric_distance is not None:
            return (0.0, numeric_distance, -match_score)
        if location_match:
            return (1.0, 0.0, -match_score)
    return (2.0, 0.0, -match_score)


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
        fts_words = [w.strip() for w in query.split() if w.strip() and len(w.strip()) > 1 and w.strip().lower() not in stop_words]
        if fts_words:
            fts_query_str = " & ".join(fts_words)
        else:
            fts_query_str = query

        service_category = str(location_state.get("service_category") or "").strip()
        geo_lat = geo_resolution.get("lat") if geo_resolution else None
        geo_lon = geo_resolution.get("lon") if geo_resolution else None
        geo_precision = geo_resolution.get("precision") if geo_resolution else None
        precision_multiplier = precision_weight_multiplier(str(geo_precision) if geo_precision else None)
        geo_radius_miles = float(os.getenv("VENDOR_PROXIMITY_RADIUS_MILES", "75"))
        geo_term_1 = location_terms[0] if len(location_terms) > 0 else ""
        geo_term_2 = location_terms[1] if len(location_terms) > 1 else ""
        geo_term_3 = location_terms[2] if len(location_terms) > 2 else ""
        location_mode_for_query = location_mode if location_mode in {"service_area", "vendor_proximity"} else "none"
        has_explicit_location_target = bool(location_terms or geo_resolution)

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
                                   image_url, category, embedding::text AS embedding_text,
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
                                   image_url, category, embedding::text AS embedding_text,
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
                                   image_url, category, embedding::text AS embedding_text,
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
                                   image_url, category, embedding::text AS embedding_text,
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
                logger.warning("[VendorProvider] search_vector column missing — falling back to vector-only")
                try:
                    async with self._engine.connect() as conn:
                        result = await conn.execute(
                            sa.text(
                                "SELECT id, name, description, tagline, website, email, phone, "
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

        # 3. Filter candidates and convert to SearchResult.
        #    - FTS matches (fts_rank > 0) are ALWAYS included regardless of distance.
        #    - Vector-only matches are filtered by distance threshold.
        #    - FTS rank normalized by dividing by FTS_NORM_DIVISOR (not capped at 1.0).
        threshold = _get_distance_threshold()
        FTS_NORM_DIVISOR = 5.0  # ts_rank_cd scores typically range 0-5 for our corpus
        results: List[SearchResult] = []
        matched_location_results: List[SearchResult] = []
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

            vec_score = max(0.0, 1.0 - float(r["distance"]))
            fts_norm = min(fts_rank_raw / FTS_NORM_DIVISOR, 1.0)
            constraint_score = 0.0
            geo_score = 0.0
            geo_distance_miles = None
            text_location_match = 0.0
            store_geo_location = str(r.get("store_geo_location") or "")
            location_match = False

            if location_mode == "service_area":
                lowered_location = store_geo_location.lower()
                term_hits = sum(1 for term in location_terms if term and term.lower() in lowered_location)
                if location_terms:
                    text_location_match = min(1.0, term_hits / len(location_terms))
                location_match = term_hits > 0
                geo_score = max(text_location_match * 0.85, neutral_geo_score(location_mode, vec_score, fts_norm, 0.0))
                if term_hits > 0:
                    constraint_score = 0.8
            elif location_mode == "vendor_proximity":
                lat = r.get("latitude")
                lon = r.get("longitude")
                if geo_lat is not None and geo_lon is not None and lat is not None and lon is not None:
                    lat1 = math.radians(float(geo_lat))
                    lon1 = math.radians(float(geo_lon))
                    lat2 = math.radians(float(lat))
                    lon2 = math.radians(float(lon))
                    dlon = lon2 - lon1
                    distance = 3959 * math.acos(
                        max(-1.0, min(1.0, math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(dlon)))
                    )
                    geo_distance_miles = distance
                    if distance <= geo_radius_miles:
                        # PHASE 2.2: Tier-based scoring with precision multiplier
                        if distance <= 10:
                            # Within 10 miles - EXCELLENT
                            base_score = 1.0
                        elif distance <= 25:
                            # 10-25 miles - GOOD
                            base_score = 0.9 - ((distance - 10) / 15) * 0.2  # 0.9 → 0.7
                        elif distance <= 50:
                            # 25-50 miles - ACCEPTABLE
                            base_score = 0.7 - ((distance - 25) / 25) * 0.3  # 0.7 → 0.4
                        else:
                            # 50-75 miles - MARGINAL
                            base_score = 0.4 - ((distance - 50) / 25) * 0.2  # 0.4 → 0.2

                        geo_score = base_score * precision_multiplier
                        location_match = True

                        # Log distance for observability (Phase 3)
                        logger.debug(
                            f"[VendorProvider] {r['name']}: distance={distance:.1f}mi, "
                            f"base_score={base_score:.2f}, geo_score={geo_score:.2f}"
                        )
                if geo_score == 0.0 and store_geo_location:
                    lowered_location = store_geo_location.lower()
                    term_hits = sum(1 for term in location_terms if term and term.lower() in lowered_location)
                    if location_terms:
                        text_location_match = min(1.0, term_hits / len(location_terms))
                    if text_location_match > 0:
                        geo_score = max(text_location_match * 0.8, neutral_geo_score(location_mode, vec_score, fts_norm, 0.0))
                        location_match = True
                if geo_score == 0.0:
                    geo_score = neutral_geo_score(location_mode, vec_score, fts_norm, 0.0)
                constraint_score = text_location_match if text_location_match > 0 else 0.0
            elif location_mode == "endpoint":
                lowered_blob = f"{(r.get('description') or '').lower()} {(r.get('tagline') or '').lower()} {store_geo_location.lower()}"
                term_hits = sum(1 for term in location_terms if term and term.lower() in lowered_blob)
                if location_terms:
                    constraint_score = min(1.0, term_hits / len(location_terms))
                geo_score = 0.0 if not geo_resolution else 0.05 * precision_multiplier

            blended = (
                weight_profile["semantic"] * vec_score
                + weight_profile["fts"] * fts_norm
                + weight_profile["geo"] * geo_score
                + weight_profile["constraint"] * constraint_score
            )

            # Parse vendor embedding for quantum reranker
            vendor_embedding = None
            emb_text = r.get("embedding_text")
            if emb_text:
                try:
                    vendor_embedding = [float(x) for x in emb_text.strip("[]").split(",")]
                except Exception:
                    pass

            result_item = SearchResult(
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
                embedding=vendor_embedding,
                metadata={
                    "semantic_score": round(vec_score, 4),
                    "fts_score": round(fts_norm, 4),
                    "geo_score": round(geo_score, 4),
                    "constraint_score": round(constraint_score, 4),
                    "location_mode": location_mode,
                    "location_match": location_match,
                    "store_geo_location": store_geo_location,
                    "geo_distance_miles": round(geo_distance_miles, 3) if geo_distance_miles is not None else None,
                    "text_location_match": round(text_location_match, 4),
                },
            )
            results.append(result_item)
            if location_match:
                matched_location_results.append(result_item)

        if has_explicit_location_target and location_mode in {"service_area", "vendor_proximity"} and matched_location_results:
            results = matched_location_results

        # PHASE 1.3: Hard filter by delivery_type constraint
        if intent_payload and isinstance(intent_payload, dict):
            constraints = intent_payload.get("constraints") or intent_payload.get("features") or {}
            delivery_type = str(constraints.get("delivery_type", "")).strip().lower()

            if delivery_type in {"in-store", "in_store", "pickup", "in store"}:
                # Filter OUT vendors that don't have a physical location
                before_count = len(results)
                results = [
                    r for r in results
                    if r.metadata and (r.metadata.get("store_geo_location") or "").strip()
                ]
                dropped = before_count - len(results)
                if dropped:
                    logger.info(
                        f"[VendorProvider] delivery_type={delivery_type}: "
                        f"Dropped {dropped}/{before_count} vendors without physical location"
                    )

        # PHASE 1.4: Filter out mismatched service categories
        # If request is a SERVICE (not product), ensure vendor category matches
        if intent_payload and isinstance(intent_payload, dict):
            service_category = str(intent_payload.get("product_category", "")).strip().lower()

            if location_mode in {"service_area", "vendor_proximity"} and service_category:
                # This is a local SERVICE request - filter out irrelevant vendors
                before_count = len(results)
                results = [
                    r for r in results
                    if _vendor_matches_service_category(
                        vendor_category=r.shipping_info or "",
                        request_category=service_category,
                        vendor_name=r.title,
                        vendor_description=r.description or ""
                    )
                ]
                dropped = before_count - len(results)
                if dropped:
                    logger.info(
                        f"[VendorProvider] Filtered {dropped}/{before_count} vendors with mismatched categories "
                        f"(request={service_category}, location_mode={location_mode})"
                    )
        # For true local searches, exact geo distance leads among local matches.
        # Service-area searches remain locality-gated but semantically ranked.
        if location_mode == "vendor_proximity":
            results.sort(key=_vendor_result_sort_key)
        else:
            results.sort(key=lambda x: x.match_score or 0, reverse=True)
        results = results[:final_limit]

        fts_included = sum(1 for r in rows if float(r.get("fts_rank", 0)) > 0)
        matched_location_count = len(matched_location_results) if matched_location_results else 0

        # PHASE 3.2: Final result summary logging
        logger.info(
            f"[VendorProvider] Final results: {len(results)} vendors, "
            f"candidates={len(rows)}, "
            f"fts_matched={fts_included}, "
            f"location_matched={matched_location_count}, "
            f"mode={location_mode}, "
            f"vec_threshold={threshold}"
        )
        return results
