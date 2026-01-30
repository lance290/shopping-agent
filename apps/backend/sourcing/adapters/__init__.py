"""Provider query adapter registry."""

from __future__ import annotations

from typing import Dict, Iterable, List

from sourcing.adapters.base import ProviderQueryAdapter
from sourcing.adapters.google_cse import GoogleCSEQueryAdapter
from sourcing.adapters.rainforest import RainforestQueryAdapter
from sourcing.models import ProviderQueryMap, SearchIntent


ADAPTERS: Dict[str, ProviderQueryAdapter] = {
    "rainforest": RainforestQueryAdapter(),
    "google_cse": GoogleCSEQueryAdapter(),
}


def build_provider_query_map(
    intent: SearchIntent, provider_ids: Iterable[str]
) -> ProviderQueryMap:
    query_map = ProviderQueryMap()
    for provider_id in provider_ids:
        adapter = ADAPTERS.get(provider_id)
        if not adapter:
            continue
        query_map.add(adapter.build_query(intent))
    return query_map


def available_provider_ids() -> List[str]:
    return list(ADAPTERS.keys())
