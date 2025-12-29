from typing import List, Optional

from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.interfaces.llm_gateway import LLMGatewayPort, LLMError
from software_factory_poc.application.core.ports.knowledge_base_port import KnowledgeBasePort
from software_factory_poc.application.core.services.prompt_builder_service import PromptBuilderService
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

class MaxRetriesExceededError(Exception):
    pass

class ScaffoldingAgent:
    DEFAULT_KNOWLEDGE_URL = "https://confluence.corp.com/wiki/spaces/ARCH/pages/carrito-de-compra-architecture"

    def __init__(self, llm_gateway: LLMGatewayPort, knowledge_port: KnowledgeBasePort, model_priority_list: Optional[List[str]] = None):
        self.llm_gateway = llm_gateway
        self.knowledge_port = knowledge_port
        self.prompt_builder = PromptBuilderService()
        self.supported_models = model_priority_list or [
            "gpt-4-turbo",
            "gpt-4o",
            "deepseek-coder"
        ]
        self._knowledge_url = self.DEFAULT_KNOWLEDGE_URL

    def execute_mission(self, request: ScaffoldingRequest) -> str:
        logger.info(f"Starting mission for {request.issue_key}")
        knowledge = self.knowledge_port.get_knowledge(self._knowledge_url)
        prompt = self.prompt_builder.build_prompt(request.raw_instruction, knowledge)
        
        return self._try_generate_with_fallback(prompt)

    def _try_generate_with_fallback(self, prompt: str) -> str:
        for model in self.supported_models:
            try:
                logger.info(f"Attempting generation with model: {model}")
                return self.llm_gateway.generate_code(prompt, model)
            except LLMError as e:
                logger.warning(f"Model {model} failed: {e}")
                continue
        
        raise MaxRetriesExceededError("All supported models failed to generate code.")
