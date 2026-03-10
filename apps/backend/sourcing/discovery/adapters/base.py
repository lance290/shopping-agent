"""Adapter primitives for live vendor discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Protocol


@dataclass
class DiscoveryCandidate:
    adapter_id: str
    query: str
    title: str
    url: str
    source_url: str
    source_type: str
    snippet: str = ""
    image_url: str | None = None
    email: str | None = None
    phone: str | None = None
    location_hint: str | None = None
    official_site: bool = False
    first_party_contact: bool = False
    canonical_domain: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    extraction_payload: dict[str, Any] = field(default_factory=dict)
    trust_signals: dict[str, Any] = field(default_factory=dict)
    classification: dict[str, Any] | None = None


@dataclass
class DiscoveryBatch:
    adapter_id: str
    query: str
    results: List[DiscoveryCandidate]
    status: str
    latency_ms: int
    error_message: str | None = None


class DiscoveryAdapter(Protocol):
    adapter_id: str
    supported_modes: set[str]

    async def search(
        self,
        query: str,
        *,
        discovery_mode: str,
        timeout_seconds: float,
        max_results: int,
    ) -> DiscoveryBatch:
        ...
