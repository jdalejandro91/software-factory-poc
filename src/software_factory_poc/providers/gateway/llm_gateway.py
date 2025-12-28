from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from software_factory_poc.application.core.entities.llm_request import LlmRequest
from software_factory_poc.application.core.entities.llm_response import LlmResponse
from software_factory_poc.application.core.exceptions.configuration_error import ConfigurationError
from software_factory_poc.application.core.value_objects.provider_name import ProviderName
from software_factory_poc.application.ports.llms.llm_provider import LlmProvider
from software_factory_poc.providers.gateway.model_allowlist import ModelAllowlist


@dataclass(frozen=True, slots=True)
class LlmGateway(LlmProvider):
    allowlist: ModelAllowlist
    providers: Mapping[ProviderName, LlmProvider]

    @property
    def name(self) -> ProviderName:
        return ProviderName.GATEWAY

    async def generate(self, request: LlmRequest) -> LlmResponse:
        self.allowlist.assert_allowed(request.model)
        provider = self._provider_for(request.model.provider)
        return await provider.generate(request)

    def _provider_for(self, name: ProviderName) -> LlmProvider:
        provider = self.providers.get(name)
        if provider is None:
            raise ConfigurationError(f"Provider not configured: {name.value}")
        return provider
