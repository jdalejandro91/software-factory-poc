from typing import cast

from software_factory_poc.application.core.domain.configuration.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)

# New Orchestrator
from software_factory_poc.application.core.domain.agents.orchestrators.scaffolding_agent import ScaffoldingAgent

# Config Entity
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_agent_config import (
    ScaffoldingAgentConfig as ScaffoldingAgentEntityConfig,
)

# Gateways
from software_factory_poc.application.core.ports.gateways.task_tracker_gateway_port import (
    TaskTrackerGatewayPort,
)

# New Adapters
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
    Orchestrator for the "Software Factory" scaffolding flow.
    Wires the infrastructure adapters to the Domain Orchestrator.
    """
    def __init__(self, config: ScaffoldingAgentConfig, resolver: ProviderResolver):
        self.config = config
        self.resolver = resolver
        
        # Map App Config to Domain Entity Config
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
            # 1. Resolver Gateways & Instantiate Adapters
            tracker_gateway = cast(TaskTrackerGatewayPort, self.resolver.resolve_tracker())
            reporter = ReporterAgentAdapter(tracker_gateway)
            
            vcs_gateway = self.resolver.resolve_vcs()
            vcs = VcsAgentAdapter(vcs_gateway)
            
            knowledge_gateway = self.resolver.resolve_knowledge()
            # Research uses KnowledgeGateway + Search Filters
            researcher = ResearchAgentAdapter(knowledge_gateway)
            # KnowledgeAgent also uses KnowledgeGateway (for retrieval patterns)
            knowledge = KnowledgeAgentAdapter(knowledge_gateway)
            
            llm_gateway = self.resolver.resolve_llm_gateway()
            # Pass model from config
            model_to_use = self.entity_config.model_name or "gpt-4-turbo"
            reasoner = ReasoningAgentAdapter(llm_gateway, model_name=model_to_use)
            
            # 2. Instantiate Orchestrator
            agent = ScaffoldingAgent(config=self.entity_config)
            
            # 3. Execute Flow
            agent.execute_flow(
                request=request,
                reporter=reporter,
                vcs=vcs,
                researcher=researcher,
                reasoner=reasoner,
                knowledge=knowledge
            )

        except Exception as e:
            logger.critical(f"Critical error during scaffolding initialization/execution for {request.issue_key}: {e}", exc_info=True)
            # Try to report failure if possible (best effort)
            try:
                tracker_gateway = cast(TaskTrackerGatewayPort, self.resolver.resolve_tracker())
                ReporterAgentAdapter(tracker_gateway).announce_failure(request.issue_key, e)
            except Exception:
                pass
            raise e
