from __future__ import annotations

import os
from dataclasses import dataclass

from software_factory_poc.application.core.exceptions.configuration_error import ConfigurationError


@dataclass(frozen=True, slots=True)
class GeminiConfig:
    api_key: str

    @staticmethod
    def from_env(var: str = "GEMINI_API_KEY") -> GeminiConfig:
        key = os.getenv(var) or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ConfigurationError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required")
        return GeminiConfig(api_key=key)
