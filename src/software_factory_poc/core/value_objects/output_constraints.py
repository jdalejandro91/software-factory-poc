from __future__ import annotations

from dataclasses import dataclass

from llm_bridge.core.value_objects.output_format import OutputFormat
from llm_bridge.core.value_objects.structured_output_schema import StructuredOutputSchema


@dataclass(frozen=True, slots=True)
class OutputConstraints:
    format: OutputFormat
    schema: StructuredOutputSchema | None = None

    def __post_init__(self) -> None:
        if self.format is OutputFormat.JSON_SCHEMA and self.schema is None:
            raise ValueError("schema is required when format=JSON_SCHEMA")
