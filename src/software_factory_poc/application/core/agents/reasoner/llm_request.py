from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional

from software_factory_poc.application.core.agents.reasoner.value_objects.generation_config import (
    GenerationConfig,
)
from software_factory_poc.application.core.agents.reasoner.value_objects.message import Message
from software_factory_poc.application.core.agents.common.value_objects.model_id import ModelId
from software_factory_poc.application.core.agents.reasoner.value_objects.output_constraints import (
    OutputConstraints,
)
from software_factory_poc.application.core.agents.common.value_objects.trace_context import TraceContext


@dataclass(frozen=True)
class LlmRequest:
    model: ModelId
    messages: tuple[Message, ...]
    generation: GenerationConfig
    output:Optional[ OutputConstraints] = None
    trace:Optional[ TraceContext] = None
    metadata:Optional[ Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("LlmRequest.messages must be non-empty")
