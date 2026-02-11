"""
Health check utilities for dependency monitoring.

Provides detailed health checks for:
- Database connectivity
- External APIs (LLM, search providers)
- System resources (memory, disk)
"""

import os
import time
import psutil
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
import httpx

from .logging import get_logger

logger = get_logger(__name__)


class HealthCheckResult:
    """Result of a health check."""

    def __init__(self, name: str, status: str, details: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.name = name
        self.status = status  # "ok", "degraded", "error"
        self.details = details or {}
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "status": self.status,
            "details": self.details,
        }
        if self.error:
            result["error"] = self.error
        return result

    @property
    def is_healthy(self) -> bool:
        return self.status == "ok"


async def check_database(session: AsyncSession, timeout: float = 5.0) -> HealthCheckResult:
    """
    Check database connectivity and performance.

    Args:
        session: Database session
        timeout: Timeout in seconds

    Returns:
        HealthCheckResult with database status
    """
    start_time = time.time()

    try:
        # Simple connectivity check
        await asyncio.wait_for(session.exec(text("SELECT 1")), timeout=timeout)
        latency = time.time() - start_time

        # Get connection pool stats if available
        pool_info = {}
        try:
            from database import engine

            pool = engine.pool
            pool_info = {
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "checked_in": pool.checkedin(),
            }
        except Exception:
            pass

        return HealthCheckResult(
            name="database",
            status="ok",
            details={
                "latency_ms": round(latency * 1000, 2),
                "pool": pool_info,
            },
        )

    except asyncio.TimeoutError:
        return HealthCheckResult(
            name="database",
            status="error",
            error=f"Database query timeout after {timeout}s",
        )

    except Exception as e:
        logger.error("Database health check failed", exc_info=True)
        return HealthCheckResult(
            name="database",
            status="error",
            error=str(e)[:200],
        )


async def check_llm_api(timeout: float = 10.0) -> HealthCheckResult:
    """
    Check LLM API connectivity.

    Args:
        timeout: Timeout in seconds

    Returns:
        HealthCheckResult with LLM API status
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if not openrouter_key:
        return HealthCheckResult(
            name="llm_api",
            status="degraded",
            details={"message": "LLM API not configured (OPENROUTER_API_KEY not set)"},
        )

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Simple connectivity check (HEAD request to OpenRouter API)
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {openrouter_key}"},
            )
            latency = time.time() - start_time

            if response.status_code == 200:
                return HealthCheckResult(
                    name="llm_api",
                    status="ok",
                    details={"latency_ms": round(latency * 1000, 2)},
                )
            else:
                return HealthCheckResult(
                    name="llm_api",
                    status="degraded",
                    error=f"API returned status {response.status_code}",
                )

    except asyncio.TimeoutError:
        return HealthCheckResult(
            name="llm_api",
            status="error",
            error=f"LLM API timeout after {timeout}s",
        )

    except Exception as e:
        logger.warning("LLM API health check failed", extra={"error": str(e)})
        return HealthCheckResult(
            name="llm_api",
            status="degraded",
            error=str(e)[:200],
        )


async def check_search_providers(timeout: float = 10.0) -> HealthCheckResult:
    """
    Check search provider connectivity.

    Args:
        timeout: Timeout in seconds

    Returns:
        HealthCheckResult with search provider status
    """
    providers = {
        "serpapi": os.getenv("SERPAPI_API_KEY"),
        "rainforest": os.getenv("RAINFOREST_API_KEY"),
        "valueserp": os.getenv("VALUESERP_API_KEY"),
        "searchapi": os.getenv("SEARCHAPI_API_KEY"),
    }

    configured_providers = {name: key for name, key in providers.items() if key}

    if not configured_providers:
        return HealthCheckResult(
            name="search_providers",
            status="degraded",
            details={"message": "No search providers configured"},
        )

    # We don't actually ping the APIs (would consume credits)
    # Just report which ones are configured
    return HealthCheckResult(
        name="search_providers",
        status="ok",
        details={
            "configured_providers": list(configured_providers.keys()),
            "count": len(configured_providers),
        },
    )


async def check_system_resources() -> HealthCheckResult:
    """
    Check system resources (memory, disk).

    Returns:
        HealthCheckResult with system resource status
    """
    try:
        # Memory check
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # Disk check
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent

        # Determine status based on thresholds
        status = "ok"
        warnings = []

        if memory_percent > 90:
            status = "degraded"
            warnings.append(f"High memory usage: {memory_percent}%")
        elif memory_percent > 95:
            status = "error"
            warnings.append(f"Critical memory usage: {memory_percent}%")

        if disk_percent > 85:
            status = "degraded"
            warnings.append(f"High disk usage: {disk_percent}%")
        elif disk_percent > 95:
            status = "error"
            warnings.append(f"Critical disk usage: {disk_percent}%")

        return HealthCheckResult(
            name="system_resources",
            status=status,
            details={
                "memory_percent": round(memory_percent, 1),
                "memory_available_mb": round(memory.available / (1024 * 1024), 1),
                "disk_percent": round(disk_percent, 1),
                "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 1),
                "warnings": warnings if warnings else None,
            },
        )

    except Exception as e:
        logger.error("System resource check failed", exc_info=True)
        return HealthCheckResult(
            name="system_resources",
            status="error",
            error=str(e)[:200],
        )


async def run_health_checks(session: AsyncSession, include_external: bool = True) -> Dict[str, Any]:
    """
    Run all health checks and return aggregated results.

    Args:
        session: Database session
        include_external: Whether to check external APIs (slower)

    Returns:
        Dictionary with health check results
    """
    checks = {}

    # Always check database
    checks["database"] = await check_database(session)

    # Always check system resources
    checks["system_resources"] = await check_system_resources()

    # Optionally check external APIs
    if include_external:
        checks["llm_api"] = await check_llm_api()
        checks["search_providers"] = await check_search_providers()

    # Determine overall status
    statuses = [check.status for check in checks.values()]
    if any(status == "error" for status in statuses):
        overall_status = "unhealthy"
    elif any(status == "degraded" for status in statuses):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {name: check.to_dict() for name, check in checks.items()},
    }
