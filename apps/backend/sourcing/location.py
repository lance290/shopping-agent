"""Location intent normalization and scoring helpers."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

from sourcing.models import (
    LocationContext,
    LocationResolution,
    LocationResolutionMap,
    LocationTargets,
    SearchIntent,
)

LOCATION_MODE_DEFAULTS = {
    "private_aviation": "endpoint",
    "yacht_charter": "endpoint",
    "real_estate": "service_area",
    "roofing": "vendor_proximity",
    "hvac": "vendor_proximity",
    "photography": "vendor_proximity",
    "interior_design": "service_area",
    "jewelry": "none",
}

LOCATION_OVERRIDE_CONFIDENCE = 0.75
LOCATION_TARGET_FIELDS = ("origin", "destination", "service_location", "search_area", "vendor_market")
TRAVEL_HINT_WORDS = {
    "charter", "flight", "flights", "jet", "aviation", "airport", "route",
    "itinerary", "yacht", "transfer", "pickup", "dropoff", "depart", "arrival",
}
LOCAL_HINT_PATTERNS = (
    r"\bnear me\b",
    r"\bnearby\b",
    r"\blocal\b",
    r"\bclosest\b",
    r"\bin my area\b",
    r"\baround me\b",
    r"\bwithin \d+",
)
MARKET_HINT_WORDS = {
    "broker", "brokers", "market", "coverage", "serves", "serving",
    "licensed", "region", "regional", "nationwide", "global", "advisor",
}
LEGACY_LOCATION_KEYS = {
    "origin": "origin",
    "from": "origin",
    "from_airport": "origin",
    "departure_airport": "origin",
    "destination": "destination",
    "to": "destination",
    "to_airport": "destination",
    "arrival_airport": "destination",
    "location": "service_location",
    "service_location": "service_location",
    "search_area": "search_area",
    "vendor_market": "vendor_market",
    "city": "search_area",
    "market": "vendor_market",
}

# Major US cities (population > ~75k) for fallback location extraction.
# Used when the LLM constraints dict doesn't contain an explicit location key
# but the user's raw input mentions a city name.
US_MAJOR_CITIES: set[str] = {
    "albuquerque", "anaheim", "anchorage", "arlington", "atlanta", "aurora",
    "austin", "bakersfield", "baltimore", "baton rouge", "birmingham", "boise",
    "boston", "buffalo", "chandler", "charlotte", "chattanooga", "chesapeake",
    "chicago", "chula vista", "cincinnati", "cleveland", "colorado springs",
    "columbus", "corpus christi", "dallas", "denver", "des moines", "detroit",
    "durham", "el paso", "eugene", "fort collins", "fort lauderdale", "fort wayne",
    "fort worth", "fremont", "fresno", "garland", "gilbert", "glendale",
    "greensboro", "henderson", "hialeah", "honolulu", "houston", "huntsville",
    "indianapolis", "irvine", "irving", "jackson", "jacksonville", "jersey city",
    "kansas city", "knoxville", "las vegas", "lexington", "lincoln", "little rock",
    "long beach", "los angeles", "louisville", "lubbock", "madison", "memphis",
    "mesa", "miami", "milwaukee", "minneapolis", "modesto", "montgomery",
    "moreno valley", "nashville", "new orleans", "new york", "newark", "norfolk",
    "north las vegas", "oakland", "oklahoma city", "omaha", "ontario", "orlando",
    "oxnard", "palm bay", "paradise", "pembroke pines", "peoria", "philadelphia",
    "phoenix", "pittsburgh", "plano", "portland", "providence", "raleigh",
    "reno", "richmond", "riverside", "rochester", "sacramento", "saint paul",
    "salt lake city", "san antonio", "san bernardino", "san diego", "san francisco",
    "san jose", "santa ana", "santa clarita", "santa rosa", "savannah", "scottsdale",
    "seattle", "shreveport", "spokane", "springfield", "st. louis", "st. paul",
    "st. petersburg", "stamford", "stockton", "tampa", "tempe", "toledo",
    "tucson", "tulsa", "virginia beach", "washington", "wichita", "wilmington",
    "winston-salem", "worcester", "yonkers",
}

# US state names and abbreviations for context
US_STATES: dict[str, str] = {
    "al": "alabama", "ak": "alaska", "az": "arizona", "ar": "arkansas",
    "ca": "california", "co": "colorado", "ct": "connecticut", "de": "delaware",
    "fl": "florida", "ga": "georgia", "hi": "hawaii", "id": "idaho",
    "il": "illinois", "in": "indiana", "ia": "iowa", "ks": "kansas",
    "ky": "kentucky", "la": "louisiana", "me": "maine", "md": "maryland",
    "ma": "massachusetts", "mi": "michigan", "mn": "minnesota", "ms": "mississippi",
    "mo": "missouri", "mt": "montana", "ne": "nebraska", "nv": "nevada",
    "nh": "new hampshire", "nj": "new jersey", "nm": "new mexico", "ny": "new york",
    "nc": "north carolina", "nd": "north dakota", "oh": "ohio", "ok": "oklahoma",
    "or": "oregon", "pa": "pennsylvania", "ri": "rhode island", "sc": "south carolina",
    "sd": "south dakota", "tn": "tennessee", "tx": "texas", "ut": "utah",
    "vt": "vermont", "va": "virginia", "wa": "washington", "wv": "west virginia",
    "wi": "wisconsin", "wy": "wyoming", "dc": "district of columbia",
}
US_STATE_NAMES: set[str] = set(US_STATES.values())


def _extract_location_from_text(text: str) -> Optional[str]:
    """Extract a US city or state name from raw text.

    Returns the first recognized city/state as a location string suitable for
    service_location, or None if nothing found.  This is the safety net that
    catches "Nashville" when the LLM constraints dict doesn't have a location key.
    """
    if not text:
        return None
    lowered = text.lower()

    # Check two-word cities first ("san diego", "new york", etc.)
    for city in US_MAJOR_CITIES:
        if " " in city and city in lowered:
            return city.title()

    # Check single-word cities against word boundaries
    words = re.findall(r'[a-z]+', lowered)
    for city in US_MAJOR_CITIES:
        if " " not in city and city in words:
            return city.title()

    # Check state names ("Tennessee", "California", etc.)
    for state_name in US_STATE_NAMES:
        if state_name in lowered:
            return state_name.title()

    return None


def category_location_mode(service_category: Optional[str], desire_tier: Optional[str] = None) -> str:
    category = (service_category or "").strip().lower()
    if category in LOCATION_MODE_DEFAULTS:
        return LOCATION_MODE_DEFAULTS[category]
    if desire_tier == "commodity":
        return "none"
    return "none"


def _build_request_text(
    service_category: Optional[str],
    constraints: Optional[Dict[str, Any]] = None,
    features: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> str:
    parts: list[str] = []
    for value in (
        service_category,
        (payload or {}).get("product_name"),
        (payload or {}).get("raw_input"),
        " ".join((payload or {}).get("keywords", []) or []),
    ):
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())

    # PHASE 2.1: Prefer constraints over features
    constraint_source = constraints if isinstance(constraints, dict) else (features if isinstance(features, dict) else {})
    for value in constraint_source.values():
        if value is None:
            continue
        if isinstance(value, list):
            parts.extend(str(item).strip() for item in value if str(item).strip())
        else:
            text = str(value).strip()
            if text:
                parts.append(text)
    return " ".join(parts).lower()


def infer_location_mode_from_request_shape(
    service_category: Optional[str],
    desire_tier: Optional[str],
    targets: LocationTargets,
    constraints: Optional[Dict[str, Any]] = None,
    features: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    request_text = _build_request_text(
        service_category=service_category,
        constraints=constraints,
        features=features,
        payload=payload,
    )
    has_local_hint = any(re.search(pattern, request_text) for pattern in LOCAL_HINT_PATTERNS)
    has_travel_hint = any(word in request_text for word in TRAVEL_HINT_WORDS)
    has_market_hint = any(word in request_text for word in MARKET_HINT_WORDS)

    if targets.origin and targets.destination:
        return "endpoint"
    if (targets.origin or targets.destination) and (has_travel_hint or desire_tier in {"service", "high_value"}):
        return "endpoint"

    if targets.vendor_market:
        return "service_area"

    if targets.search_area:
        if has_local_hint:
            return "vendor_proximity"
        if has_market_hint or desire_tier in {"service", "high_value", "advisory"}:
            return "service_area"
        return "none" if desire_tier == "commodity" else "service_area"

    if targets.service_location:
        if has_local_hint:
            return "vendor_proximity"
        if desire_tier == "commodity" and not has_market_hint:
            return "none"
        if has_market_hint:
            return "service_area"
        if desire_tier in {"service", "high_value"}:
            return "vendor_proximity"
        return None

    if has_local_hint and desire_tier in {"service", "high_value"}:
        return "vendor_proximity"

    return None


def normalize_location_targets(*payloads: Optional[Dict[str, Any]]) -> LocationTargets:
    normalized: Dict[str, Optional[str]] = {field: None for field in LOCATION_TARGET_FIELDS}
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        for key, value in payload.items():
            canonical = LEGACY_LOCATION_KEYS.get(str(key).strip().lower())
            if not canonical:
                continue
            if value is None:
                continue
            text = str(value).strip()
            if not text or text.lower() in {"none", "null", "not answered"}:
                continue
            if not normalized.get(canonical):
                normalized[canonical] = text
    return LocationTargets(**normalized)


def resolve_location_context(
    service_category: Optional[str],
    desire_tier: Optional[str],
    constraints: Optional[Dict[str, Any]] = None,
    features: Optional[Dict[str, Any]] = None,
    location_context_payload: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> LocationContext:
    targets = normalize_location_targets(constraints, features)

    # Fallback: if no explicit location target was found in constraints,
    # scan the raw text (product_name, raw_input, keywords) for city names.
    if not targets.non_empty_items():
        request_text = _build_request_text(
            service_category=service_category,
            constraints=constraints,
            features=features,
            payload=payload,
        )
        extracted = _extract_location_from_text(request_text)
        if extracted:
            targets = LocationTargets(service_location=extracted)
            logger.info(
                f"[Location] Fallback extraction: found '{extracted}' in raw text -> service_location"
            )

    shape_mode = infer_location_mode_from_request_shape(
        service_category=service_category,
        desire_tier=desire_tier,
        targets=targets,
        constraints=constraints,
        features=features,
        payload=payload,
    )
    default_mode = shape_mode or category_location_mode(service_category, desire_tier=desire_tier)

    if isinstance(location_context_payload, dict):
        try:
            candidate = LocationContext.model_validate(location_context_payload)
        except Exception:
            candidate = None
        if candidate is not None:
            merged_targets = normalize_location_targets(
                constraints,
                features,
                candidate.targets.model_dump(),
            )
            inferred_mode = infer_location_mode_from_request_shape(
                service_category=service_category,
                desire_tier=desire_tier,
                targets=merged_targets,
                constraints=constraints,
                features=features,
                payload=payload,
            )
            relevance = candidate.relevance
            fallback_mode = inferred_mode or default_mode
            if relevance != fallback_mode and candidate.confidence < LOCATION_OVERRIDE_CONFIDENCE:
                relevance = fallback_mode
            return LocationContext(
                relevance=relevance,
                confidence=candidate.confidence,
                targets=merged_targets,
                notes=candidate.notes,
            )

    return LocationContext(
        relevance=default_mode,
        confidence=0.0,
        targets=targets,
    )


def normalize_search_intent_payload(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return payload

    normalized = dict(payload)
    features = normalized.get("features")
    constraints = normalized.get("constraints")
    if not isinstance(features, dict):
        features = constraints if isinstance(constraints, dict) else {}
    if not isinstance(constraints, dict):
        constraints = features if isinstance(features, dict) else {}

    normalized["features"] = features
    if "constraints" in normalized:
        normalized["constraints"] = constraints

    location_context = resolve_location_context(
        service_category=normalized.get("product_category"),
        desire_tier=normalized.get("desire_tier"),
        constraints=constraints,
        features=features,
        location_context_payload=normalized.get("location_context"),
        payload=normalized,
    )
    normalized["location_context"] = location_context.model_dump()

    if "location_resolution" in normalized and isinstance(normalized["location_resolution"], dict):
        try:
            normalized["location_resolution"] = LocationResolutionMap.model_validate(
                normalized["location_resolution"]
            ).model_dump(mode="json")
        except Exception:
            normalized["location_resolution"] = LocationResolutionMap().model_dump(mode="json")
    else:
        normalized["location_resolution"] = LocationResolutionMap().model_dump(mode="json")
    return normalized


def location_weight_profile(location_mode: str) -> Dict[str, float]:
    profiles = {
        "none": {"semantic": 0.55, "fts": 0.25, "geo": 0.0, "constraint": 0.20},
        "endpoint": {"semantic": 0.50, "fts": 0.20, "geo": 0.05, "constraint": 0.25},
        "service_area": {"semantic": 0.40, "fts": 0.20, "geo": 0.20, "constraint": 0.20},
        "vendor_proximity": {"semantic": 0.30, "fts": 0.15, "geo": 0.40, "constraint": 0.15},
    }
    return profiles.get(location_mode, profiles["none"])


def precision_weight_multiplier(precision: Optional[str]) -> float:
    return {
        "address": 1.0,
        "postal_code": 0.95,
        "neighborhood": 0.85,
        "city": 0.75,
        "metro": 0.65,
        "region": 0.45,
    }.get((precision or "").lower(), 0.5)


def has_non_geo_relevance(semantic_score: float, fts_score: float, constraint_score: float) -> bool:
    return max(semantic_score, fts_score, constraint_score) > 0.0


def neutral_geo_score(location_mode: str, semantic_score: float, fts_score: float, constraint_score: float) -> float:
    # Non-matching vendors get ZERO geo credit.  The old value of 0.5 let
    # out-of-area vendors rank competitively with local ones.
    return 0.0


def apply_location_resolution(intent: SearchIntent, field_name: str, resolution: LocationResolution) -> SearchIntent:
    resolution_map = intent.location_resolution.model_copy(deep=True)
    setattr(resolution_map, field_name, resolution)
    return intent.model_copy(update={"location_resolution": resolution_map})
