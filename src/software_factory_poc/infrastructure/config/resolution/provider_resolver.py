import logging

from software_factory_poc.core.application.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.core.application.agents.code_reviewer.config.code_reviewer_agent_di_config import (
    CodeReviewerAgentConfig,
)
from software_factory_poc.core.application.agents.code_reviewer.prompt_templates.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.core.application.agents.common.agent_structures import AgentPorts
from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.agents.scaffolder.config.scaffolder_agent_di_config import (
    ScaffolderAgentConfig,
)
from software_factory_poc.core.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewSkill,
)
from software_factory_poc.core.application.skills.review.fetch_review_diff_skill import (
    FetchReviewDiffSkill,
)
from software_factory_poc.core.application.skills.review.publish_code_review_skill import (
    PublishCodeReviewSkill,
)
from software_factory_poc.core.application.skills.review.validate_review_context_skill import (
    ValidateReviewContextSkill,
)
from software_factory_poc.core.application.skills.scaffold.apply_scaffold_delivery_skill import (
    ApplyScaffoldDeliverySkill,
)
from software_factory_poc.core.application.skills.scaffold.fetch_scaffold_context_skill import (
    FetchScaffoldContextSkill,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.application.skills.scaffold.idempotency_check_skill import (
    IdempotencyCheckSkill,
)
from software_factory_poc.core.application.skills.scaffold.report_success_skill import (
    ReportSuccessSkill,
)
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

    Responsabilidad unica: wiring de infraestructura. Los agentes reciben solo Ports.
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

    async def create_scaffolder_agent(self, mcp_manager: McpConnectionManager) -> ScaffolderAgent:
        """Ensambla el ScaffolderAgent inyectando los 4 drivers MCP + Skills + LoopRunner."""
        vcs, tracker, docs, brain = await self._build_drivers(mcp_manager)
        prompt_builder = ScaffoldingPromptBuilder()

        return ScaffolderAgent(
            config=ScaffolderAgentConfig(
                priority_models=self.app_config.llm.scaffolding_llm_model_priority,
            ),
            ports=AgentPorts(vcs=vcs, tracker=tracker, docs=docs, brain=brain),
            idempotency_check=IdempotencyCheckSkill(vcs=vcs, tracker=tracker),
            fetch_context=FetchScaffoldContextSkill(docs=docs),
            generate_plan=GenerateScaffoldPlanSkill(brain=brain, prompt_builder=prompt_builder),
            apply_delivery=ApplyScaffoldDeliverySkill(vcs=vcs),
            report_success=ReportSuccessSkill(tracker=tracker),
            loop_runner=AgenticLoopRunner(brain=brain, policy=ToolSafetyPolicy()),
        )

    async def create_code_reviewer_agent(
        self, mcp_manager: McpConnectionManager
    ) -> CodeReviewerAgent:
        """Ensambla el CodeReviewerAgent inyectando los 4 drivers MCP + Skills + LoopRunner."""
        vcs, tracker, docs, brain = await self._build_drivers(mcp_manager)
        prompt_builder = CodeReviewPromptBuilder()

        return CodeReviewerAgent(
            config=CodeReviewerAgentConfig(
                priority_models=self.app_config.llm.code_review_llm_model_priority,
            ),
            ports=AgentPorts(vcs=vcs, tracker=tracker, docs=docs, brain=brain),
            validate_context=ValidateReviewContextSkill(tracker=tracker),
            fetch_diff=FetchReviewDiffSkill(vcs=vcs, docs=docs),
            analyze=AnalyzeCodeReviewSkill(brain=brain, prompt_builder=prompt_builder),
            publish=PublishCodeReviewSkill(vcs=vcs, tracker=tracker),
            loop_runner=AgenticLoopRunner(brain=brain, policy=ToolSafetyPolicy()),
        )
