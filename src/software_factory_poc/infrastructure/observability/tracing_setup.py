"""OpenTelemetry tracing configuration for BrahMAS.

Provides:
- configure_tracing(): one-shot TracerProvider setup with BatchSpanProcessor
- get_tracer(): returns a named Tracer instance
- trace_operation(): decorator for creating spans on async/sync functions
"""

from __future__ import annotations

import functools
import os
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_CONFIGURED = False

P = ParamSpec("P")
R = TypeVar("R")


def configure_tracing() -> None:
    """One-shot OTel TracerProvider setup. Safe to call multiple times."""
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    _CONFIGURED = True

    resource = Resource.create(
        {
            "service.name": os.environ.get("SERVICE_NAME", "brahmas"),
            "deployment.environment": os.environ.get("APP_ENV", "local"),
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


def get_tracer(name: str = "brahmas") -> trace.Tracer:
    """Return a named OTel Tracer."""
    return trace.get_tracer(name)


def trace_operation(span_name: str, attributes: dict[str, str] | None = None) -> Callable:
    """Decorator that wraps async or sync functions in an OTel span.

    Usage:
        @trace_operation("workflow.scaffold")
        async def execute(self, mission): ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        tracer = get_tracer()

        if _is_coroutine_function(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with tracer.start_as_current_span(span_name) as span:
                    if attributes:
                        for k, v in attributes.items():
                            span.set_attribute(k, v)
                    return await func(*args, **kwargs)  # type: ignore[misc]

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, v)
                return func(*args, **kwargs)

        return sync_wrapper

    return decorator


def _is_coroutine_function(func: Any) -> bool:
    """Check if a function is a coroutine, unwrapping functools.wraps layers."""
    import asyncio
    import inspect

    return asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func)
