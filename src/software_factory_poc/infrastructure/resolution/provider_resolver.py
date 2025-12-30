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
from software_factory_poc.infrastructure.configuration.tool_settings import ToolSettings
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
from software_factory_poc.infrastructure.providers.vcs.mappers.gitlab_payload_builder_service import (
    GitLabPayloadBuilderService,
)


class ProviderResolver:
    """
    Factory responsible for resolving and instantiating the correct infrastructure adapters
    based on the domain configuration.
    """
    def __init__(self, config: ScaffoldingAgentConfig, settings: ToolSettings | None = None):
        self.config = config
        # Fallback only if needed, ideally injected
        self.settings = settings or ToolSettings() 

    def resolve_vcs(self) -> VcsGateway:
        """
        Resolves the configured VCS provider.
        """
        if self.config.vcs_provider == VcsProviderType.GITLAB:
            http_client = GitLabHttpClient(self.settings)
            payload_builder = GitLabPayloadBuilderService()
            return GitLabProviderImpl(http_client, payload_builder)
            
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
        clients: dict[LlmProviderType, LlmGateway] = {}
        
        # 1. OpenAI (Placeholder for future wiring)
        if self.settings and hasattr(self.settings, 'openai_api_key') and self.settings.openai_api_key:
             # Ideally we use Settings injection here properly
             
             # Note: We likely need a bridge or adapter if OpenAiProviderImpl implements old LlmProvider interface
             # and we need LlmGateway. P8 plan mentioned this.
             # Assuming 'LlmGatewayAdapter' exists to bridge legacy Provider -> New Port
             pass
             
        return CompositeLlmGateway(self.config, clients)
