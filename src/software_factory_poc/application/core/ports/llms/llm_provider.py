from __future__ import annotations

from abc import ABC, abstractmethod

from software_factory_poc.application.core.domain.entities.llm.llm_request import LlmRequest
from software_factory_poc.application.core.domain.entities.llm.llm_response import LlmResponse
from software_factory_poc.application.core.domain.configuration.llm_provider_type import LlmProviderType


class LlmProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> LlmProviderType: ...

    @abstractmethod
    async def generate(self, request: LlmRequest) -> LlmResponse: ...
