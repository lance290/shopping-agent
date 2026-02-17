"""Choice factor filtering utilities for filtering results based on user-specified attributes."""

import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Normalize text for case-insensitive matching."""
    return text.lower().strip()


def _title_contains_term(normalized_title: str, term: str) -> bool:
    """Check if a single term appears in the title (word-boundary aware for short terms)."""
    term = term.strip()
    if not term:
        return True
    if len(term) <= 3:
        pattern = r'\b' + re.escape(term) + r'\b'
        return bool(re.search(pattern, normalized_title))
    else:
        return term in normalized_title


def matches_choice_constraint(
    title: str,
    constraint_key: str,
    constraint_value: Any
) -> bool:
    """
    Check if a product title matches a specific choice constraint.

    Handles compound values like "gold or platinum" by splitting on
    or/and/comma and returning True if ANY part matches.

    Args:
        title: Product title to check
        constraint_key: The constraint key (e.g., "color", "size", "material")
        constraint_value: The constraint value (e.g., "green", "XL", "cotton")

    Returns:
        True if the title matches the constraint, False otherwise
    """
    if not title or not constraint_value:
        return True  # No constraint to check

    # Skip boolean "No" answers and special values
    if constraint_value is False or str(constraint_value).lower() in ["no", "not answered", "false"]:
        return True

    # Skip price constraints (handled separately)
    if constraint_key in ["min_price", "max_price"]:
        return True

    normalized_title = _normalize_text(title)
    normalized_value = _normalize_text(str(constraint_value))

    # For boolean True values, just check for the key itself
    if constraint_value is True:
        return constraint_key.lower() in normalized_title

    # Split compound values: "gold or platinum", "red, blue, green", "cotton and linen"
    parts = re.split(r'\s+or\s+|\s+and\s+|,\s*|/\s*', normalized_value)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return True

    # ANY part matching = constraint satisfied
    return any(_title_contains_term(normalized_title, part) for part in parts)


def should_exclude_by_choices(
    title: str,
    choice_answers: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Determine if a search result should be excluded based on choice factor constraints.

    Only PRODUCT-ATTRIBUTE keys are used for title filtering. User-intent keys
    (recipient, occasion, budget, price, etc.) describe the buyer's context and
    should NEVER exclude results by title match.

    Args:
        title: Product title to check
        choice_answers: Dictionary of choice factor answers from the user

    Returns:
        True if the result should be excluded, False otherwise
    """
    if not title or not choice_answers:
        return False

    # Keys that describe PRODUCT ATTRIBUTES and CAN be title-matched
    PRODUCT_ATTRIBUTE_KEYS = {
        "material", "color", "colour", "size", "style", "brand",
        "type", "finish", "pattern", "shape", "flavor",
        "weight", "length", "width", "height",
    }

    # Keys that describe USER INTENT / CONTEXT and must NOT be title-matched
    # (also skip price — handled by the price filter)
    SKIP_KEYS = {
        "min_price", "max_price", "price", "budget",
        "recipient", "occasion", "purpose", "use_case", "reason",
        "timeline", "urgency", "delivery", "shipping",
        "format",  # physical/digital is a delivery preference, not a title keyword
        "notes", "comments", "description", "safety_status", "safety_reason",
        "quantity", "count",
    }

    for key, value in choice_answers.items():
        if not value:
            continue

        key_lower = key.lower()

        # Explicit skip list
        if key_lower in SKIP_KEYS:
            continue

        # Only filter on known product-attribute keys
        if key_lower not in PRODUCT_ATTRIBUTE_KEYS:
            continue

        # If constraint doesn't match, exclude this result
        if not matches_choice_constraint(title, key, value):
            logger.debug(f"[CHOICE FILTER] Excluding '{title}' - doesn't match {key}={value}")
            return True

    return False


def extract_choice_constraints(choice_answers: Optional[str]) -> Dict[str, Any]:
    """
    Extract choice constraints from choice_answers JSON string.

    Args:
        choice_answers: JSON string of choice answers

    Returns:
        Dictionary of parsed choice constraints, excluding price and meta fields
    """
    import json

    if not choice_answers:
        return {}

    try:
        answers_obj = json.loads(choice_answers)
        # Filter out price constraints and meta fields
        return {
            k: v for k, v in answers_obj.items()
            if k not in ["min_price", "max_price", "notes", "comments", "description"]
            and v
            and str(v).lower() not in ["not answered", ""]
        }
    except Exception as e:
        logger.error(f"[CHOICE FILTER] Failed to parse choice_answers: {e}")
        return {}
