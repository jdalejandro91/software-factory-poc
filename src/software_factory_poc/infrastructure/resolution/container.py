import os
from software_factory_poc.domain.value_objects.execution_mode import ExecutionMode

# 1. Configuración Centralizada Original
from software_factory_poc.infrastructure.configuration.app_config import AppConfig

# 2. Adaptadores
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.adapters.drivers.vcs.gitlab_mcp_adapter import GitlabMcpAdapter
from software_factory_poc.infrastructure.adapters.drivers.tracker.jira_rest_adapter import JiraRestAdapter
from software_factory_poc.infrastructure.adapters.drivers.research.confluence_rest_adapter import ConfluenceRestAdapter
from software_factory_poc.infrastructure.adapters.drivers.llms.llm_gateway_adapter import LlmGatewayAdapter

# 3. Clientes REST Base Originales
from software_factory_poc.infrastructure.adapters.drivers.tracker.clients.jira_http_client import JiraHttpClient
from software_factory_poc.infrastructure.adapters.drivers.research.clients.confluence_http_client import \
    ConfluenceHttpClient
from software_factory_poc.infrastructure.adapters.drivers.llms.gateway.composite_gateway import CompositeLlmGateway

# 4. Mappers ADF Originales
from software_factory_poc.infrastructure.adapters.drivers.tracker.mappers.jira_description_mapper import \
    JiraDescriptionMapper
from software_factory_poc.infrastructure.adapters.drivers.tracker.mappers.jira_panel_factory import JiraPanelFactory

# 5. Agentes y Casos de Uso
from software_factory_poc.application.core.agents.scaffolder_agent import ScaffolderAgent
from software_factory_poc.application.core.agents.code_reviewer_agent import CodeReviewerAgent
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import CreateScaffoldingUseCase
from software_factory_poc.application.usecases.code_review.perform_code_review_usecase import PerformCodeReviewUseCase


class McpConnectionManager:
    """Gestiona conexiones stdio a los servidores MCP"""

    async def get_session(self, server_name: str): pass


async def _build_drivers(mcp_manager: McpConnectionManager, config: AppConfig):
    """Factory interno que ensambla la infraestructura inyectando la Configuración Centralizada."""
    redactor = RedactionService()

    # Validaciones Tempranas (Fail Fast) de credenciales de AppConfig
    config.tools.validate_jira_credentials()
    config.tools.validate_gitlab_credentials()
    config.tools.validate_confluence_credentials()

    # 1. Driver VCS (MCP GitLab)
    session_vcs = await mcp_manager.get_session("mcp_server_gitlab")
    # Utilizamos variables de entorno por defecto para no comprometer el código
    project_id = os.getenv("GITLAB_PROJECT_ID", "default_project")
    vcs_driver = GitlabMcpAdapter(session_vcs, project_id, redactor)

    # 2. Driver Tracker (REST Jira + Mappers ADF)
    # 🟢 AQUI INYECTAMOS REALMENTE LOS SECRETOS PROVENIENTES DE TU APPCONFIG 🟢
    jira_client = JiraHttpClient(
        base_url=config.jira.base_url,
        auth_mode=config.jira.auth_mode.value,
        user_email=config.jira.user_email,
        # Desenvolvemos el SecretStr si existe (Pydantic v2)
        api_token=config.jira.api_token.get_secret_value() if config.jira.api_token else None,
        bearer_token=config.jira.bearer_token.get_secret_value() if config.jira.bearer_token else None,
        webhook_secret=config.jira.webhook_secret.get_secret_value() if config.jira.webhook_secret else None
    )
    tracker_driver = JiraRestAdapter(
        jira_client,
        JiraDescriptionMapper(),
        JiraPanelFactory(),
        config.jira.transition_in_review
    )

    # 3. Driver Research (REST Confluence)
    confluence_client = ConfluenceHttpClient(
        base_url=config.confluence.base_url,
        user_email=config.confluence.user_email,
        api_token=config.confluence.api_token.get_secret_value() if config.confluence.api_token else None
    )
    research_driver = ConfluenceRestAdapter(confluence_client)

    # 4. Driver LLM (Gateway Composite)
    composite_gateway = CompositeLlmGateway(
        allowed_models=config.llm.allowed_models,
        openai_key=config.llm.openai_api_key.get_secret_value() if config.llm.openai_api_key else None,
        gemini_key=config.llm.gemini_api_key.get_secret_value() if config.llm.gemini_api_key else None,
        deepseek_key=config.llm.deepseek_api_key.get_secret_value() if config.llm.deepseek_api_key else None,
        anthropic_key=config.llm.anthropic_api_key.get_secret_value() if config.llm.anthropic_api_key else None
    )
    llm_driver = LlmGatewayAdapter(composite_gateway)

    return vcs_driver, tracker_driver, research_driver, llm_driver


# === BUILDERS PÚBLICOS EXPORTADOS ===

async def build_scaffolding_usecase(mcp_manager: McpConnectionManager) -> CreateScaffoldingUseCase:
    config = AppConfig()
    vcs, tracker, research, llm = await _build_drivers(mcp_manager, config)

    # 🟢 INYECCIÓN DEL MODO DEL AGENTE
    mode_str = os.getenv("SCAFFOLDING_EXECUTION_MODE", "DETERMINISTIC").upper()
    mode = ExecutionMode(mode_str)

    agent = ScaffolderAgent(vcs=vcs, tracker=tracker, research=research, llm=llm, mode=mode)
    return CreateScaffoldingUseCase(agent=agent, tracker=tracker)


async def build_code_review_usecase(mcp_manager: McpConnectionManager) -> PerformCodeReviewUseCase:
    config = AppConfig()
    vcs, tracker, research, llm = await _build_drivers(mcp_manager, config)

    mode_str = os.getenv("CODE_REVIEW_EXECUTION_MODE", "DETERMINISTIC").upper()
    mode = ExecutionMode(mode_str)

    agent = CodeReviewerAgent(
        vcs=vcs, tracker=tracker, research=research, llm=llm, mode=mode,
        default_arch_page_id=config.confluence.architecture_doc_page_id
    )
    return PerformCodeReviewUseCase(agent=agent, tracker=tracker)