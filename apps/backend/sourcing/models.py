"""Typed models for the Search Architecture v2 pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional, Sequence, Union

from pydantic import BaseModel, Field, field_validator

ConditionType = Literal["new", "used", "refurbished", "any"]
PriceFlexibility = Literal["strict", "flexible"]
ProviderStatus = Literal["ok", "error", "timeout", "exhausted", "rate_limited"]

FeatureValue = Union[str, List[str]]
LocationRelevance = Literal["none", "endpoint", "service_area", "vendor_proximity"]
LocationPrecision = Literal["address", "postal_code", "neighborhood", "city", "metro", "region"]
LocationResolutionStatus = Literal["resolved", "unresolved", "ambiguous"]


class LocationTargets(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    service_location: Optional[str] = None
    search_area: Optional[str] = None
    vendor_market: Optional[str] = None

    def non_empty_items(self) -> Dict[str, str]:
        return {
            key: value.strip()
            for key, value in self.model_dump().items()
            if isinstance(value, str) and value.strip()
        }


class LocationContext(BaseModel):
    relevance: LocationRelevance = "none"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    targets: LocationTargets = Field(default_factory=LocationTargets)
    notes: Optional[str] = None


class LocationResolution(BaseModel):
    normalized_label: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    precision: Optional[LocationPrecision] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    status: LocationResolutionStatus = "unresolved"


class LocationResolutionMap(BaseModel):
    origin: Optional[LocationResolution] = None
    destination: Optional[LocationResolution] = None
    service_location: Optional[LocationResolution] = None
    search_area: Optional[LocationResolution] = None
    vendor_market: Optional[LocationResolution] = None


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
    location_context: LocationContext = Field(default_factory=LocationContext)
    location_resolution: LocationResolutionMap = Field(default_factory=LocationResolutionMap)
    execution_mode: Optional[str] = Field(None, description="affiliate_only | sourcing_only | affiliate_plus_sourcing")
    search_strategies: List[str] = Field(default_factory=list, description="Subset of official_first, market_first, specialist_first, prestige_first, local_network_first")
    source_archetypes: List[str] = Field(default_factory=list, description="Expected source types: brokerage, association, registry, etc.")

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

    @field_validator("location_context", mode="before")
    @classmethod
    def _ensure_location_context(cls, value: object) -> LocationContext:
        if isinstance(value, LocationContext):
            return value
        if not isinstance(value, dict):
            return LocationContext()
        return LocationContext.model_validate(value)

    @field_validator("location_resolution", mode="before")
    @classmethod
    def _ensure_location_resolution(cls, value: object) -> LocationResolutionMap:
        if isinstance(value, LocationResolutionMap):
            return value
        if not isinstance(value, dict):
            return LocationResolutionMap()
        return LocationResolutionMap.model_validate(value)


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
