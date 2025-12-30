from __future__ import annotations

from dataclasses import dataclass

from software_factory_poc.application.core.domain.configuration.llm_provider_type import LlmProviderType


@dataclass(frozen=True, slots=True)
class ModelId:
    provider: LlmProviderType
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ModelId.name must be non-empty")

    @property
    def qualified_name(self) -> str:
        return f"{self.provider.value}:{self.name}"
