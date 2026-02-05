"""Choice factor filtering utilities for filtering results based on user-specified attributes."""

import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Normalize text for case-insensitive matching."""
    return text.lower().strip()


def matches_choice_constraint(
    title: str,
    constraint_key: str,
    constraint_value: Any
) -> bool:
    """
    Check if a product title matches a specific choice constraint.

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

    # Check if the constraint value appears in the title
    # Use word boundary matching to avoid false positives
    # e.g., "green" should match "green shirt" but not "greenish"
    if len(normalized_value) <= 3:
        # For short values, use word boundary
        pattern = r'\b' + re.escape(normalized_value) + r'\b'
        return bool(re.search(pattern, normalized_title))
    else:
        # For longer values, simple substring match is fine
        return normalized_value in normalized_title


def should_exclude_by_choices(
    title: str,
    choice_answers: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Determine if a search result should be excluded based on choice factor constraints.

    Args:
        title: Product title to check
        choice_answers: Dictionary of choice factor answers from the user

    Returns:
        True if the result should be excluded, False otherwise
    """
    if not title or not choice_answers:
        return False

    # Check each constraint
    for key, value in choice_answers.items():
        if not value:
            continue

        # Skip price constraints (handled separately)
        if key in ["min_price", "max_price"]:
            continue

        # Skip generic or irrelevant keys
        if key.lower() in ["notes", "comments", "description"]:
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
