"""
CouponProvider abstraction layer for Pop swap/coupon sourcing.

This module defines the interface that all coupon providers must implement,
plus concrete implementations:

  - ManualProvider: Admin-uploaded swaps via API/CSV
  - HomeBrewProvider: Brand self-serve portal (reads from pop_swap table)
  - IbottaProvider: Stub for future Ibotta Performance Network integration
  - AggregateProvider: Queries all active providers and merges results

Architecture note:
  GroFlo was originally planned as the primary coupon MCP server, but has no
  API/MCP available (as of Feb 2026). This abstraction lets us plug in any
  provider — external API, MCP server, or our own DB — behind a uniform
  interface.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.coupons import PopSwap

logger = logging.getLogger(__name__)


class SwapOffer:
    """Normalized swap offer returned by any CouponProvider."""

    def __init__(
        self,
        swap_id: Optional[int],
        category: str,
        target_product: Optional[str],
        swap_product_name: str,
        offer_type: str,
        savings_cents: int,
        offer_description: Optional[str] = None,
        brand_name: Optional[str] = None,
        swap_product_image: Optional[str] = None,
        swap_product_url: Optional[str] = None,
        provider: str = "unknown",
        provider_offer_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ):
        self.swap_id = swap_id
        self.category = category
        self.target_product = target_product
        self.swap_product_name = swap_product_name
        self.offer_type = offer_type
        self.savings_cents = savings_cents
        self.offer_description = offer_description
        self.brand_name = brand_name
        self.swap_product_image = swap_product_image
        self.swap_product_url = swap_product_url
        self.provider = provider
        self.provider_offer_id = provider_offer_id
        self.expires_at = expires_at

    def to_dict(self) -> dict:
        return {
            "swap_id": self.swap_id,
            "category": self.category,
            "target_product": self.target_product,
            "swap_product_name": self.swap_product_name,
            "offer_type": self.offer_type,
            "savings_cents": self.savings_cents,
            "savings_display": f"${self.savings_cents / 100:.2f}",
            "offer_description": self.offer_description,
            "brand_name": self.brand_name,
            "swap_product_image": self.swap_product_image,
            "swap_product_url": self.swap_product_url,
            "provider": self.provider,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class CouponProvider(ABC):
    """
    Abstract base class for coupon/swap providers.

    Every provider must implement search_swaps(). Optional methods for
    claim tracking and receipt verification have default no-op implementations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'manual', 'homebrew', 'ibotta')."""
        ...

    @abstractmethod
    async def search_swaps(
        self,
        category: str,
        product_name: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SwapOffer]:
        """
        Search for available swap/coupon offers matching the given category
        and optional product name.

        Args:
            category: Product category (e.g. "steak sauce", "milk")
            product_name: Specific product (e.g. "A1 Steak Sauce")
            session: DB session (required for DB-backed providers)

        Returns:
            List of matching SwapOffer objects, sorted by savings (highest first)
        """
        ...

    async def record_claim(
        self,
        swap_id: int,
        user_id: int,
        row_id: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> bool:
        """Record that a user claimed this swap offer. Returns True on success."""
        return True

    async def verify_receipt(
        self,
        swap_id: int,
        user_id: int,
        receipt_id: str,
        session: Optional[AsyncSession] = None,
    ) -> bool:
        """Verify a receipt against a claimed swap. Returns True if verified."""
        return True


# ---------------------------------------------------------------------------
# Concrete Providers
# ---------------------------------------------------------------------------


class ManualProvider(CouponProvider):
    """
    Reads swap offers from the pop_swap table where provider='manual'.
    Admin uploads swaps via the /pop/admin/swaps API or CSV import.
    """

    @property
    def name(self) -> str:
        return "manual"

    async def search_swaps(
        self,
        category: str,
        product_name: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SwapOffer]:
        if session is None:
            logger.warning("[ManualProvider] No DB session provided")
            return []

        now = datetime.utcnow()
        stmt = (
            select(PopSwap)
            .where(PopSwap.provider == "manual")
            .where(PopSwap.is_active == True)
            .where(
                (PopSwap.expires_at == None) | (PopSwap.expires_at > now)
            )
        )

        result = await session.execute(stmt)
        swaps = result.scalars().all()

        matched_swaps = []
        search_terms = category.lower().split()
        if product_name:
            search_terms.extend(product_name.lower().split())

        for s in swaps:
            s_cat = s.category.lower() if s.category else ""
            s_target = s.target_product.lower() if s.target_product else ""
            
            # Simple substring matching: does the swap category appear in the search query, or vice-versa?
            if s_cat in category.lower() or category.lower() in s_cat:
                matched_swaps.append(s)
            elif s_target and (s_target in category.lower() or category.lower() in s_target):
                matched_swaps.append(s)
            elif product_name and (s_cat in product_name.lower() or s_target and s_target in product_name.lower()):
                matched_swaps.append(s)
            elif any(term in s_cat or term in s_target for term in search_terms if len(term) > 3):
                matched_swaps.append(s)

        # Deduplicate
        matched_swaps = list({s.id: s for s in matched_swaps}.values())

        return sorted(
            [_swap_to_offer(s) for s in matched_swaps],
            key=lambda o: o.savings_cents,
            reverse=True,
        )


class HomeBrewProvider(CouponProvider):
    """
    Reads swap offers from the pop_swap table where provider='homebrew'.
    Brands create these via a self-serve portal (future feature).
    """

    @property
    def name(self) -> str:
        return "homebrew"

    async def search_swaps(
        self,
        category: str,
        product_name: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SwapOffer]:
        if session is None:
            logger.warning("[HomeBrewProvider] No DB session provided")
            return []

        now = datetime.utcnow()
        stmt = (
            select(PopSwap)
            .where(PopSwap.provider == "homebrew")
            .where(PopSwap.is_active == True)
            .where(
                (PopSwap.expires_at == None) | (PopSwap.expires_at > now)
            )
            .where(PopSwap.category.ilike(f"%{category}%"))
        )

        # If max_redemptions set, exclude fully redeemed offers
        result = await session.execute(stmt)
        swaps = result.scalars().all()

        available = [
            s for s in swaps
            if s.max_redemptions is None or s.current_redemptions < s.max_redemptions
        ]

        return sorted(
            [_swap_to_offer(s) for s in available],
            key=lambda o: o.savings_cents,
            reverse=True,
        )


class IbottaProvider(CouponProvider):
    """
    Stub for Ibotta Performance Network (IPN) integration.

    IPN provides a REST API at https://api.ibotta.com/v2/offers with
    2,600+ CPG brand offers. Access requires an enterprise partnership.

    When activated, this provider will:
      1. Call GET /v2/offers?category={category}&retailer={retailer}
      2. Map Ibotta offers to SwapOffer objects
      3. Cache results in pop_swap table with provider='ibotta'

    To activate: Set IBOTTA_API_KEY env var and call IbottaProvider(api_key=...).
    """

    @property
    def name(self) -> str:
        return "ibotta"

    async def search_swaps(
        self,
        category: str,
        product_name: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SwapOffer]:
        raise NotImplementedError(
            "Ibotta IPN integration not yet available. "
            "Requires enterprise partnership and IBOTTA_API_KEY. "
            "See: https://ipn.ibotta.com/integrating-with-the-ipn"
        )


# ---------------------------------------------------------------------------
# Aggregate Provider (queries all active providers)
# ---------------------------------------------------------------------------


class AggregateProvider:
    """
    Queries all registered CouponProviders and merges results.
    Gracefully handles provider failures (logs and skips).
    """

    def __init__(self, providers: Optional[List[CouponProvider]] = None):
        self.providers: List[CouponProvider] = providers or [
            ManualProvider(),
            HomeBrewProvider(),
        ]

    async def search_swaps(
        self,
        category: str,
        product_name: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SwapOffer]:
        """Search all providers and return merged, deduplicated results."""
        all_offers: List[SwapOffer] = []

        for provider in self.providers:
            try:
                offers = await provider.search_swaps(category, product_name, session)
                all_offers.extend(offers)
                if offers:
                    logger.info(
                        f"[CouponProvider] {provider.name} returned {len(offers)} "
                        f"swap(s) for '{category}'"
                    )
            except NotImplementedError:
                logger.debug(f"[CouponProvider] {provider.name} not implemented, skipping")
            except Exception as e:
                logger.warning(
                    f"[CouponProvider] {provider.name} failed for '{category}': {e}"
                )

        # Sort by savings (highest first), deduplicate by swap_id
        seen_ids = set()
        unique: List[SwapOffer] = []
        for offer in sorted(all_offers, key=lambda o: o.savings_cents, reverse=True):
            if offer.swap_id and offer.swap_id in seen_ids:
                continue
            if offer.swap_id:
                seen_ids.add(offer.swap_id)
            unique.append(offer)

        return unique


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _swap_to_offer(swap: PopSwap) -> SwapOffer:
    """Convert a PopSwap DB row to a SwapOffer DTO."""
    return SwapOffer(
        swap_id=swap.id,
        category=swap.category,
        target_product=swap.target_product,
        swap_product_name=swap.swap_product_name,
        offer_type=swap.offer_type,
        savings_cents=swap.savings_cents,
        offer_description=swap.offer_description,
        brand_name=swap.brand_name,
        swap_product_image=swap.swap_product_image,
        swap_product_url=swap.swap_product_url,
        provider=swap.provider,
        provider_offer_id=swap.provider_offer_id,
        expires_at=swap.expires_at,
    )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_aggregate: Optional[AggregateProvider] = None


def get_coupon_provider() -> AggregateProvider:
    """Get the singleton AggregateProvider instance."""
    global _aggregate
    if _aggregate is None:
        _aggregate = AggregateProvider()
    return _aggregate
