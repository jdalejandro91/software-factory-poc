from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.domain.agents.common.tools.dependency_guard import DependencyGuard
from software_factory_poc.infrastructure.providers.llms.gemini.clients.gemini_config import (
    GeminiConfig,
)


@dataclass(frozen=True, slots=True)
class GeminiClientFactory:
    config: GeminiConfig

    def create(self) -> Any:
        try:
            from google import genai
        except ImportError:
            DependencyGuard(package="google-genai", extra="gemini").require()
        return genai.Client(api_key=self.config.api_key, http_options={"timeout": self.config.timeout_s})
