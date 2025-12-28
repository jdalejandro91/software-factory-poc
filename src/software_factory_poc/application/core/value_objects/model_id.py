from __future__ import annotations

from dataclasses import dataclass

from software_factory_poc.application.core.value_objects.provider_name import ProviderName


@dataclass(frozen=True, slots=True)
class ModelId:
    provider: ProviderName
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ModelId.name must be non-empty")

    @property
    def qualified_name(self) -> str:
        return f"{self.provider.value}:{self.name}"
