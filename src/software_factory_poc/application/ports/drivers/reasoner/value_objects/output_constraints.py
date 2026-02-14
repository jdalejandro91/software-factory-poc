from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from software_factory_poc.application.ports.drivers.reasoner.value_objects.output_format import OutputFormat
from software_factory_poc.application.ports.drivers.reasoner.value_objects.structured_output_schema import (
    StructuredOutputSchema,
)


@dataclass(frozen=True)
class OutputConstraints:
    format: OutputFormat
    schema:Optional[ StructuredOutputSchema] = None

    def __post_init__(self) -> None:
        pass
        # if self.format is OutputFormat.JSON and self.schema is None:
        #    # Optional: could enforce schema for JSON if desired, but user didn't ask.
        #    pass
