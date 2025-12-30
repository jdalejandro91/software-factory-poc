from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from software_factory_poc.application.core.value_objects.output_format import OutputFormat

@dataclass(frozen=True, slots=True)
class GenerationConfig:
    max_output_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    seed: int | None = None
    stop: Sequence[str] | None = None
    format: OutputFormat = OutputFormat.TEXT

    @property
    def json_mode(self) -> bool:
         return self.format == OutputFormat.JSON

    @property
    def is_json(self) -> bool:
         return self.format == OutputFormat.JSON

    def __post_init__(self) -> None:
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        if self.temperature is not None and not (0.0 <= self.temperature <= 2.0):
            raise ValueError("temperature must be in [0.0, 2.0]")
        if self.top_p is not None and not (0.0 < self.top_p <= 1.0):
            raise ValueError("top_p must be in (0.0, 1.0]")
