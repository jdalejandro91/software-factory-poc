
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

        registered_providers = [p.value for p in clients.keys()]
        logger.info(f"--- [DEBUG] CompositeGateway initialized with providers: {registered_providers}")

    def generate_code(self, prompt: str, model: str) -> str:
        """
        Generates code trying providers in order defined by priority_list.
        Each item in priority_list is expected to be a ModelId object.
        """
        
        last_exception = None
        
        # Iteramos sobre objetos ModelId configurados
        for model_entry in self.priority_list:
            # 1. Extraer el Enum del proveedor para buscar el cliente
            # model_entry is expected to be ModelId(provider=..., name=...)
            
            # Defensive check or just assume typed list as per instruction
            if hasattr(model_entry, "provider"):
                 provider_type = model_entry.provider
                 target_model = model_entry.name
            else:
                 # Fallback if it actually is just an Enum
                 provider_type = model_entry
                 target_model = model 

            client = self.clients.get(provider_type)
            
            if not client:
                logger.warning(f"Client for provider '{provider_type}' not found. Available: {list(self.clients.keys())}")
                continue

            try:
                # 2. Usar el nombre específico del modelo definido en la config
                logger.info(f"Using Provider: {provider_type.value} | Model: {target_model}")
                
                # We count tokens roughly here if needed
                self._log_token_usage_estimate(prompt)
                
                return client.generate_code(prompt, model=target_model)
                
            except (RetryableError, LLMError) as e:
                # 5xx, 429, or generic LLMError => Try next
                logger.warning(f"Provider {provider_type} failed with recoverable error: {e}. Falling back...")
                last_exception = e
                continue
            except Exception as e:
                # Unknown error => Fail fast or fallback?
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
