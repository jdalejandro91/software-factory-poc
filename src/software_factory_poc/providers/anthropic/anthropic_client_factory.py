from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_bridge.providers.anthropic.anthropic_config import AnthropicConfig
from llm_bridge.providers.shared.dependency_guard import DependencyGuard


@dataclass(frozen=True, slots=True)
class AnthropicClientFactory:
    config: AnthropicConfig

    def create(self) -> Any:
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            DependencyGuard(package="anthropic", extra="anthropic").require()
        return AsyncAnthropic(api_key=self.config.api_key, timeout=self.config.timeout_s, max_retries=self.config.max_retries)
