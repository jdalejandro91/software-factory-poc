from __future__ import annotations

from dataclasses import dataclass

from llm_bridge.core.exceptions.configuration_error import ConfigurationError
from llm_bridge.core.value_objects.model_id import ModelId


@dataclass(frozen=True, slots=True)
class ModelAllowlist:
    allowed: frozenset[str]

    def assert_allowed(self, model: ModelId) -> None:
        if model.qualified_name not in self.allowed:
            raise ConfigurationError(f"Model is not allowed: {model.qualified_name}")
