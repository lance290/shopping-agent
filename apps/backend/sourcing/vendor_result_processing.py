"""Vendor result scoring, filtering, and post-processing.

Extracted from VendorDirectoryProvider.search() to keep vendor_provider.py
focused on query construction and DB execution.
"""

import logging
import math
import os
from typing import Dict, List, Optional

from sourcing.location import location_weight_profile, neutral_geo_score, precision_weight_multiplier
from sourcing.repository import SearchResult

logger = logging.getLogger(__name__)

# Domains that are social platforms, directories, or listing aggregators.
# Vendor DB entries with these domains are duplicates of real-agent entries
# and add no direct-engagement value.  Skip them entirely.
AGGREGATOR_DOMAINS: set[str] = {
    # Social / platform
    "google.com", "www.google.com", "maps.google.com",
    "yelp.com", "www.yelp.com",
    "facebook.com", "www.facebook.com",
    "linkedin.com", "www.linkedin.com",
    "instagram.com", "www.instagram.com",
    "twitter.com", "www.twitter.com", "x.com",
    "youtube.com", "www.youtube.com",
    # Directory / listing / lead-gen aggregators
    "luxuryhomemagazine.com", "www.luxuryhomemagazine.com",
    "ownluxuryhomes.com", "www.ownluxuryhomes.com",
    "realtor.com", "www.realtor.com",
    "zillow.com", "www.zillow.com",
    "redfin.com", "www.redfin.com",
    "trulia.com", "www.trulia.com",
    "homes.com", "www.homes.com",
    "homelight.com", "www.homelight.com",
    "thumbtack.com", "www.thumbtack.com",
    "angi.com", "www.angi.com",
    "homeadvisor.com", "www.homeadvisor.com",
    "bark.com", "www.bark.com",
}

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


def _get_distance_threshold() -> float:
    return float(os.getenv("VENDOR_DISTANCE_THRESHOLD", "0.65"))


def _vendor_matches_service_category(
    vendor_category: str,
    request_category: str,
    vendor_name: str,
    vendor_description: str
) -> bool:
    """Check if vendor category reasonably matches the service request."""
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


def process_vendor_rows(
    rows,
    *,
    location_state: Dict[str, object],
    intent_payload: Optional[dict],
    final_limit: int,
) -> List[SearchResult]:
    """Score, filter, and convert raw DB rows into SearchResult objects."""
    location_mode = str(location_state["mode"])
    location_terms = location_state["terms"] if isinstance(location_state["terms"], list) else []
    geo_resolution = location_state["geo_resolution"] if isinstance(location_state["geo_resolution"], dict) else None
    weight_profile = location_weight_profile(location_mode)
    has_explicit_location_target = bool(location_terms or geo_resolution)

    geo_lat = geo_resolution.get("lat") if geo_resolution else None
    geo_lon = geo_resolution.get("lon") if geo_resolution else None
    geo_precision = geo_resolution.get("precision") if geo_resolution else None
    precision_multiplier = precision_weight_multiplier(str(geo_precision) if geo_precision else None)
    geo_radius_miles = float(os.getenv("VENDOR_PROXIMITY_RADIUS_MILES", "75"))

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

        # Extract domain and skip aggregator/directory results entirely
        raw_domain = ""
        if r["website"]:
            raw_domain = r["website"].replace("https://", "").replace("http://", "").split("/")[0]
        if raw_domain and raw_domain.lower() in AGGREGATOR_DOMAINS:
            continue
        merchant_domain = raw_domain

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
                        base_score = 1.0
                    elif distance <= 25:
                        base_score = 0.9 - ((distance - 10) / 15) * 0.2
                    elif distance <= 50:
                        base_score = 0.7 - ((distance - 25) / 25) * 0.3
                    else:
                        base_score = 0.4 - ((distance - 50) / 25) * 0.2

                    geo_score = base_score * precision_multiplier
                    location_match = True

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

        # Contact quality boost: vendors with real contact info rank higher
        cq_score = 0.0
        if r.get("phone"):
            cq_score += 0.30
        if r.get("email"):
            cq_score += 0.25
        if r.get("website"):
            cq_score += 0.25
        if r.get("description") or r.get("tagline"):
            cq_score += 0.20

        trust_score = float(r.get("trust_score") or 0.0)
        trust_score = max(0.0, min(trust_score, 1.0))

        blended = (
            weight_profile["semantic"] * vec_score
            + weight_profile["fts"] * fts_norm
            + weight_profile["geo"] * geo_score
            + weight_profile["constraint"] * constraint_score
            + 0.10 * trust_score
            + 0.10 * cq_score
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
            vendor_id=r["id"],
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
                "vendor_category": r.get("category"),
                "location_mode": location_mode,
                "location_match": location_match,
                "store_geo_location": store_geo_location,
                "geo_distance_miles": round(geo_distance_miles, 3) if geo_distance_miles is not None else None,
                "text_location_match": round(text_location_match, 4),
                "trust_score": round(trust_score, 4),
                "contact_quality_score": round(cq_score, 2),
            },
        )
        results.append(result_item)
        if location_match:
            matched_location_results.append(result_item)

    if has_explicit_location_target:
        if matched_location_results:
            results = matched_location_results
            if location_mode not in {"service_area", "vendor_proximity"}:
                logger.warning(
                    f"[VendorProvider] Defense-in-depth: location_terms={location_terms} "
                    f"but mode={location_mode}; still hard-filtering to {len(matched_location_results)} local results"
                )
        elif location_mode in {"service_area", "vendor_proximity"}:
            logger.info(
                f"[VendorProvider] No vendor_directory matches for "
                f"location_terms={location_terms} mode={location_mode}; "
                f"returning 0 results to avoid non-local noise"
            )
            results = []

    # PHASE 1.3: Hard filter by delivery_type constraint
    if intent_payload and isinstance(intent_payload, dict):
        constraints = intent_payload.get("constraints") or intent_payload.get("features") or {}
        delivery_type = str(constraints.get("delivery_type", "")).strip().lower()

        if delivery_type in {"in-store", "in_store", "pickup", "in store"}:
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
    if intent_payload and isinstance(intent_payload, dict):
        service_category = str(intent_payload.get("product_category", "")).strip().lower()

        if location_mode in {"service_area", "vendor_proximity"} and service_category:
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
