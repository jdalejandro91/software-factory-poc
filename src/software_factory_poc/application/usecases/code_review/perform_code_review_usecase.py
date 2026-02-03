from typing import Optional, Tuple, TYPE_CHECKING

from software_factory_poc.application.core.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.application.core.agents.code_reviewer.config.code_reviewer_agent_config import (
    CodeReviewerAgentConfig,
)
from software_factory_poc.application.core.agents.code_reviewer.value_objects.code_review_order import (
    CodeReviewOrder,
)
from software_factory_poc.application.core.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

# SOLUCIÓN CIRCULAR IMPORT: Importar solo para chequeo de tipos estático
if TYPE_CHECKING:
    from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver

logger = LoggerFactoryService.build_logger(__name__)


class PerformCodeReviewUseCase:
    """
    Use Case for performing a code review.
    Refactored to resolve dependencies and wire the agent internally.
    """

    # SOLUCIÓN: Usar "ProviderResolver" entre comillas (Forward Reference)
    def __init__(self, config: CodeReviewerAgentConfig, resolver: "ProviderResolver"):
        self.config = config
        self.resolver = resolver

    def execute(self, order: CodeReviewOrder) -> None:
        """
        Executes the code review process.
        Flow: Prepare -> Build -> Delegate.
        """
        self._log_execution_start(order)
        reporter = None

        try:
            # 1. Prepare Dependencies
            reporter, vcs, researcher, reasoner = self._prepare_collaborators()

            # 2. Build Orchestrator
            orchestrator = self._build_orchestrator(reporter, vcs, researcher, reasoner)

            # 3. Delegate execution
            self._delegate_execution(orchestrator, order)

        except Exception as e:
            # 4. Safety Net
            self._handle_critical_error(order, e, reporter)

    def _log_execution_start(self, order: CodeReviewOrder) -> None:
        logger.info(f"🚀 CODE REVIEW USECASE STARTED | Project ID: {order.project_id}")
        logger.info(f"Orchestrating code review for MR {order.mr_id} (Issue: {order.issue_key})")

    def _prepare_collaborators(self) -> Tuple[ReporterAgent, VcsAgent, ResearchAgent, ReasonerAgent]:
        """
        Resolves all necessary collaborator agents.
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
    ) -> CodeReviewerAgent:
        """
        Injects dependencies into the CodeReviewerAgent.
        """
        return CodeReviewerAgent(
            config=self.config,
            reporter=reporter,
            vcs=vcs,
            researcher=researcher,
            reasoner=reasoner
        )

    def _delegate_execution(self, orchestrator: CodeReviewerAgent, order: CodeReviewOrder) -> None:
        logger.info("Delegating control to CodeReviewerAgent...")
        orchestrator.execute_flow(order)

    def _handle_critical_error(self, order: CodeReviewOrder, e: Exception, reporter: Optional[ReporterAgent]) -> None:
        """
        Handles failures before Agent control or catastrophic crashes.
        """
        logger.critical(f"Critical wiring/system error for Code Review {order.issue_key}: {e}", exc_info=True)

        if reporter:
            try:
                reporter.report_failure(order.issue_key, f"System Error (Initialization): {str(e)}")
            except Exception as report_error:
                logger.error(f"Failed to report failure to tracker: {report_error}")
        
        raise e