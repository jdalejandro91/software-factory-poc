import asyncio
from typing import Any

from software_factory_poc.application.core.agents.common.config.llm_provider_type import (
    LlmProviderType,
)
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.agents.reasoner.exceptions.all_models_exhausted_error import (
    AllModelsExhaustedException,
)
from software_factory_poc.application.core.agents.common.exceptions.retryable_error import RetryableError
from software_factory_poc.application.core.agents.reasoner.ports.llm_gateway import LLMError, LlmGateway
from software_factory_poc.application.core.agents.reasoner.ports.llm_provider import LlmProvider
from software_factory_poc.application.core.agents.reasoner.llm_request import LlmRequest
from software_factory_poc.application.core.agents.reasoner.value_objects.message import Message
from software_factory_poc.application.core.agents.reasoner.value_objects.message_role import MessageRole
from software_factory_poc.application.core.agents.reasoner.value_objects.generation_config import GenerationConfig
from software_factory_poc.application.core.agents.common.value_objects.model_id import ModelId
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

class CompositeLlmGateway(LlmGateway):
    """
    Gateway that iterates over a priority list of providers to generate code.
    Fallback pattern: tries first, if fails (retryable), tries next.
    Acts as a bridge between Sync Use Case and Async Providers.
    """
    def __init__(
        self, 
        config: ScaffoldingAgentConfig,
        clients: dict[LlmProviderType, LlmProvider]
    ):
        self.config = config
        self.clients = clients
        # Use config provided priority list, or fallback to known keys
        self.priority_list: list[Any] = config.llm_model_priority
        
        # Security validation
        if not self.priority_list:
            logger.warning("Priority list is empty in config! Fallback to available clients.")
            self.priority_list = list(clients.keys())

        logger.info(f"CompositeGateway loaded {len(self.priority_list)} priority items.")
        
        registered_providers = [p.value for p in clients.keys()]
        logger.info(f"--- [DEBUG] CompositeGateway initialized with providers: {registered_providers}")

    def generate_code(self, prompt: str, context: str, model_hints: list[ModelId]) -> Any:
        # Note: Return type is LlmResponse, imported locally or Any to avoid circular deps if needed, 
        # but LlmGateway says -> LlmResponse.
        
        last_exception = None
        
        # Priority: Hints > Config Priority
        # If hints are provided, we should probably try them? 
        # Or does config override? Usually hints from agent are specific.
        # But 'config.priority_list' is the main strategy.
        # Let's verify requirement: "Asegura que ReasonerAgent pase correctamente los model_hints basados en la configuración".
        # If hints are passed, we use them. If not, use priority list.
        
        candidates = model_hints if model_hints else self.priority_list
        
        for item in candidates:
            try:
                result = self._attempt_generation_with_provider(item, prompt)
                if result:
                    return result
            except (RetryableError, LLMError) as e:
                logger.warning(f"Provider failed with recoverable error: {e}. Falling back...")
                last_exception = e
                continue
            except Exception as e:
                logger.error(f"Provider failed with unexpected error: {e}. Falling back...", exc_info=True)
                last_exception = e
                continue

        raise AllModelsExhaustedException(
            message="All configured LLM providers failed to generate code.",
            original_exception=last_exception
        )

    def _attempt_generation_with_provider(self, item: Any, prompt: str) -> Any:
        """
        Attempts to generate code using a single provider configuration item.
        Returns the LlmResponse if successful, or raises exception if failed.
        """
        provider_enum = None
        model_name = None

        # Case 1: ModelId object (Expected)
        if hasattr(item, "provider") and hasattr(item, "name"):
            provider_enum = item.provider
            model_name = item.name
        # Case 2: Dictionary (Pydantic artifacts)
        elif isinstance(item, dict):
            provider_val = item.get("provider")
            model_name = item.get("name")
            
            if isinstance(provider_val, str):
                try:
                    provider_enum = LlmProviderType(provider_val.lower())
                except ValueError:
                    logger.warning(f"Invalid provider string in dict: {provider_val}")
                    return None
            elif isinstance(provider_val, LlmProviderType):
                provider_enum = provider_val

        # Case 3: Enum only (Legacy config)
        elif isinstance(item, LlmProviderType):
            provider_enum = item
            # We don't have 'default_model' passed easily here unless we pass it down.
            # But hints usually have names.
            model_name = "gpt-4-turbo" # Fallback default

        # Validation
        if not provider_enum:
            logger.warning(f"Skipping invalid priority item: {item} (Type: {type(item)})")
            return None

        # Find client
        client = self.clients.get(provider_enum)
        if not client:
            logger.warning(f"Client for provider '{provider_enum}' not found. Available: {list(self.clients.keys())}")
            return None
        
        target_model = model_name if model_name else "gpt-4-turbo"

        logger.info(f"Using Provider: {provider_enum.value} | Model: {target_model}")
        self._log_token_usage_estimate(prompt)
        
        # BRIDGE: Construct Domain Request
        request = LlmRequest(
            model=ModelId(provider=provider_enum, name=target_model),
            messages=(Message(role=MessageRole.USER, content=prompt),),
            generation=GenerationConfig(max_output_tokens=4000)
        )
        
        # BRIDGE: Async to Sync execution
        response = asyncio.run(client.generate(request))
        return response

    def _log_token_usage_estimate(self, text: str):
        # Basic character count / 4 estimation
        chars = len(text)
        est_tokens = chars // 4
        logger.debug(f"Estimated prompt tokens: {est_tokens}")
