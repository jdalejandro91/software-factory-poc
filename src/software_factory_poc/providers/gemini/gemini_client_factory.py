from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from software_factory_poc.providers.gemini.gemini_config import GeminiConfig
from software_factory_poc.providers.shared.dependency_guard import DependencyGuard


@dataclass(frozen=True, slots=True)
class GeminiClientFactory:
    config: GeminiConfig

    def create(self) -> Any:
        try:
            from google import genai
        except ImportError:
            DependencyGuard(package="google-genai", extra="gemini").require()
        return genai.Client(api_key=self.config.api_key)
