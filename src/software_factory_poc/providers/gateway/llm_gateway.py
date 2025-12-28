from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from llm_bridge.core.entities.llm_request import LlmRequest
from llm_bridge.core.entities.llm_response import LlmResponse
from llm_bridge.core.exceptions.configuration_error import ConfigurationError
from llm_bridge.core.value_objects.provider_name import ProviderName
from llm_bridge.providers.gateway.model_allowlist import ModelAllowlist
from llm_bridge.providers.ports.llm_provider import LlmProvider


@dataclass(frozen=True, slots=True)
class LlmGateway:
    allowlist: ModelAllowlist
    providers: Mapping[ProviderName, LlmProvider]

    async def generate(self, request: LlmRequest) -> LlmResponse:
        self.allowlist.assert_allowed(request.model)
        provider = self._provider_for(request.model.provider)
        return await provider.generate(request)

    def _provider_for(self, name: ProviderName) -> LlmProvider:
        provider = self.providers.get(name)
        if provider is None:
            raise ConfigurationError(f"Provider not configured: {name.value}")
        return provider
