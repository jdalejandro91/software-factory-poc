from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional

from software_factory_poc.application.ports.drivers.common.value_objects.model_id import ModelId
from software_factory_poc.application.ports.drivers.reasoner.token_metric import TokenMetric


@dataclass(frozen=True)
class LlmResponse:
    model: ModelId
    content: str
    usage:Optional[ TokenMetric] = None
    provider_payload:Optional[ Mapping[str, Any]] = None
    reasoning_content:Optional[ str] = None

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("LlmResponse.content must be non-empty")
