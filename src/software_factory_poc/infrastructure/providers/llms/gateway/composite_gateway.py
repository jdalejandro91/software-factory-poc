
# Check which interface is actually used. Assuming LlmGatewayPort from interfaces based on imports.
from software_factory_poc.application.core.domain.configuration.llm_provider_type import (
    LlmProviderType,
)
from software_factory_poc.application.core.domain.configuration.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.domain.exceptions.all_models_exhausted_error import (
    AllModelsExhaustedException,
)
from software_factory_poc.application.core.domain.exceptions.retryable_error import RetryableError
from software_factory_poc.application.core.ports.gateways.llm_gateway import LLMError, LlmGateway
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class CompositeLlmGateway(LlmGateway):
    """
    Gateway that iterates over a priority list of providers to generate code.
    Fallback pattern: tries first, if fails (retryable), tries next.
    """
    def __init__(
        self, 
        config: ScaffoldingAgentConfig,
        clients: dict[LlmProviderType, LlmGateway]
    ):
        self.config = config
        self.clients = clients
        # Use config provided priority list, or fallback to known keys
        self.priority_list: list[LlmProviderType] = config.llm_priority_list or list(clients.keys())

    def generate_code(self, prompt: str, model: str) -> str:
        """
        Generates code trying providers in order.
        'model' arg might be a hint or ignored in favor of priority list iteration if the intention is fallback.
        However, the interface asks for 'model'. 
        If the requirement is "Fallback logic using priority list", we treat the list as the source of truth for *providers*.
        The 'model' param in the interface might be specific to the underlying call.
        
        Strategy:
        Iterate priority list (ProviderType).
        Get client for provider.
        Call client.generate_code(prompt, model).
        """
        
        last_exception = None
        
        # We iterate over the providers configured in priority list
        # We assume the 'model' string passed here is either generic or we rely on the provider's default 
        # OR we need to map the generic requirement to the provider's specific model?
        # For this scope, we will iterate the PROVIDERS.
        
        for provider_type in self.priority_list:
            client = self.clients.get(provider_type)
            if not client:
                logger.warning(f"Provider {provider_type} in priority list but no client configured. Skipping.")
                continue

            try:
                logger.info(f"Attempting generic generation with provider: {provider_type}")
                # We count tokens roughly here if needed or delegate
                self._log_token_usage_estimate(prompt)
                
                return client.generate_code(prompt, model)
                
            except (RetryableError, LLMError) as e:
                # 5xx, 429, or generic LLMError => Try next
                logger.warning(f"Provider {provider_type} failed with recoverable error: {e}. Falling back...")
                last_exception = e
                continue
            except Exception as e:
                # Unknown error => Fail fast or fallback?
                # Usually safely fallback for robustness
                logger.error(f"Provider {provider_type} failed with unexpected error: {e}. Falling back...", exc_info=True)
                last_exception = e
                continue

        # If we exit loop, all failed
        raise AllModelsExhaustedException(
            message="All configured LLM providers failed to generate code.",
            original_exception=last_exception
        )

    def _log_token_usage_estimate(self, text: str):
        # Basic character count / 4 estimation
        chars = len(text)
        est_tokens = chars // 4
        logger.debug(f"Estimated prompt tokens: {est_tokens}")
