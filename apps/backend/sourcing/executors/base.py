"""Provider executors with status instrumentation."""

from __future__ import annotations

import asyncio
import time
from typing import List, Tuple, TYPE_CHECKING

from sourcing.models import ProviderStatusSnapshot

if TYPE_CHECKING:
    from sourcing.repository import SourcingProvider, SearchResult


async def run_provider_with_status(
    provider_id: str,
    provider: "SourcingProvider",
    query: str,
    *,
    timeout_seconds: float = 8.0,
    **kwargs,
) -> Tuple[List["SearchResult"], ProviderStatusSnapshot]:
    started = time.monotonic()
    try:
        results = await asyncio.wait_for(
            provider.search(query, **kwargs), timeout=timeout_seconds
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        status = ProviderStatusSnapshot(
            provider_id=provider_id,
            status="ok",
            result_count=len(results),
            latency_ms=elapsed_ms,
        )
        return results, status
    except asyncio.TimeoutError:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        status = ProviderStatusSnapshot(
            provider_id=provider_id,
            status="timeout",
            result_count=0,
            latency_ms=elapsed_ms,
            message="Search timed out",
        )
        return [], status
    except Exception as e:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        error_msg = str(e)
        print(f"[{provider_id}] Search error: {type(e).__name__}: {error_msg}")
        status = ProviderStatusSnapshot(
            provider_id=provider_id,
            status="error",
            result_count=0,
            latency_ms=elapsed_ms,
            message=f"Search failed: {error_msg[:100]}",
        )
        return [], status
