import asyncio
from typing import Any

from software_factory_poc.application.ports.drivers.common.config.llm_provider_type import (
    LlmProviderType,
)
from software_factory_poc.application.ports.drivers.common.exceptions import RetryableError
from software_factory_poc.application.ports.drivers.common.value_objects.model_id import ModelId
from software_factory_poc.application.ports.drivers.reasoner.exceptions.all_models_exhausted_error import (
    AllModelsExhaustedException,
)
from software_factory_poc.application.ports.drivers.reasoner.llm_request import LlmRequest
from software_factory_poc.application.ports.drivers.reasoner.ports.llm_gateway import LLMError, LlmGateway
from software_factory_poc.application.ports.drivers.reasoner.ports.llm_provider import LlmProvider
from software_factory_poc.application.ports.drivers.reasoner.value_objects.generation_config import GenerationConfig
from software_factory_poc.application.ports.drivers.reasoner.value_objects.message import Message
from software_factory_poc.application.ports.drivers.reasoner.value_objects.message_role import MessageRole
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


from software_factory_poc.application.ports.drivers.reasoner import OutputFormat

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
        last_exception = None

        candidates = []
        if model_hints:
            candidates.extend(model_hints)

        if self.priority_list:
            candidates.extend(self.priority_list)

        logger.info(f"Generation plan: Trying {len(candidates)} candidates (Hints + Priority List).")

        for item in candidates:
            try:
                result = self._attempt_generation_with_provider(item, prompt)
                if result:
                    return result
            except (RetryableError, LLMError) as e:
                logger.warning(f"Provider/Model failed with recoverable error: {e}. Falling back...")
                last_exception = e
                continue
            except Exception as e:
                logger.error(f"Provider/Model failed with unexpected error: {e}. Falling back...", exc_info=True)
                last_exception = e
                continue

        raise AllModelsExhaustedException(
            message="All configured LLM providers failed to generate code.",
            original_exception=last_exception
        )

    def _attempt_generation_with_provider(self, item: Any, prompt: str) -> Any:
        provider_enum = None
        model_name = None

        # Case 0: String Parsing
        if isinstance(item, str):
            if ":" in item:
                parts = item.split(":", 1)
                provider_str = parts[0].lower()
                model_name = parts[1]
                try:
                    provider_enum = LlmProviderType(provider_str)
                except ValueError:
                    logger.warning(f"Unknown provider in string '{provider_str}'.")
                    return None
            else:
                model_lower = item.lower()
                if "gemini" in model_lower:
                    provider_enum = LlmProviderType.GEMINI
                elif "claude" in model_lower:
                    provider_enum = LlmProviderType.ANTHROPIC
                elif "deepseek" in model_lower:
                    provider_enum = LlmProviderType.DEEPSEEK
                else:
                    provider_enum = LlmProviderType.OPENAI
                model_name = item

        # Case 1: ModelId object
        elif hasattr(item, "provider") and hasattr(item, "name"):
            provider_enum = item.provider
            model_name = item.name

        # Case 2: Dictionary
        elif isinstance(item, dict):
            provider_val = item.get("provider")
            model_name = item.get("name")
            if isinstance(provider_val, str):
                try:
                    provider_enum = LlmProviderType(provider_val.lower())
                except ValueError:
                    return None
            elif isinstance(provider_val, LlmProviderType):
                provider_enum = provider_val

        # Case 3: Enum only
        elif isinstance(item, LlmProviderType):
            provider_enum = item
            model_name = "gpt-4-turbo"

        if not provider_enum:
            return None

        client = self.clients.get(provider_enum)
        if not client:
            logger.debug(f"Client for provider '{provider_enum}' not found. Skipping.")
            return None

        target_model = model_name if model_name else "gpt-4-turbo"

        logger.info(f"Using Provider: {provider_enum.value} | Model: {target_model}")
        self._log_token_usage_estimate(prompt)

        request = LlmRequest(
            model=ModelId(provider=provider_enum, name=target_model),
            messages=(Message(role=MessageRole.USER, content=prompt),),
            generation=GenerationConfig(
                max_output_tokens=15000,
                format=OutputFormat.JSON
            )
        )

        response = asyncio.run(client.generate(request))
        return response

    def _log_token_usage_estimate(self, text: str):
        chars = len(text)
        est_tokens = chars // 4
        logger.debug(f"Estimated prompt tokens: {est_tokens}")