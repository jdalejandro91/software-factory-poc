from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from software_factory_poc.application.core.entities.llm_request import LlmRequest
from software_factory_poc.application.core.entities.llm_response import LlmResponse
from software_factory_poc.application.core.value_objects.provider_name import ProviderName
from software_factory_poc.application.ports.llms.llm_provider import LlmProvider
from software_factory_poc.configuration.llms.llm_settings import LlmSettings
from software_factory_poc.infrastructure.providers.llms.openai.clients.openai_client_factory import (
    OpenAiClientFactory,
)
from software_factory_poc.infrastructure.providers.llms.openai.clients.openai_config import (
    OpenAiConfig,
)
from software_factory_poc.infrastructure.providers.llms.openai.mappers.openai_request_mapper import (
    OpenAiRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.openai.mappers.openai_response_mapper import (
    OpenAiResponseMapper,
)
from software_factory_poc.infrastructure.providers.llms.openai.openai_provider_impl import (
    OpenAiProvider,
)
from software_factory_poc.infrastructure.providers.llms.deepseek.clients.deepseek_client_factory import (
    DeepSeekClientFactory,
)
from software_factory_poc.infrastructure.providers.llms.deepseek.clients.deepseek_config import (
    DeepSeekConfig,
)
from software_factory_poc.infrastructure.providers.llms.deepseek.mappers.deepseek_request_mapper import (
    DeepSeekRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.deepseek.mappers.deepseek_response_mapper import (
    DeepSeekResponseMapper,
)
from software_factory_poc.infrastructure.providers.llms.deepseek.deepseek_provider_impl import (
    DeepSeekProviderImpl,
)
from software_factory_poc.infrastructure.providers.llms.gemini.clients.gemini_client_factory import (
    GeminiClientFactory,
)
from software_factory_poc.infrastructure.providers.llms.gemini.clients.gemini_config import (
    GeminiConfig,
)
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_request_mapper import (
    GeminiRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_response_mapper import (
    GeminiResponseMapper,
)
from software_factory_poc.infrastructure.providers.llms.gemini.gemini_provider_impl import (
    GeminiProviderImpl,
)
from software_factory_poc.infrastructure.providers.llms.anthropic.clients.anthropic_client_factory import (
    AnthropicClientFactory,
)
from software_factory_poc.infrastructure.providers.llms.anthropic.clients.anthropic_config import (
    AnthropicConfig,
)
from software_factory_poc.infrastructure.providers.llms.anthropic.mappers.anthropic_request_mapper import (
    AnthropicRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.anthropic.mappers.anthropic_response_mapper import (
    AnthropicResponseMapper,
)
from software_factory_poc.infrastructure.providers.llms.anthropic.anthropic_provider_impl import (
    AnthropicProviderImpl,
)
from software_factory_poc.infrastructure.providers.llms.gateway.llm_gateway import LlmGateway
from software_factory_poc.infrastructure.providers.llms.gateway.model_allowlist import ModelAllowlist
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import CorrelationIdContext
from software_factory_poc.infrastructure.observability.logging.logging_configurator import LoggingConfigurator
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy


@dataclass(frozen=True, slots=True)
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
        
        providers = _build_providers(settings, retry, correlation)
        return LlmBridge(gateway=LlmGateway(allowlist=allowlist, providers=providers), correlation=correlation)


def _build_providers(settings: LlmSettings, retry: RetryPolicy, correlation: CorrelationIdContext) -> Mapping[ProviderName, LlmProvider]:
    providers: dict[ProviderName, LlmProvider] = {}
    
    if settings.openai_api_key:
        api_key = settings.openai_api_key.get_secret_value()
        config = OpenAiConfig(api_key=api_key) 
        
        client = OpenAiClientFactory(config).create()
        providers[ProviderName.OPENAI] = OpenAiProvider(
            client=client, 
            retry=retry, 
            request_mapper=OpenAiRequestMapper(), 
            response_mapper=OpenAiResponseMapper(), 
            correlation=correlation
        )

    if settings.deepseek_api_key:
        api_key = settings.deepseek_api_key.get_secret_value()
        config = DeepSeekConfig(api_key=api_key)
        client = DeepSeekClientFactory(config).create()
        providers[ProviderName.DEEPSEEK] = DeepSeekProviderImpl(
            client=client,
            retry=retry,
            request_mapper=DeepSeekRequestMapper(),
            response_mapper=DeepSeekResponseMapper(),
            correlation=correlation
        )

    if settings.gemini_api_key:
        api_key = settings.gemini_api_key.get_secret_value()
        config = GeminiConfig(api_key=api_key)
        client = GeminiClientFactory(config).create()
        providers[ProviderName.GEMINI] = GeminiProviderImpl(
            client=client,
            retry=retry,
            request_mapper=GeminiRequestMapper(),
            response_mapper=GeminiResponseMapper(),
            correlation=correlation
        )

    if settings.anthropic_api_key:
        api_key = settings.anthropic_api_key.get_secret_value()
        config = AnthropicConfig(api_key=api_key)
        client = AnthropicClientFactory(config).create()
        providers[ProviderName.ANTHROPIC] = AnthropicProviderImpl(
            client=client,
            retry=retry,
            request_mapper=AnthropicRequestMapper(),
            response_mapper=AnthropicResponseMapper(),
            correlation=correlation
        )
        
    return providers
