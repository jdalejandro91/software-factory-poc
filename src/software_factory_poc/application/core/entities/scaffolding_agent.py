from dataclasses import dataclass, field
from typing import List, Any
import logging

from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.interfaces.llm_gateway import LLMGatewayPort, LLMError
from software_factory_poc.application.core.interfaces.knowledge_base import KnowledgeBasePort

logger = logging.getLogger(__name__)

class MaxRetriesExceededError(Exception):
    """Raised when all models fail to generate code."""
    pass

@dataclass
class ScaffoldingAgent:
    supported_models: List[str]
    tools: List[Any] = field(default_factory=list)

    def execute_scaffolding_mission(
        self, 
        request: ScaffoldingRequest, 
        knowledge_url: str, 
        knowledge_port: KnowledgeBasePort,
        llm_gateway: LLMGatewayPort
    ) -> str:
        # 1. Retrieve Knowledge
        try:
            guidelines = knowledge_port.get_architecture_guidelines(knowledge_url)
        except Exception as e:
            logger.warning(f"Failed to retrieve guidelines from {knowledge_url}: {e}")
            guidelines = "Follow standard clean architecture principles."

        # 2. Build Prompt
        system_role = "You are an expert Software Architect and Engineer. Generate the requested scaffolding structure."
        final_prompt = (
            f"{system_role}\n\n"
            f"ARCHITECTURE GUIDELINES:\n{guidelines}\n\n"
            f"USER REQUEST:\n{request.raw_instruction}\n\n"
            f"CONTEXT:\nTicket: {request.ticket_id}\nRequester: {request.requester}"
        )

        # 3. Chain of Fallback
        last_error = None
        for model in self.supported_models:
            try:
                logger.info(f"Attempting generation with model: {model}")
                result = llm_gateway.generate_code(final_prompt, model)
                logger.info(f"Success with model: {model}")
                return result
            except LLMError as e:
                logger.error(f"Model {model} failed: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Model {model} failed with unexpected error: {e}")
                last_error = e
                continue
        
        # 4. Failure
        raise MaxRetriesExceededError(f"All models failed. Last error: {last_error}")
