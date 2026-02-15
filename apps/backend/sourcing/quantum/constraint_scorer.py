"""
Constraint Satisfaction Scorer.

Scores how well a search result satisfies the user's structured constraints
(e.g., route, aircraft class, capacity, date, features).

This fills the "fit" gap identified in the User Intention Audit:
the existing scorer doesn't ask "does this result satisfy the user's constraints?"
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def constraint_satisfaction_score(
    result_data: Dict[str, Any],
    constraints: Optional[Dict[str, Any]],
) -> float:
    """
    Score how well a result satisfies structured constraints.

    Returns 0.0-1.0. Each satisfied constraint adds to the score.
    Constraints are additive bonuses, not hard filters — bad extraction
    degrades gracefully to the status quo.

    Args:
        result_data: Raw data from the search result (title, description, metadata).
        constraints: Structured constraints from desire classification.

    Returns:
        Score between 0.0 and 1.0.
    """
    if not constraints:
        return 0.5  # No constraints = neutral

    score = 0.0
    total_weight = 0.0
    title = str(result_data.get("title", "")).lower()
    description = str(result_data.get("description", "") or result_data.get("snippet", "")).lower()
    searchable = f"{title} {description}"

    # Vendor metadata (if available from vendor_directory results)
    vendor_meta = result_data.get("vendor_metadata") or result_data.get("raw_data") or {}
    if isinstance(vendor_meta, str):
        try:
            vendor_meta = json.loads(vendor_meta)
        except (json.JSONDecodeError, TypeError):
            vendor_meta = {}

    # --- Route matching (travel/charter) ---
    if "origin" in constraints:
        total_weight += 1.0
        origin = str(constraints["origin"]).lower()
        routes = vendor_meta.get("routes", [])
        if isinstance(routes, list) and any(origin in str(r).lower() for r in routes):
            score += 1.0
        elif origin in searchable:
            score += 0.6  # Mentioned but not confirmed as a route

    if "destination" in constraints:
        total_weight += 0.8
        dest = str(constraints["destination"]).lower()
        routes = vendor_meta.get("routes", [])
        if isinstance(routes, list) and any(dest in str(r).lower() for r in routes):
            score += 0.8
        elif dest in searchable:
            score += 0.5

    # --- Aircraft class / vehicle type ---
    if "aircraft_class" in constraints:
        total_weight += 0.8
        aircraft = str(constraints["aircraft_class"]).lower()
        aircraft_classes = vendor_meta.get("aircraft_classes", [])
        if isinstance(aircraft_classes, list) and any(aircraft in str(c).lower() for c in aircraft_classes):
            score += 0.8
        elif aircraft in searchable:
            score += 0.5

    # --- Capacity / passengers ---
    if "passengers" in constraints:
        total_weight += 0.6
        try:
            pax = int(constraints["passengers"])
            capacity = vendor_meta.get("capacity") or vendor_meta.get("max_passengers")
            if capacity is not None and int(capacity) >= pax:
                score += 0.6
            elif str(pax) in searchable or "passenger" in searchable:
                score += 0.3
        except (ValueError, TypeError):
            pass

    # --- Location matching ---
    if "location" in constraints:
        total_weight += 0.7
        location = str(constraints["location"]).lower()
        service_area = vendor_meta.get("service_area", [])
        if isinstance(service_area, list) and any(location in str(a).lower() for a in service_area):
            score += 0.7
        elif location in searchable:
            score += 0.4

    # --- Budget range ---
    if "budget" in constraints or "max_budget" in constraints or "budget_range" in constraints:
        total_weight += 0.5
        # Budget is already handled by the price scorer — give partial credit if in range
        score += 0.3

    # --- Feature matching (Wi-Fi, certifications, etc.) ---
    features = constraints.get("features", [])
    if isinstance(features, str):
        features = [features]
    if features:
        total_weight += 0.4
        matched = sum(1 for f in features if str(f).lower() in searchable)
        if features:
            score += 0.4 * (matched / len(features))

    # --- Generic string constraints (color, material, style, etc.) ---
    GENERIC_KEYS = {"color", "material", "style", "size", "brand", "condition", "cuisine", "dietary"}
    for key in GENERIC_KEYS:
        if key in constraints and constraints[key]:
            total_weight += 0.3
            val = str(constraints[key]).lower()
            if val in searchable:
                score += 0.3

    if total_weight <= 0:
        return 0.5

    return min(1.0, score / total_weight)
