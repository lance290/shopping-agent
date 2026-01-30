"""Taxonomy helpers for Search Architecture v2."""

from __future__ import annotations

import re
from typing import Dict, List

DEFAULT_TAXONOMY_VERSION = "shopping_v1"

_CATEGORY_LABELS: Dict[str, str] = {
    "running_shoes": "running shoes",
    "laptop": "laptop",
    "headphones": "headphones",
    "office_chair": "office chair",
}

_CATEGORY_PATHS: Dict[str, List[str]] = {
    "running_shoes": ["shoes", "running shoes"],
    "laptop": ["electronics", "computers", "laptop"],
    "headphones": ["electronics", "audio", "headphones"],
    "office_chair": ["furniture", "office", "chair"],
}


def normalize_category(category: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", category.strip().lower())
    return normalized.strip("_")


def resolve_category_label(category: str) -> str:
    normalized = normalize_category(category)
    return _CATEGORY_LABELS.get(normalized, normalized.replace("_", " ")).strip()


def resolve_category_path(category: str) -> List[str]:
    normalized = normalize_category(category)
    path = _CATEGORY_PATHS.get(normalized)
    if path:
        return path
    label = resolve_category_label(normalized)
    return [segment for segment in label.split(" ") if segment]
