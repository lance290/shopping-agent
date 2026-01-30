"""Rainforest adapter for provider query mapping."""

from __future__ import annotations

from sourcing.models import ProviderQuery, SearchIntent
from sourcing.taxonomy import DEFAULT_TAXONOMY_VERSION
from sourcing.adapters.base import ProviderQueryAdapter, build_query_string


class RainforestQueryAdapter(ProviderQueryAdapter):
    provider_id = "rainforest"

    def build_query(self, intent: SearchIntent) -> ProviderQuery:
        filters = {}
        if intent.min_price is not None:
            filters["min_price"] = intent.min_price
        if intent.max_price is not None:
            filters["max_price"] = intent.max_price
        if intent.condition and intent.condition != "any":
            filters["condition"] = intent.condition

        metadata = {
            "taxonomy_version": intent.taxonomy_version or DEFAULT_TAXONOMY_VERSION,
            "category": intent.product_category,
        }

        return ProviderQuery(
            provider_id=self.provider_id,
            query=build_query_string(intent),
            filters=filters,
            metadata=metadata,
        )
