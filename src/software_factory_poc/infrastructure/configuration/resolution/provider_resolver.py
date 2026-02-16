import os
import logging

from software_factory_poc.infrastructure.configuration.app_config import AppConfig

from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.drivers.vcs.gitlab_mcp_adapter import GitlabMcpAdapter
from software_factory_poc.infrastructure.drivers.tracker.jira_mcp_adapter import JiraMcpAdapter
from software_factory_poc.infrastructure.drivers.research.confluence_mcp_adapter import ConfluenceMcpAdapter
from software_factory_poc.infrastructure.drivers.llms.llm_gateway_adapter import LlmGatewayAdapter

from software_factory_poc.infrastructure.drivers.tracker.mappers.jira_description_mapper import (
    JiraDescriptionMapper,
)
from software_factory_poc.infrastructure.drivers.llms.gateway.composite_gateway import CompositeLlmGateway

from software_factory_poc.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.application.agents import CodeReviewerAgent
from software_factory_poc.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import ScaffoldingPromptBuilder
from software_factory_poc.application.agents.code_reviewer.prompt_templates.code_review_prompt_builder import CodeReviewPromptBuilder

logger = logging.getLogger(__name__)


class McpConnectionManager:
    """Gestiona conexiones stdio a los servidores MCP."""

    async def get_session(self, server_name: str):
        pass


class ProviderResolver:
    """Ensambla el sistema inyectando adaptadores MCP y configuracion validada Pydantic.

    Responsabilidad unica: wiring de infraestructura. Los agentes reciben solo Ports.
    """

    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        self.redactor = RedactionService()

    async def _build_drivers(self, mcp_manager: McpConnectionManager):
        """Factory interno que ensambla los 4 drivers MCP del Tooling Plane."""
        # 1. VCS Driver (MCP GitLab)
        session_vcs = await mcp_manager.get_session("mcp_server_gitlab")
        project_id = os.getenv("GITLAB_PROJECT_ID", "default_project")
        vcs_driver = GitlabMcpAdapter(session_vcs, project_id, self.redactor)

        # 2. Tracker Driver (MCP Jira)
        session_jira = await mcp_manager.get_session("mcp_server_jira")
        tracker_driver = JiraMcpAdapter(
            mcp_session=session_jira,
            desc_mapper=JiraDescriptionMapper(),
            transition_in_review=self.app_config.jira.transition_in_review,
            redactor=self.redactor,
        )

        # 3. Research Driver (MCP Confluence)
        session_confluence = await mcp_manager.get_session("mcp_server_confluence")
        research_driver = ConfluenceMcpAdapter(
            mcp_session=session_confluence,
            redactor=self.redactor,
        )

        # 4. LLM Gateway (Composite — sin MCP, usa gateway propio)
        composite_gateway = CompositeLlmGateway(
            allowed_models=self.app_config.llm.allowed_models,
            openai_key=self.app_config.llm.openai_api_key.get_secret_value() if self.app_config.llm.openai_api_key else None,
            gemini_key=self.app_config.llm.gemini_api_key.get_secret_value() if self.app_config.llm.gemini_api_key else None,
            deepseek_key=self.app_config.llm.deepseek_api_key.get_secret_value() if self.app_config.llm.deepseek_api_key else None,
            anthropic_key=self.app_config.llm.anthropic_api_key.get_secret_value() if self.app_config.llm.anthropic_api_key else None,
        )
        llm_driver = LlmGatewayAdapter(gateway=composite_gateway)

        return vcs_driver, tracker_driver, research_driver, llm_driver

    async def create_scaffolder_agent(self, mcp_manager: McpConnectionManager) -> ScaffolderAgent:
        """Ensambla el ScaffolderAgent inyectando los 4 drivers MCP + PromptBuilder."""
        vcs, tracker, research, llm = await self._build_drivers(mcp_manager)

        return ScaffolderAgent(
            vcs=vcs,
            tracker=tracker,
            research=research,
            llm=llm,
            prompt_builder=ScaffoldingPromptBuilder(),
        )

    async def create_code_reviewer_agent(self, mcp_manager: McpConnectionManager) -> CodeReviewerAgent:
        """Ensambla el CodeReviewerAgent inyectando los 4 drivers MCP + PromptBuilder."""
        vcs, tracker, research, llm = await self._build_drivers(mcp_manager)

        return CodeReviewerAgent(
            vcs=vcs,
            tracker=tracker,
            research=research,
            llm=llm,
            prompt_builder=CodeReviewPromptBuilder(),
        )
