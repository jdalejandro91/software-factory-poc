from typing import cast

from software_factory_poc.application.core.domain.agents.scaffolding.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_order import (
    ScaffoldingOrder,
)

# Domain Agents (Concrete Orchestrator and Capabilities)
from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.domain.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.domain.agents.vcs.ports.vcs_gateway import VcsGateway
from software_factory_poc.application.core.domain.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.domain.agents.reasoner.reasoner_agent import ReasonerAgent

# Domain Entity Config (Target for Orchestrator)
from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_agent_config import (
    ScaffoldingAgentConfig as ScaffoldingAgentEntityConfig,
)

# Gateways
from software_factory_poc.application.core.domain.agents.reporter.ports.task_tracker_gateway import (
    TaskTrackerGateway,
)
from software_factory_poc.application.core.domain.agents.common.config.task_status import TaskStatus

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
        
        self.entity_config = ScaffoldingAgentEntityConfig(
            model_name=model_name,
            temperature=0.0,
            extra_params={
                "architecture_page_id": config.architecture_page_id
            }
        )

    def execute(self, request: ScaffoldingOrder) -> None:
        logger.info(f"Starting scaffolding execution for issue: {request.issue_key}")
        
        try:
            # 1. Resolve Infrastructure Gateways
            tracker_gateway = cast(TaskTrackerGateway, self.resolver.resolve_tracker())
            vcs_gateway = self.resolver.resolve_vcs()
            # knowledge_gateway removed, now part of research (or directly resolved as research_gateway)
            research_gateway = self.resolver.resolve_research()
            llm_gateway = self.resolver.resolve_llm_gateway()
            
            # 2. Instantiate Concrete Domain Agents
            reporter = ReporterAgent(
                name="Reporter", 
                role="Communicator", 
                goal="Report status to Issue Tracker", 
                gateway=tracker_gateway
            )
            
            vcs = VcsAgent(
                name="GitLabVcs", 
                role="Vcs", 
                goal="Manage GitLab branches/MRs", 
                gateway=vcs_gateway
            )
            
            researcher = ResearchAgent(
                name="Researcher", 
                role="Researcher", 
                goal="Gather context", 
                gateway=research_gateway
            )
            # Wait, I need to check the file first.
            # Assuming check_file reveals it expects llm_gateway or gateway.
            # Let's see the view_file output first.
            
            # Knowledge Agent is removed/merged into Research
            
            reasoner = ReasonerAgent(
                name="ArchitectAI",
                role="Engineer",
                goal="Generate scaffolding code",
                llm_gateway=llm_gateway
            )
            
            # 3. Instantiate Domain Orchestrator (also an Agent)
            # Config holds model info now
            orchestrator_config = ScaffoldingAgentEntityConfig(
                model_name="gpt-4-turbo", 
                temperature=0.2,
                extra_params={"max_tokens": 4000}
            )
            orchestrator = ScaffoldingAgent(config=orchestrator_config)
            
            # 4. Delegate to Orchestrator
            logger.info("Delegating to ScaffoldingAgent Orchestrator...")
            orchestrator.execute_flow(
                request=request,
                reporter=reporter,
                vcs=vcs,
                researcher=researcher,
                reasoner=reasoner
            )

        except Exception as e:
            logger.critical(f"Critical error during scaffolding flow for {request.issue_key}: {e}", exc_info=True)
            
            # Best-effort failure reporting
            try:
                # We resolve tracker again or use local variable if available to ensure freshness or availability
                tracker_gateway = cast(TaskTrackerGateway, self.resolver.resolve_tracker())
                emergency_reporter = ReporterAgent(
                    name="EmergencyReporter",
                    role="Communicator",
                    goal="Report critical failure",
                    gateway=tracker_gateway
                )
                emergency_reporter.report_failure(request.issue_key, str(e))
                emergency_reporter.transition_task(request.issue_key, TaskStatus.TO_DO)
            except Exception as report_error:
                logger.error(f"Failed to report failure to tracker: {report_error}")
            
            # Bubbling up the exception is crucial for the entrypoint (e.g. API) to handle http status or background task logic
            raise e
