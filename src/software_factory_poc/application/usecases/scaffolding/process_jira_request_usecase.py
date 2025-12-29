from dataclasses import dataclass
from software_factory_poc.application.core.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.application.core.entities.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

@dataclass
class ProcessJiraRequestUseCase:
    agent: ScaffoldingAgent

    def execute(self, request: ScaffoldingRequest) -> str:
        logger.info(f"Processing Jira Request for ticket {request.issue_key}")
        return self.agent.execute_mission(request)
