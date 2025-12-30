from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.value_objects.model_id import ModelId
from software_factory_poc.application.core.value_objects.token_usage import TokenUsage


@dataclass(frozen=True, slots=True)
class LlmResponse:
    model: ModelId
    content: str
    usage: TokenUsage | None = None
    provider_payload: Mapping[str, Any] | None = None
    reasoning_content: str | None = None

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("LlmResponse.content must be non-empty")
