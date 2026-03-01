"""Typed models for the Search Architecture v2 pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional, Sequence, Union

from pydantic import BaseModel, Field, field_validator

ConditionType = Literal["new", "used", "refurbished", "any"]
PriceFlexibility = Literal["strict", "flexible"]
ProviderStatus = Literal["ok", "error", "timeout", "exhausted", "rate_limited"]

FeatureValue = Union[str, List[str]]


class SearchIntent(BaseModel):
    """Structured representation of an end-user purchasing request."""

    product_category: str = Field(..., description="Normalized category identifier")
    taxonomy_version: Optional[str] = Field(None, description="Version of taxonomy used")
    category_path: List[str] = Field(default_factory=list)
    product_name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    price_flexibility: Optional[PriceFlexibility] = None
    condition: Optional[ConditionType] = None
    features: Dict[str, FeatureValue] = Field(default_factory=dict)
    keywords: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    raw_input: str = Field("", description="Original free-form text")

    @field_validator("keywords", mode="before")
    @classmethod
    def _normalize_keywords(
        cls, value: Sequence[str] | str | None
    ) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            candidates = [segment.strip() for segment in value.split(",")]
        else:
            candidates = [str(item).strip() for item in value]

        dedup: Dict[str, str] = {}
        for item in candidates:
            if not item:
                continue
            key = item.casefold()
            if key not in dedup:
                dedup[key] = item

        return [dedup[key] for key in sorted(dedup.keys())]

    @field_validator("features", mode="before")
    @classmethod
    def _ensure_features(cls, value: Optional[Dict[str, FeatureValue]]) -> Dict[str, FeatureValue]:
        return value or {}

    @field_validator("category_path", mode="before")
    @classmethod
    def _ensure_category_path(cls, value: Optional[Sequence[str]]) -> List[str]:
        if value is None:
            return []
        return [item for item in value if item]


class ProviderQuery(BaseModel):
    """Provider-specific query payload sent to adapters/executors."""

    provider_id: str
    query: str
    filters: Dict[str, Union[str, float, int, bool]] = Field(default_factory=dict)
    metadata: Dict[str, str] = Field(default_factory=dict)


class ProviderQueryMap(BaseModel):
    """Collection of per-provider queries used for auditing and persistence."""

    queries: Dict[str, ProviderQuery] = Field(default_factory=dict)

    def add(self, provider_query: ProviderQuery) -> None:
        self.queries[provider_query.provider_id] = provider_query

    def get(self, provider_id: str) -> Optional[ProviderQuery]:
        return self.queries.get(provider_id)


class ProviderStatusSnapshot(BaseModel):
    provider_id: str
    status: ProviderStatus
    result_count: int = 0
    latency_ms: Optional[int] = None
    message: Optional[str] = None


class NormalizedResult(BaseModel):
    """Canonical bid/offer representation persisted to the DB."""

    title: str
    url: str
    source: str
    price: Optional[float] = Field(None, ge=0)
    currency: str = "USD"
    price_original: Optional[float] = Field(None, ge=0)
    currency_original: Optional[str] = None
    canonical_url: Optional[str] = None
    merchant_name: str
    merchant_domain: str
    image_url: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0)
    reviews_count: Optional[int] = Field(None, ge=0)
    shipping_info: Optional[str] = None
    raw_data: Dict[str, object] = Field(default_factory=dict)
    provenance: Dict[str, object] = Field(default_factory=dict)


class AggregatedSearchResponse(BaseModel):
    """Full search payload persisted on rows and used downstream."""

    search_intent: SearchIntent
    provider_queries: ProviderQueryMap = Field(default_factory=ProviderQueryMap)
    results: List[NormalizedResult] = Field(default_factory=list)
    provider_statuses: List[ProviderStatusSnapshot] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    def provider_summary(self) -> Dict[str, ProviderStatusSnapshot]:
        return {status.provider_id: status for status in self.provider_statuses}
