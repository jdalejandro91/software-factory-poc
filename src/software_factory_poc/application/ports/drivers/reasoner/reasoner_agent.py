from dataclasses import dataclass

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.ports.drivers.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.ports.drivers.common.value_objects.model_id import ModelId
from software_factory_poc.application.ports.drivers.reasoner.ports.llm_gateway import LlmGateway
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


@dataclass
class ReasonerAgent(BaseAgent):
    """
    Agent responsible for reasoning about the requirements and generating the scaffolding code.
    Cohesive implementation that handles Prompt Construction and Output Parsing internally.
    """
    llm_gateway: LlmGateway

    def reason(self, prompt: str, model_id: str | list[str]) -> str:
        """
        Sends the prompt to the LLM and returns the raw response.
        Stateless operation.
        """
        logger.info(f"Reasoning with models {model_id}...")

        hints = []
        
        # Normalize input to list
        models = model_id if isinstance(model_id, list) else [model_id]
        
        for mid in models:
            provider = LlmProviderType.OPENAI
            name = mid
            
            if ":" in mid:
                parts = mid.split(":", 1)
                provider_str = parts[0].lower()
                name = parts[1]
                try:
                    provider = LlmProviderType(provider_str)
                except ValueError:
                    logger.warning(f"Unknown provider '{provider_str}' in model_id '{mid}'. Defaults may apply.")
            
            hints.append(ModelId(provider=provider, name=name))

        response = self.llm_gateway.generate_code(
            prompt=prompt,
            context="",
            model_hints=hints
        )
        return response.content