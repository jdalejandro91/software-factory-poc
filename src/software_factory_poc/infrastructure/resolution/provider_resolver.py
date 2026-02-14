import os
from software_factory_poc.domain.value_objects.execution_mode import ExecutionMode

# Configuración
from software_factory_poc.infrastructure.configuration.app_config import AppConfig
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import \
    ScaffoldingAgentConfig

# Adaptadores
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.adapters.drivers.vcs.gitlab_mcp_adapter import GitlabMcpAdapter
from software_factory_poc.infrastructure.adapters.drivers.tracker.jira_rest_adapter import JiraRestAdapter
from software_factory_poc.infrastructure.adapters.drivers.research.confluence_rest_adapter import ConfluenceRestAdapter
from software_factory_poc.infrastructure.adapters.drivers.llms.llm_gateway_adapter import LlmGatewayAdapter

# Clientes HTTP Originales
from software_factory_poc.infrastructure.adapters.drivers.tracker.clients.jira_http_client import JiraHttpClient
from software_factory_poc.infrastructure.adapters.drivers.research.clients.confluence_http_client import \
    ConfluenceHttpClient
from software_factory_poc.infrastructure.adapters.drivers.llms.gateway.composite_gateway import CompositeLlmGateway

# Agentes
from software_factory_poc.application.core.agents.code_reviewer_agent import CodeReviewerAgent
from software_factory_poc.application.core.agents.scaffolder_agent import ScaffolderAgent


class McpConnectionManager:
    async def get_session(self, server_name: str): pass


class ProviderResolver:
    """Ensambla el sistema inyectando configuración validada."""

    def __init__(self, scaffolding_config: ScaffoldingAgentConfig, app_config: AppConfig):
        self.scaff_config = scaffolding_config
        self.app_config = app_config
        self.redactor = RedactionService()

    async def _build_drivers(self, mcp_manager: McpConnectionManager):
        # 1. Validaciones Pydantic Fall Fast
        self.app_config.tools.validate_jira_credentials()
        self.app_config.tools.validate_gitlab_credentials()
        self.app_config.tools.validate_confluence_credentials()

        # 2. VCS MCP
        session_vcs = await mcp_manager.get_session("mcp_server_gitlab")
        project_id = os.getenv("GITLAB_PROJECT_ID", "default_id")
        vcs_driver = GitlabMcpAdapter(session_vcs, project_id, self.redactor)

        jira_client = JiraHttpClient(
            base_url=self.app_config.tools.jira_base_url,
            auth_mode=self.app_config.tools.jira_auth_mode.value,
            user_email=self.app_config.tools.jira_user_email,
            api_token=api_t.get_secret_value() if api_t else None,
            bearer_token=bear_t.get_secret_value() if bear_t else None,
            webhook_secret=wh_secret.get_secret_value() if wh_secret else None
        )
        tracker_driver = JiraRestAdapter(jira_client, self.app_config.tools.jira_transition_in_review)

        # 4. Confluence REST
        conf_t = self.app_config.tools.confluence_api_token
        confluence_client = ConfluenceHttpClient(
            base_url=self.app_config.tools.confluence_base_url,
            user_email=self.app_config.tools.confluence_user_email,
            api_token=conf_t.get_secret_value() if conf_t else None
        )
        research_driver = ConfluenceRestAdapter(confluence_client)

        # 5. LLM Gateway
        llm = self.app_config.llm
        composite_gateway = CompositeLlmGateway(
            allowed_models=llm.allowed_models,
            openai_key=llm.openai_api_key.get_secret_value() if llm.openai_api_key else None,
            gemini_key=llm.gemini_api_key.get_secret_value() if llm.gemini_api_key else None,
            deepseek_key=llm.deepseek_api_key.get_secret_value() if llm.deepseek_api_key else None,
            anthropic_key=llm.anthropic_api_key.get_secret_value() if llm.anthropic_api_key else None
        )
        llm_driver = LlmGatewayAdapter(composite_gateway)
        # 3. Jira REST (🟢 INYECCIÓN REAL DESDE AppConfig)
        # Manejo seguro de SecretStr de Pydantic
        api_t = self.app_config.tools.jira_api_token
        bear_t = self.app_config.tools.jira_bearer_token
        wh_secret = self.app_config.tools.jira_webhook_secret


        return vcs_driver, tracker_driver, research_driver, llm_driver

    async def create_code_reviewer_agent(self, mcp_manager: McpConnectionManager) -> CodeReviewerAgent:
        vcs, tracker, research, llm = await self._build_drivers(mcp_manager)

        # El Modo es Configuración de Infraestructura, no una propiedad del Dominio (Task)
        mode = ExecutionMode(os.getenv("CODE_REVIEW_EXECUTION_MODE", "DETERMINISTIC").upper())

        return CodeReviewerAgent(
            vcs=vcs, tracker=tracker, research=research, llm=llm,
            mode=mode, default_arch_page_id=self.app_config.tools.architecture_doc_page_id
        )

    async def create_scaffolder_agent(self, mcp_manager: McpConnectionManager) -> ScaffolderAgent:
        vcs, tracker, research, llm = await self._build_drivers(mcp_manager)
        mode = ExecutionMode(os.getenv("SCAFFOLDING_EXECUTION_MODE", "DETERMINISTIC").upper())
        return ScaffolderAgent(vcs=vcs, tracker=tracker, research=research, llm=llm, mode=mode)



