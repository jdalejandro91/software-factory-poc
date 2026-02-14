from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from software_factory_poc.application.ports.drivers.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.ports.drivers.common.exceptions.configuration_error import (
    ConfigurationError,
)
from software_factory_poc.application.ports.drivers.reasoner.llm_request import LlmRequest
from software_factory_poc.application.ports.drivers.reasoner import LlmResponse
from software_factory_poc.application.ports.drivers.reasoner.ports.llm_provider import LlmProvider
from software_factory_poc.infrastructure.adapters.drivers.llms.gateway.model_allowlist import (
    ModelAllowlist,
)


@dataclass(frozen=True)
class LlmGateway(LlmProvider):
    allowlist: ModelAllowlist
    providers: Mapping[LlmProviderType, LlmProvider]

    @property
    def name(self) -> LlmProviderType:
        return LlmProviderType.GATEWAY

    async def generate(self, request: LlmRequest) -> LlmResponse:
        self.allowlist.assert_allowed(request.model)
        provider = self._provider_for(request.model.provider)
        return await provider.generate(request)

    def _provider_for(self, name: LlmProviderType) -> LlmProvider:
        provider = self.providers.get(name)
        if provider is None:
            raise ConfigurationError(f"Provider not configured: {name.value}")
        return provider
