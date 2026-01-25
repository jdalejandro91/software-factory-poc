from pathlib import Path

from software_factory_poc.application.core.domain.configuration.knowledge_provider_type import (
    KnowledgeProviderType,
)
from software_factory_poc.application.core.domain.configuration.llm_provider_type import (
    LlmProviderType,
)
from software_factory_poc.application.core.domain.configuration.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.domain.configuration.task_tracker_type import (
    TaskTrackerType,
)
from software_factory_poc.application.core.domain.configuration.vcs_provider_type import (
    VcsProviderType,
)
from software_factory_poc.application.core.ports.gateways.llm_gateway import LlmGateway
from software_factory_poc.application.core.ports.gateways.knowledge_gateway import KnowledgeGateway
from software_factory_poc.application.core.ports.gateways.tracker_gateway import TrackerGateway
from software_factory_poc.application.core.ports.gateways.vcs_gateway import VcsGateway
from software_factory_poc.infrastructure.configuration.main_settings import Settings
from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
    CorrelationIdContext,
)
from software_factory_poc.infrastructure.providers.llms.facade.llm_provider_factory import (
    LlmProviderFactory,
)
from software_factory_poc.infrastructure.providers.knowledge.clients.confluence_http_client import (
    ConfluenceHttpClient,
)
from software_factory_poc.infrastructure.providers.knowledge.confluence_knowledge_adapter import (
    ConfluenceKnowledgeAdapter,
)
from software_factory_poc.infrastructure.providers.knowledge.filesystem_knowledge_adapter import (
    FileSystemKnowledgeAdapter,
)
from software_factory_poc.infrastructure.providers.llms.gateway.composite_gateway import (
    CompositeLlmGateway,
)
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
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_branch_service import (
    GitLabBranchService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_commit_service import (
    GitLabCommitService,
)
from software_factory_poc.infrastructure.providers.vcs.services.gitlab_mr_service import (
    GitLabMrService,
)
from software_factory_poc.infrastructure.providers.vcs.mappers.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)


class ProviderResolver:
    """
    Factory responsible for resolving and instantiating the correct infrastructure adapters
    based on the domain configuration.
    """
    def __init__(self, config: ScaffoldingAgentConfig, settings: Settings | None = None):
        self.config = config
        # Global settings (secrets, api keys, etc)
        self.settings = settings or Settings()

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

    def resolve_tracker(self) -> TrackerGateway:
        """
        Resolves the configured Tracker provider.
        """
        if self.config.tracker_provider == TaskTrackerType.JIRA:
            http_client = JiraHttpClient(self.settings)
            return JiraProviderImpl(http_client)
            
        elif self.config.tracker_provider == TaskTrackerType.AZURE_DEVOPS:
            raise NotImplementedError("Azure DevOps adapter is not yet implemented.")
            
        else:
            raise ValueError(f"Unsupported Tracker Provider: {self.config.tracker_provider}")

    def resolve_knowledge(self) -> KnowledgeGateway:
        """
        Resolves the configured Knowledge provider.
        """
        if self.config.knowledge_provider == KnowledgeProviderType.CONFLUENCE:
             http_client = ConfluenceHttpClient(self.settings)
             return ConfluenceKnowledgeAdapter(http_client)
             
        elif self.config.knowledge_provider == KnowledgeProviderType.FILE_SYSTEM:
             # Use a default assets path relative to project root or config
             # self.config.work_dir might be for output, let's look for assets/templates
             # Assuming running from root:
             assets_path = Path("assets") 
             return FileSystemKnowledgeAdapter(assets_path)
             
        else:
             raise ValueError(f"Unsupported Knowledge Provider: {self.config.knowledge_provider}")

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
