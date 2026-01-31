from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional

from software_factory_poc.application.core.agents.reasoner.value_objects.output_format import OutputFormat


@dataclass(frozen=True)
class GenerationConfig:
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    seed: Optional[int] = None
    stop: Optional[Sequence[str]] = None
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
