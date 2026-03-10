"""Location intent normalization and scoring helpers."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

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
    for source in (constraints, features):
        if not isinstance(source, dict):
            continue
        for value in source.values():
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
    if location_mode in {"service_area", "vendor_proximity"} and has_non_geo_relevance(
        semantic_score, fts_score, constraint_score
    ):
        return 0.5
    return 0.0


def apply_location_resolution(intent: SearchIntent, field_name: str, resolution: LocationResolution) -> SearchIntent:
    resolution_map = intent.location_resolution.model_copy(deep=True)
    setattr(resolution_map, field_name, resolution)
    return intent.model_copy(update={"location_resolution": resolution_map})
