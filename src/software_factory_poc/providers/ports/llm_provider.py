from __future__ import annotations

from abc import ABC, abstractmethod

from llm_bridge.core.entities.llm_request import LlmRequest
from llm_bridge.core.entities.llm_response import LlmResponse
from llm_bridge.core.value_objects.provider_name import ProviderName


class LlmProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> ProviderName: ...

    @abstractmethod
    async def generate(self, request: LlmRequest) -> LlmResponse: ...