# import os
# from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
# from software_factory_poc.infrastructure.adapters.drivers.vcs.gitlab_mcp_adapter import GitlabMcpAdapter
# from software_factory_poc.infrastructure.adapters.drivers.tracker.jira_rest_adapter import JiraRestAdapter
# from software_factory_poc.infrastructure.adapters.drivers.research.confluence_rest_adapter import ConfluenceRestAdapter
# from software_factory_poc.infrastructure.adapters.drivers.llms.llm_gateway_adapter import LlmGatewayAdapter
# from software_factory_poc.application.core.agents.scaffolder_agent import ScaffolderAgent
# from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import CreateScaffoldingUseCase
#
# # Importamos los viejos clientes HTTP que ya tenías desarrollados
# from software_factory_poc.infrastructure.adapters.drivers.tracker.clients.jira_http_client import JiraHttpClient
# from software_factory_poc.infrastructure.adapters.drivers.research.clients.confluence_http_client import ConfluenceHttpClient
# from software_factory_poc.infrastructure.adapters.drivers.llms.gateway.composite_gateway import CompositeLlmGateway
#
#
# class McpConnectionManager:
#     """Gestiona conexiones stdio a los servidores MCP (Mocked for clarity)"""
#
#     async def get_session(self, server_name: str):
#         pass
#
#
# async def build_scaffolding_usecase(mcp_manager: McpConnectionManager) -> CreateScaffoldingUseCase:
#     redactor = RedactionService()
#
#     # 1. Driver VCS Vía MCP (El único migrado)
#     session_vcs = await mcp_manager.get_session("mcp_server_gitlab")
#     vcs_driver = GitlabMcpAdapter(session_vcs, os.getenv("GITLAB_PROJECT_ID"), redactor)
#
#     # 2. Driver Tracker (Vía REST Clásico original)
#     jira_client = JiraHttpClient()  # Inject env vars here
#     tracker_driver = JiraRestAdapter(jira_client)
#
#     # 3. Driver Research (Vía REST Clásico original)
#     confluence_client = ConfluenceHttpClient()  # Inject env vars here
#     research_driver = ConfluenceRestAdapter(confluence_client)
#
#     # 4. Driver LLM (Vía Gateway original)
#     composite_gateway = CompositeLlmGateway()  # Inject env vars here
#     llm_driver = LlmGatewayAdapter(composite_gateway)
#
#     # 5. Ensamblar Agente (Application Service)
#     agent = ScaffolderAgent(vcs=vcs_driver, tracker=tracker_driver, research=research_driver, llm=llm_driver)
#
#     # 6. Inyectar en el Caso de Uso
#     return CreateScaffoldingUseCase(agent=agent)
#

