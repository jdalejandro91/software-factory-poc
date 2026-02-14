from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.ports.drivers.common.tools import DependencyGuard
from software_factory_poc.infrastructure.adapters.drivers.llms.anthropic.clients.anthropic_config import (
    AnthropicConfig,
)


@dataclass(frozen=True)
class AnthropicClientFactory:
    config: AnthropicConfig

    def create(self) -> Any:
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            DependencyGuard(package="anthropic", extra="anthropic").require()
        return AsyncAnthropic(api_key=self.config.api_key, timeout=self.config.timeout_s, max_retries=self.config.max_retries)
