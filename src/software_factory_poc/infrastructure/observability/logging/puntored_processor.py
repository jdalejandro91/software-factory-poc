"""Puntored corporate schema processor for structlog.

Transforms flat structlog event_dict into a nested JSON structure
compliant with the Puntored observability standard.
All field extraction uses dict.pop(key, default) to avoid KeyError.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4


def _build_root_fields(event_dict: dict[str, Any]) -> dict[str, Any]:
    """Extract root-level fields: timestamp, level, service, environment, IDs."""
    return {
        "timestamp": event_dict.pop("timestamp", None),
        "level": event_dict.pop("level", "info"),
        "service": os.environ.get("SERVICE_NAME", "brahmas"),
        "environment": os.environ.get("APP_ENV", "local"),
        "trace_id": event_dict.pop("trace_id", None),
        "correlation_id": event_dict.pop("correlation_id", None),
        "span_id": event_dict.pop("span_id", None),
        "message": event_dict.pop("event", ""),
    }


def _safe_float(value: Any) -> float | None:
    """Cast a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_processing(event_dict: dict[str, Any]) -> dict[str, Any] | None:
    """Extract processing metrics block."""
    status = event_dict.pop("processing_status", None)
    if status is None:
        return None
    return {
        "status": status,
        "duration_ms": _safe_float(event_dict.pop("processing_duration_ms", None)),
        "retries": event_dict.pop("processing_retries", None),
    }


def _build_error(event_dict: dict[str, Any]) -> dict[str, Any] | None:
    """Extract error block. Returns None if no error_type present."""
    error_type = event_dict.pop("error_type", None)
    if error_type is None:
        return None
    return {
        "type": error_type,
        "code": event_dict.pop("error_code", None),
        "details": event_dict.pop("error_details", None),
        "retryable": event_dict.pop("error_retryable", False),
    }


def _build_event_block(event_dict: dict[str, Any]) -> dict[str, Any]:
    """Extract event identification block (camelCase per Puntored spec)."""
    return {
        "eventId": event_dict.pop("event_id", str(uuid4())),
        "eventType": event_dict.pop("event_type", None),
        "actorId": event_dict.pop("actor_id", None),
    }


def _build_context(event_dict: dict[str, Any]) -> dict[str, Any] | None:
    """Extract request/execution context block."""
    component = event_dict.pop("context_component", None)
    if component is None:
        return None
    return {
        "component": component,
        "endpoint": event_dict.pop("context_endpoint", None),
        "method": event_dict.pop("context_method", None),
        "client_ip": event_dict.pop("context_client_ip", None),
    }


def _build_metadata(event_dict: dict[str, Any]) -> dict[str, Any] | None:
    """Extract metadata block."""
    source = event_dict.pop("source_system", None)
    tags = event_dict.pop("tags", None)
    if source is None and tags is None:
        return None
    return {
        "source_system": source,
        "tags": tags,
    }


def _hex_to_uuid(hex_str: str) -> str:
    """Convert a 32-char hex string to UUID format 8-4-4-4-12."""
    return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:]}"


def _inject_otel_ids(event_dict: dict[str, Any]) -> None:
    """Overwrite trace_id and span_id from the current OTel span if recording."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            event_dict["trace_id"] = _hex_to_uuid(format(ctx.trace_id, "032x"))
            event_dict["span_id"] = format(ctx.span_id, "016x")
    except Exception:  # noqa: BLE001
        pass  # OTel not available or not configured — keep existing values


def puntored_schema_processor(
    logger: Any,  # noqa: ARG001
    method_name: str,  # noqa: ARG001
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that reshapes flat event_dict into Puntored schema."""
    _inject_otel_ids(event_dict)
    result = _build_root_fields(event_dict)

    processing = _build_processing(event_dict)
    if processing is not None:
        result["processing"] = processing

    error = _build_error(event_dict)
    if error is not None:
        result["error"] = error

    result["event"] = _build_event_block(event_dict)

    context = _build_context(event_dict)
    if context is not None:
        result["context"] = context

    metadata = _build_metadata(event_dict)
    if metadata is not None:
        result["metadata"] = metadata

    if event_dict:
        result["extra"] = dict(event_dict)

    return result
