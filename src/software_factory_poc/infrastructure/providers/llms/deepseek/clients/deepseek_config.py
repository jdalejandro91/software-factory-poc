from __future__ import annotations

import os
from dataclasses import dataclass

from software_factory_poc.application.core.domain.exceptions.configuration_error import (
    ConfigurationError,
)


@dataclass(frozen=True, slots=True)
class DeepSeekConfig:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    timeout_s: float = 120.0
    max_retries: int = 0

    @staticmethod
    def from_env(prefix: str = "DEEPSEEK_") -> DeepSeekConfig:
        key = os.getenv(f"{prefix}API_KEY")
        if not key:
            raise ConfigurationError(f"{prefix}API_KEY is required")
        base_url = os.getenv(f"{prefix}BASE_URL", "https://api.deepseek.com")
        timeout = float(os.getenv(f"{prefix}TIMEOUT_S", "120.0"))
        return DeepSeekConfig(api_key=key, base_url=base_url, timeout_s=timeout)
