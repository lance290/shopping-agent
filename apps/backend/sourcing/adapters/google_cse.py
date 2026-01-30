"""Google CSE adapter for provider query mapping."""

from __future__ import annotations

from sourcing.adapters.base import ProviderQueryAdapter, build_category_path, build_query_string
from sourcing.models import ProviderQuery, SearchIntent
from sourcing.taxonomy import DEFAULT_TAXONOMY_VERSION


class GoogleCSEQueryAdapter(ProviderQueryAdapter):
    provider_id = "google_cse"

    def build_query(self, intent: SearchIntent) -> ProviderQuery:
        metadata = {
            "taxonomy_version": intent.taxonomy_version or DEFAULT_TAXONOMY_VERSION,
            "category_path": build_category_path(intent),
        }

        return ProviderQuery(
            provider_id=self.provider_id,
            query=build_query_string(intent),
            metadata=metadata,
        )
