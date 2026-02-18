"""Pure ASGI middleware for correlation/trace ID propagation via structlog contextvars.

Injects correlation_id, trace_id, endpoint, and method into structlog context
for every HTTP/WebSocket request. Logs request completion with duration.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger()


class CorrelationMiddleware:
    """ASGI middleware that binds correlation/trace IDs to structlog contextvars."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        await self._handle_request(scope, receive, send)

    async def _handle_request(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        clear_contextvars()

        correlation_id = _extract_header(scope, b"x-correlation-id") or str(uuid4())
        trace_id = str(uuid4())
        endpoint = _extract_path(scope)
        method = _extract_method(scope)

        bind_contextvars(
            correlation_id=correlation_id,
            trace_id=trace_id,
            context_endpoint=endpoint,
            context_method=method,
        )

        http_status = 500
        start = time.perf_counter()
        try:

            async def _send_wrapper(message: dict[str, Any]) -> None:
                nonlocal http_status
                if message.get("type") == "http.response.start":
                    http_status = message.get("status", 500)
                await send(message)

            await self.app(scope, receive, _send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            status_label = "SUCCESS" if http_status < 400 else "ERROR"
            await logger.ainfo(
                "Request processed",
                processing_status=status_label,
                processing_duration_ms=duration_ms,
            )


def _extract_header(scope: dict[str, Any], name: bytes) -> str | None:
    """Extract a header value from ASGI scope (case-insensitive)."""
    headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
    lower_name = name.lower()
    for key, value in headers:
        if key.lower() == lower_name:
            return value.decode("latin-1")
    return None


def _extract_path(scope: dict[str, Any]) -> str:
    """Extract request path from ASGI scope."""
    return scope.get("path", "/")


def _extract_method(scope: dict[str, Any]) -> str:
    """Extract HTTP method from ASGI scope."""
    return scope.get("method", "UNKNOWN")
