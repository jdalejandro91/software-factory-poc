from typing import Any, Optional, Tuple

from software_factory_poc.application.core.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.agents.scaffolding.value_objects.scaffolding_order import (
    ScaffoldingOrder,
)
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver

logger = LoggerFactoryService.build_logger(__name__)


class CreateScaffoldingUseCase:
    """
    Application Service (UseCase) responsible for wiring the Clean Architecture components.
    Refactored for readability and granular execution steps.
    """

    def __init__(self, config: ScaffoldingAgentConfig, resolver: ProviderResolver):
        self.config = config
        self.resolver = resolver

    def execute(self, request: ScaffoldingOrder) -> None:
        """
        Executes the scaffolding process for a given issue key.
        The flow is linear: Log -> Prepare -> Build -> Execute.
        """
        self._log_execution_start(request)
        reporter = None

        try:
            # 1. Prepare Dependencies
            reporter, vcs, researcher, reasoner = self._prepare_collaborators()

            # 2. Build Orchestrator
            orchestrator = self._build_orchestrator(reporter, vcs, researcher, reasoner)

            # 3. Delegate to Orchestrator
            self._delegate_execution(orchestrator, request)

        except Exception as e:
            # 4. Safety Net (Circuit Breaker)
            self._handle_critical_error(request, e, reporter)

    def _log_execution_start(self, request: ScaffoldingOrder) -> None:
        service_name = request.extra_params.get("service_name", "Unknown") if request.extra_params else "Unknown"
        logger.info(f"🚀 USECASE STARTED | Project Target: '{service_name}'")
        logger.info(f"Starting scaffolding execution for issue: {request.issue_key}")

    def _prepare_collaborators(self) -> Tuple[ReporterAgent, VcsAgent, ResearchAgent, ReasonerAgent]:
        """
        Resolves and instantiates all the collaborator agents required by the orchestrator.
        """
        logger.debug("Resolving collaborator agents...")
        reporter = self.resolver.create_reporter_agent()
        vcs = self.resolver.create_vcs_agent()
        researcher = self.resolver.create_research_agent()
        reasoner = self.resolver.create_reasoner_agent()
        return reporter, vcs, researcher, reasoner

    def _build_orchestrator(
        self,
        reporter: ReporterAgent,
        vcs: VcsAgent,
        researcher: ResearchAgent,
        reasoner: ReasonerAgent
    ) -> ScaffoldingAgent:
        """
        Injects dependencies into the ScaffoldingAgent.
        """
        return ScaffoldingAgent(
            config=self.config,
            reporter=reporter,
            vcs=vcs,
            researcher=researcher,
            reasoner=reasoner
        )

    def _delegate_execution(self, orchestrator: ScaffoldingAgent, request: ScaffoldingOrder) -> None:
        """
        Hands over control to the domain agent.
        """
        logger.info("Delegating control to ScaffoldingAgent Orchestrator...")
        orchestrator.execute_flow(request)

    def _handle_critical_error(self, request: ScaffoldingOrder, e: Exception, reporter: Optional[ReporterAgent]) -> None:
        """
        Handles failures that occur BEFORE the agent takes control or catastrophic crashes.
        """
        logger.critical(f"Critical wiring/system error for {request.issue_key}: {e}", exc_info=True)

        if reporter:
            try:
                reporter.report_failure(request.issue_key, f"System Error (Initialization): {str(e)}")
            except Exception as report_error:
                logger.error(f"Failed to report system failure to tracker: {report_error}")
        
        # Re-raise to ensure API controller returns 500
        raise e