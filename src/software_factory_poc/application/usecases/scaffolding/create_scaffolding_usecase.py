from typing import Any, Optional

from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import (
    ScaffoldingOrder,
)
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

    def execute(self, request: ScaffoldingOrder) -> None:
        """
        Executes the scaffolding process for a given issue key.
        """

        logger.info(f"Starting scaffolding execution for issue: {request.issue_key}")
        reporter = None

        try:
            # 1. Instantiate Domain Agents (Wiring)
            reporter = self.resolver.create_reporter_agent()
            vcs = self.resolver.create_vcs_agent()
            researcher = self.resolver.create_research_agent()
            reasoner = self.resolver.create_reasoner_agent()

            if self.config.llm_model_priority:
                priority_model = self.config.llm_model_priority[0].qualified_name
            else:
                priority_model = "openai:gpt-4-turbo"

            orchestrator = self.resolver.create_scaffolding_agent(
                model_name=priority_model
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
            # 3. Safety Net (Circuit Breaker)
            self._handle_initialization_failure(request, e, reporter)

    def _handle_initialization_failure(self, request: ScaffoldingOrder, e: Exception, reporter: Optional[Any]) -> None:
        """
        Handles failures that occur BEFORE the agent takes control or catastrophic crashes.
        """
        logger.critical(f"Critical wiring/system error for {request.issue_key}: {e}", exc_info=True)

        if reporter:
            try:
                reporter.report_failure(request.issue_key, f"System Error (Initialization): {str(e)}")
            except Exception as report_error:
                logger.error(f"Failed to report system failure to tracker: {report_error}")
        raise e