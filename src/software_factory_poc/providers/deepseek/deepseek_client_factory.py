from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_bridge.providers.deepseek.deepseek_config import DeepSeekConfig
from llm_bridge.providers.shared.dependency_guard import DependencyGuard


@dataclass(frozen=True, slots=True)
class DeepSeekClientFactory:
    config: DeepSeekConfig

    def create(self) -> Any:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            DependencyGuard(package="openai", extra="openai").require()
        c = self.config
        return AsyncOpenAI(api_key=c.api_key, base_url=c.base_url, timeout=c.timeout_s, max_retries=c.max_retries)
