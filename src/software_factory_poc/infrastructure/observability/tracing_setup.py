"""OpenTelemetry tracing configuration for BrahMAS.

Provides:
- configure_tracing(): one-shot TracerProvider setup with BatchSpanProcessor
- get_tracer(): returns a named Tracer instance
"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_CONFIGURED = False


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
