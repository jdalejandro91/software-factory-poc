from __future__ import annotations

from abc import ABC, abstractmethod

from software_factory_poc.application.ports.drivers.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.ports.drivers.reasoner.llm_request import LlmRequest
from software_factory_poc.application.ports.drivers.reasoner.llm_response import LlmResponse


class LlmProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> LlmProviderType: ...

    @abstractmethod
    async def generate(self, request: LlmRequest) -> LlmResponse: ...
