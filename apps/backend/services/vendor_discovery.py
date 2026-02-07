"""
Vendor Discovery Adapter Layer

Provides a pluggable interface for vendor/seller discovery.
Backends:
  - LocalVendorAdapter: wraps the local early-adopter vendor registry (vendors.py)
  - WattDataAdapter: connects to WattData MCP (when available)

Usage:
  adapter = get_vendor_adapter()
  sellers = await adapter.find_sellers("private_aviation", limit=5)
"""
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Vendor:
    """Normalized vendor record."""
    name: str
    company: str
    email: str
    phone: Optional[str] = None
    category: Optional[str] = None
    website: Optional[str] = None
    service_areas: Optional[List[str]] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuyerNeed:
    """A buyer request that a seller might want to quote on."""
    row_id: int
    title: str
    category: str
    choice_factors: Dict[str, Any] = field(default_factory=dict)
    budget_max: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


class VendorDiscoveryAdapter(ABC):
    """Base interface for vendor discovery backends."""

    @abstractmethod
    async def find_sellers(
        self,
        category: str,
        constraints: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Vendor]:
        """Find sellers/vendors matching a buyer's need."""
        ...

    @abstractmethod
    async def find_buyers(
        self,
        seller_profile: Dict[str, Any],
        limit: int = 10,
    ) -> List[BuyerNeed]:
        """Find buyer needs matching a seller's profile (ICP matching)."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is reachable."""
        ...


# ── Local Adapter (early-adopter registry) ──────────────────────────────────────────


class LocalVendorAdapter(VendorDiscoveryAdapter):
    """Wraps the local early-adopter vendor registry (vendors.py)."""

    async def find_sellers(
        self,
        category: str,
        constraints: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Vendor]:
        from services.vendors import get_vendors

        registered = get_vendors(category, limit)
        return [
            Vendor(
                name=v.name,
                company=v.company,
                email=v.email,
                phone=getattr(v, "phone", None),
                category=category,
                website=getattr(v, "website", None),
                service_areas=getattr(v, "service_areas", None),
            )
            for v in registered
        ]

    async def find_buyers(
        self,
        seller_profile: Dict[str, Any],
        limit: int = 10,
    ) -> List[BuyerNeed]:
        # Local adapter cannot discover buyers
        return []

    async def health_check(self) -> bool:
        return True


# ── WattData MCP Adapter (scaffold) ─────────────────────────────────────


class WattDataAdapter(VendorDiscoveryAdapter):
    """
    Connects to the WattData MCP server for real vendor discovery.

    Status: SCAFFOLD — MCP is not yet online (~2 weeks from 2026-02-06).
    Implementation will be filled in once the API shape is known.
    """

    def __init__(self):
        self.mcp_url = os.getenv("WATTDATA_MCP_URL", "")
        self.api_key = os.getenv("WATTDATA_API_KEY", "")

    async def find_sellers(
        self,
        category: str,
        constraints: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Vendor]:
        # TODO: Implement when MCP API shape is known
        # Expected: POST {mcp_url}/find-sellers with category + constraints
        # Response: normalize into List[Vendor], preserve unknown fields in raw_data
        logger.warning(
            "[WattDataAdapter] find_sellers called but MCP not yet implemented. "
            "Returning empty list."
        )
        return []

    async def find_buyers(
        self,
        seller_profile: Dict[str, Any],
        limit: int = 10,
    ) -> List[BuyerNeed]:
        # TODO: Implement when MCP API shape is known
        # Expected: POST {mcp_url}/find-buyers with seller_profile
        # Response: normalize into List[BuyerNeed]
        logger.warning(
            "[WattDataAdapter] find_buyers called but MCP not yet implemented. "
            "Returning empty list."
        )
        return []

    async def health_check(self) -> bool:
        if not self.mcp_url:
            return False
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.mcp_url}/health")
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"[WattDataAdapter] Health check failed: {e}")
            return False


# ── Factory ──────────────────────────────────────────────────────────────

_adapter_instance: Optional[VendorDiscoveryAdapter] = None


async def get_vendor_adapter() -> VendorDiscoveryAdapter:
    """
    Return the configured vendor discovery adapter.

    Reads VENDOR_DISCOVERY_BACKEND env var:
      - "local" (default): LocalVendorAdapter (early-adopter registry)
      - "wattdata": WattDataAdapter (falls back to local if unreachable)
    """
    global _adapter_instance

    if _adapter_instance is not None:
        return _adapter_instance

    backend = os.getenv("VENDOR_DISCOVERY_BACKEND", "local").strip().lower()

    if backend == "wattdata":
        adapter = WattDataAdapter()
        try:
            healthy = await adapter.health_check()
            if healthy:
                logger.info("[VendorDiscovery] Using WattData MCP adapter")
                _adapter_instance = adapter
                return adapter
            else:
                logger.warning(
                    "[VendorDiscovery] WattData MCP unreachable, falling back to local registry"
                )
        except Exception as e:
            logger.warning(
                f"[VendorDiscovery] WattData init failed, falling back to local registry: {e}"
            )

    logger.info("[VendorDiscovery] Using local vendor adapter (early-adopter registry)")
    _adapter_instance = LocalVendorAdapter()
    return _adapter_instance


def reset_adapter():
    """Reset the cached adapter (useful for testing or config changes)."""
    global _adapter_instance
    _adapter_instance = None
