"""Base provider query adapter utilities."""

from __future__ import annotations

from typing import Dict, Iterable, List

from sourcing.models import ProviderQuery, SearchIntent
from sourcing.taxonomy import resolve_category_label, resolve_category_path


def _dedupe_terms(terms: Iterable[str]) -> List[str]:
    seen: Dict[str, str] = {}
    for term in terms:
        cleaned = str(term).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key not in seen:
            seen[key] = cleaned
    return list(seen.values())


def build_query_terms(intent: SearchIntent) -> List[str]:
    terms: List[str] = []
    if intent.brand:
        terms.append(intent.brand)
    if intent.model:
        terms.append(intent.model)
    if intent.product_name:
        terms.append(intent.product_name)
    if intent.product_category:
        terms.append(resolve_category_label(intent.product_category))
    if intent.keywords:
        terms.extend(intent.keywords)
    for value in intent.features.values():
        if isinstance(value, list):
            terms.extend([str(item) for item in value])
        elif value:
            terms.append(str(value))
    if intent.raw_input:
        terms.append(intent.raw_input)
    return _dedupe_terms(terms)


def build_query_string(intent: SearchIntent) -> str:
    terms = build_query_terms(intent)
    if not terms:
        return intent.raw_input or resolve_category_label(intent.product_category)
    return " ".join(terms)


def build_category_path(intent: SearchIntent) -> str:
    if intent.category_path:
        return " > ".join(intent.category_path)
    return " > ".join(resolve_category_path(intent.product_category))


class ProviderQueryAdapter:
    provider_id: str

    def build_query(self, intent: SearchIntent) -> ProviderQuery:
        raise NotImplementedError
