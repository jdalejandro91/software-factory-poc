from typing import cast, Optional

from software_factory_poc.application.core.agents.reasoner.ports.llm_gateway import LlmGateway
from software_factory_poc.application.core.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.reporter.config.task_tracker_type import (
    TaskTrackerType,
)
from software_factory_poc.application.core.agents.reporter.ports.task_tracker_gateway import TaskTrackerGateway
from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.agents.research.ports.research_gateway import ResearchGateway
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.agents.vcs.config.vcs_provider_type import (
    VcsProviderType,
)
from software_factory_poc.application.core.agents.vcs.ports.vcs_gateway import VcsGateway
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
from software_factory_poc.infrastructure.configuration.app_config import AppConfig
from software_factory_poc.infrastructure.configuration.main_settings import Settings  # Legacy or remove
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
    CorrelationIdContext,
)
from software_factory_poc.infrastructure.providers.llms.facade.llm_provider_factory import (
    LlmProviderFactory,
)
from software_factory_poc.infrastructure.providers.llms.gateway.composite_gateway import (
    CompositeLlmGateway,
)
from software_factory_poc.infrastructure.providers.research.research_provider_factory import ResearchProviderFactory
from software_factory_poc.infrastructure.providers.tracker.clients.jira_http_client import (
    JiraHttpClient,
)
from software_factory_poc.infrastructure.providers.tracker.jira_provider_impl import (
    JiraProviderImpl,
)
from software_factory_poc.infrastructure.providers.vcs.clients.gitlab_http_client import (
    GitLabHttpClient,
)
from software_factory_poc.infrastructure.providers.vcs.gitlab_provider_impl import (
    GitLabProviderImpl,
)
from software_factory_poc.infrastructure.providers.vcs.mappers.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_branch_service import (
    GitLabBranchService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_commit_service import (
    GitLabCommitService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_mr_service import (
    GitLabMrService,
)


class ProviderResolver:
    """
    Factory responsible for resolving and instantiating the correct infrastructure adapters
    based on the domain configuration.
    """
    def __init__(self, config: ScaffoldingAgentConfig, app_config:Optional[ AppConfig] = None):
        self.config = config
        self.app_config = app_config or AppConfig()
        # Legacy settings for components not yet using AppConfig
        self.settings = Settings()

    def resolve_vcs(self) -> VcsGateway:
        """
        Resolves the configured VCS provider.
        """
        if self.config.vcs_provider == VcsProviderType.GITLAB:
            http_client = GitLabHttpClient(self.settings)
            
            # Instantiate Services
            branch_service = GitLabBranchService(http_client)
            payload_builder = GitLabPayloadBuilderService()
            commit_service = GitLabCommitService(http_client, payload_builder)
            mr_service = GitLabMrService(http_client)
            
            return GitLabProviderImpl(
                branch_service=branch_service,
                commit_service=commit_service,
                mr_service=mr_service,
                http_client=http_client
            )
            
        elif self.config.vcs_provider == VcsProviderType.GITHUB:
            raise NotImplementedError("GitHub adapter is not yet implemented.")
            
        else:
            raise ValueError(f"Unsupported VCS Provider: {self.config.vcs_provider}")

    def resolve_tracker(self) -> TaskTrackerGateway:
        """
        Resolves the configured Tracker provider.
        """
        if self.config.tracker_provider == TaskTrackerType.JIRA:
            http_client = JiraHttpClient(self.app_config.jira)
            return JiraProviderImpl(http_client, self.app_config.jira)
            
        elif self.config.tracker_provider == TaskTrackerType.AZURE_DEVOPS:
            raise NotImplementedError("Azure DevOps adapter is not yet implemented.")
            
        else:
            raise ValueError(f"Unsupported Tracker Provider: {self.config.tracker_provider}")

    def resolve_research(self) -> ResearchGateway:
        """
        Resolves the configured Research provider using ResearchProviderFactory.
        """
        return ResearchProviderFactory.build_research_gateway(self.app_config, self.config.research_provider)

    def resolve_knowledge(self) -> ResearchGateway:
        """
        Deprecated: Use resolve_research. Kept for backward compatibility.
        """
        return self.resolve_research()

    def resolve_llm_gateway(self) -> LlmGateway:
        """
        Resolves the configured LLM Composite Gateway.
        """
        # 1. Prepare dependencies for Factory
        correlation = CorrelationIdContext()
        # Default retry policy of 3 attempts with exponential backoff
        retry = RetryPolicy(max_attempts=3) 
        
        # 2. Build Providers via Factory
        # self.settings inherits from LlmSettings, so it works directly
        clients = LlmProviderFactory.build_providers(self.settings, retry, correlation)
        
        # 3. Return Composite Gateway
        return CompositeLlmGateway(self.config, clients)

    # ---------------------------------------------------------
    # Domain Agent Factory Methods (Clean Code / DI Encapsulation)
    # ---------------------------------------------------------

    def create_reporter_agent(self) -> ReporterAgent:
        tracker_gateway = cast(TaskTrackerGateway, self.resolve_tracker())
        return ReporterAgent(
            name="Reporter", 
            role="Communicator", 
            goal="Report status to Issue Tracker", 
            tracker=tracker_gateway
        )

    def create_vcs_agent(self) -> VcsAgent:
        vcs_gateway = self.resolve_vcs()
        return VcsAgent(
            name="GitLabVcs", 
            role="Vcs", 
            goal="Manage GitLab branches/MRs", 
            gateway=vcs_gateway
        )

    def create_research_agent(self) -> ResearchAgent:
        research_gateway = self.resolve_research()
        return ResearchAgent(
            name="Researcher", 
            role="Researcher", 
            goal="Gather context", 
            gateway=research_gateway,
            config=self.config
        )

    def create_reasoner_agent(self) -> ReasonerAgent:
        llm_gateway = self.resolve_llm_gateway()
        return ReasonerAgent(
            name="ArchitectAI",
            role="Engineer",
            goal="Generate scaffolding code",
            llm_gateway=llm_gateway
        )

    def create_scaffolding_agent(self, model_name: str = "gpt-4-turbo", temperature: float = 0.2, max_tokens: int = 4000) -> ScaffoldingAgent:
        orchestrator_config = self.config.model_copy(update={
            "model_name": model_name,
            "temperature": temperature,
            "extra_params": {"max_tokens": max_tokens}
        })
        return ScaffoldingAgent(config=orchestrator_config)
