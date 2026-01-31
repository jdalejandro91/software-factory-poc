from __future__ import annotations

import os
from dataclasses import dataclass

from software_factory_poc.application.core.agents.common.exceptions.configuration_error import (
    ConfigurationError,
)


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    timeout_s: float = 300.0  # Increased default to 300s (5 min) to satisfy Gemini min deadline

    @staticmethod
    def from_env(var: str = "GEMINI_API_KEY") -> GeminiConfig:
        key = os.getenv(var) or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ConfigurationError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required")

        # Robust parsing for timeout
        timeout_val = os.getenv("GEMINI_TIMEOUT_S", "300.0")
        try:
            timeout = float(timeout_val)
        except ValueError:
            timeout = 300.0

        return GeminiConfig(api_key=key, timeout_s=timeout)