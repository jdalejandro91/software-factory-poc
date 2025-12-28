from __future__ import annotations

import os
from dataclasses import dataclass

from llm_bridge.core.exceptions.configuration_error import ConfigurationError


@dataclass(frozen=True, slots=True)
class OpenAiConfig:
    api_key: str
    timeout_s: float = 30.0
    max_retries: int = 0

    @staticmethod
    def from_env(prefix: str = "OPENAI_") -> "OpenAiConfig":
        key = os.getenv(f"{prefix}API_KEY")
        if not key:
            raise ConfigurationError(f"{prefix}API_KEY is required")
        timeout = float(os.getenv(f"{prefix}TIMEOUT_S", "30.0"))
        return OpenAiConfig(api_key=key, timeout_s=timeout)
