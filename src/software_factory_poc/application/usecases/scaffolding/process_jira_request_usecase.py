from dataclasses import dataclass

from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.interfaces.knowledge_base import KnowledgeBasePort
from software_factory_poc.application.core.interfaces.llm_gateway import LLMGatewayPort
from software_factory_poc.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

@dataclass
class ProcessJiraRequestUseCase:
    agent: ScaffoldingAgent
    knowledge_base: KnowledgeBasePort
    llm_gateway: LLMGatewayPort
    knowledge_url: str = "http://confluence.corp/docs/carrito-de-compra-arch"

    def execute(self, request: ScaffoldingRequest) -> str:
        logger.info(f"Processing Jira Request for ticket {request.ticket_id}")
        
        # Execute Agent Mission
        generated_code = self.agent.execute_scaffolding_mission(
            request,
            self.knowledge_url,
            self.knowledge_base,
            self.llm_gateway
        )
        
        return generated_code
