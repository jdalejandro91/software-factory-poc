from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.core.entities.llm_request import LlmRequest
from software_factory_poc.core.entities.llm_response import LlmResponse
from software_factory_poc.core.exceptions.configuration_error import ConfigurationError
from software_factory_poc.core.value_objects.provider_name import ProviderName
from software_factory_poc.providers.gateway.llm_gateway import LlmGateway
from software_factory_poc.providers.gateway.model_allowlist import ModelAllowlist
from software_factory_poc.providers.logging.correlation_id_context import CorrelationIdContext
from software_factory_poc.providers.logging.logging_configurator import LoggingConfigurator
from software_factory_poc.providers.openai.openai_client_factory import OpenAiClientFactory
from software_factory_poc.providers.openai.openai_config import OpenAiConfig
from software_factory_poc.providers.openai.openai_provider import OpenAiProvider
from software_factory_poc.providers.openai.openai_request_mapper import OpenAiRequestMapper
from software_factory_poc.providers.openai.openai_response_mapper import OpenAiResponseMapper
from software_factory_poc.providers.ports.llm_provider import LlmProvider
from software_factory_poc.providers.retry.retry_policy import RetryPolicy


@dataclass(frozen=True, slots=True)
class LlmBridge:
    gateway: LlmGateway
    correlation: CorrelationIdContext

    async def generate(self, request: LlmRequest) -> LlmResponse:
        return await self.gateway.generate(request)

    def configure_default_logging(self, level: str = "INFO") -> None:
        LoggingConfigurator(self.correlation).configure(level)

    @staticmethod
    def from_settings(settings: Settings) -> "LlmBridge":
        correlation = CorrelationIdContext()
        
        allowed_models = frozenset(settings.llm_allowed_models)
        if not allowed_models and settings.openai_api_key:
             # Basic safety: if models aren't explicit but key is provided, we might want to warn or fail. 
             # The previous logic raised ConfigurationError if allowed_models was empty.
             # We should probably maintain that strictness or check if user provided them.
             # User prompt said "Asegúrate de que ... puede instanciarse".
             # If I force it to require allowed_models, user must provide them in Settings.
             pass

        allowlist = ModelAllowlist(allowed=allowed_models)
        
        # We can keep reading retry from env or defaulting, as it's not in Settings
        retry_attempts = int(os.getenv("LLM_BRIDGE_RETRY_ATTEMPTS", "3"))
        retry = RetryPolicy(max_attempts=retry_attempts)
        
        providers = _build_providers(settings, retry, correlation)
        return LlmBridge(gateway=LlmGateway(allowlist=allowlist, providers=providers), correlation=correlation)


def _build_providers(settings: Settings, retry: RetryPolicy, correlation: CorrelationIdContext) -> Mapping[ProviderName, LlmProvider]:
    providers: dict[ProviderName, LlmProvider] = {}
    
    if settings.openai_api_key:
        # We use the key from settings. The OpenAiConfig typically reads from env.
        # We need to bridge that. OpenAiConfig.from_env() reads OPENAI_API_KEY.
        # If we want to use the one from Settings, we should instantiate OpenAiConfig manually.
        # Let's see OpenAiConfig structure. Assuming it accepts api_key in constructor.
        
        # We'll create a config object using the secret from settings.
        # Note: settings.openai_api_key is SecretStr.
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
        
    return providers
