import asyncio

from software_factory_poc.application.core.entities.llm_request import LlmRequest
from software_factory_poc.application.core.interfaces.llm_gateway import LLMError, LLMGatewayPort
from software_factory_poc.application.core.value_objects.generation_config import GenerationConfig
from software_factory_poc.application.core.value_objects.message import Message
from software_factory_poc.application.core.value_objects.message_role import MessageRole
from software_factory_poc.application.core.value_objects.model_id import ModelId
from software_factory_poc.application.core.value_objects.provider_name import ProviderName
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger
from software_factory_poc.infrastructure.providers.llms.facade.llm_bridge import LlmBridge

logger = build_logger(__name__)


class LlmGatewayAdapter(LLMGatewayPort):
    def __init__(self, bridge: LlmBridge):
        self.bridge = bridge

    def generate_code(self, prompt: str, model: str) -> str:
        # Detect provider based on model string
        model_lower = model.lower()
        if "gpt" in model_lower:
            provider = ProviderName.OPENAI
        elif "deepseek" in model_lower:
            provider = ProviderName.DEEPSEEK
        elif "gemini" in model_lower:
            provider = ProviderName.GEMINI
        elif "claude" in model_lower:
            provider = ProviderName.ANTHROPIC
        else:
            provider = ProviderName.OPENAI  # Default

        # Construct the formal LLM Request object
        # Heuristic: Enable JSON mode if "JSON" matches in prompt (case insensitive)
        json_mode = "json" in prompt.lower()
        
        request = LlmRequest(
            model=ModelId(provider=provider, name=model),
            messages=(Message(role=MessageRole.USER, content=prompt),),
            generation=GenerationConfig(temperature=0.0, json_mode=json_mode)
        )
        
        try:
            # Execute async generation through the bridge
            result = asyncio.run(self.bridge.gateway.generate(request))
            return result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            logger.error(f"LLM Adapter failed: {e}")
            raise LLMError(f"Failed to generate code: {e}") from e
