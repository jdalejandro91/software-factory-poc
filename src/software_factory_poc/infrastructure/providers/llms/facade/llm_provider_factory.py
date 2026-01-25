from collections.abc import Mapping

import logging
from software_factory_poc.application.core.domain.agents.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.core.domain.agents.reasoner.ports.llm_provider import LlmProvider
from software_factory_poc.infrastructure.configuration.llm_settings import LlmSettings
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
    CorrelationIdContext,
)
from software_factory_poc.infrastructure.providers.llms.anthropic.anthropic_provider_impl import (
    AnthropicProviderImpl,
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
from software_factory_poc.infrastructure.providers.llms.deepseek.clients.deepseek_client_factory import (
    DeepSeekClientFactory,
)
from software_factory_poc.infrastructure.providers.llms.deepseek.clients.deepseek_config import (
    DeepSeekConfig,
)
from software_factory_poc.infrastructure.providers.llms.deepseek.deepseek_provider_impl import (
    DeepSeekProviderImpl,
)
from software_factory_poc.infrastructure.providers.llms.deepseek.mappers.deepseek_request_mapper import (
    DeepSeekRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.deepseek.mappers.deepseek_response_mapper import (
    DeepSeekResponseMapper,
)
from software_factory_poc.infrastructure.providers.llms.gemini.clients.gemini_client_factory import (
    GeminiClientFactory,
)
from software_factory_poc.infrastructure.providers.llms.gemini.clients.gemini_config import (
    GeminiConfig,
)
from software_factory_poc.infrastructure.providers.llms.gemini.gemini_provider_impl import (
    GeminiProviderImpl,
)
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_request_mapper import (
    GeminiRequestMapper,
)
from software_factory_poc.infrastructure.providers.llms.gemini.mappers.gemini_response_mapper import (
    GeminiResponseMapper,
)
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


from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


class LlmProviderFactory:
    """
    Factory to build LLM Providers based on configuration.
    """
    
    @staticmethod
    @staticmethod
    def build_providers(settings: LlmSettings, retry: RetryPolicy, correlation: CorrelationIdContext) -> dict[LlmProviderType, LlmProvider]:
        """
        Builds and returns a dictionary of enabled LLM providers based on settings.
        """
        # Debugging explicito de configuracion
        logger = logging.getLogger(__name__)
        
        has_openai = bool(settings.openai_api_key)
        has_deepseek = bool(settings.deepseek_api_key)
        logger.info(f"Factory Config Check: OpenAI={has_openai}, DeepSeek={has_deepseek}")

        providers: dict[LlmProviderType, LlmGateway] = {}
        logger.info("--- [DEBUG] LLM Provider Factory Initialization ---")
        logger.info(f"OpenAI Key Configured: {'YES' if settings.openai_api_key else 'NO'}")
        logger.info(f"DeepSeek Key Configured: {'YES' if settings.deepseek_api_key else 'NO'}")
        logger.info(f"Gemini Key Configured: {'YES' if settings.gemini_api_key else 'NO'}")
        logger.info(f"Anthropic Key Configured: {'YES' if settings.anthropic_api_key else 'NO'}")
        providers: dict[LlmProviderType, LlmProvider] = {}
        
        if settings.openai_api_key:
            api_key = settings.openai_api_key.get_secret_value()
            config = OpenAiConfig(api_key=api_key) 
            
            client = OpenAiClientFactory(config).create()
            providers[LlmProviderType.OPENAI] = OpenAiProvider(
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
            providers[LlmProviderType.DEEPSEEK] = DeepSeekProviderImpl(
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
            providers[LlmProviderType.GEMINI] = GeminiProviderImpl(
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
            providers[LlmProviderType.ANTHROPIC] = AnthropicProviderImpl(
                client=client,
                retry=retry,
                request_mapper=AnthropicRequestMapper(),
                response_mapper=AnthropicResponseMapper(),
                correlation=correlation
            )
            
        return providers
