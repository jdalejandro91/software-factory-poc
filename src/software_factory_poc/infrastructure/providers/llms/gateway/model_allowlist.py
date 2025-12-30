from __future__ import annotations

from dataclasses import dataclass

from software_factory_poc.application.core.domain.exceptions.configuration_error import (
    ConfigurationError,
)
from software_factory_poc.application.core.domain.value_objects.model_id import ModelId


@dataclass(frozen=True, slots=True)
class ModelAllowlist:
    allowed: frozenset[str]

    def assert_allowed(self, model: ModelId) -> None:
        if model.qualified_name not in self.allowed:
            raise ConfigurationError(f"Model is not allowed: {model.qualified_name}")
