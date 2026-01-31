from dataclasses import dataclass

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.common.config.llm_provider_type import LlmProviderType
from software_factory_poc.application.core.agents.common.value_objects.model_id import ModelId
from software_factory_poc.application.core.agents.reasoner.ports.llm_gateway import LlmGateway
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)

@dataclass
class ReasonerAgent(BaseAgent):
    """
    Agent responsible for reasoning about the requirements and generating the scaffolding code.
    Cohesive implementation that handles Prompt Construction and Output Parsing internally.
    """
    llm_gateway: LlmGateway

    def reason(self, prompt: str, model_id: str) -> str:
        """
        Sends the prompt to the LLM and returns the raw response.
        Stateless operation.
        """
        logger.info(f"Reasoning with model {model_id}...")
        
        # Adapt to Gateway Interface
        # Gateway expects (prompt, context, hints)
        # We assume 'prompt' here is the full accumulated prompt/context combo.
        # Assuming OPENAI if vague string, but ModelId requires explicit provider.
        # Since we only get a name, we default to OPENAI.
        hints = [ModelId(provider=LlmProviderType.OPENAI, name=model_id)]
        
        response = self.llm_gateway.generate_code(
            prompt=prompt, 
            context="", 
            model_hints=hints
        )
        return response.content
