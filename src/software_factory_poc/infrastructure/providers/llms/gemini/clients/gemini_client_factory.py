from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.agents.common.tools.dependency_guard import DependencyGuard
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.providers.llms.gemini.clients.gemini_config import (
    GeminiConfig,
)

logger = LoggerFactoryService.build_logger(__name__)


@dataclass(frozen=True)
class GeminiClientFactory:
    config: GeminiConfig

    def create(self) -> Any:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            DependencyGuard(package="google-genai", extra="gemini").require()
            from google import genai
            from google.genai import types

        safe_timeout_seconds = max(30.0, self.config.timeout_s)
        timeout_ms = int(safe_timeout_seconds * 1000)

        logger.info(f"Initializing Gemini Client with timeout={timeout_ms}ms ({safe_timeout_seconds}s)")

        return genai.Client(
            api_key=self.config.api_key,
            http_options=types.HttpOptions(timeout=timeout_ms)
        )