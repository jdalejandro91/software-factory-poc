from __future__ import annotations

import os
from dataclasses import dataclass

from software_factory_poc.application.drivers.brain import LlmRequest
from software_factory_poc.application.drivers.brain import LlmResponse
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
from software_factory_poc.infrastructure.configuration.tools.llm.llm_settings import LlmSettings
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
    CorrelationIdContext,
)
from software_factory_poc.infrastructure.observability.logging.logging_configurator import (
    LoggingConfigurator,
)
from software_factory_poc.infrastructure.drivers.llms.facade.llm_provider_factory import (
    LlmProviderFactory,
)
from software_factory_poc.infrastructure.drivers.llms.gateway.llm_gateway import LlmGateway
from software_factory_poc.infrastructure.drivers.llms.gateway.model_allowlist import (
    ModelAllowlist,
)


@dataclass(frozen=True)
class LlmBridge:
    gateway: LlmGateway
    correlation: CorrelationIdContext

    async def generate(self, request: LlmRequest) -> LlmResponse:
        return await self.gateway.generate(request)

    def configure_default_logging(self, level: str = "INFO") -> None:
        LoggingConfigurator(self.correlation).configure(level)

    @staticmethod
    def from_settings(settings: LlmSettings) -> LlmBridge:
        correlation = CorrelationIdContext()
        
        allowed_models = frozenset(settings.llm_allowed_models)
        if not allowed_models and settings.openai_api_key:
             pass

        allowlist = ModelAllowlist(allowed=allowed_models)
        
        # CAMBIO: Default a 1 para evitar reintentos costosos. El agente maneja el fallback.
        retry_attempts = int(os.getenv("LLM_BRIDGE_RETRY_ATTEMPTS", "1"))
        retry = RetryPolicy(max_attempts=retry_attempts)
        
        providers = LlmProviderFactory.build_providers(settings, retry, correlation)
        return LlmBridge(gateway=LlmGateway(allowlist=allowlist, providers=providers), correlation=correlation)
