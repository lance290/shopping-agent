"""Material filtering utilities for excluding petroleum-based and synthetic materials."""

import re
from typing import List, Set

# Comprehensive list of synthetic, petroleum-based, and non-natural materials
# that should be excluded when user requests "no plastic" or "no petroleum"
SYNTHETIC_MATERIAL_KEYWORDS = {
    # Direct plastic/polymer terms
    "plastic",
    "polymer",
    "polyester",
    "polyurethane",
    "polypropylene",
    "polyethylene",
    "polycarbonate",
    "pvc",
    "vinyl",
    "nylon",
    "acrylic",
    "spandex",
    "lycra",
    "elastane",

    # Faux/synthetic leather and fabrics
    "faux leather",
    "faux-leather",
    "fake leather",
    "synthetic leather",
    "vegan leather",  # Usually PU-based
    "pleather",
    "leatherette",
    "pu leather",
    "pu-leather",
    "polyurethane leather",

    # Abbreviations commonly used in product listings
    "pu",  # polyurethane
    "pet",  # polyethylene terephthalate
    "pp",   # polypropylene
    "pe",   # polyethylene

    # Other synthetic materials
    "rayon",
    "microfiber",
    "fiberboard",
    "particle board",
    "particleboard",
    "melamine",
    "laminate",
    "laminated",
    "bonded leather",  # Contains synthetic materials

    # Common composite terms
    "synthetic fiber",
    "synthetic fabric",
    "man-made",
    "manmade",
}


def _normalize_text(text: str) -> str:
    """Normalize text for case-insensitive matching."""
    return text.lower().strip()


def contains_synthetic_material(text: str) -> bool:
    """
    Check if the given text contains references to synthetic or petroleum-based materials.

    Args:
        text: Product title or description to check

    Returns:
        True if synthetic materials are detected, False otherwise
    """
    if not text:
        return False

    normalized_text = _normalize_text(text)

    # Check for each synthetic keyword
    for keyword in SYNTHETIC_MATERIAL_KEYWORDS:
        # Use word boundary matching for short abbreviations to avoid false positives
        # For example, "PU" should match "PU leather" but not "PUR" or "PUSH"
        if len(keyword) <= 3 and keyword.isalpha():
            # For short abbreviations, require word boundaries
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, normalized_text, re.IGNORECASE):
                return True
        else:
            # For longer terms, simple substring match is sufficient
            if keyword in normalized_text:
                return True

    return False


def extract_material_constraints(constraints: dict) -> tuple[bool, Set[str]]:
    """
    Extract material-related constraints from the constraints dictionary.

    Args:
        constraints: Dictionary of constraints from RequestSpec or choice_answers

    Returns:
        Tuple of (exclude_synthetics, custom_exclude_keywords)
        - exclude_synthetics: True if user wants to exclude plastic/petroleum materials
        - custom_exclude_keywords: Additional material keywords to exclude
    """
    exclude_synthetics = False
    custom_exclude_keywords: Set[str] = set()

    for key, value in constraints.items():
        if not value:
            continue

        key_lower = key.lower()
        value_lower = str(value).lower()

        # Check if user is requesting exclusion of plastic/petroleum materials
        if "plastic" in key_lower or "petroleum" in key_lower or "synthetic" in key_lower:
            if "no" in value_lower or "without" in value_lower or "exclude" in value_lower:
                exclude_synthetics = True

        # Check for explicit "no X" constraints
        if key_lower.startswith("no "):
            material = key_lower[3:].strip()
            custom_exclude_keywords.add(material)

        # Check for "without X" in values
        if "without" in value_lower:
            # Extract material after "without"
            parts = value_lower.split("without")
            if len(parts) > 1:
                material = parts[1].strip()
                if material:
                    custom_exclude_keywords.add(material)

    return exclude_synthetics, custom_exclude_keywords


def should_exclude_result(
    title: str,
    exclude_synthetics: bool = False,
    custom_exclude_keywords: Set[str] = None
) -> bool:
    """
    Determine if a search result should be excluded based on material constraints.

    Args:
        title: Product title to check
        exclude_synthetics: Whether to exclude synthetic/petroleum materials
        custom_exclude_keywords: Additional keywords to check for exclusion

    Returns:
        True if the result should be excluded, False otherwise
    """
    if not title:
        return False

    # Check for synthetic materials if requested
    if exclude_synthetics and contains_synthetic_material(title):
        return True

    # Check for custom exclude keywords
    if custom_exclude_keywords:
        normalized_title = _normalize_text(title)
        for keyword in custom_exclude_keywords:
            if keyword in normalized_title:
                return True

    return False
