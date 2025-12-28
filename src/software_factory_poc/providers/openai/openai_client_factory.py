from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_bridge.providers.openai.openai_config import OpenAiConfig
from llm_bridge.providers.shared.dependency_guard import DependencyGuard


@dataclass(frozen=True, slots=True)
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
