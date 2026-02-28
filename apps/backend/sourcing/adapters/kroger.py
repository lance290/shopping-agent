"""Kroger query adapter for Search Architecture v2."""

from __future__ import annotations

from sourcing.adapters.base import ProviderQueryAdapter, build_query_string
from sourcing.models import ProviderQuery, SearchIntent


class KrogerQueryAdapter(ProviderQueryAdapter):
    provider_id = "kroger"

    def build_query(self, intent: SearchIntent) -> ProviderQuery:
        query = build_query_string(intent)
        return ProviderQuery(provider_id=self.provider_id, query=query)
