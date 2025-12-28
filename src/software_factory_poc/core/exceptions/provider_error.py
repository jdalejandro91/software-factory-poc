from __future__ import annotations

from dataclasses import dataclass

from llm_bridge.core.exceptions.llm_bridge_error import LlmBridgeError
from llm_bridge.core.value_objects.provider_name import ProviderName


@dataclass(frozen=True, slots=True)
class ProviderError(LlmBridgeError):
    provider: ProviderName
    message: str
    retryable: bool = False
    status_code: int | None = None
    error_code: str | None = None

    def __str__(self) -> str:
        code = f" status={self.status_code}" if self.status_code is not None else ""
        return f"{self.provider.value}: {self.message}{code}"
