from typing import cast, Any, Optional

from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import (
    ScaffoldingOrder,
)

# Domain Agents (Imports removed, handled by Resolver Factory)

# Domain Entity Config (Imports removed, handled by Resolver Factory)

# Gateways
# from software_factory_poc.application.core.agents.reporter.ports.task_tracker_gateway import (
#     TaskTrackerGateway,
# )
from software_factory_poc.application.core.agents.common.config.task_status import TaskStatus

from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver

logger = LoggerFactoryService.build_logger(__name__)


class CreateScaffoldingUseCase:
    """
    Application Service (UseCase) responsible for wiring the Clean Architecture components.
    It resolves infrastructure gateways, instantiates concrete Domain Agents, and hands control
    to the Domain Orchestrator.
    """
    def __init__(self, config: ScaffoldingAgentConfig, resolver: ProviderResolver):
        self.config = config
        self.resolver = resolver
        
        # Mapping App Config -> Domain Config
        # This mapping decouples the internal domain configuration format from the application/infrastructure config.
        model_name = config.llm_model_priority[0].name if config.llm_model_priority else "gpt-4-turbo"
        


    def execute(self, request: ScaffoldingOrder) -> None:
        logger.info(f"Starting scaffolding execution for issue: {request.issue_key}")
        reporter = None
        
        try:
            # 1. Instantiate Domain Agents
            reporter = self.resolver.create_reporter_agent()
            vcs = self.resolver.create_vcs_agent()
            researcher = self.resolver.create_research_agent()
            reasoner = self.resolver.create_reasoner_agent()
            
            orchestrator = self.resolver.create_scaffolding_agent(
                model_name=self.config.llm_model_priority[0].name if self.config.llm_model_priority else "gpt-4-turbo"
            )
            
            # 2. Delegate to Orchestrator
            logger.info("Delegating to ScaffoldingAgent Orchestrator...")
            orchestrator.execute_flow(
                request=request,
                reporter=reporter,
                vcs=vcs,
                researcher=researcher,
                reasoner=reasoner
            )

        except Exception as e:
            self._handle_critical_failure(request, e, reporter)

    def _handle_critical_failure(self, request: ScaffoldingOrder, e: Exception, reporter:Optional[ Any]) -> None:
        logger.critical(f"Critical error during scaffolding flow for {request.issue_key}: {e}", exc_info=True)
        try:
            # Use existing reporter if available, otherwise resolve a fresh one
            # The prompt requested removing "Manual instantiation", meaning ensure we use the Resolver.
            # self.resolver is injected, so calling create_reporter_agent is safe/clean.
            if not reporter:
                logger.warning("Reporter not initialized during failure, resolving emergency reporter...")
                reporter = self.resolver.create_reporter_agent()
                
            reporter.report_failure(request.issue_key, str(e))
            reporter.transition_task(request.issue_key, TaskStatus.TO_DO)
        except Exception as report_error:
            logger.error(f"Failed to report failure to tracker: {report_error}")
        
        # Propagate error so infrastructure knows
        raise e
