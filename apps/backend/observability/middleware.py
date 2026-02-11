"""
FastAPI middleware for observability.

Provides:
- Request correlation ID injection
- Automatic metrics collection
- Performance tracing
- Request/response logging
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging import get_logger, correlation_id_context, set_correlation_id
from .metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
)

logger = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic observability instrumentation.

    Adds:
    - Correlation ID to all requests
    - Automatic metrics collection
    - Request/response logging
    - Performance tracking
    """

    def __init__(self, app: ASGIApp, enable_request_logging: bool = True):
        super().__init__(app)
        self.enable_request_logging = enable_request_logging

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")

        # Use correlation_id_context to set it for the request lifecycle
        with correlation_id_context(correlation_id) as req_id:
            # Add to request state for downstream use
            request.state.correlation_id = req_id

            # Get path for metrics (sanitize to avoid cardinality explosion)
            path = self._sanitize_path(request.url.path)
            method = request.method

            # Track in-progress requests
            http_requests_in_progress.labels(method=method, endpoint=path).inc()

            # Start timer
            start_time = time.time()

            try:
                # Log request (if enabled and not health check)
                if self.enable_request_logging and not self._is_health_check(request):
                    logger.info(
                        "Request started",
                        extra={
                            "method": method,
                            "path": path,
                            "client_host": request.client.host if request.client else None,
                            "user_agent": request.headers.get("user-agent", "")[:200],
                        },
                    )

                # Process request
                response = await call_next(request)

                # Calculate duration
                duration = time.time() - start_time

                # Record metrics
                http_requests_total.labels(
                    method=method,
                    endpoint=path,
                    status=response.status_code,
                ).inc()

                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=path,
                ).observe(duration)

                # Add correlation ID to response headers
                response.headers["X-Request-ID"] = req_id

                # Log response (if enabled and not health check)
                if self.enable_request_logging and not self._is_health_check(request):
                    logger.info(
                        "Request completed",
                        extra={
                            "method": method,
                            "path": path,
                            "status_code": response.status_code,
                            "duration_seconds": round(duration, 3),
                        },
                    )

                # Warn on slow requests (>2s)
                if duration > 2.0 and not self._is_health_check(request):
                    logger.warning(
                        "Slow request detected",
                        extra={
                            "method": method,
                            "path": path,
                            "duration_seconds": round(duration, 3),
                            "status_code": response.status_code,
                        },
                    )

                return response

            except Exception as exc:
                # Calculate duration even on error
                duration = time.time() - start_time

                # Record error metrics (status 500 for unhandled exceptions)
                http_requests_total.labels(
                    method=method,
                    endpoint=path,
                    status=500,
                ).inc()

                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=path,
                ).observe(duration)

                # Log error
                logger.error(
                    "Request failed",
                    extra={
                        "method": method,
                        "path": path,
                        "duration_seconds": round(duration, 3),
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                    exc_info=True,
                )

                # Re-raise to let FastAPI handle it
                raise

            finally:
                # Decrement in-progress counter
                http_requests_in_progress.labels(method=method, endpoint=path).dec()

    def _sanitize_path(self, path: str) -> str:
        """
        Sanitize path to avoid metric cardinality explosion.

        Replace UUIDs and numeric IDs with placeholders.
        """
        import re

        # Replace UUIDs with placeholder
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{uuid}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs with placeholder
        path = re.sub(r"/\d+", "/{id}", path)

        return path

    def _is_health_check(self, request: Request) -> bool:
        """Check if request is a health check endpoint."""
        return request.url.path.startswith("/health") or request.url.path.startswith("/metrics")


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware that only adds correlation ID to requests.

    Use this if you don't want full observability instrumentation.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")

        with correlation_id_context(correlation_id) as req_id:
            request.state.correlation_id = req_id
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
