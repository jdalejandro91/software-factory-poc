from typing import Optional, Tuple, TYPE_CHECKING

from software_factory_poc.application.ports.drivers.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.ports.drivers.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.ports.drivers.research import ResearchAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.ports.drivers.vcs.vcs_agent import VcsAgent
from software_factory_poc.domain.entities.task import Task
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

# SOLUCIÓN CIRCULAR IMPORT
if TYPE_CHECKING:
    from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver

logger = LoggerFactoryService.build_logger(__name__)


class CreateScaffoldingUseCase:
    """
    Application Service (UseCase) responsible for wiring the Clean Architecture components.
    Refactored for readability and granular execution steps.
    """

    # SOLUCIÓN: Usar "ProviderResolver" entre comillas
    def __init__(self, config: ScaffoldingAgentConfig, resolver: "ProviderResolver"):
        self.config = config
        self.resolver = resolver

    def execute(self, task: Task) -> None:
        """
        Executes the scaffolding process for a given domain Task.
        The flow is linear: Log -> Prepare -> Build -> Execute.
        """
        self._log_execution_start(task)
        reporter = None

        try:
            # 1. Prepare Dependencies
            reporter, vcs, researcher, reasoner = self._prepare_collaborators()

            # 2. Build Orchestrator
            orchestrator = self._build_orchestrator(reporter, vcs, researcher, reasoner)

            # 3. Delegate to Orchestrator
            self._delegate_execution(orchestrator, task)

        except Exception as e:
            # 4. Safety Net (Circuit Breaker)
            self._handle_critical_error(task, e, reporter)

    def _log_execution_start(self, task: Task) -> None:
        # Task Config is valid at this point (mapper ensures it)
        service_name = task.description.config.get("parameters", {}).get("service_name", "Unknown")
        logger.info(f"🚀 USECASE STARTED | Project Target: '{service_name}'")
        logger.info(f"Starting scaffolding execution for issue: {task.key}")

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

    def _delegate_execution(self, orchestrator: ScaffoldingAgent, task: Task) -> None:
        """
        Hands over control to the domain agent.
        """
        logger.info("Delegating control to ScaffoldingAgent Orchestrator...")
        orchestrator.execute_flow(task)

    def _handle_critical_error(self, task: Task, e: Exception, reporter: Optional[ReporterAgent]) -> None:
        """
        Handles failures that occur BEFORE the agent takes control or catastrophic crashes.
        """
        logger.critical(f"Critical wiring/system error for {task.key}: {e}", exc_info=True)

        if reporter:
            try:
                reporter.report_failure(task.key, f"System Error (Initialization): {str(e)}")
            except Exception as report_error:
                logger.error(f"Failed to report system failure to tracker: {report_error}")
        
        # Re-raise to ensure API controller returns 500
        raise e