# from typing import cast, Optional
#
# from software_factory_poc.application.core.agents.code_reviewer.code_reviewer_agent import CodeReviewerAgent
# from software_factory_poc.application.core.agents.code_reviewer.config.code_reviewer_agent_config import (
#     CodeReviewerAgentConfig,
# )
# from software_factory_poc.application.ports.drivers.reasoner.ports.llm_gateway import LlmGateway
# from software_factory_poc.application.ports.drivers.reasoner.reasoner_agent import ReasonerAgent
# from software_factory_poc.application.ports.drivers.reporter.config.task_tracker_type import (
#     TaskTrackerType,
# )
# from software_factory_poc.application.ports.drivers.reporter.ports.task_tracker_gateway import TaskTrackerGateway
# from software_factory_poc.application.ports.drivers.reporter.reporter_agent import ReporterAgent
# from software_factory_poc.application.ports.drivers.research.ports.research_gateway import ResearchGateway
# from software_factory_poc.application.ports.drivers.research import ResearchAgent
# from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import (
#     ScaffoldingAgentConfig,
# )
# from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
# from software_factory_poc.application.ports.drivers.vcs import (
#     VcsProviderType,
# )
# from software_factory_poc.application.ports.drivers.vcs import VcsGateway
# from software_factory_poc.application.ports.drivers.vcs.vcs_agent import VcsAgent
# from software_factory_poc.application.usecases.code_review.perform_code_review_usecase import (
#     PerformCodeReviewUseCase,
# )
# from software_factory_poc.infrastructure.common.retry.retry_policy import RetryPolicy
# from software_factory_poc.infrastructure.configuration.app_config import AppConfig
# from software_factory_poc.infrastructure.configuration.main_settings import Settings  # Legacy or remove
# from software_factory_poc.infrastructure.observability.logging.correlation_id_context import (
#     CorrelationIdContext,
# )
# from software_factory_poc.infrastructure.adapters.drivers.llms.facade.llm_provider_factory import (
#     LlmProviderFactory,
# )
# from software_factory_poc.infrastructure.adapters.drivers.llms.gateway.composite_gateway import (
#     CompositeLlmGateway,
# )
# from software_factory_poc.infrastructure.adapters.drivers.research.research_provider_factory import ResearchProviderFactory
# from software_factory_poc.infrastructure.adapters.drivers.tracker.clients import (
#     JiraHttpClient,
# )
# from software_factory_poc.infrastructure.adapters.drivers.tracker.jira_provider_impl import (
#     JiraProviderImpl,
# )
# from software_factory_poc.infrastructure.adapters.drivers.vcs.clients.gitlab_http_client import (
#     GitLabHttpClient,
# )
# from software_factory_poc.infrastructure.adapters.drivers.vcs.gitlab_provider_impl import (
#     GitLabProviderImpl,
# )
# from software_factory_poc.infrastructure.adapters.drivers.vcs.mappers import (
#     GitLabPayloadBuilderService,
# )
# from software_factory_poc.infrastructure.adapters.drivers.vcs import (
#     GitLabBranchService,
# )
# from software_factory_poc.infrastructure.adapters.drivers.vcs.services.gitlab_commit_service import (
#     GitLabCommitService,
# )
# from software_factory_poc.infrastructure.adapters.drivers.vcs.services.gitlab_mr_service import (
#     GitLabMrService,
# )
#
#
# class ProviderResolver:
#     """
#     Factory responsible for resolving and instantiating the correct infrastructure adapters
#     based on the domain configuration.
#     """
#     def __init__(self, config: ScaffoldingAgentConfig, app_config:Optional[ AppConfig] = None):
#         self.config = config
#         self.app_config = app_config or AppConfig()
#         # Legacy settings for components not yet using AppConfig
#         self.settings = Settings()
#
#     def resolve_vcs(self) -> VcsGateway:
#         """
#         Resolves the configured VCS provider.
#         """
#         if self.config.vcs_provider == VcsProviderType.GITLAB:
#             http_client = GitLabHttpClient(self.settings)
#
#             # Instantiate Services
#             branch_service = GitLabBranchService(http_client)
#             payload_builder = GitLabPayloadBuilderService()
#             commit_service = GitLabCommitService(http_client, payload_builder)
#             mr_service = GitLabMrService(http_client)
#
#             return GitLabProviderImpl(
#                 branch_service=branch_service,
#                 commit_service=commit_service,
#                 mr_service=mr_service,
#                 http_client=http_client
#             )
#
#         elif self.config.vcs_provider == VcsProviderType.GITHUB:
#             raise NotImplementedError("GitHub adapter is not yet implemented.")
#
#         else:
#             raise ValueError(f"Unsupported VCS Provider: {self.config.vcs_provider}")
#
#     def resolve_tracker(self) -> TaskTrackerGateway:
#         """
#         Resolves the configured Tracker provider.
#         """
#         if self.config.tracker_provider == TaskTrackerType.JIRA:
#             http_client = JiraHttpClient(self.app_config.jira)
#             return JiraProviderImpl(http_client, self.app_config.jira)
#
#         elif self.config.tracker_provider == TaskTrackerType.AZURE_DEVOPS:
#             raise NotImplementedError("Azure DevOps adapter is not yet implemented.")
#
#         else:
#             raise ValueError(f"Unsupported Tracker Provider: {self.config.tracker_provider}")
#
#     def resolve_research(self) -> ResearchGateway:
#         """
#         Resolves the configured Research provider using ResearchProviderFactory.
#         """
#         return ResearchProviderFactory.build_research_gateway(self.app_config, self.config.research_provider)
#
#     def resolve_knowledge(self) -> ResearchGateway:
#         """
#         Deprecated: Use resolve_research. Kept for backward compatibility.
#         """
#         return self.resolve_research()
#
#     def resolve_llm_gateway(self) -> LlmGateway:
#         """
#         Resolves the configured LLM Composite Gateway.
#         """
#         # 1. Prepare dependencies for Factory
#         correlation = CorrelationIdContext()
#         # Default retry policy of 3 attempts with exponential backoff
#         retry = RetryPolicy(max_attempts=3)
#
#         # 2. Build Providers via Factory
#         # self.settings inherits from LlmSettings, so it works directly
#         clients = LlmProviderFactory.build_providers(self.settings, retry, correlation)
#
#         # 3. Return Composite Gateway
#         return CompositeLlmGateway(self.config, clients)
#
#     # ---------------------------------------------------------
#     # Domain Agent Factory Methods (Clean Code / DI Encapsulation)
#     # ---------------------------------------------------------
#
#     def create_reporter_agent(self) -> ReporterAgent:
#         tracker_gateway = cast(TaskTrackerGateway, self.resolve_tracker())
#         return ReporterAgent(
#             name="Reporter",
#             role="Communicator",
#             goal="Report status to Issue Tracker",
#             tracker=tracker_gateway
#         )
#
#     def create_vcs_agent(self) -> VcsAgent:
#         vcs_gateway = self.resolve_vcs()
#         return VcsAgent(
#             name="GitLabVcs",
#             role="Vcs",
#             goal="Manage GitLab branches/MRs",
#             gateway=vcs_gateway
#         )
#
#     def create_research_agent(self) -> ResearchAgent:
#         research_gateway = self.resolve_research()
#         return ResearchAgent(
#             name="Researcher",
#             role="Researcher",
#             goal="Gather context",
#             gateway=research_gateway,
#             config=self.config
#         )
#
#     def create_reasoner_agent(self) -> ReasonerAgent:
#         llm_gateway = self.resolve_llm_gateway()
#         return ReasonerAgent(
#             name="ArchitectAI",
#             role="Engineer",
#             goal="Generate scaffolding code",
#             llm_gateway=llm_gateway
#         )
#
#     def create_scaffolding_agent(self, model_name: str = "gpt-4-turbo", temperature: float = 0.2, max_tokens: int = 4000) -> ScaffoldingAgent:
#         orchestrator_config = self.config.model_copy(update={
#             "model_name": model_name,
#             "temperature": temperature,
#             "extra_params": {"max_tokens": max_tokens}
#         })
#         return ScaffoldingAgent(config=orchestrator_config)
#
#     def _resolve_code_reviewer_config(self) -> CodeReviewerAgentConfig:
#         """
#         Builds the configuration for Code Reviewer Agent.
#         """
#         # Parse Priority List
#         import json
#         priority_json = self.app_config.tools.code_review_llm_model_priority
#         try:
#              priority_list = json.loads(priority_json)
#              if not isinstance(priority_list, list):
#                  raise ValueError("Parsed JSON is not a list")
#         except Exception as e:
#              # Robust fallback
#              from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
#              logger = LoggerFactoryService.build_logger(__name__)
#              logger.warning(f"Failed to parse CODE_REVIEW_LLM_MODEL_PRIORITY: {priority_json}. Error: {e}. Defaulting to GPT-4 Turbo.")
#              priority_list = ["openai:gpt-4-turbo"]
#
#         return CodeReviewerAgentConfig(
#             api_key="",  # API Keys are handled by LlmGateway internally via Env/Settings
#             model=self.app_config.tools.code_review_model, # Legacy support
#             llm_model_priority=priority_list
#         )
#
#     def create_code_reviewer_agent(self) -> CodeReviewerAgent:
#         # Resolve dependencies
#         reporter = self.create_reporter_agent()
#         vcs = self.create_vcs_agent()
#         researcher = self.create_research_agent()
#         reasoner = self.create_reasoner_agent()
#
#         # Build Config
#         config = self._resolve_code_reviewer_config()
#
#         return CodeReviewerAgent(
#             config=config,
#             reporter=reporter,
#             vcs=vcs,
#             researcher=researcher,
#             reasoner=reasoner
#         )
#
#     def create_perform_code_review_usecase(self) -> PerformCodeReviewUseCase:
#         config = self._resolve_code_reviewer_config()
#         return PerformCodeReviewUseCase(config, self)
