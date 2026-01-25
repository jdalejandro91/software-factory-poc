from typing import cast

from software_factory_poc.application.core.domain.configuration.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_order import (
    ScaffoldingOrder,
)

# Domain Agents (Concrete Orchestrator and Capabilities)
from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.domain.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.domain.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.application.core.domain.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.domain.agents.knowledge.knowledge_agent import KnowledgeAgent
from software_factory_poc.application.core.domain.agents.reasoner.reasoner_agent import ReasonerAgent

# Domain Entity Config (Target for Orchestrator)
from software_factory_poc.application.core.domain.agents.scaffolding.scaffolding_agent_config import (
    ScaffoldingAgentConfig as ScaffoldingAgentEntityConfig,
)

# Gateways
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import (
    TaskTrackerGatewayPort,
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
            tracker_gateway = cast(TaskTrackerGatewayPort, self.resolver.resolve_tracker())
            vcs_gateway = self.resolver.resolve_vcs()
            knowledge_gateway = self.resolver.resolve_knowledge()
            llm_gateway = self.resolver.resolve_llm_gateway()
            
            # 2. Instantiate Concrete Domain Agents
            reporter = ReporterAgent(
                name="Reporter", 
                role="Communicator", 
                goal="Report status to Issue Tracker", 
                gateway=tracker_gateway
            )
            
            vcs = VcsAgent(
                name="VcsManager",
                role="VersionController",
                goal="Manage branches and MRs",
                gateway=vcs_gateway
            )
            
            researcher = ResearchAgent(
                name="Researcher",
                role="Analyst",
                goal="Investigate architectural standards",
                gateway=knowledge_gateway
            )
            
            knowledge = KnowledgeAgent(
                name="KnowledgeMan",
                role="Librarian",
                goal="Retrieve similar solutions",
                gateway=knowledge_gateway
            )
            
            # Pass model configuration to the Reasoning Agent
            model_to_use = self.entity_config.model_name or "gpt-4-turbo"
            reasoner = ReasonerAgent(
                name="ArchitectAI",
                role="Engineer",
                goal="Generate scaffolding code",
                llm_gateway=llm_gateway,
                model_name=model_to_use
            )
            
            # 3. Instantiate Domain Orchestrator (also an Agent)
            agent = ScaffoldingAgent(config=self.entity_config)
            
            # 4. Delegate to Orchestrator
            logger.info("Delegating to ScaffoldingAgent Orchestrator...")
            agent.execute_flow(
                request=request,
                reporter=reporter,
                vcs=vcs,
                researcher=researcher,
                reasoner=reasoner,
                knowledge=knowledge
            )

        except Exception as e:
            logger.critical(f"Critical error during scaffolding flow for {request.issue_key}: {e}", exc_info=True)
            
            # Best-effort failure reporting
            try:
                # We resolve tracker again or use local variable if available to ensure freshness or availability
                tracker_gateway = cast(TaskTrackerGatewayPort, self.resolver.resolve_tracker())
                emergency_reporter = ReporterAgent(
                    name="EmergencyReporter",
                    role="Communicator",
                    goal="Report critical failure",
                    gateway=tracker_gateway
                )
                emergency_reporter.announce_failure(request.issue_key, e)
            except Exception as report_error:
                logger.error(f"Failed to report failure to tracker: {report_error}")
            
            # Bubbling up the exception is crucial for the entrypoint (e.g. API) to handle http status or background task logic
            raise e
