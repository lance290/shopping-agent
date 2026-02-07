"""eBay Browse API executor wrapper."""

from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING

from sourcing.executors.base import run_provider_with_status
from sourcing.models import ProviderStatusSnapshot

if TYPE_CHECKING:
    from sourcing.repository import SourcingProvider, SearchResult


async def execute_ebay(
    provider: "SourcingProvider", query: str, *, timeout_seconds: float = 8.0, **kwargs
) -> Tuple[List["SearchResult"], ProviderStatusSnapshot]:
    return await run_provider_with_status(
        "ebay_browse", provider, query, timeout_seconds=timeout_seconds, **kwargs
    )
