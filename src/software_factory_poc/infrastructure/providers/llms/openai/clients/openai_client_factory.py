from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.agents.common.tools.dependency_guard import DependencyGuard
from software_factory_poc.infrastructure.providers.llms.openai.clients.openai_config import (
    OpenAiConfig,
)


@dataclass(frozen=True)
class OpenAiClientFactory:
    config: OpenAiConfig

    def create(self) -> Any:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            DependencyGuard(package="openai", extra="openai").require()
        return AsyncOpenAI(
            api_key=self.config.api_key,
            timeout=self.config.timeout_s,
            max_retries=self.config.max_retries,
        )
