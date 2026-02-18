"""Structlog-based logging configuration with Puntored schema and stdlib bridge.

Provides:
- configure_logging(): one-shot structlog + stdlib setup
- get_logger(): returns bound structlog logger
- LoggerFactoryService: backward-compatible facade
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog

from software_factory_poc.infrastructure.observability.logging.puntored_processor import (
    puntored_schema_processor,
)

_CONFIGURED = False


def configure_logging() -> None:
    """One-shot structlog + stdlib bridge configuration.

    Safe to call multiple times; only the first invocation takes effect.
    Renderer is selected by LOG_FORMAT env (json|console) or APP_ENV.
    """
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    _CONFIGURED = True

    renderer = _select_renderer()
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        puntored_schema_processor,
    ]

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Stdlib bridge: route logging.getLogger() output through structlog pipeline
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *shared_processors,
            renderer,
        ],
    )
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def get_logger(component: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger pre-bound with context_component."""
    return structlog.get_logger().bind(context_component=component)


def _select_renderer() -> Any:
    """Choose renderer based on LOG_FORMAT env or APP_ENV."""
    log_format = os.environ.get("LOG_FORMAT", "").lower()
    if log_format == "json":
        return structlog.processors.JSONRenderer()
    if log_format == "console":
        return structlog.dev.ConsoleRenderer(colors=True)

    env = os.environ.get("APP_ENV", "local").lower()
    if env in ("qa", "staging", "prod", "production"):
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer(colors=True)


class LoggerFactoryService:
    """Backward-compatible facade. Prefer get_logger() for new code."""

    @staticmethod
    def configure_root_logger() -> None:
        """Delegate to configure_logging()."""
        configure_logging()

    @staticmethod
    def build_logger(name: str) -> logging.Logger:
        """Return a stdlib logger (routed through structlog via ProcessorFormatter)."""
        configure_logging()
        return logging.getLogger(name)
