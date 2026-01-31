from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.agents.common.tools.dependency_guard import DependencyGuard
from software_factory_poc.infrastructure.providers.llms.gemini.clients.gemini_config import (
    GeminiConfig,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


@dataclass(frozen=True)
class GeminiClientFactory:
    config: GeminiConfig

    def create(self) -> Any:
        try:
            from google import genai
        except ImportError:
            DependencyGuard(package="google-genai", extra="gemini").require()

        final_timeout = max(30.0, self.config.timeout_s)

        if final_timeout != self.config.timeout_s:
            logger.warning(
                f"Gemini config timeout {self.config.timeout_s}s is too low. Enforcing minimum {final_timeout}s.")

        logger.info(f"Initializing Gemini Client with timeout={final_timeout}s")

        return genai.Client(
            api_key=self.config.api_key,
            http_options={"timeout": final_timeout}
        )