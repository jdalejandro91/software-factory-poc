from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class StructuredOutputSchema:
    name: str
    json_schema: Mapping[str, Any]
    strict: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("StructuredOutputSchema.name must be non-empty")
        if not self.json_schema:
            raise ValueError("StructuredOutputSchema.json_schema must be non-empty")
