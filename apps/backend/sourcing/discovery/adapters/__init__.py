"""Discovery adapters."""

from sourcing.discovery.adapters.base import DiscoveryAdapter, DiscoveryBatch, DiscoveryCandidate
from sourcing.discovery.adapters.organic import OrganicDiscoveryAdapter

__all__ = [
    "DiscoveryAdapter",
    "DiscoveryBatch",
    "DiscoveryCandidate",
    "OrganicDiscoveryAdapter",
]
