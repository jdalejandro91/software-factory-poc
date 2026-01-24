from typing import cast

from software_factory_poc.application.core.domain.configuration.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)

# Domain Orchestrator
from software_factory_poc.application.core.domain.agents.orchestrators.scaffolding_agent import ScaffoldingAgent

# Domain Entity Config (Target for Orchestrator)
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_agent_config import (
    ScaffoldingAgentConfig as ScaffoldingAgentEntityConfig,
)

# Gateways
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import (
    TaskTrackerGatewayPort,
)

# Interface Adapters
from software_factory_poc.application.usecases.scaffolding.adapters.agent_adapters import (
    ReasoningAgentAdapter,
    ResearchAgentAdapter,
    VcsAgentAdapter,
    ReporterAgentAdapter,
    KnowledgeAgentAdapter
)

from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver

logger = LoggerFactoryService.build_logger(__name__)


class CreateScaffoldingUseCase:
    """
    Application Service (UseCase) responsible for wiring the Clean Architecture components.
    It resolves infrastructure gateways, adapts them to domain interfaces, and hands control
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

    def execute(self, request: ScaffoldingRequest) -> None:
        logger.info(f"Starting scaffolding execution for issue: {request.issue_key}")
        
        try:
            # 1. Resolve Infrastructure Gateways
            tracker_gateway = cast(TaskTrackerGatewayPort, self.resolver.resolve_tracker())
            vcs_gateway = self.resolver.resolve_vcs()
            knowledge_gateway = self.resolver.resolve_knowledge()
            llm_gateway = self.resolver.resolve_llm_gateway()
            
            # 2. Instantiate Interface Adapters (Injecting Gateways)
            reporter = ReporterAgentAdapter(tracker_gateway)
            vcs = VcsAgentAdapter(vcs_gateway)
            researcher = ResearchAgentAdapter(knowledge_gateway)
            knowledge = KnowledgeAgentAdapter(knowledge_gateway)
            
            # Pass model configuration to the Reasoning Adapter
            model_to_use = self.entity_config.model_name or "gpt-4-turbo"
            reasoner = ReasoningAgentAdapter(llm_gateway, model_name=model_to_use)
            
            # 3. Instantiate Domain Orchestrator
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
                emergency_reporter = ReporterAgentAdapter(tracker_gateway)
                emergency_reporter.announce_failure(request.issue_key, e)
            except Exception as report_error:
                logger.error(f"Failed to report failure to tracker: {report_error}")
            
            # Bubbling up the exception is crucial for the entrypoint (e.g. API) to handle http status or background task logic
            raise e
