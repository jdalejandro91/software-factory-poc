import logging
from typing import Any

from software_factory_poc.core.application.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.core.application.agents.code_reviewer.prompt_templates.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.core.application.agents.common.agent_config import (
    CodeReviewerAgentConfig,
    ScaffolderAgentConfig,
)
from software_factory_poc.core.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewSkill,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType
from software_factory_poc.infrastructure.config.app_config import AppConfig
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

    Responsabilidad unica: wiring de infraestructura. Los agentes reciben solo Tools.
    """

    def __init__(self, app_config: AppConfig):
        self.app_config = app_config

    async def _build_drivers(self, mcp_manager: McpConnectionManager):
        """Factory interno que ensambla los 4 drivers MCP del Tooling Plane."""
        vcs = GitlabMcpClient(settings=self.app_config.gitlab)
        tracker = JiraMcpClient(settings=self.app_config.jira)
        docs = ConfluenceMcpClient(settings=self.app_config.confluence)
        brain = LiteLlmBrainAdapter(self.app_config.llm)

        return vcs, tracker, docs, brain

    def _build_tools(
        self,
        vcs: GitlabMcpClient,
        tracker: JiraMcpClient,
        docs: ConfluenceMcpClient,
        brain: LiteLlmBrainAdapter,
    ) -> dict[ToolType, BaseTool]:
        """Build the shared tools registry."""
        return {
            ToolType.VCS: vcs,
            ToolType.TRACKER: tracker,
            ToolType.DOCS: docs,
            ToolType.BRAIN: brain,
        }

    async def create_scaffolder_agent(self, mcp_manager: McpConnectionManager) -> ScaffolderAgent:
        """Ensambla el ScaffolderAgent inyectando los 4 drivers MCP + Skills."""
        vcs, tracker, docs, brain = await self._build_drivers(mcp_manager)
        tools = self._build_tools(vcs, tracker, docs, brain)

        skills: dict[SkillType, BaseSkill[Any, Any]] = {
            SkillType.GENERATE_SCAFFOLD_PLAN: GenerateScaffoldPlanSkill(
                brain=brain, prompt_builder=ScaffoldingPromptBuilder()
            ),
        }

        return ScaffolderAgent(
            config=ScaffolderAgentConfig(
                priority_models=self.app_config.llm.scaffolding_llm_model_priority,
            ),
            tools=tools,
            skills=skills,
        )

    async def create_code_reviewer_agent(
        self, mcp_manager: McpConnectionManager
    ) -> CodeReviewerAgent:
        """Ensambla el CodeReviewerAgent inyectando los 4 drivers MCP + Skills."""
        vcs, tracker, docs, brain = await self._build_drivers(mcp_manager)
        tools = self._build_tools(vcs, tracker, docs, brain)

        skills: dict[SkillType, BaseSkill[Any, Any]] = {
            SkillType.ANALYZE_CODE_REVIEW: AnalyzeCodeReviewSkill(
                brain=brain, prompt_builder=CodeReviewPromptBuilder()
            ),
        }

        return CodeReviewerAgent(
            config=CodeReviewerAgentConfig(
                priority_models=self.app_config.llm.code_review_llm_model_priority,
            ),
            tools=tools,
            skills=skills,
        )
