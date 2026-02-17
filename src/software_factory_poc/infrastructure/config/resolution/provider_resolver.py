import logging

from software_factory_poc.core.application.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.core.application.agents.code_reviewer.prompt_templates.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.core.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.infrastructure.config.app_config import AppConfig
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.tools.docs.confluence.confluence_mcp_client import (
    ConfluenceMcpClient,
)
from software_factory_poc.infrastructure.tools.llm.litellm_brain_adapter import LiteLlmBrainAdapter
from software_factory_poc.infrastructure.tools.tracker.jira.jira_mcp_client import JiraMcpClient
from software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_mcp_client import GitlabMcpClient

logger = logging.getLogger(__name__)


class McpConnectionManager:
    """Gestiona conexiones stdio a los servidores MCP."""

    async def get_session(self, _server_name: str):
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
        # 1. VCS (MCP GitLab — self-managed stdio connection)
        vcs = GitlabMcpClient(settings=self.app_config.gitlab, redactor=self.redactor)

        # 2. Tracker (MCP Jira — self-managed stdio connection)
        tracker = JiraMcpClient(settings=self.app_config.jira, redactor=self.redactor)

        # 3. Docs (MCP Confluence — self-managed stdio connection)
        docs = ConfluenceMcpClient(settings=self.app_config.confluence, redactor=self.redactor)

        # 4. Brain (LiteLLM)
        brain = LiteLlmBrainAdapter(self.app_config.llm)

        return vcs, tracker, docs, brain

    async def create_scaffolder_agent(self, mcp_manager: McpConnectionManager) -> ScaffolderAgent:
        """Ensambla el ScaffolderAgent inyectando los 4 drivers MCP + PromptBuilder."""
        vcs, tracker, docs, brain = await self._build_drivers(mcp_manager)

        return ScaffolderAgent(
            vcs=vcs,
            tracker=tracker,
            research=docs,
            brain=brain,
            prompt_builder=ScaffoldingPromptBuilder(),
        )

    async def create_code_reviewer_agent(
        self, mcp_manager: McpConnectionManager
    ) -> CodeReviewerAgent:
        """Ensambla el CodeReviewerAgent inyectando los 4 drivers MCP + PromptBuilder."""
        vcs, tracker, docs, brain = await self._build_drivers(mcp_manager)

        return CodeReviewerAgent(
            vcs=vcs,
            tracker=tracker,
            research=docs,
            brain=brain,
            prompt_builder=CodeReviewPromptBuilder(),
        )
