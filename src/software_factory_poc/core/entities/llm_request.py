from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from software_factory_poc.core.value_objects.generation_config import GenerationConfig
from software_factory_poc.core.value_objects.message import Message
from software_factory_poc.core.value_objects.model_id import ModelId
from software_factory_poc.core.value_objects.output_constraints import OutputConstraints
from software_factory_poc.core.value_objects.trace_context import TraceContext


@dataclass(frozen=True, slots=True)
class LlmRequest:
    model: ModelId
    messages: tuple[Message, ...]
    generation: GenerationConfig
    output: OutputConstraints | None = None
    trace: TraceContext | None = None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("LlmRequest.messages must be non-empty")
